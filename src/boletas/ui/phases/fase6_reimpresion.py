"""Fase 6: Reimpresión.

Igual que la Revisión, registra material/tiempo y calcula su propio precio.
"""

from .base import PhaseSection
from ...services import PricingService


class Phase6Reimpresion(PhaseSection):
    index = 5

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.field(row, 0, 'F6_Uso_Material_g', "USO DE MATERIAL (g)")
        self.vars['F6_Uso_Material_g'].trace_add('write', self._calculate_price)
        self.field(row, 2, 'F6_Tiempo_Impresion_HHMM', "TIEMPO DE IMPRESIÓN", "HH:MM")

        row = self.new_row()
        self.field(row, 0, 'F6_Precio', "PRECIO (₡)", "Calculado automáticamente", state='readonly')
        self.field(row, 2, 'F6_Observaciones', "OBSERVACIONES")

    def _calculate_price(self, *args):
        self.vars['F6_Precio'].set(PricingService.calcular(self.vars['F6_Uso_Material_g'].get()))
