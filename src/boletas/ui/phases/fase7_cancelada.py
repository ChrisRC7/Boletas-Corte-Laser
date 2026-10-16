"""Fase 7: Cancelada.

Registra el motivo de cancelación en un cuadro de texto multilínea, sincronizado
con la variable `F7_Motivo_Cancelacion`.
"""

import tkinter as tk

import customtkinter as ctk

from .. import theme
from .base import PhaseSection, PAD_X, PAD_Y


class Phase7Cancelada(PhaseSection):
    index = 6

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.label(row, 0, "MOTIVO DE\nCANCELACIÓN")
        self.vars['F7_Motivo_Cancelacion'] = tk.StringVar()
        self.text_widget = ctk.CTkTextbox(frame, height=110, wrap="word", border_width=1,
                                          border_color=theme.SEPARATOR, font=theme.font(12))
        self.text_widget.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(0, PAD_X), pady=PAD_Y)
        self.text_widget.bind("<KeyRelease>", self._on_text_change)

    def on_populate(self, boleta_data):
        import pandas as pd
        motivo = boleta_data.get('F7_Motivo_Cancelacion', '')
        if motivo and not pd.isna(motivo):
            self.text_widget.delete("1.0", "end")
            self.text_widget.insert("1.0", str(motivo))

    def _on_text_change(self, *args):
        self.vars['F7_Motivo_Cancelacion'].set(self.text_widget.get("1.0", "end-1c"))
