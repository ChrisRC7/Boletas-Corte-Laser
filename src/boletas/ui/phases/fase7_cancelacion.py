"""Fase 7: Cancelación.

Registra el motivo de cancelación en un cuadro de texto multilínea, sincronizado
con la variable `F7_Motivo_Cancelacion`.
"""

from .base import PhaseSection


class Phase7Cancelacion(PhaseSection):
    index = 6

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.text_area(row, 'F7_Motivo_Cancelacion', "MOTIVO DE\nCANCELACIÓN")
