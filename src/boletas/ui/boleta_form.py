"""Formulario de creación/edición de una boleta (una sola vista con fases desplegables).

Imita la boleta impresa: todas las fases están en la misma ventana, una debajo de
otra, cada una con su barra de color que se despliega u oculta al hacer clic.

Esta clase es el **orquestador**: arma la ventana, la navegación entre fases y la
carga/guardado de datos, pero NO conoce los detalles de cada fase. Cada fase es
una clase independiente en `ui/phases/` (ver ese paquete). Para cambiar o añadir
una fase no se toca este archivo, solo el de la fase correspondiente.
"""

import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

import customtkinter as ctk
import pandas as pd

from .. import config
from ..services import PhaseDetector
from . import theme
from .phases import build_phases


class BoletaForm(ctk.CTkToplevel):
    """Ventana para crear o editar una boleta."""

    def __init__(self, parent_app, boleta_id=None):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.boleta_id = boleta_id
        self.vars = {'Fase Actual': tk.StringVar(value=config.FASES[0])}

        if self.boleta_id:
            self.title(f"Editando Boleta #{self.boleta_id}")
        else:
            self.title("Añadir Nueva Boleta de Impresión")
        self.geometry("1020x860")
        self.minsize(900, 560)
        self.configure(fg_color=theme.BG)

        self._build_banner()
        self._build_controls()  # Se empaca abajo antes que el área con scroll.

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=theme.BG, corner_radius=0)
        self.scroll.pack(expand=True, fill="both", padx=6, pady=(0, 4))

        # Cada fase se construye a sí misma como una sección desplegable.
        self.phases = build_phases(self)
        for phase in self.phases:
            phase.build(self.scroll)

        # En Windows, CTkToplevel a veces se abre detrás de la ventana principal.
        self.after(200, self._bring_to_front)

        if self.boleta_id:
            self.populate_form()
        else:
            self.set_datetime('F1_Fecha', 'F1_Hora')
            self.set_current_phase(0)

    # --- Construcción de la ventana ---------------------------------------
    def _build_banner(self):
        """Encabezado como el de la boleta: LAIMI · CONTROL DE IMPRESIONES · Boleta N."""
        banner = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=0, height=64)
        banner.pack(fill="x")

        ctk.CTkLabel(banner, text="▪ ▚ LAIMI", font=theme.font(24, "bold"),
                     text_color=theme.TEXT).pack(side="left", padx=(20, 30), pady=12)
        ctk.CTkLabel(banner, text="CONTROL DE IMPRESIONES", font=theme.font(22),
                     text_color=theme.TEXT).pack(side="left", pady=12)

        numero = self.boleta_id if self.boleta_id else self.parent_app.get_next_id()
        estado = "" if self.boleta_id else "  (nueva)"
        ctk.CTkLabel(banner, text=f"Boleta {numero}{estado}", font=theme.font(16, "bold"),
                     text_color=theme.ACCENT_RED).pack(side="right", padx=20, pady=12)

    def _build_controls(self):
        controls = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=0)
        controls.pack(side="bottom", fill="x")

        neutral = dict(fg_color=theme.NEUTRAL, hover_color=theme.darken(theme.NEUTRAL))

        self.prev_button = ctk.CTkButton(controls, text="◀  Anterior", width=110,
                                         command=self._previous_phase, **neutral)
        self.prev_button.pack(side="left", padx=(12, 4), pady=10)
        self.next_button = ctk.CTkButton(controls, text="Siguiente  ▶", width=110,
                                         command=self._next_phase, **neutral)
        self.next_button.pack(side="left", padx=4, pady=10)

        ctk.CTkLabel(controls, text="Fase Actual:", font=theme.font(12, "bold"),
                     text_color=theme.TEXT).pack(side="left", padx=(16, 6))
        self.fase_menu = ctk.CTkOptionMenu(
            controls, values=config.FASES, variable=self.vars['Fase Actual'], width=220,
            font=theme.font(12), dynamic_resizing=False,
            command=lambda _choice: self._on_current_phase_changed(),
        )
        self.fase_menu.pack(side="left")

        ctk.CTkButton(controls, text="Expandir todo", width=100, command=self.expand_all,
                      **neutral).pack(side="left", padx=(16, 4))
        ctk.CTkButton(controls, text="Contraer todo", width=100, command=self.collapse_all,
                      **neutral).pack(side="left", padx=4)

        ctk.CTkButton(controls, text="💾  Guardar Cambios", width=150, font=theme.font(13, "bold"),
                      fg_color=theme.SUCCESS, hover_color=theme.darken(theme.SUCCESS),
                      command=self.guardar_cambios).pack(side="right", padx=12, pady=10)

    def _bring_to_front(self):
        self.lift()
        self.focus_force()

    # --- Utilidad compartida con las fases --------------------------------
    def set_datetime(self, fecha_key, hora_key):
        now = datetime.now()
        if fecha_key in self.vars:
            self.vars[fecha_key].set(now.strftime(config.FORMATO_FECHA))
        if hora_key in self.vars:
            self.vars[hora_key].set(now.strftime(config.FORMATO_HORA))

    def en_segundo_plano(self, tarea, al_terminar):
        """Ejecuta `tarea()` en un hilo y luego `al_terminar(resultado)` en la UI.

        Sirve para consultas lentas (p. ej. el AD) sin congelar la ventana. Si
        la ventana se cerró antes de terminar, el resultado se descarta.
        """
        resultado = {}
        hilo = threading.Thread(target=lambda: resultado.setdefault('valor', tarea()), daemon=True)
        hilo.start()

        def revisar():
            if not self.winfo_exists():
                return
            if hilo.is_alive():
                self.after(100, revisar)
            else:
                al_terminar(resultado.get('valor'))

        self.after(100, revisar)

    def current_index(self):
        """Índice (0..6) de la fase marcada como actual."""
        fase = self.vars['Fase Actual'].get()
        return config.FASES.index(fase) if fase in config.FASES else 0

    # --- Secciones desplegables -------------------------------------------
    def show_phase(self, index):
        """Despliega una fase y desplaza la vista hasta ella."""
        phase = self.phases[index]
        phase.expand()
        self.after(60, lambda: self._scroll_to(phase))

    def _scroll_to(self, phase):
        self.update_idletasks()
        canvas = self.scroll._parent_canvas
        canvas.configure(scrollregion=canvas.bbox("all"))
        altura = self.scroll.winfo_height()
        if altura > 0:
            canvas.yview_moveto(phase.container.winfo_y() / altura)

    def expand_all(self):
        for phase in self.phases:
            phase.expand()

    def collapse_all(self):
        for phase in self.phases:
            phase.collapse()

    # --- Navegación entre fases -------------------------------------------
    def set_current_phase(self, index):
        self.vars['Fase Actual'].set(config.FASES[index])
        self._on_current_phase_changed()

    def _on_current_phase_changed(self):
        index = self.current_index()
        color = theme.PHASE_COLORS[index]
        self.fase_menu.configure(fg_color=color, button_color=theme.darken(color, 0.1),
                                 button_hover_color=theme.darken(color, 0.25))
        for phase in self.phases:
            phase.refresh_header()
        self.prev_button.configure(state='normal' if index > 0 else 'disabled')
        self.next_button.configure(state='normal' if index < len(config.FASES) - 1 else 'disabled')
        self.show_phase(index)

    def _next_phase(self):
        current_index = self.current_index()
        if not self._validate_phase(current_index):
            self.show_phase(current_index)
            return
        if current_index < len(config.FASES) - 1:
            self.phases[current_index].collapse()
            self.set_current_phase(current_index + 1)

    def _previous_phase(self):
        current_index = self.current_index()
        if current_index > 0:
            self.set_current_phase(current_index - 1)

    def _validate_phase(self, phase_index):
        """Valida los campos obligatorios de una fase. True si está completa."""
        required_keys = config.REQUIRED_FIELDS.get(phase_index, [])
        missing_fields = [
            config.FIELD_NAMES.get(key, key)
            for key in required_keys
            if key in self.vars and not self.vars[key].get().strip()
        ]
        if missing_fields:
            messagebox.showwarning(
                "Campos Obligatorios",
                "Por favor, complete los siguientes campos antes de continuar:\n\n"
                + "\n".join(f"• {name}" for name in missing_fields),
                parent=self,
            )
            return False
        return True

    # --- Carga / guardado --------------------------------------------------
    def populate_form(self):
        boleta_data = self.parent_app.get_boleta_by_id(self.boleta_id)
        if boleta_data is None:
            messagebox.showerror("Error", "No se encontró la boleta.", parent=self)
            self.destroy()
            return

        for key, var in self.vars.items():
            value = boleta_data.get(key, '')
            if pd.isna(value):
                value = ''
            if isinstance(var, tk.BooleanVar):
                var.set(str(value).lower() == 'true')
            else:
                var.set(str(value))

        # Carga específica de cada fase (fallos, motivo de cancelación, etc.).
        for phase in self.phases:
            phase.on_populate(boleta_data)

        fase_actual = PhaseDetector.detectar_fase_actual(boleta_data)
        self.set_current_phase(config.FASES.index(fase_actual))

    def guardar_cambios(self):
        # Validar todas las fases que ya tienen operador asignado.
        for i in range(len(config.FASES)):
            operator_key = f'F{i + 1}_Operador'
            if operator_key in self.vars and self.vars[operator_key].get().strip():
                if not self._validate_phase(i):
                    self.show_phase(i)
                    return

        form_data = {key: var.get() for key, var in self.vars.items()}

        # Datos específicos de cada fase (p. ej. la lista de fallos en JSON).
        for phase in self.phases:
            phase.on_collect(form_data)

        if self.boleta_id:
            self.parent_app.update_record(self.boleta_id, form_data)
            messagebox.showinfo("Éxito", f"Boleta #{self.boleta_id} actualizada correctamente.", parent=self)
        else:
            form_data['ID Boleta'] = self.parent_app.get_next_id()
            if not form_data.get('Fase Actual'):
                form_data['Fase Actual'] = config.FASES[0]
            self.parent_app.add_new_record(form_data)
            messagebox.showinfo("Éxito", f"Boleta #{form_data['ID Boleta']} creada correctamente.", parent=self)
        self.destroy()
