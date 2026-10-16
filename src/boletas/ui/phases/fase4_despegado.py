"""Fase 4: Despegado de Piezas."""

from .. import theme
from .base import PhaseSection, PAD_X, PAD_Y


class Phase4Despegado(PhaseSection):
    index = 3

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.field(row, 0, 'Observaciones_Despegado', "OBSERVACIONES", "Fecha - Hora - Observación", colspan=3)

        row = self.new_row()
        self.checkbox(frame, 'F4_Imprimio_Correctamente', "Se imprimió correctamente").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PAD_X, pady=PAD_Y)
        self.checkbox(frame, 'F4_Envio_Correo', "Envío de correo de notificación de finalización",
                      text_color=theme.ACCENT_RED).grid(row=row, column=2, columnspan=2, sticky="w", padx=PAD_X, pady=PAD_Y)
