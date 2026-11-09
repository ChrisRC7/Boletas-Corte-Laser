"""Fase 6: Cancelación.

Registra el motivo de cancelación en un cuadro de texto multilínea, sincronizado
con la variable `F6_Motivo_Cancelacion`.
"""

from .base import PhaseSection


class Phase6Cancelacion(PhaseSection):
    index = 5

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.text_area(row, 'F6_Motivo_Cancelacion', "MOTIVO DE\nCANCELACIÓN")
