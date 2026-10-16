"""Lógica de negocio reutilizable, independiente de la interfaz gráfica.

Separar estos cálculos de los widgets permite probarlos por separado y reusarlos
(por ejemplo, el precio se calcula igual en la fase de Revisión y en la de
Reimpresión).
"""

from . import config


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
