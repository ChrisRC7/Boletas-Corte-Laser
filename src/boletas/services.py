"""Lógica de negocio reutilizable, independiente de la interfaz gráfica.

Separar estos cálculos de los widgets permite probarlos por separado y reusarlos
(por ejemplo, el precio se calcula igual en la fase de Revisión y en la de
Reimpresión).
"""

from . import config
from .directorio_ad import es_carne, es_correo, es_cuenta, normalizar_cuenta


class PricingService:
    """Cálculo del precio a partir del material usado."""

    @staticmethod
    def calcular(gramos_texto):
        """Devuelve el precio formateado a partir de los gramos (como texto).

        Si el valor no es un número válido devuelve una cadena vacía.
        """
        try:
            gramos = float(gramos_texto)
            return f"{gramos * config.PRECIO_POR_GRAMO:.2f}"
        except (ValueError, TypeError):
            return ""


class PhaseDetector:
    """Determina en qué fase se encuentra una boleta según sus operadores."""

    @staticmethod
    def detectar_fase_actual(boleta_data):
        """Devuelve la fase más avanzada que tiene operador asignado.

        Se recorre de la última fase a la primera; la primera que tenga
        operador es la fase actual. Si ninguna lo tiene, es la fase inicial.
        """
        for indice in range(len(config.FASES) - 1, 0, -1):
            operador = boleta_data.get(f'F{indice + 1}_Operador')
            if operador and str(operador).strip():
                return config.FASES[indice]
        return config.FASES[0]



class UsuarioService:
    """Autocompletado de datos de estudiantes: primero el historial, luego el AD.

    - `datos_desde_historial` es instantáneo (lee las boletas cargadas).
    - `datos_desde_directorio` y `nombre_operador` consultan el AD y pueden
      tardar unos segundos: la UI debe llamarlos en segundo plano.
    """

    def __init__(self, repositorio, directorio):
        self.repositorio = repositorio
        self.directorio = directorio

    @staticmethod
    def identificar(texto):
        """Clasifica lo escrito: ('Carné', carne), ('Cuenta', usuario) o (None, texto).

        Una cuenta puede escribirse con o sin @estudiantec.cr. Un texto con
        espacios (p. ej. un nombre completo) no se considera cuenta.
        """
        texto = (texto or "").strip()
        if es_carne(texto):
            return 'Carné', texto
        if es_correo(texto) or es_cuenta(texto):
            return 'Cuenta', normalizar_cuenta(texto)
        return None, texto

    def datos_desde_historial(self, campo, valor):
        """Nombre, cuenta, carrera, carné y teléfono de la boleta más reciente del usuario."""
        return self.repositorio.buscar_datos_usuario(campo, valor)

    def datos_desde_directorio(self, campo, valor):
        """Nombre, cuenta, carrera, carné y teléfono del usuario según el AD."""
        if campo == 'Carné':
            usuario = self.directorio.buscar_por_carne(valor)
        else:
            usuario = self.directorio.buscar_por_cuenta(valor)
        if not usuario:
            return None
        usuario = dict(usuario, Nombre_Usuario=usuario.get("Nombre", ""))
        return {campo: usuario[campo] for campo in config.CAMPOS_DATOS_USUARIO if usuario.get(campo)}

    def nombre_operador(self, texto):
        """Nombre completo para un correo, cuenta o carné escrito como operador (o None)."""
        campo, valor = self.identificar(texto)
        if campo is None:
            return None
        usuario = self.directorio.buscar(valor)
        return usuario["Nombre"] if usuario and usuario.get("Nombre") else None
