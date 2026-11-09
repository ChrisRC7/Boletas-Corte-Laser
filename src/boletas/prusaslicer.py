"""Integración con PrusaSlicer: gramos de material y tiempo de impresión.

No tiene interfaz. Ofrece una sola entrada, `leer_trabajo(ruta)`, que acepta:

- **G-code exportado por PrusaSlicer** (`.gcode` de texto o `.bgcode` binario,
  el de las MK4/Core One): se leen los datos que PrusaSlicer escribe al final
  del archivo (o en los bloques de metadatos del binario). Es instantáneo y da
  exactamente lo mismo que muestra el slicer.
- **Proyecto `.3mf` de PrusaSlicer**: se slicea con `prusa-slicer-console.exe`
  usando la configuración guardada en el propio proyecto y se lee el G-code.
- **Modelo `.stl` / `.obj`**: igual, pero hace falta un perfil exportado desde
  PrusaSlicer (Archivo > Exportar > Exportar configuración) en
  `config.PRUSASLICER_PERFIL`.

Si el perfil no tiene densidad de filamento, PrusaSlicer reporta 0 g; en ese
caso los gramos se estiman como volumen (cm³) × densidad
(`filament_density` del G-code o `config.DENSIDAD_FILAMENTO`).
"""

import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from dataclasses import dataclass

from . import config

EXTENSIONES_GCODE = ('.gcode', '.bgcode')
EXTENSIONES_PROYECTO = ('.3mf',)
EXTENSIONES_MODELO = ('.stl', '.obj')
EXTENSIONES = EXTENSIONES_GCODE + EXTENSIONES_PROYECTO + EXTENSIONES_MODELO

# Rutas habituales del ejecutable de consola en Windows.
_RUTAS_CONOCIDAS = [
    os.path.join(os.environ.get(variable, ''), 'Prusa3D', 'PrusaSlicer', 'prusa-slicer-console.exe')
    for variable in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)')
]

# Claves que escribe PrusaSlicer (en el texto van como "; clave = valor").
CLAVE_TIEMPO = 'estimated printing time (normal mode)'
CLAVES_GRAMOS = ('total filament used [g]', 'filament used [g]')
CLAVE_VOLUMEN = 'filament used [cm3]'
CLAVE_DENSIDAD = 'filament_density'
_CLAVES = (CLAVE_TIEMPO, CLAVE_VOLUMEN, CLAVE_DENSIDAD) + CLAVES_GRAMOS

# Bytes del final de un G-code de texto donde suelen estar los datos.
_BYTES_FINALES = 512 * 1024


class ErrorSlicer(Exception):
    """El archivo no se pudo leer o slicear. El mensaje es apto para mostrarse."""


@dataclass
class ResultadoSlicer:
    gramos: float
    minutos: int
    gramos_estimados: bool = False   # True si salieron de volumen × densidad
    archivo: str = ''

    @property
    def tiempo_hhmm(self):
        return f"{self.minutos // 60}:{self.minutos % 60:02d}"

    @property
    def gramos_texto(self):
        return f"{self.gramos:.2f}"


# --- Entrada principal ------------------------------------------------------
def leer_trabajo(ruta):
    """Gramos y tiempo de un G-code, proyecto 3MF o modelo. Lanza ErrorSlicer."""
    extension = os.path.splitext(ruta)[1].lower()
    if not os.path.isfile(ruta):
        raise ErrorSlicer(f"No existe el archivo:\n{ruta}")
    if extension in EXTENSIONES_GCODE:
        return leer_gcode(ruta)
    if extension in EXTENSIONES_PROYECTO + EXTENSIONES_MODELO:
        return slicear(ruta)
    raise ErrorSlicer(f"Tipo de archivo no soportado: {extension or 'sin extensión'}.")


