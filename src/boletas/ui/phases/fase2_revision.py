"""Fase 2: Revisión y Preparación.

Registra el material usado y el tiempo; calcula el precio automáticamente a
partir de los gramos.
"""

from .base import PhaseSection
from ...services import PricingService


class Phase2Revision(PhaseSection):
    index = 1

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.field(row, 0, 'Uso_Material_g', "USO DE MATERIAL (g)")
        self.vars['Uso_Material_g'].trace_add('write', self._calculate_price)
        self.field(row, 2, 'Tiempo_Impresion_HHMM', "TIEMPO DE IMPRESIÓN", "HH:MM")

        row = self.new_row()
        self.field(row, 0, 'Precio', "PRECIO (₡)", "Calculado automáticamente", state='readonly')

    def _calculate_price(self, *args):
        self.vars['Precio'].set(PricingService.calcular(self.vars['Uso_Material_g'].get()))
