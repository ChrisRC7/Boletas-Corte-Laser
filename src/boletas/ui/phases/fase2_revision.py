"""Fase 2: Revisión y Preparación.

Registra el material usado y el tiempo; calcula el precio automáticamente a
partir de los gramos. También indica en qué tipo de impresora se debe imprimir
(si `config.USAR_TIPO_IMPRESORA` está activo; si no, el campo se oculta pero se
conserva el valor que ya tuviera la boleta).
"""

import tkinter as tk

from ... import catalogo, config
from ...services import PricingService
from .base import PhaseSection


class Phase2Revision(PhaseSection):
    index = 1

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.field(row, 0, 'Uso_Material_g', "USO DE MATERIAL (g)")
        self.vars['Uso_Material_g'].trace_add('write', self._calculate_price)
        self.duration_field(row, 2, 'Tiempo_Impresion_HHMM', "TIEMPO DE IMPRESIÓN")

        row = self.new_row()
        self.field(row, 0, 'Precio', "PRECIO (₡)", "Calculado automáticamente", state='readonly')

        if config.USAR_TIPO_IMPRESORA:
            row = self.new_row()
            self.label(row, 0, "TIPO DE IMPRESORA", "Dónde se debe imprimir")
            self.radio_group(self.cell(row, 1, colspan=3), 'Tipo_Impresora',
                             catalogo.opciones_tipo_impresora(), item_width=150)
        else:
            self.vars['Tipo_Impresora'] = tk.StringVar()

    def _calculate_price(self, *args):
        self.vars['Precio'].set(PricingService.calcular(self.vars['Uso_Material_g'].get()))
