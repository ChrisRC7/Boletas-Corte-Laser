"""Ajustes editables desde la interfaz, guardados en `configuracion.json`.

Permite cambiar opciones de `config.py` (precio, materiales, colores,
impresoras...) sin recompilar el `.exe`: la ventana de Configuración guarda los
valores en un JSON y, al arrancar, `cargar()` los aplica encima de los valores
por defecto de `config.py`. El resto del programa sigue leyendo `config.X`
como siempre.

El archivo se guarda en el directorio de trabajo de la aplicación. Si no
existe, o tiene un valor inválido, se usan los valores por defecto.
"""

import copy
import json
import os

from . import config

ARCHIVO_AJUSTES = "configuracion.json"

# Atributos de `config` que se pueden editar desde la interfaz.
EDITABLES = [
    'DB_FILE', 'EXCEL_FILE', 'AD_DOMINIO_CORREO', 'AD_TIMEOUT_SEGUNDOS',
    'PRECIO_POR_GRAMO', 'GRAMOS_POR_ROLLO',
    'PRUSASLICER_RUTA', 'PRUSASLICER_PERFIL', 'PRUSASLICER_TIMEOUT_SEGUNDOS', 'DENSIDAD_FILAMENTO',
    'USOS', 'PRIORIDAD_POR_DEFECTO',
    'MATERIAL_OPTIONS', 'COLORES_POR_MATERIAL',
    'RESOLUCION_OPTIONS', 'RESOLUCION_DEFAULT', 'RELLENO_OPTIONS', 'RELLENO_DEFAULT',
    'CONFIRMACION_OPTIONS',
    'USAR_TIPO_IMPRESORA', 'TIPOS_IMPRESORA', 'IMPRESORAS',
]

# Copia de los valores de config.py antes de aplicar el JSON (para "Restaurar").
_POR_DEFECTO = {nombre: copy.deepcopy(getattr(config, nombre)) for nombre in EDITABLES}


def valores_actuales():
    """Copia de los valores editables vigentes."""
    return {nombre: copy.deepcopy(getattr(config, nombre)) for nombre in EDITABLES}


def valores_por_defecto():
    """Copia de los valores definidos en config.py."""
    return copy.deepcopy(_POR_DEFECTO)


def _es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def _registros(valor, campos):
    """True si `valor` es una lista de diccionarios con los `campos` {clave: comprobación}.

    Una clave terminada en '?' es opcional.
    """
    if not isinstance(valor, list):
        return False
    for registro in valor:
        if not isinstance(registro, dict):
            return False
        for clave, comprobar in campos.items():
            opcional = clave.endswith('?')
            clave = clave.rstrip('?')
            if clave not in registro:
                if opcional:
                    continue
                return False
            if not comprobar(registro[clave]):
                return False
    return True


def _es_texto(valor):
    return isinstance(valor, str)


def _es_bool(valor):
    return isinstance(valor, bool)


# Estructura interna de los valores compuestos (lo que esperan `catalogo` y la UI).
_ESTRUCTURA = {
    'USOS': lambda v: _registros(v, {'nombre': _es_texto, 'prioridad': _es_entero, 'detalle?': _es_bool}),
    'IMPRESORAS': lambda v: _registros(v, {'numero': _es_entero, 'tipo': _es_texto, 'activa?': _es_bool}),
    'COLORES_POR_MATERIAL': lambda v: isinstance(v, dict) and all(
        isinstance(material, str) and _registros(colores, {'color': _es_texto, 'disponible?': _es_bool})
        for material, colores in v.items()),
    'MATERIAL_OPTIONS': lambda v: all(_es_texto(x) for x in v),
    'TIPOS_IMPRESORA': lambda v: all(_es_texto(x) for x in v),
    'CONFIRMACION_OPTIONS': lambda v: all(_es_texto(x) for x in v),
    'RESOLUCION_OPTIONS': lambda v: all(_es_numero(x) for x in v),
    'RELLENO_OPTIONS': lambda v: all(_es_numero(x) for x in v),
}


def _tipo_compatible(nombre, valor):
    """El valor del JSON debe tener el mismo tipo (y estructura) que el de config.py.

    int y float valen igual. En listas y diccionarios se revisa también lo que
    contienen (`_ESTRUCTURA`), para que un JSON editado a mano no tumbe la app.
    """
    defecto = _POR_DEFECTO[nombre]
    if isinstance(defecto, bool):
        return isinstance(valor, bool)
    if isinstance(defecto, (int, float)):
        return _es_numero(valor)
    if not isinstance(valor, type(defecto)):
        return False
    return _ESTRUCTURA.get(nombre, lambda _v: True)(valor)


