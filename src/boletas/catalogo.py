"""Consultas sobre las opciones configurables (usos, colores, impresoras, slicer).

`config.py` guarda los datos tal cual (listas de diccionarios, editables desde
la ventana de Configuración). Este módulo responde las preguntas que hace el
resto del programa sobre esos datos, para que la UI y los servicios no tengan
que conocer su forma interna. Siempre lee `config` en el momento de la llamada,
así los cambios hechos desde la Configuración se ven sin reiniciar.
"""

import re

from . import config


# --- Usos y prioridad -------------------------------------------------------
def opciones_uso():
    """Nombres de los tipos de uso, en el orden configurado."""
    return [uso["nombre"] for uso in config.USOS]


def usos_con_detalle():
    """Usos que habilitan el campo "Indicar" (curso/evento)."""
    return [uso["nombre"] for uso in config.USOS if uso.get("detalle")]


def prioridad_uso(nombre):
    """Prioridad de un uso (menor = más prioritario)."""
    for uso in config.USOS:
        if uso["nombre"] == nombre:
            return uso["prioridad"]
    return config.PRIORIDAD_POR_DEFECTO


def mapa_prioridades():
    """Diccionario uso -> prioridad."""
    return {uso["nombre"]: uso["prioridad"] for uso in config.USOS}


# --- Colores de filamento ---------------------------------------------------
def colores_disponibles(material):
    """Colores activos de un material. Lista vacía = el color se escribe a mano."""
    return [c["color"] for c in config.COLORES_POR_MATERIAL.get(material, []) if c.get("disponible", True)]


def material_tiene_colores(material):
    """True si el material tiene colores configurados (aunque estén agotados)."""
    return bool(config.COLORES_POR_MATERIAL.get(material))


# --- Parámetros que vienen de PrusaSlicer ------------------------------------
def material_desde_slicer(tipo):
    """Opción de material para el `filament_type` de PrusaSlicer: (material, detalle).

    'PLA' -> ('PLA', ''); 'FLEX' -> ('Flex (TPU)', '') porque coincide con una
    palabra de la opción; un tipo que no está en la lista -> ('Otro', 'PC').
    ('', '') si no hay tipo o no se puede representar.
    """
    tipo = str(tipo or '').strip()
    if not tipo:
        return '', ''
    buscado = tipo.upper()
    for opcion in config.MATERIAL_OPTIONS:
        if opcion == config.MATERIAL_OTRO:
            continue
        palabras = [p for p in re.split(r'[\s()/,+-]+', opcion.upper()) if p]
        if opcion.upper() == buscado or buscado in palabras:
            return opcion, ''
    if config.MATERIAL_OTRO in config.MATERIAL_OPTIONS:
        return config.MATERIAL_OTRO, tipo
    return '', ''


def opcion_cercana(opciones, valor):
    """La opción (como texto, igual que en los botones) más cercana a `valor`; '' si no hay."""
    if valor is None or not opciones:
        return ''
    return str(min(opciones, key=lambda opcion: abs(float(opcion) - float(valor))))


# --- Impresoras -------------------------------------------------------------
def impresoras_activas():
    """Impresoras activas, ordenadas por número."""
    return sorted((i for i in config.IMPRESORAS if i.get("activa", True)), key=lambda i: i["numero"])


def tipo_de_impresora(numero):
    """Tipo de la impresora con ese número (o '' si no existe)."""
    for impresora in config.IMPRESORAS:
        if str(impresora["numero"]) == str(numero).strip():
            return impresora.get("tipo", "")
    return ""


def existe_impresora(numero):
    """True si la impresora con ese número sigue en la Configuración (activa o no)."""
    return any(str(i["numero"]) == str(numero).strip() for i in config.IMPRESORAS)


def opciones_tipo_impresora():
    """Opciones del campo "Tipo de impresora" en la Revisión (tipos + 'Cualquiera')."""
    return list(config.TIPOS_IMPRESORA) + [config.TIPO_IMPRESORA_CUALQUIERA]


def tipo_compatible(tipo_requerido, tipo_impresora):
    """True si una impresora de `tipo_impresora` sirve para un trabajo que pide `tipo_requerido`."""
    if not config.USAR_TIPO_IMPRESORA:
        return True
    tipo_requerido = (tipo_requerido or "").strip()
    if not tipo_requerido or tipo_requerido == config.TIPO_IMPRESORA_CUALQUIERA:
        return True
    return tipo_requerido == tipo_impresora


# --- Validación -------------------------------------------------------------
def campos_obligatorios(indice_fase):
    """Campos obligatorios de una fase, según las opciones activas."""
    campos = list(config.REQUIRED_FIELDS.get(indice_fase, []))
    if not config.USAR_TIPO_IMPRESORA and 'Tipo_Impresora' in campos:
        campos.remove('Tipo_Impresora')
    return campos
