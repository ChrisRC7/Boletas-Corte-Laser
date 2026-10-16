"""Fase 3: Impresión.

Registra la impresora usada y gestiona una lista dinámica de fallos de
impresión, que se guarda serializada como JSON en la columna `Fallo_Lista`.
"""

import json
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ... import config
from .. import theme
from .base import PhaseSection, PAD_X, PAD_Y


class Phase3Impresion(PhaseSection):
    index = 2

    def __init__(self, form):
        super().__init__(form)
        self.fallos_lista = []

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.label(row, 0, "CONFIRMACIÓN\nDEL USUARIO")
        self.radio_group(self.cell(row, 1, colspan=3), 'Confirmacion_Usuario',
                         config.CONFIRMACION_OPTIONS, item_width=180)

        row = self.new_row()
        self.label(row, 0, "IMPRESORA")
        self.radio_group(self.cell(row, 1), 'Impresora_Num', config.IMPRESORA_OPTIONS, item_width=40)
        self.checkbox(frame, 'F3_Envio_Correo', "Envío de correo de notificación de inicio",
                      text_color=theme.ACCENT_RED).grid(row=row, column=2, columnspan=2, sticky="w", padx=PAD_X, pady=PAD_Y)

        # Sistema dinámico de fallos
        row = self.new_row()
        self.label(row, 0, "DETECCIÓN DE FALLOS", "Descripción, fecha, hora\ny operador")
        fallos_frame = self.cell(row, 1, colspan=3, sticky="ew")
        fallos_frame.grid_columnconfigure(0, weight=1)

        self.fallos_listbox = tk.Listbox(
            fallos_frame, height=4, font=(theme.FONT_FAMILY, 10), relief="flat",
            highlightthickness=1, highlightbackground=theme.SEPARATOR, highlightcolor=self.color,
            selectbackground=self.color, selectforeground="white", activestyle="none",
        )
        fallos_scroll = ctk.CTkScrollbar(fallos_frame, height=60, command=self.fallos_listbox.yview)
        self.fallos_listbox.configure(yscrollcommand=fallos_scroll.set)
        self.fallos_listbox.grid(row=0, column=0, sticky="ew")
        fallos_scroll.grid(row=0, column=1, sticky="ns")

        botones = ctk.CTkFrame(fallos_frame, fg_color="transparent")
        botones.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ctk.CTkButton(botones, text="+ Agregar Fallo", width=120, fg_color=self.color,
                      hover_color=self.hover_color, command=self._agregar_fallo).pack(side="left", padx=(0, 6))
        ctk.CTkButton(botones, text="− Eliminar Fallo", width=120, fg_color=theme.NEUTRAL,
                      hover_color=theme.darken(theme.NEUTRAL), command=self._eliminar_fallo).pack(side="left")

    def on_populate(self, boleta_data):
        import pandas as pd
        fallo_lista_str = boleta_data.get('Fallo_Lista', '')
        if fallo_lista_str and not pd.isna(fallo_lista_str) and str(fallo_lista_str).strip():
            try:
                self.fallos_lista = json.loads(str(fallo_lista_str))
                self._refrescar_lista_fallos()
            except json.JSONDecodeError:
                self.fallos_lista = []

    def on_collect(self, form_data):
        form_data['Fallo_Lista'] = json.dumps(self.fallos_lista) if self.fallos_lista else ''

    # --- Gestión de la lista de fallos ------------------------------------
    def _agregar_fallo(self):
        dialog = ctk.CTkToplevel(self.form)
        dialog.title("Agregar Fallo")
        dialog.geometry("420x240")
        dialog.configure(fg_color=theme.PAPER)
        dialog.transient(self.form)
        # CTkToplevel aún no es visible al crearse: el grab se hace un instante después.
        dialog.after(150, dialog.grab_set)

        ctk.CTkLabel(dialog, text="Descripción del Fallo:", font=theme.font(12, "bold")).pack(pady=(10, 5), padx=10, anchor="w")
        descripcion_text = ctk.CTkTextbox(dialog, height=110, wrap="word", border_width=1,
                                          border_color=theme.SEPARATOR, font=theme.font(12))
        descripcion_text.pack(pady=5, padx=10, fill="both", expand=True)
        dialog.after(200, descripcion_text.focus_set)

        def guardar_fallo():
            descripcion = descripcion_text.get("1.0", "end-1c").strip()
            if not descripcion:
                messagebox.showwarning("Campo Vacío", "Por favor ingrese una descripción del fallo.", parent=dialog)
                return
            self.fallos_lista.append(descripcion)
            self.fallos_listbox.insert(tk.END, f"{len(self.fallos_lista)}. {descripcion}")
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Guardar", width=100, fg_color=self.color,
                      hover_color=self.hover_color, command=guardar_fallo).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", width=100, fg_color=theme.NEUTRAL,
                      hover_color=theme.darken(theme.NEUTRAL), command=dialog.destroy).pack(side="left", padx=5)

    def _eliminar_fallo(self):
        selection = self.fallos_listbox.curselection()
        if not selection:
            messagebox.showwarning("Sin Selección", "Por favor seleccione un fallo para eliminar.", parent=self.form)
            return
        self.fallos_lista.pop(selection[0])
        self._refrescar_lista_fallos()

    def _refrescar_lista_fallos(self):
        self.fallos_listbox.delete(0, tk.END)
        for i, fallo in enumerate(self.fallos_lista, 1):
            self.fallos_listbox.insert(tk.END, f"{i}. {fallo}")