def leer_gcode(ruta):
    """Lee los datos de un G-code de PrusaSlicer (texto o binario)."""
    try:
        with open(ruta, 'rb') as archivo:
            binario = archivo.read(4) == b'GCDE'
        metadatos = _metadatos_binario(ruta) if binario else _metadatos_texto(ruta)
    except OSError as error:
        raise ErrorSlicer(f"No se pudo leer el archivo: {error}") from None
    return _resultado(metadatos, ruta)


# --- Slicear con la consola de PrusaSlicer -----------------------------------
def ejecutable():
    """Ruta de prusa-slicer-console.exe, o None si no se encuentra."""
    configurada = str(config.PRUSASLICER_RUTA or '').strip()
    candidatos = [configurada] if configurada else []
    candidatos += _RUTAS_CONOCIDAS
    candidatos += [shutil.which('prusa-slicer-console') or '', shutil.which('prusa-slicer') or '']
    return next((c for c in candidatos if c and os.path.isfile(c)), None)


def slicear(ruta):
    """Slicea un 3MF/STL con PrusaSlicer en una carpeta temporal y lee el G-code."""
    programa = ejecutable()
    if not programa:
        raise ErrorSlicer("No se encontró PrusaSlicer. Indique la ruta de prusa-slicer-console.exe "
                          "en Configuración, o exporte el G-code desde PrusaSlicer y ábralo aquí.")

    comando = [programa, '--export-gcode', '--loglevel', '1']
    if not ruta.lower().endswith(EXTENSIONES_PROYECTO):
        perfil = str(config.PRUSASLICER_PERFIL or '').strip()
        if not perfil or not os.path.isfile(perfil):
            raise ErrorSlicer("Para un STL/OBJ hace falta un perfil de PrusaSlicer (.ini) en "
                              "Configuración.\nTambién puede abrir el modelo en PrusaSlicer, "
                              "exportar el G-code y abrir ese archivo aquí.")
        comando += ['--load', perfil]

    with tempfile.TemporaryDirectory(prefix='boleta_slicer_') as carpeta:
        salida = os.path.join(carpeta, 'trabajo.gcode')
        comando += ['--output', salida, ruta]
        try:
            proceso = subprocess.run(
                comando, capture_output=True, text=True, errors='replace',
                timeout=config.PRUSASLICER_TIMEOUT_SEGUNDOS,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        except subprocess.TimeoutExpired:
            raise ErrorSlicer(f"PrusaSlicer tardó más de {config.PRUSASLICER_TIMEOUT_SEGUNDOS} s "
                              "en slicear el modelo.") from None
        except OSError as error:
            raise ErrorSlicer(f"No se pudo ejecutar PrusaSlicer: {error}") from None

        if not os.path.isfile(salida):
            detalle = _ultimas_lineas(proceso.stdout + '\n' + proceso.stderr)
            raise ErrorSlicer("PrusaSlicer no pudo slicear el modelo."
                              + (f"\n\n{detalle}" if detalle else ''))
        resultado = leer_gcode(salida)
    resultado.archivo = ruta
    return resultado


def _ultimas_lineas(texto, cantidad=4):
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    return "\n".join(lineas[-cantidad:])


# --- Lectura de metadatos ------------------------------------------------------
def _metadatos_texto(ruta):
    """Busca '; clave = valor' primero al final del archivo y, si falta algo, en todo."""
    tamano = os.path.getsize(ruta)
    with open(ruta, 'rb') as archivo:
        archivo.seek(max(0, tamano - _BYTES_FINALES))
        metadatos = _comentarios(archivo.read().decode('utf-8', errors='replace').splitlines())
        if CLAVE_TIEMPO not in metadatos and tamano > _BYTES_FINALES:
            archivo.seek(0)
            lineas = (linea.decode('utf-8', errors='replace') for linea in archivo
                      if linea.startswith(b';'))
            metadatos = _comentarios(lineas)
    return metadatos


def _comentarios(lineas):
    metadatos = {}
    for linea in lineas:
        if linea.startswith(';') and '=' in linea:
            clave, _, valor = linea[1:].partition('=')
            clave = clave.strip()
            if clave in _CLAVES:
                metadatos[clave] = valor.strip()
    return metadatos


def _metadatos_binario(ruta):
    """Lee los bloques de metadatos de un .bgcode (formato libbgcode de Prusa).

    Cabecera: 'GCDE', versión (u32), tipo de checksum (u16). Cada bloque:
    tipo (u16), compresión (u16), tamaño sin comprimir (u32), tamaño
    comprimido (u32, solo si hay compresión), parámetros (6 bytes en
    miniaturas, 2 en el resto), datos y checksum (4 bytes si es CRC32).
    Los metadatos son texto 'clave=valor' por línea; se detiene al llegar al
    primer bloque de G-code (tipo 1).
    """
    metadatos = {}
    with open(ruta, 'rb') as archivo:
        cabecera = archivo.read(10)
        if len(cabecera) < 10:
            raise ErrorSlicer("El archivo .bgcode está incompleto.")
        _version, checksum = struct.unpack('<IH', cabecera[4:])
        tamano_checksum = 4 if checksum == 1 else 0
        while True:
            encabezado = archivo.read(8)
            if len(encabezado) < 8:
                break
            tipo, compresion, sin_comprimir = struct.unpack('<HHI', encabezado)
            if tipo == 1:  # G-code: ya no hay más metadatos útiles
                break
            tamano = struct.unpack('<I', archivo.read(4))[0] if compresion else sin_comprimir
            archivo.seek(6 if tipo == 5 else 2, os.SEEK_CUR)
            datos = archivo.read(tamano)
            archivo.seek(tamano_checksum, os.SEEK_CUR)
            if tipo == 5:  # miniatura
                continue
            if compresion == 1:
                datos = zlib.decompress(datos)
            elif compresion != 0:
                continue  # heatshrink: PrusaSlicer no lo usa para metadatos
            for linea in datos.decode('utf-8', errors='replace').splitlines():
                clave, _, valor = linea.partition('=')
                if clave.strip() in _CLAVES:
                    metadatos.setdefault(clave.strip(), valor.strip())
    return metadatos


# --- Interpretación ------------------------------------------------------------
def _resultado(metadatos, ruta):
    if CLAVE_TIEMPO not in metadatos:
        raise ErrorSlicer("El archivo no tiene el tiempo estimado de PrusaSlicer. "
                          "¿Es un G-code exportado con PrusaSlicer?")
    minutos = minutos_desde_duracion(metadatos[CLAVE_TIEMPO])

    gramos = max((_suma(metadatos[c]) for c in CLAVES_GRAMOS if c in metadatos), default=0.0)
    estimados = False
    if gramos <= 0:
        volumen = _suma(metadatos.get(CLAVE_VOLUMEN, ''))
        if volumen <= 0:
            raise ErrorSlicer("El archivo no indica cuánto material se usa.")
        gramos = volumen * _densidad(metadatos.get(CLAVE_DENSIDAD, ''))
        estimados = True
    return ResultadoSlicer(gramos=round(gramos, 2), minutos=minutos,
                           gramos_estimados=estimados, archivo=ruta)


def minutos_desde_duracion(texto):
    """'1d 2h 3m 4s' -> 1564 (se redondea hacia arriba al minuto)."""
    segundos = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
    total = sum(int(n) * segundos[u] for n, u in re.findall(r'(\d+)\s*([dhms])', texto))
    return math.ceil(total / 60)


def _numeros(texto):
    return [float(n) for n in re.findall(r'\d+(?:\.\d+)?', str(texto))]


def _suma(texto):
    """'12.5, 3.1' (varios extrusores) -> 15.6."""
    return sum(_numeros(texto))


def _densidad(texto):
    return next((d for d in _numeros(texto) if d > 0), config.DENSIDAD_FILAMENTO)
