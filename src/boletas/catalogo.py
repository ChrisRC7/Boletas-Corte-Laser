"""Consultas sobre las opciones configurables (usos, colores, impresoras).

`config.py` guarda los datos tal cual (listas de diccionarios, editables desde
la ventana de Configuración). Este módulo responde las preguntas que hace el
resto del programa sobre esos datos, para que la UI y los servicios no tengan
que conocer su forma interna. Siempre lee `config` en el momento de la llamada,
así los cambios hechos desde la Configuración se ven sin reiniciar.
"""

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
    """Diccionario uso -> prioridad (para ordenar con pandas)."""
    return {uso["nombre"]: uso["prioridad"] for uso in config.USOS}


# --- Colores de filamento ---------------------------------------------------
def colores_disponibles(material):
    """Colores activos de un material. Lista vacía = el color se escribe a mano."""
    return [c["color"] for c in config.COLORES_POR_MATERIAL.get(material, []) if c.get("disponible", True)]


def material_tiene_colores(material):
    """True si el material tiene colores configurados (aunque estén agotados)."""
    return bool(config.COLORES_POR_MATERIAL.get(material))


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
