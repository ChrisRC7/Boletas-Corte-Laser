"""Clase base de una sección (fase) desplegable del formulario de boletas.

Cada fase del proceso es una subclase de `PhaseSection` en su propio archivo. La
clase encapsula TODO lo de esa fase: los widgets, sus callbacks y cómo se cargan
y guardan sus datos. Así, para cambiar o añadir una fase basta con tocar (o
crear) un único archivo y registrarlo en `phases/__init__.py`, sin tocar el
código de las demás fases ni el del formulario.

Visualmente cada fase es una barra de color (como en la boleta impresa) que al
hacer clic despliega u oculta su contenido.

Contrato que puede implementar cada fase:
    index              -> índice de la fase (0..6), enlaza con config.FASES (obligatorio)
    build_widgets(f)   -> construye los widgets dentro del frame `f` (obligatorio)
    on_populate(data)  -> carga datos específicos al editar una boleta (opcional)
    on_collect(out)    -> añade datos específicos al diccionario a guardar (opcional)

El título y el color de la barra salen de config.FASES y theme.PHASE_COLORS.
"""

import tkinter as tk

import customtkinter as ctk

from ... import config
from .. import theme

# Columnas de la cuadrícula de cada sección:  etiqueta | campo | etiqueta | campo
LABEL_COLUMNS = (0, 2)
FIELD_COLUMNS = (1, 3)
PAD_X = 12
PAD_Y = 5


