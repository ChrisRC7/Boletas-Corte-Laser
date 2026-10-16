"""Fase 5: Entrega de Piezas."""

from .. import theme
from .base import PhaseSection, PAD_X, PAD_Y


class Phase5Entrega(PhaseSection):
    index = 4

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.checkbox(frame, 'Verificacion_Cobro', "Verificación del cobro", text_color=theme.ACCENT_RED).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PAD_X, pady=PAD_Y)
        self.checkbox(frame, 'Recibido_Conforme', "Recibido conforme").grid(
            row=row, column=2, columnspan=2, sticky="w", padx=PAD_X, pady=PAD_Y)
