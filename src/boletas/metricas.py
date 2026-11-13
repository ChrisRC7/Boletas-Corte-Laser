"""Métricas del servicio de impresión calculadas a partir de las boletas (sin interfaz).

`calcular(registros)` recibe las boletas tal como las entrega el repositorio
(lista de diccionarios de texto) y devuelve un `Resumen` con los totales y los
desgloses que muestra el reporte. No sabe nada de Excel: de eso se encarga
`reporte.py`.

Criterios:
- **Estado** de una boleta: «Cancelada» si tiene operador de Cancelación (o esa
  es su fase actual); «Entregada» si tiene operador en la última fase del
  avance normal (Entrega); si no, «En proceso».
- **Material, tiempo y monto** solo suman las boletas **no canceladas**.
- **Monto cobrado**: boletas entregadas con «Verificación del cobro» marcada.
- **Días hasta la entrega**: de la fecha de Recepción a la fecha de Entrega.
"""

import json
from collections import OrderedDict
from dataclasses import dataclass, field

from . import config
from .fechas import leer_fecha_hora
from .planificador import minutos_desde_texto
from .services import PhaseDetector, PricingService

ENTREGADA = "Entregada"
EN_PROCESO = "En proceso"
CANCELADA = "Cancelada"

SIN_DATO = "(sin indicar)"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# --- Modelo -----------------------------------------------------------------
@dataclass
class Boleta:
    """Una boleta con sus valores ya interpretados (números, fechas, estado)."""
    datos: dict
    numero: int
    fase: str
    estado: str
    gramos: float
    minutos: int
    monto: float
    recibida: object      # datetime o None
    entregada: object     # datetime o None
    fallos: list

    @property
    def cuenta_para_totales(self):
        return self.estado != CANCELADA

    def texto(self, columna):
        return str(self.datos.get(columna, '') or '').strip()


@dataclass
class Resumen:
    boletas: list = field(default_factory=list)
    total: int = 0
    entregadas: int = 0
    en_proceso: int = 0
    canceladas: int = 0
    gramos: float = 0.0
    minutos: int = 0
    monto: float = 0.0
    monto_cobrado: float = 0.0
    usuarios_distintos: int = 0
    boletas_con_fallos: int = 0
    total_fallos: int = 0
    dias_entrega_promedio: object = None   # float o None si no hay entregas con fechas
    desde: object = None                   # datetime de la primera recepción
    hasta: object = None
    # Desgloses: listas de tuplas listas para tabular.
    por_fase: list = field(default_factory=list)        # (fase, boletas)
    por_uso: list = field(default_factory=list)         # (uso, boletas, gramos, monto)
    por_material: list = field(default_factory=list)    # (material, boletas, gramos)
    por_color: list = field(default_factory=list)       # (material y color, boletas, gramos)
    por_mes: list = field(default_factory=list)         # (mes, boletas, gramos, monto, horas)
    por_impresora: list = field(default_factory=list)   # (impresora, trabajos, horas, gramos)
    por_carrera: list = field(default_factory=list)     # (carrera, boletas, gramos)
    por_operador: list = field(default_factory=list)    # (operador, fases atendidas)
    usuarios: list = field(default_factory=list)        # dict por usuario
    fallos: list = field(default_factory=list)          # dict por fallo


# --- Lectura de una boleta ----------------------------------------------------
def _indice_entrega():
    """Índice de la última fase del avance normal (la Entrega)."""
    return max(i for i, fase in enumerate(config.FASES) if fase not in config.FASES_SIN_ORDEN)


def _numero(texto):
    """'1250.00' o '1250,5' -> float; 0.0 si no es un número."""
    return PricingService.gramos(texto) or 0.0


def _minutos(texto):
    try:
        return minutos_desde_texto(texto) or 0
    except (OverflowError, ValueError):
        return 0


def leer_fallos(texto):
    """Lista de fallos de la columna `Fallo_Lista` como diccionarios (los viejos eran solo texto)."""
    texto = str(texto or '').strip()
    if not texto:
        return []
    try:
        fallos = json.loads(texto)
    except json.JSONDecodeError:
        fallos = None
    if not isinstance(fallos, list):
        fallos = [texto]
    return [f if isinstance(f, dict) else {"descripcion": str(f)} for f in fallos]