class PhaseSection:
    index = None

    def __init__(self, form):
        # `form` es la BoletaForm anfitriona: da acceso a las variables
        # compartidas (form.vars) y a utilidades comunes (set_datetime, etc.).
        self.form = form
        self.expanded = False
        self._next_grid_row = 0

    @property
    def vars(self):
        return self.form.vars

    @property
    def title(self):
        return f"FASE {config.FASES[self.index].upper()}"

    @property
    def color(self):
        return theme.PHASE_COLORS[self.index]

    @property
    def hover_color(self):
        return theme.darken(self.color)

    # --- Scaffolding de la sección desplegable ----------------------------
    def build(self, parent):
        self.container = ctk.CTkFrame(parent, fg_color="transparent")
        self.container.pack(fill="x", pady=(0, 8))

        self.header = ctk.CTkButton(
            self.container, height=36, corner_radius=4, anchor="center",
            fg_color=self.color, hover_color=self.hover_color, text_color="white",
            font=theme.font(14, "bold"), command=self.toggle,
        )
        self.header.pack(fill="x")

        self.body = ctk.CTkFrame(
            self.container, fg_color=theme.PAPER, corner_radius=0,
            border_width=2, border_color=self.color,
        )
        for col in LABEL_COLUMNS:
            self.body.grid_columnconfigure(col, minsize=150)
        for col in FIELD_COLUMNS:
            self.body.grid_columnconfigure(col, weight=1)

        self.build_widgets(self.body)
        self._add_bottom_padding()

        operador = self.vars.get(f'F{self.index + 1}_Operador')
        if operador is not None:
            operador.trace_add('write', lambda *_: self.refresh_header())
        self.refresh_header()

    def build_widgets(self, frame):
        raise NotImplementedError

    def toggle(self):
        if self.expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        if not self.expanded:
            self.body.pack(fill="x")
            self.expanded = True
            self.refresh_header()

    def collapse(self):
        if self.expanded:
            self.body.pack_forget()
            self.expanded = False
            self.refresh_header()

    def refresh_header(self):
        """Actualiza la barra: flecha, ✓ si tiene operador y marca de fase actual."""
        arrow = "▼" if self.expanded else "▶"
        text = f"{arrow}    {self.title}"
        if self.is_started():
            text += "   ✓"
        if self.form.current_index() == self.index:
            text += "      ●  FASE ACTUAL"
        self.header.configure(text=text)

    def is_started(self):
        operador = self.vars.get(f'F{self.index + 1}_Operador')
        return operador is not None and bool(operador.get().strip())

    # --- Hooks opcionales (por defecto no hacen nada) ---------------------
    def on_populate(self, boleta_data):
        """Carga específica de la fase al abrir una boleta para editar."""

    def on_collect(self, form_data):
        """Añade datos específicos de la fase al diccionario que se guardará."""

    # --- Filas de la cuadrícula -------------------------------------------
    def new_row(self):
        """Devuelve el número de la siguiente fila, separada por una línea."""
        if self._next_grid_row > 0:
            tk.Frame(self.body, height=1, bg=theme.SEPARATOR).grid(
                row=self._next_grid_row, column=0, columnspan=4, sticky="ew", padx=PAD_X)
            self._next_grid_row += 1
        else:
            # Espacio superior para no pisar el borde de la sección.
            tk.Frame(self.body, height=4, bg=theme.PAPER).grid(row=0, column=0)
            self._next_grid_row += 1
        row = self._next_grid_row
        self._next_grid_row += 1
        return row

    def _add_bottom_padding(self):
        tk.Frame(self.body, height=4, bg=theme.PAPER).grid(row=self._next_grid_row, column=0)

    # --- Constructores de campos reutilizables ----------------------------
    def label(self, row, col, text, hint=None, text_color=theme.TEXT):
        """Etiqueta en mayúsculas con un texto de ayuda opcional debajo."""
        cell = ctk.CTkFrame(self.body, fg_color="transparent")
        cell.grid(row=row, column=col, sticky="w", padx=(PAD_X, 6), pady=PAD_Y)
        ctk.CTkLabel(cell, text=text, font=theme.font(12, "bold"), text_color=text_color,
                     anchor="w", justify="left", height=20).pack(anchor="w")
        if hint:
            ctk.CTkLabel(cell, text=hint, font=theme.font(10), text_color=theme.HINT,
                         anchor="w", justify="left", height=14).pack(anchor="w")
        return cell

    def entry(self, parent, key, width=140, **kwargs):
        """Crea un CTkEntry ligado a una variable nueva registrada en `vars`."""
        self.vars[key] = tk.StringVar()
        return ctk.CTkEntry(parent, textvariable=self.vars[key], width=width,
                            border_color=theme.SEPARATOR, font=theme.font(12), **kwargs)

    def field(self, row, col, key, text, hint=None, colspan=1, **kwargs):
        """Etiqueta + campo de texto en la cuadrícula. Devuelve el CTkEntry."""
        self.label(row, col, text, hint)
        widget = self.entry(self.body, key, **kwargs)
        widget.grid(row=row, column=col + 1, columnspan=colspan, sticky="ew", padx=(0, PAD_X), pady=PAD_Y)
        return widget

    def cell(self, row, col, colspan=1, sticky="w"):
        """Frame transparente para agrupar varios widgets en una celda."""
        frame = ctk.CTkFrame(self.body, fg_color="transparent")
        frame.grid(row=row, column=col, columnspan=colspan, sticky=sticky, padx=(0, PAD_X), pady=PAD_Y)
        return frame

    def operator_row(self):
        """Fila estándar de cada fase: OPERADOR | FECHA  HORA  [Hoy]."""
        n = self.index + 1
        row = self.new_row()
        self.field(row, 0, f'F{n}_Operador', "OPERADOR")
        self.datetime_fields(row, 2, f'F{n}_Fecha', f'F{n}_Hora')
        return row

    def datetime_fields(self, row, col, fecha_key, hora_key):
        """Campos de Fecha y Hora con un botón 'Hoy'."""
        self.label(row, col, "FECHA", "dd/mm/aaaa · hh:mm am/pm")
        cell = self.cell(row, col + 1, sticky="ew")
        self.entry(cell, fecha_key, width=105).pack(side="left")
        ctk.CTkLabel(cell, text="HORA", font=theme.font(12, "bold"), text_color=theme.TEXT).pack(side="left", padx=(10, 6))
        self.entry(cell, hora_key, width=90).pack(side="left")
        ctk.CTkButton(
            cell, text="Hoy", width=50, fg_color=self.color, hover_color=self.hover_color,
            command=lambda: self.form.set_datetime(fecha_key, hora_key),
        ).pack(side="left", padx=(8, 0))

    def radio_group(self, parent, key, options, per_row=None, command=None, default="", item_width=70):
        """Grupo de opciones (como las casillas de la boleta) ligado a `vars[key]`."""
        self.vars[key] = tk.StringVar(value=default)
        per_row = per_row or len(options)
        for i, option in enumerate(options):
            ctk.CTkRadioButton(
                parent, text=str(option), value=str(option), variable=self.vars[key], command=command,
                width=item_width, radiobutton_width=16, radiobutton_height=16,
                border_width_unchecked=2, border_width_checked=5,
                fg_color=self.color, hover_color=self.hover_color, font=theme.font(12),
            ).grid(row=i // per_row, column=i % per_row, sticky="w", padx=(0, 10), pady=2)

    def checkbox(self, parent, key, text, text_color=theme.TEXT):
        """Casilla de verificación ligada a una BooleanVar en `vars[key]`."""
        self.vars[key] = tk.BooleanVar()
        return ctk.CTkCheckBox(
            parent, text=text, variable=self.vars[key], onvalue=True, offvalue=False,
            checkbox_width=18, checkbox_height=18, border_width=2,
            fg_color=self.color, hover_color=self.hover_color,
            font=theme.font(12), text_color=text_color,
        )
