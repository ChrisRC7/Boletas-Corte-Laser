"""Abre correos como borrador en el Outlook de la PC (integración externa).

Usa el objeto COM `Outlook.Application` de Outlook clásico a través de
PowerShell, igual que `directorio_ad.py` consulta el AD: no hace falta
instalar librerías y funciona dentro del `.exe`. El correo se abre en una
ventana de Outlook ya lleno; **nunca se envía solo**: el operador lo revisa y
pulsa «Enviar».

Destinatario, asunto y cuerpo llegan al script por variables de entorno (nunca
se interpolan en el código). Si Outlook no está instalado, es el "Outlook
nuevo" (que no admite COM) o falla, se lanza `OutlookError` con el motivo.
"""

import os
import subprocess
import sys

_SCRIPT_BORRADOR = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$outlook = New-Object -ComObject Outlook.Application
$correo = $outlook.CreateItem(0)
$correo.To = $env:BOLETAS_CORREO_PARA
$correo.Subject = $env:BOLETAS_CORREO_ASUNTO
$correo.HTMLBody = $env:BOLETAS_CORREO_HTML
$correo.Display($false)
"""

TIMEOUT_SEGUNDOS = 120  # Abrir Outlook en frío puede tardar más de un minuto.


class OutlookError(Exception):
    """No se pudo abrir el borrador en Outlook."""


def abrir_borrador(correo):
    """Abre en Outlook un correo nuevo con `correo.para`, `.asunto` y `.html`."""
    if sys.platform != "win32":
        raise OutlookError("Outlook solo está disponible en Windows.")
    env = dict(os.environ, BOLETAS_CORREO_PARA=correo.para,
               BOLETAS_CORREO_ASUNTO=correo.asunto, BOLETAS_CORREO_HTML=correo.html)
    try:
        resultado = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_BORRADOR],
            capture_output=True, timeout=TIMEOUT_SEGUNDOS, env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        raise OutlookError(
            "Outlook no respondió a tiempo. Si se estaba abriendo, espere a que "
            "termine de cargar y vuelva a pulsar el botón.") from None
    except OSError as error:
        raise OutlookError(f"No se pudo ejecutar PowerShell: {error}") from None
    if resultado.returncode != 0:
        detalle = resultado.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise OutlookError(
            "No se pudo abrir Outlook. Verifique que Outlook clásico esté instalado "
            "y con la cuenta configurada.\n\n" + (detalle[0] if detalle else "")
        )
