"""Plantillas de los correos de notificación al usuario (sin interfaz).

Son los tres correos que el LAIMI envía a quien pidió la impresión, con el
mismo asunto y texto que se usaban a mano:

- ``autorizacion``: costo y solicitud de autorización (Fase 3, antes de imprimir).
- ``inicio``: la impresión comenzó y cuánto tardará (Fase 3).
- ``finalizacion``: la pieza está lista para retirar (Fase 4).

Cada plantilla recibe los valores del formulario (``{columna: valor}``) y
devuelve un ``Correo`` (destinatario, asunto y cuerpo HTML). `faltantes()`
dice qué datos hacen falta antes de poder armarlo. El envío está en
`outlook.py`; este módulo no sabe nada de Outlook ni de la UI.
"""

from dataclasses import dataclass
from datetime import datetime
from html import escape

from . import config
from .directorio_ad import normalizar_cuenta

AUTORIZACION = "autorizacion"
INICIO = "inicio"
FINALIZACION = "finalizacion"

FIRMA = "LAIMI - Servicio de Impresión 3D"

# Datos (columnas) que necesita cada correo, además de la cuenta y el archivo.
_DATOS_REQUERIDOS = {
    AUTORIZACION: ['Precio', 'Uso_Material_g', 'Tiempo_Impresion_HHMM'],
    INICIO: ['F3_Fecha', 'F3_Hora', 'Tiempo_Impresion_HHMM'],
    FINALIZACION: [],
}


@dataclass
class Correo:
    para: str
    asunto: str
    html: str


# --- API pública -------------------------------------------------------------
def faltantes(tipo, datos):
    """Nombres legibles de los datos vacíos que impiden armar el correo `tipo`."""
    claves = ['Cuenta', 'Nombre_Pieza', 'ID Boleta'] + _DATOS_REQUERIDOS[tipo]
    return [config.FIELD_NAMES.get(c, _NOMBRES_EXTRA.get(c, c)) for c in claves if not _valor(datos, c)]


def armar(tipo, datos):
    """Devuelve el `Correo` del `tipo` pedido con los datos de la boleta."""
    return _PLANTILLAS[tipo](datos)


def destinatario(datos):
    """Correo institucional del usuario: cuenta + dominio configurado."""
    cuenta = normalizar_cuenta(_valor(datos, 'Cuenta'))
    return f"{cuenta}{config.AD_DOMINIO_CORREO}" if cuenta else ""


# --- Plantillas ----------------------------------------------------------------
def _autorizacion(datos):
    archivo, boleta = _valor(datos, 'Nombre_Pieza'), _valor(datos, 'ID Boleta')
    filas = [
        ("Archivo", archivo),
        ("Precio", f"₡{_valor(datos, 'Precio')}"),
        ("Cantidad de material (gramos / ml)", f"{_valor(datos, 'Uso_Material_g')} g"),
        ("Tiempo estimado de impresión (HH:MM)", _hhmm(_valor(datos, 'Tiempo_Impresion_HHMM'))),
        ("Boleta No.", boleta),
    ]
    tabla = "".join(
        f'<tr><td style="{_CELDA}">{escape(k)}</td><td style="{_CELDA}"><b>{escape(v)}</b></td></tr>'
        for k, v in filas
    )
    cuerpo = (
        f'<table style="border-collapse:collapse;min-width:520px">'
        f'<tr><td colspan="2" style="{_CELDA}"><b>INFORMACIÓN DEL TRABAJO</b></td></tr>{tabla}</table>'
        "<p>Si está de acuerdo con el precio de la pieza, por favor responda a este correo lo antes "
        "posible y cambie el asunto por el siguiente texto:</p>"
        f"<p><b>AUTORIZO LA IMPRESIÓN DE LA PIEZA {escape(archivo)}</b></p>"
        "<p>Usted será notificado(a) nuevamente cuando se inicie la impresión de su trabajo y "
        "cuando el mismo ya esté listo para ser retirado. 😁🤞</p>"
    )
    asunto = f"Impresión 3D - COSTO y SOLICITUD DE AUTORIZACIÓN: {archivo} (BOLETA {boleta})"
    return Correo(destinatario(datos), asunto, _html(cuerpo))


def _inicio(datos):
    archivo, boleta = _valor(datos, 'Nombre_Pieza'), _valor(datos, 'ID Boleta')
    cuerpo = (
        f"<p>Su impresión 3D se colocó el <b>{escape(_dia_mes(_valor(datos, 'F3_Fecha')))}</b> "
        f"a las <b>{escape(_valor(datos, 'F3_Hora'))}</b> y tardará aproximadamente "
        f"<b>{escape(duracion_en_texto(_valor(datos, 'Tiempo_Impresion_HHMM')))}</b> "
        "si no se presenta ningún problema durante la impresión.</p>"
        "<p>Usted recibirá otro correo cuando la pieza esté lista para ser retirada. 😉</p>"
    )
    asunto = f"Impresión 3D INICIADA: {archivo} (BOLETA {boleta})"
    return Correo(destinatario(datos), asunto, _html(cuerpo))


def _finalizacion(datos):
    archivo, boleta = _valor(datos, 'Nombre_Pieza'), _valor(datos, 'ID Boleta')
    cuerpo = (
        "<p>Su trabajo de impresión en 3D ha finalizado y puede pasar a retirarlo "
        "(recuerde presentar su carné). 😃</p>"
    )
    asunto = f"Impresión 3D finalizada: {archivo} (BOLETA {boleta})"
    return Correo(destinatario(datos), asunto, _html(cuerpo))


_PLANTILLAS = {AUTORIZACION: _autorizacion, INICIO: _inicio, FINALIZACION: _finalizacion}
_NOMBRES_EXTRA = {'ID Boleta': 'Número de boleta'}
_CELDA = "border:1px solid #999;padding:3px 8px"


# --- Formatos ------------------------------------------------------------------
def duracion_en_texto(hhmm):
    """'26:05' -> '1 día, 2 horas y 5 minutos' (omite las partes en cero)."""
    total = _minutos(hhmm)
    if total is None:
        return hhmm
    dias, resto = divmod(total, 24 * 60)
    horas, minutos = divmod(resto, 60)
    partes = [f"{n} {singular if n == 1 else plural}" for n, singular, plural in (
        (dias, "día", "días"), (horas, "hora", "horas"), (minutos, "minuto", "minutos")) if n]
    if not partes:
        return "0 minutos"
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def _minutos(hhmm):
    partes = str(hhmm or "").strip().split(":")
    if len(partes) != 2 or not all(p.strip().isdigit() for p in partes):
        return None
    return int(partes[0]) * 60 + int(partes[1])


def _hhmm(hhmm):
    total = _minutos(hhmm)
    return hhmm if total is None else f"{total // 60:02d}:{total % 60:02d}"


def _dia_mes(fecha):
    """'09/11/2026' -> '09/11'."""
    try:
        return datetime.strptime(fecha.strip(), config.FORMATO_FECHA).strftime("%d/%m")
    except ValueError:
        return fecha


def _valor(datos, clave):
    valor = datos.get(clave, "")
    return "" if valor is None or str(valor).lower() == "nan" else str(valor).strip()


def _html(cuerpo):
    return (
        '<html><body style="font-family:Calibri,Arial,sans-serif;font-size:11pt">'
        f"{cuerpo}<p>______________________<br>{escape(FIRMA)}</p></body></html>"
    )