def interpretar(registro):
    """Convierte un registro del repositorio en una `Boleta`."""
    def lleno(columna):
        return bool(str(registro.get(columna, '') or '').strip())

    fase = str(registro.get('Fase Actual', '') or '').strip()
    if fase not in config.FASES:
        fase = PhaseDetector.detectar_fase_actual(registro)
    cancelada = fase in config.FASES_SIN_ORDEN or any(
        lleno(f'F{i + 1}_Operador') for i, f in enumerate(config.FASES) if f in config.FASES_SIN_ORDEN)
    entrega = _indice_entrega() + 1
    if cancelada:
        estado = CANCELADA
    elif lleno(f'F{entrega}_Operador'):
        estado = ENTREGADA
    else:
        estado = EN_PROCESO

    return Boleta(
        datos=registro,
        numero=int(registro.get('ID Boleta') or 0),
        fase=fase,
        estado=estado,
        gramos=_numero(registro.get('Uso_Material_g')),
        minutos=_minutos(registro.get('Tiempo_Impresion_HHMM')),
        monto=_numero(registro.get('Precio')),
        recibida=leer_fecha_hora(registro.get('F1_Fecha', ''), registro.get('F1_Hora', '')),
        entregada=(leer_fecha_hora(registro.get(f'F{entrega}_Fecha', ''), registro.get(f'F{entrega}_Hora', ''))
                   if estado == ENTREGADA else None),
        fallos=leer_fallos(registro.get('Fallo_Lista')),
    )


def nombre_material(boleta):
    material = boleta.texto('Material')
    if material == config.MATERIAL_OTRO:
        material = boleta.texto('Material_Otro_Detalle') or config.MATERIAL_OTRO
    return material or SIN_DATO


# --- Cálculo ------------------------------------------------------------------
class _Grupos:
    """Acumula sumas por clave conservando el orden de aparición."""

    def __init__(self, columnas):
        self.columnas = columnas
        self.filas = OrderedDict()

    def sumar(self, clave, **valores):
        fila = self.filas.setdefault(clave, dict.fromkeys(self.columnas, 0))
        for columna, valor in valores.items():
            fila[columna] += valor

    def tuplas(self, orden=None, descendente=True):
        """[(clave, *valores)]; `orden` = columna por la que ordenar (None = orden de aparición)."""
        filas = [(clave,) + tuple(fila[c] for c in self.columnas) for clave, fila in self.filas.items()]
        if orden:
            posicion = self.columnas.index(orden) + 1
            filas.sort(key=lambda f: (-f[posicion] if descendente else f[posicion], str(f[0])))
        return filas