def validar(valores):
    """Revisa que los valores sean coherentes entre sí. Devuelve una lista de errores."""
    errores = []

    def duplicados(lista):
        vistos, repetidos = set(), set()
        for elemento in lista:
            (repetidos if elemento in vistos else vistos).add(elemento)
        return repetidos

    if not str(valores.get('DB_FILE', '')).strip():
        errores.append("Falta el archivo de la base de datos.")
    if valores.get('PRECIO_POR_GRAMO', 0) < 0:
        errores.append("El precio por gramo no puede ser negativo.")
    for nombre, texto in (('GRAMOS_POR_ROLLO', "Los gramos por rollo"),
                          ('AD_TIMEOUT_SEGUNDOS', "El tiempo de espera del AD"),
                          ('PRUSASLICER_TIMEOUT_SEGUNDOS', "El tiempo de espera de PrusaSlicer"),
                          ('DENSIDAD_FILAMENTO', "La densidad del filamento")):
        if valores.get(nombre, 0) <= 0:
            errores.append(f"{texto} debe ser mayor que 0.")

    materiales = valores.get('MATERIAL_OPTIONS', [])
    if not materiales:
        errores.append("Debe haber al menos un material.")
    if duplicados(materiales):
        errores.append(f"Materiales repetidos: {', '.join(duplicados(materiales))}.")

    for lista, defecto, texto in (('RESOLUCION_OPTIONS', 'RESOLUCION_DEFAULT', "resolución"),
                                  ('RELLENO_OPTIONS', 'RELLENO_DEFAULT', "relleno")):
        opciones = valores.get(lista, [])
        if not opciones:
            errores.append(f"Debe haber al menos una opción de {texto}.")
        elif valores.get(defecto, '') not in [str(o) for o in opciones]:
            errores.append(f"La {texto} por defecto debe ser una de las opciones.")

    usos = valores.get('USOS', [])
    if not usos:
        errores.append("Debe haber al menos un tipo de uso.")
    if duplicados([u['nombre'] for u in usos]):
        errores.append("Hay tipos de uso con el mismo nombre.")

    impresoras = valores.get('IMPRESORAS', [])
    if not impresoras:
        errores.append("Debe haber al menos una impresora.")
    if duplicados([i['numero'] for i in impresoras]):
        errores.append("Hay impresoras con el mismo número.")
    tipos = valores.get('TIPOS_IMPRESORA', [])
    if valores.get('USAR_TIPO_IMPRESORA'):
        if not tipos:
            errores.append("Indique al menos un tipo de impresora (o desactive los tipos).")
        if config.TIPO_IMPRESORA_CUALQUIERA in tipos:
            errores.append(f"«{config.TIPO_IMPRESORA_CUALQUIERA}» está reservado; no lo use como tipo.")
        for impresora in impresoras:
            if impresora['tipo'] not in tipos:
                errores.append(f"La impresora {impresora['numero']} tiene un tipo que no está en la lista: "
                               f"«{impresora['tipo']}».")

    for material, colores in valores.get('COLORES_POR_MATERIAL', {}).items():
        if material not in materiales:
            errores.append(f"Hay colores para «{material}», que no está en la lista de materiales.")
        if duplicados([c['color'] for c in colores]):
            errores.append(f"Hay colores repetidos en {material}.")
    return errores


def aplicar(valores):
    """Aplica en `config` los valores válidos. Devuelve los nombres ignorados."""
    ignorados = []
    for nombre, valor in valores.items():
        if nombre in EDITABLES and _tipo_compatible(nombre, valor):
            setattr(config, nombre, copy.deepcopy(valor))
        else:
            ignorados.append(nombre)
    return ignorados


def cargar(ruta=ARCHIVO_AJUSTES):
    """Lee el JSON (si existe) y lo aplica. Devuelve un mensaje de error o None.

    Si el resultado no es coherente (`validar`), se vuelve a los valores por
    defecto en lugar de arrancar con una configuración que rompería la app.
    """
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, encoding="utf-8") as archivo:
            valores = json.load(archivo)
    except (OSError, ValueError) as error:
        return f"No se pudo leer '{ruta}': {error}. Se usan los valores por defecto."
    if not isinstance(valores, dict):
        return f"'{ruta}' no tiene el formato esperado. Se usan los valores por defecto."
    ignorados = aplicar(valores)
    errores = validar(valores_actuales())
    if errores:
        aplicar(valores_por_defecto())
        return (f"La configuración de '{ruta}' no es válida; se usan los valores por defecto.\n\n"
                + "\n".join(f"• {e}" for e in errores))
    if ignorados:
        return f"Se ignoraron valores inválidos en '{ruta}': {', '.join(ignorados)}."
    return None


def guardar(valores, ruta=ARCHIVO_AJUSTES):
    """Escribe los valores en el JSON y, si se escribió bien, los aplica. Lanza la excepción si falla.

    Se escribe en un temporal y luego se reemplaza el archivo: si falla, ni el
    JSON ni la configuración en memoria cambian.
    """
    validos = {nombre: valor for nombre, valor in valores.items()
               if nombre in EDITABLES and _tipo_compatible(nombre, valor)}
    completos = dict(valores_actuales(), **copy.deepcopy(validos))
    temporal = f"{ruta}.tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(completos, archivo, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)
    aplicar(validos)


def restaurar(ruta=ARCHIVO_AJUSTES):
    """Vuelve a los valores de config.py y borra el JSON."""
    aplicar(valores_por_defecto())
    if os.path.exists(ruta):
        os.remove(ruta)
