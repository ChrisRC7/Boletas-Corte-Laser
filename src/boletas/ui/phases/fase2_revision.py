"""Fase 2: Revisión y Preparación.

Registra el material usado y el tiempo (a mano o leídos de PrusaSlicer, que
también actualiza material, resolución y relleno de la Recepción);
calcula el precio automáticamente a partir de los gramos. También indica en qué tipo de impresora se debe imprimir
(si `config.USAR_TIPO_IMPRESORA` está activo; si no, el campo se oculta pero se
conserva el valor que ya tuviera la boleta).
"""

import tkinter as tk

from ... import catalogo, config
from ...services import PricingService
from ..importar_slicer import fila_prusaslicer
from .base import PhaseSection, PATRON_DECIMAL


class Phase2Revision(PhaseSection):
    index = 1

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.restringir(self.field(row, 0, 'Uso_Material_g', "USO DE MATERIAL (g)"), PATRON_DECIMAL)
        self.vars['Uso_Material_g'].trace_add('write', self._calculate_price)
        self.duration_field(row, 2, 'Tiempo_Impresion_HHMM', "TIEMPO DE IMPRESIÓN")
        fila_prusaslicer(self, 'Uso_Material_g', 'Tiempo_Impresion_HHMM', parametros=True)

        row = self.new_row()
        self.field(row, 0, 'Precio', "PRECIO (₡)", "Calculado automáticamente", state='readonly')

        if config.USAR_TIPO_IMPRESORA:
            row = self.new_row()
            self.label(row, 0, "TIPO DE IMPRESORA", "Dónde se debe imprimir")
            self.radio_group(self.cell(row, 1, colspan=3), 'Tipo_Impresora',
                             catalogo.opciones_tipo_impresora(), item_width=150)
        else:
            self.vars['Tipo_Impresora'] = tk.StringVar()

    def problemas(self):
        # Valores viejos del Excel no pasan por la restricción de teclado.
        gramos = self.vars['Uso_Material_g'].get().strip()
        if gramos and PricingService.gramos(gramos) is None:
            return [f"{config.FIELD_NAMES['Uso_Material_g']} no es un número válido («{gramos}»)."]
        return []

    def _calculate_price(self, *args):
        self.vars['Precio'].set(PricingService.calcular(self.vars['Uso_Material_g'].get()))
