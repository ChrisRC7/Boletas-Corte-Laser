"""Fase 3: Impresión.

Muestra en qué tipo de impresora hay que imprimir (lo decide la Revisión) y
solo deja elegir impresoras activas de ese tipo. Registra la impresora usada, una lista de fallos de impresión (guardada como
JSON en la columna `Fallo_Lista`) y notas libres sobre la impresión.

Tiene dos botones de correo (se abren como borrador en Outlook):
- «Solicitar autorización»: costo de la pieza; al abrirlo marca la
  confirmación por «Correo Institucional».
- «Correo de inicio»: aviso de que empezó la impresión; marca la casilla de
  notificación de inicio (y pone la fecha/hora de ahora si están vacías).

Los fallos solo se pueden agregar, nunca eliminar: así queda el historial
completo de cada boleta y el proceso es transparente. Cada fallo guarda su
descripción, fecha, hora y operador (`{"descripcion", "fecha", "hora",
"operador"}`); los fallos de versiones anteriores, guardados solo como texto,
se siguen mostrando.
"""

import json
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from ... import catalogo, config, correos
from .. import theme
from ..enviar_correo import boton_correo
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
        confirmacion = self.cell(row, 1, colspan=3)
        self.radio_group(confirmacion, 'Confirmacion_Usuario',
                         config.CONFIRMACION_OPTIONS, item_width=180)
        boton_correo(self, confirmacion, correos.AUTORIZACION, "✉  Solicitar autorización",
                     al_abrir=self._marcar_confirmacion_por_correo).grid(
            row=0, column=len(config.CONFIRMACION_OPTIONS), padx=(10, 0))

        # Tipo de impresora pedido en la Revisión (solo lectura).
        row = self.new_row()
        self.label(row, 0, "IMPRIMIR EN", "Tipo de impresora\n(se elige en la Revisión)")
        self.tipo_label = ctk.CTkLabel(frame, text="", font=theme.font(14, "bold"),
                                       text_color=theme.ACCENT_RED, anchor="w")
        self.tipo_label.grid(row=row, column=1, sticky="w", padx=(0, PAD_X), pady=PAD_Y)
        correo = self.cell(row, 2, colspan=2)
        self.checkbox(correo, 'F3_Envio_Correo', "Envío de correo de notificación de inicio",
                      text_color=theme.ACCENT_RED).pack(side="left")
        boton_correo(self, correo, correos.INICIO, "✉  Correo de inicio", width=140,
                     antes=self._fecha_si_vacia,
                     al_abrir=lambda: self.vars['F3_Envio_Correo'].set(True)).pack(side="left", padx=(10, 0))

        row = self.new_row()
        self.label(row, 0, "IMPRESORA", "Solo las del tipo indicado")
        impresoras = catalogo.impresoras_activas()
        textos = {str(i["numero"]): f'{i["numero"]} · {i.get("tipo", "")}' for i in impresoras}
        self.impresora_radios = self.radio_group(
            self.cell(row, 1, colspan=3), 'Impresora_Num', [i["numero"] for i in impresoras],
            per_row=4, labels=textos if config.USAR_TIPO_IMPRESORA else None,
            item_width=150 if config.USAR_TIPO_IMPRESORA else 40,
        )
        self.vars['Tipo_Impresora'].trace_add('write', lambda *_: self._actualizar_tipo())
        self._actualizar_tipo()

        # Sistema dinámico de fallos
        row = self.new_row()
        self.label(row, 0, "DETECCIÓN DE FALLOS", "Descripción, fecha, hora\ny operador\n(no se pueden eliminar)")
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
                      hover_color=self.hover_color, command=self._agregar_fallo).pack(side="left")

        row = self.new_row()
        self.text_area(row, 'F3_Notas', "NOTAS DE\nIMPRESIÓN", "Observaciones sobre\nla impresión", height=90)

    def on_populate(self, boleta_data):
        self._actualizar_tipo()  # La impresora se carga después que el tipo.
        # El repositorio ya devuelve los vacíos como '' (nunca NaN).
        fallo_lista_str = boleta_data.get('Fallo_Lista', '') or ''
        if str(fallo_lista_str).strip():
            try:
                fallos = json.loads(str(fallo_lista_str))
            except json.JSONDecodeError:
                fallos = None
            # Un valor que no es una lista se conserva como un fallo de texto
            # (los fallos nunca se pierden).
            self.fallos_lista = fallos if isinstance(fallos, list) else [str(fallo_lista_str)]
            self._refrescar_lista_fallos()

    # --- Tipo de impresora ------------------------------------------------
    def _actualizar_tipo(self):
        """Muestra el tipo pedido y deshabilita las impresoras de otro tipo."""
        tipo = self.vars['Tipo_Impresora'].get().strip()
        if not config.USAR_TIPO_IMPRESORA:
            self.tipo_label.configure(text="Cualquier impresora")
        elif not tipo:
            self.tipo_label.configure(text="(sin indicar en la Revisión)")
        elif tipo == config.TIPO_IMPRESORA_CUALQUIERA:
            self.tipo_label.configure(text="Cualquier impresora")
        else:
            self.tipo_label.configure(text=tipo)

        seleccionada = self.vars['Impresora_Num'].get()
        for numero, boton in self.impresora_radios.items():
            compatible = catalogo.tipo_compatible(tipo, catalogo.tipo_de_impresora(numero))
            # La ya elegida queda habilitada para no "perderla" al editar boletas viejas.
            boton.configure(state='normal' if compatible or numero == seleccionada else 'disabled')

    def problemas(self):
        """La impresora elegida debe ser del tipo pedido (pudo cambiar en la Revisión).

        Una impresora que ya no está en la Configuración no se puede comprobar:
        la boleta conserva su número y se puede seguir guardando.
        """
        numero = self.vars['Impresora_Num'].get().strip()
        tipo = self.vars['Tipo_Impresora'].get().strip()
        if (numero and catalogo.existe_impresora(numero)
                and not catalogo.tipo_compatible(tipo, catalogo.tipo_de_impresora(numero))):
            return [f"La impresora {numero} no es del tipo pedido en la Revisión ({tipo})."]
        return []

    # --- Correos -----------------------------------------------------------
    def _marcar_confirmacion_por_correo(self):
        """La autorización se pidió por correo: se marca la primera opción (Correo Institucional)."""
        if config.CONFIRMACION_OPTIONS:
            self.vars['Confirmacion_Usuario'].set(config.CONFIRMACION_OPTIONS[0])

    def _fecha_si_vacia(self):
        """El correo de inicio dice cuándo se colocó la impresión: si no hay fecha, es ahora."""
        if not self.vars['F3_Fecha'].get().strip() or not self.vars['F3_Hora'].get().strip():
            self.form.set_datetime('F3_Fecha', 'F3_Hora')

    def on_collect(self, form_data):
        form_data['Fallo_Lista'] = json.dumps(self.fallos_lista) if self.fallos_lista else ''

    # --- Gestión de la lista de fallos ------------------------------------
    def _agregar_fallo(self):
        dialog = ctk.CTkToplevel(self.form)
        dialog.title("Agregar Fallo")
        dialog.geometry("420x300")
        dialog.configure(fg_color=theme.PAPER)
        dialog.transient(self.form)
        # CTkToplevel aún no es visible al crearse: el grab se hace un instante después.
        dialog.after(150, dialog.grab_set)

        # Operador que detectó el fallo (por defecto, el de la Impresión).
        ctk.CTkLabel(dialog, text="Operador:", font=theme.font(12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        operador_var = tk.StringVar(value=self.vars['F3_Operador'].get().strip())
        ctk.CTkEntry(dialog, textvariable=operador_var, font=theme.font(12),
                     border_color=theme.SEPARATOR).pack(padx=10, fill="x")

        ctk.CTkLabel(dialog, text="Descripción del Fallo:", font=theme.font(12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        ctk.CTkLabel(dialog, text="Una vez guardado, el fallo no se puede eliminar.", font=theme.font(10),
                     text_color=theme.HINT).pack(padx=10, anchor="w")
        descripcion_text = ctk.CTkTextbox(dialog, height=110, wrap="word", border_width=1,
                                          border_color=theme.SEPARATOR, font=theme.font(12))
        descripcion_text.pack(pady=5, padx=10, fill="both", expand=True)
        dialog.after(200, descripcion_text.focus_set)

        def guardar_fallo():
            descripcion = descripcion_text.get("1.0", "end-1c").strip()
            if not descripcion:
                messagebox.showwarning("Campo Vacío", "Por favor ingrese una descripción del fallo.", parent=dialog)
                return
            operador = operador_var.get().strip()
            if not operador:
                messagebox.showwarning("Campo Vacío", "Indique el operador que detectó el fallo.", parent=dialog)
                return
            ahora = datetime.now()
            self.fallos_lista.append({
                "descripcion": descripcion,
                "fecha": ahora.strftime(config.FORMATO_FECHA),
                "hora": ahora.strftime(config.FORMATO_HORA),
                "operador": operador,
            })
            self._refrescar_lista_fallos()
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Guardar", width=100, fg_color=self.color,
                      hover_color=self.hover_color, command=guardar_fallo).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", width=100, fg_color=theme.NEUTRAL,
                      hover_color=theme.darken(theme.NEUTRAL), command=dialog.destroy).pack(side="left", padx=5)

    def _refrescar_lista_fallos(self):
        self.fallos_listbox.delete(0, tk.END)
        for i, fallo in enumerate(self.fallos_lista, 1):
            self.fallos_listbox.insert(tk.END, f"{i}. {self._texto_fallo(fallo)}")

    @staticmethod
    def _texto_fallo(fallo):
        """'09/11/2026 02:30 PM · Ana — Se despegó' (o el texto tal cual si es un fallo viejo)."""
        if not isinstance(fallo, dict):
            return str(fallo)
        cuando = f"{fallo.get('fecha', '')} {fallo.get('hora', '')}".strip()
        quien = fallo.get('operador', '')
        encabezado = " · ".join(parte for parte in (cuando, quien) if parte)
        descripcion = fallo.get('descripcion', '')
        return f"{encabezado} — {descripcion}" if encabezado else descripcion
