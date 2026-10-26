"""Consulta de estudiantes en el Active Directory (SOLO LECTURA).

`DirectorioAD` es la única parte del programa que sabe hablar con el AD. Expone
exclusivamente métodos de búsqueda: nunca crea, modifica ni borra nada (ver la
regla 3 de CLAUDE.md).

La consulta se hace con `System.DirectoryServices.DirectorySearcher` de Windows
(a través de PowerShell), que usa las credenciales de la sesión del usuario que
abrió la aplicación. Así no hace falta instalar librerías ni guardar
contraseñas. Si la PC no está en el dominio o el AD no responde, las búsquedas
simplemente devuelven None.

Atributos del AD usados:
    sAMAccountName -> Cuenta (usuario del correo, sin @estudiantec.cr)
    employeeID     -> Carné
    name           -> Nombre completo
    mail           -> Correo institucional
    description    -> "SEDE - CARRERA" (se toma la parte de la carrera)
    telephoneNumber / mobile -> Teléfono (si el AD lo tiene)
"""

import json
import os
import re
import subprocess
import sys

from . import config

# Script de solo lectura: el filtro LDAP llega por variable de entorno (nunca se
# interpola en el código) y el resultado sale como JSON en UTF-8.
_SCRIPT_BUSQUEDA = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$atributos = 'name', 'mail', 'sAMAccountName', 'employeeID', 'description', 'telephoneNumber', 'mobile'
$buscador = New-Object System.DirectoryServices.DirectorySearcher
$buscador.Filter = $env:BOLETAS_AD_FILTRO
$buscador.SizeLimit = 1
foreach ($a in $atributos) { [void]$buscador.PropertiesToLoad.Add($a) }
$r = $buscador.FindOne()
if ($r) {
    $salida = @{}
    foreach ($a in $atributos) {
        $v = $r.Properties[$a]
        $salida[$a] = if ($v.Count) { [string]$v[0] } else { '' }
    }
    $salida | ConvertTo-Json -Compress
}
"""

_PATRON_CARNE = re.compile(r"^\d{6,12}$")
_PATRON_CUENTA = re.compile(r"^[a-z0-9._-]{2,64}$")


# --- Normalización de lo que escribe el operador ---------------------------
def es_carne(texto):
    """True si el texto tiene forma de carné (solo dígitos)."""
    return bool(_PATRON_CARNE.match((texto or "").strip()))


def es_correo(texto):
    """True si el texto es un correo (contiene '@')."""
    return "@" in (texto or "")


def es_cuenta(texto):
    """True si el texto tiene forma de usuario de correo (sin espacios ni '@')."""
    return bool(_PATRON_CUENTA.match((texto or "").strip().lower()))


def normalizar_cuenta(texto):
    """Devuelve solo el usuario del correo: 'Juan@estudiantec.cr' -> 'juan'."""
    return (texto or "").strip().split("@", 1)[0].strip().lower()


def _escapar_ldap(valor):
    """Escapa los caracteres especiales de un valor de filtro LDAP (RFC 4515)."""
    reemplazos = {"\\": r"\5c", "*": r"\2a", "(": r"\28", ")": r"\29", "\0": r"\00"}
    return "".join(reemplazos.get(c, c) for c in valor)


class DirectorioAD:
    """Búsquedas de estudiantes en el Active Directory. Solo lectura."""

    def __init__(self, timeout=config.AD_TIMEOUT_SEGUNDOS):
        self.timeout = timeout

    # --- API pública (solo consultas) -------------------------------------
    def buscar_por_carne(self, carne):
        carne = (carne or "").strip()
        if not es_carne(carne):
            return None
        return self._buscar(f"(employeeID={_escapar_ldap(carne)})")

    def buscar_por_cuenta(self, cuenta):
        cuenta = normalizar_cuenta(cuenta)
        if not es_cuenta(cuenta):
            return None
        return self._buscar(f"(sAMAccountName={_escapar_ldap(cuenta)})")

    def buscar(self, texto):
        """Busca por carné o por correo/cuenta según lo que se haya escrito."""
        if es_carne(texto):
            return self.buscar_por_carne(texto)
        return self.buscar_por_cuenta(texto)

    # --- Implementación ----------------------------------------------------
    def _buscar(self, filtro_atributo):
        """Ejecuta la búsqueda y devuelve el estudiante normalizado, o None."""
        filtro = f"(&(objectCategory=person)(objectClass=user){filtro_atributo})"
        env = dict(os.environ, BOLETAS_AD_FILTRO=filtro)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            resultado = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_BUSQUEDA],
                capture_output=True, timeout=self.timeout, env=env, creationflags=flags,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        salida = resultado.stdout.decode("utf-8", errors="replace").strip()
        if resultado.returncode != 0 or not salida:
            return None
        try:
            datos = json.loads(salida)
        except json.JSONDecodeError:
            return None
        return self._normalizar(datos)

    @staticmethod
    def _normalizar(datos):
        descripcion = datos.get("description", "")
        carrera = descripcion.split(" - ", 1)[1] if " - " in descripcion else descripcion
        return {
            "Nombre": datos.get("name", "").strip(),
            "Correo": datos.get("mail", "").strip().lower(),
            "Cuenta": datos.get("sAMAccountName", "").strip().lower(),
            "Carné": datos.get("employeeID", "").strip(),
            "Carrera": carrera.strip(),
            "Teléfono": (datos.get("telephoneNumber") or datos.get("mobile") or "").strip(),
        }
