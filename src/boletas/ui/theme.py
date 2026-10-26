"""Colores y fuentes de la interfaz (imitan la boleta impresa del LAIMI).

Único lugar con la apariencia visual: para cambiar el color de una fase o la
fuente basta con editar este archivo.
"""

import customtkinter as ctk

# Color de la barra de cada fase, en el mismo orden que config.FASES.
# Las fases 1-5 copian los colores de la boleta en papel.
PHASE_COLORS = [
    "#3E73B9",  # 1. Recepción             (azul)
    "#3D9BDA",  # 2. Revisión y Preparación (celeste)
    "#76B041",  # 3. Impresión             (verde)
    "#2E9B7B",  # 4. Despegado de Piezas   (verde azulado)
    "#B73A3A",  # 5. Entrega de Piezas     (rojo)
    "#E0892E",  # 6. Reimpresión           (naranja)
    "#7A7A7A",  # 7. Cancelación           (gris)
]

BG = "#E6E9EE"         # Fondo de la ventana (la "mesa" bajo la hoja)
PAPER = "#FFFFFF"      # Fondo de las secciones (la hoja)
TEXT = "#1F2937"       # Texto principal
HINT = "#6B7280"       # Texto de ayuda (gris)
ACCENT_RED = "#C0392B" # Textos en rojo de la boleta
SEPARATOR = "#D5DAE1"  # Líneas entre filas
SUCCESS = "#2E9B47"    # Botón de guardar / añadir
DANGER = "#C0392B"     # Botón de borrar
NEUTRAL = "#6B7280"    # Botones secundarios

FONT_FAMILY = "Segoe UI"


def setup():
    """Configura CustomTkinter (modo claro, como la hoja de papel)."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


def font(size=12, weight="normal"):
    """Fuente de la aplicación. Solo puede llamarse con la ventana ya creada."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def _mix(hex_color, other, amount):
    hex_color, other = hex_color.lstrip("#"), other.lstrip("#")
    channels = (
        round(int(hex_color[i:i + 2], 16) * (1 - amount) + int(other[i:i + 2], 16) * amount)
        for i in (0, 2, 4)
    )
    return "#" + "".join(f"{c:02X}" for c in channels)


def darken(hex_color, amount=0.18):
    """Color más oscuro (para el estado 'hover' de los botones)."""
    return _mix(hex_color, "#000000", amount)


def lighten(hex_color, amount=0.85):
    """Color más claro (tinte de fondo para las filas de la tabla)."""
    return _mix(hex_color, "#FFFFFF", amount)