def calcular(registros):
    """Devuelve el `Resumen` de todas las boletas."""
    boletas = [interpretar(r) for r in registros]
    resumen = Resumen(boletas=boletas, total=len(boletas))

    fases = OrderedDict((fase, 0) for fase in config.FASES)
    usos = _Grupos(['boletas', 'gramos', 'monto'])
    materiales = _Grupos(['boletas', 'gramos'])
    colores = _Grupos(['boletas', 'gramos'])
    meses = _Grupos(['boletas', 'gramos', 'monto', 'horas'])
    impresoras = _Grupos(['trabajos', 'horas', 'gramos'])
    carreras = _Grupos(['boletas', 'gramos'])
    operadores = _Grupos(['fases'])
    usuarios = OrderedDict()
    dias_entrega = []

    for b in boletas:
        fases[b.fase] = fases.get(b.fase, 0) + 1
        resumen.entregadas += b.estado == ENTREGADA
        resumen.en_proceso += b.estado == EN_PROCESO
        resumen.canceladas += b.estado == CANCELADA
        # Lo que suma a los totales (las canceladas cuentan como boleta, no como material).
        gramos, minutos, monto = (b.gramos, b.minutos, b.monto) if b.cuenta_para_totales else (0, 0, 0)
        resumen.gramos += gramos
        resumen.minutos += minutos
        resumen.monto += monto
        if b.estado == ENTREGADA and b.texto('Verificacion_Cobro').lower() == 'true':
            resumen.monto_cobrado += monto

        usos.sumar(b.texto('Uso') or SIN_DATO, boletas=1, gramos=gramos, monto=monto)
        material = nombre_material(b)
        materiales.sumar(material, boletas=1, gramos=gramos)
        colores.sumar(f"{material} · {b.texto('Color_Filamento') or SIN_DATO}", boletas=1, gramos=gramos)
        carreras.sumar(b.texto('Carrera') or SIN_DATO, boletas=1, gramos=gramos)
        if b.texto('Impresora_Num'):
            impresoras.sumar(f"Impresora {b.texto('Impresora_Num')}", trabajos=1, horas=b.minutos / 60, gramos=b.gramos)
        for n in range(1, len(config.FASES) + 1):
            if b.texto(f'F{n}_Operador'):
                operadores.sumar(b.texto(f'F{n}_Operador'), fases=1)

        if b.recibida:
            resumen.desde = min(resumen.desde or b.recibida, b.recibida)
            resumen.hasta = max(resumen.hasta or b.recibida, b.recibida)
            meses.sumar((b.recibida.year, b.recibida.month), boletas=1, gramos=gramos, monto=monto,
                        horas=minutos / 60)
            if b.entregada and b.entregada >= b.recibida:
                dias_entrega.append((b.entregada - b.recibida).total_seconds() / 86400)

        if b.fallos:
            resumen.boletas_con_fallos += 1
            resumen.total_fallos += len(b.fallos)
            for fallo in b.fallos:
                resumen.fallos.append({
                    'boleta': b.numero, 'usuario': b.texto('Nombre_Usuario') or b.texto('Cuenta'),
                    'archivo': b.texto('Nombre_Pieza'), 'impresora': b.texto('Impresora_Num'),
                    'material': material,
                    'fecha': str(fallo.get('fecha', '')), 'hora': str(fallo.get('hora', '')),
                    'operador': str(fallo.get('operador', '')), 'descripcion': str(fallo.get('descripcion', '')),
                })

        clave = (b.texto('Carné') or b.texto('Cuenta')).lower()
        if clave:
            usuario = usuarios.setdefault(clave, {
                'carne': '', 'nombre': '', 'cuenta': '', 'carrera': '',
                'boletas': 0, 'entregadas': 0, 'canceladas': 0, 'gramos': 0.0, 'monto': 0.0, 'ultima': None})
            # Los datos personales son los de su boleta más reciente con ese dato.
            for campo, columna in (('carne', 'Carné'), ('nombre', 'Nombre_Usuario'),
                                   ('cuenta', 'Cuenta'), ('carrera', 'Carrera')):
                usuario[campo] = b.texto(columna) or usuario[campo]
            usuario['boletas'] += 1
            usuario['entregadas'] += b.estado == ENTREGADA
            usuario['canceladas'] += b.estado == CANCELADA
            usuario['gramos'] += gramos
            usuario['monto'] += monto
            if b.recibida and (usuario['ultima'] is None or b.recibida > usuario['ultima']):
                usuario['ultima'] = b.recibida

    resumen.usuarios_distintos = len(usuarios)
    resumen.dias_entrega_promedio = sum(dias_entrega) / len(dias_entrega) if dias_entrega else None
    resumen.por_fase = list(fases.items())
    resumen.por_uso = usos.tuplas(orden='boletas')
    resumen.por_material = materiales.tuplas(orden='gramos')
    resumen.por_color = colores.tuplas(orden='gramos')
    resumen.por_mes = [(_etiqueta_mes(f[0]),) + f[1:] for f in sorted(meses.tuplas(), key=lambda f: f[0])]
    resumen.por_impresora = sorted(impresoras.tuplas(), key=lambda f: _orden_natural(f[0]))
    resumen.por_carrera = carreras.tuplas(orden='boletas')
    resumen.por_operador = operadores.tuplas(orden='fases')
    resumen.usuarios = sorted(usuarios.values(), key=lambda u: (-u['boletas'], u['nombre']))
    return resumen


def _etiqueta_mes(clave):
    """(2026, 11) -> 'nov 2026'."""
    anio, mes = clave
    return f"{MESES[mes - 1]} {anio}"


def _orden_natural(texto):
    """'Impresora 10' después de 'Impresora 2'."""
    numero = ''.join(c for c in texto if c.isdigit())
    return (int(numero) if numero else 0, texto)
