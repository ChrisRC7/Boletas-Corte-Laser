"""Lectura y normalización de fechas y horas escritas a mano (sin interfaz).

Las boletas guardan la fecha y la hora como texto con `config.FORMATO_FECHA`
("dd/mm/aaaa") y `config.FORMATO_HORA` ("hh:mm AM/PM"). Los operadores, sin
embargo, escriben variantes ("1/2/2026", "10:30 p.m.", "14:30"). Este módulo
las lleva al formato canónico para que el resto del programa (p. ej. el
planificador) siempre las pueda leer.
"""

import re
from datetime import datetime

from . import config

# hh:mm con am/pm opcional en sus variantes: "am", "a.m.", "a. m.", "PM"...
_PATRON_HORA = re.compile(r"(\d{1,2}):(\d{2})\s*(?:([aApP])\.?\s*[mM]?\.?)?")


def normalizar_fecha(texto):
    """'1/2/2026' -> '01/02/2026'. Devuelve el texto tal cual si no es una fecha válida."""
    texto = str(texto or "").strip()
    try:
        return datetime.strptime(texto, config.FORMATO_FECHA).strftime(config.FORMATO_FECHA)
    except ValueError:
        return texto


def normalizar_hora(texto):
    """'10:30 p.m.' -> '10:30 PM'; '14:30' -> '02:30 PM' (sin am/pm se toma como reloj de 24 h).

    Devuelve el texto tal cual si no es una hora válida.
    """
    texto = str(texto or "").strip()
    coincidencia = _PATRON_HORA.fullmatch(texto)
    if not coincidencia:
        return texto
    horas, minutos, sufijo = int(coincidencia.group(1)), int(coincidencia.group(2)), coincidencia.group(3)
    if minutos > 59:
        return texto
    if sufijo:
        if not 1 <= horas <= 12:
            return texto
        if horas == 12:
            horas = 0
        if sufijo.lower() == "p":
            horas += 12
    elif horas > 23:
        return texto
    return datetime(2000, 1, 1, horas, minutos).strftime(config.FORMATO_HORA)


def fecha_valida(texto):
    try:
        datetime.strptime(str(texto or "").strip(), config.FORMATO_FECHA)
        return True
    except ValueError:
        return False


def hora_valida(texto):
    try:
        datetime.strptime(normalizar_hora(texto), config.FORMATO_HORA)
        return True
    except ValueError:
        return False


def leer_fecha_hora(fecha, hora):
    """datetime de una fecha y hora de boleta; solo la fecha si la hora no se entiende; None si no hay fecha."""
    try:
        dia = datetime.strptime(str(fecha or "").strip(), config.FORMATO_FECHA)
    except ValueError:
        return None
    try:
        momento = datetime.strptime(normalizar_hora(hora), config.FORMATO_HORA)
    except ValueError:
        return dia
    return dia.replace(hour=momento.hour, minute=momento.minute)
