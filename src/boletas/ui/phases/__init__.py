"""Registro de las fases del formulario de boletas.

Cada fase vive en su propio archivo. Para **añadir** una fase nueva:
    1. Crea un archivo `faseN_nombre.py` con una subclase de `PhaseSection`.
    2. Impórtala y añádela a `PHASE_CLASSES` (en el orden deseado).
    3. Añade su fase a `config.FASES`, sus campos obligatorios a
       `config.REQUIRED_FIELDS` y el color de su barra a `theme.PHASE_COLORS`.
No hace falta tocar el código de las demás fases ni el de `BoletaForm`.
"""

from .fase1_recepcion import Phase1Recepcion
from .fase2_revision import Phase2Revision
from .fase3_impresion import Phase3Impresion
from .fase4_despegado import Phase4Despegado
from .fase5_entrega import Phase5Entrega
from .fase6_reimpresion import Phase6Reimpresion
from .fase7_cancelada import Phase7Cancelada

# Orden de las secciones (coincide con el orden de config.FASES).
PHASE_CLASSES = [
    Phase1Recepcion,
    Phase2Revision,
    Phase3Impresion,
    Phase4Despegado,
    Phase5Entrega,
    Phase6Reimpresion,
    Phase7Cancelada,
]


def build_phases(form):
    """Instancia todas las fases para una BoletaForm dada."""
    return [phase_cls(form) for phase_cls in PHASE_CLASSES]
