"""Clase base de una sección (fase) desplegable del formulario de boletas.

Cada fase del proceso es una subclase de `PhaseSection` en su propio archivo. La
clase encapsula TODO lo de esa fase: los widgets, sus callbacks y cómo se cargan
y guardan sus datos. Así, para cambiar o añadir una fase basta con tocar (o
crear) un único archivo y registrarlo en `phases/__init__.py`, sin tocar el
código de las demás fases ni el del formulario.

Visualmente cada fase es una barra de color (como en la boleta impresa) que al
hacer clic despliega u oculta su contenido. Una fase cuyas fases previas no
están completas está **bloqueada** (🔒, barra atenuada); en cuanto se
completan, un clic en su barra la abre y la hace la fase actual.

Contrato que puede implementar cada fase:
    index              -> índice de la fase (0..5), enlaza con config.FASES (obligatorio)
    build_widgets(f)   -> construye los widgets dentro del frame `f` (obligatorio)
    on_populate(data)  -> carga datos específicos al editar una boleta (opcional)
    on_collect(out)    -> añade datos específicos al diccionario a guardar (opcional)
    on_valores_externos(claves) -> reacciona a variables llenadas desde fuera,
                          p. ej. desde PrusaSlicer (opcional)
    problemas()        -> errores propios de la fase que impiden avanzar o
                          guardar (opcional)

El título y el color de la barra salen de config.FASES y theme.PHASE_COLORS.
"""

import re
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ... import config
from ...fechas import normalizar_fecha, normalizar_hora
from .. import theme

# Columnas de la cuadrícula de cada sección:  etiqueta | campo | etiqueta | campo
LABEL_COLUMNS = (0, 2)
FIELD_COLUMNS = (1, 3)
PAD_X = 12
PAD_Y = 5

# Lo que se puede escribir (o pegar) en los campos con formato fijo. Los
# patrones validan el texto completo mientras se teclea, así que aceptan
# valores a medio escribir.
PATRON_FECHA = r"[\d/]{0,10}"                                      # dd/mm/aaaa
PATRON_HORA = r"[\d:]{0,5}|\d{1,2}:\d{2}(\s?[aApP]\.?\s?[mM]?\.?|\s)"  # hh:mm am/pm (am/pm tras hh:mm)
PATRON_HORAS = r"\d{0,3}"                                          # tiempo: horas
PATRON_MINUTOS = r"\d{0,4}"                                        # tiempo: minutos (90 -> 1 h 30)
PATRON_ENTERO = r"\d{0,4}"                                         # cantidades (copias)
PATRON_DECIMAL = r"\d{0,6}([.,]\d{0,2})?"                          # gramos (12.5 o 12,5)
PATRON_TELEFONO = r"[\d\s+()-]{0,20}"                              # dígitos, espacios, +, -, ()


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

    def is_locked(self):
        """True si la fase todavía no se puede usar (está después de la actual)."""
        return not self.form.phase_accessible(self.index)

    def toggle(self):
        if self.expanded:
            self.collapse()
        elif self.is_locked():
            pendiente = self.form.primera_fase_incompleta(self.index)
            pendiente = config.FASES[pendiente if pendiente is not None else self.form.current_index()]
            faltan = self.form._campos_faltantes(config.FASES.index(pendiente))
            messagebox.showinfo(
                "Fase bloqueada",
                f"Primero complete la fase «{pendiente}».\n\nFaltan:\n"
                + "\n".join(f"• {campo}" for campo in faltan),
                parent=self.form,
            )
        else:
            self.form.open_phase(self.index)

    def expand(self):
        if not self.expanded and not self.is_locked():
            self.body.pack(fill="x")
            self.expanded = True
            self.refresh_header()

    def collapse(self):
        if self.expanded:
            self.body.pack_forget()
            self.expanded = False
            self.refresh_header()

    def refresh_header(self):
        """Actualiza la barra: flecha o candado, ✓ si tiene operador y marca de fase actual."""
        locked = self.is_locked()
        arrow = "🔒" if locked else ("▼" if self.expanded else "▶")
        text = f"{arrow}    {self.title}"
        if self.is_started():
            text += "   ✓"
        if self.form.current_index() == self.index:
            text += "      ●  FASE ACTUAL"
        color = theme.lighten(self.color, 0.55) if locked else self.color
        self.header.configure(text=text, fg_color=color,
                              hover_color=color if locked else self.hover_color)

    def is_started(self):
        operador = self.vars.get(f'F{self.index + 1}_Operador')
        return operador is not None and bool(operador.get().strip())

    # --- Hooks opcionales (por defecto no hacen nada) ---------------------
    def on_populate(self, boleta_data):
        """Carga específica de la fase al abrir una boleta para editar."""

    def on_collect(self, form_data):
        """Añade datos específicos de la fase al diccionario que se guardará."""

    def on_valores_externos(self, claves):
        """Se llama tras llenar `vars[clave]` desde fuera (p. ej. PrusaSlicer) para refrescar la fase."""

    def problemas(self):
        """Errores propios de la fase (además de obligatorios y fecha/hora), como textos legibles."""
        return []

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

    @staticmethod
    def restringir(entry, patron):
        """Solo deja escribir o pegar en `entry` textos que cumplan `patron` (completo)."""
        comando = entry.register(lambda propuesto: re.fullmatch(patron, propuesto) is not None)
        entry.configure(validate="key", validatecommand=(comando, "%P"))
        return entry

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
        """Fila estándar de cada fase: OPERADOR | FECHA  HORA  [Hoy].

        Si en OPERADOR se escribe un correo o un carné, se sustituye por el
        nombre completo del estudiante según el Active Directory.
        """
        n = self.index + 1
        key = f'F{n}_Operador'
        row = self.new_row()
        operador = self.field(row, 0, key, "OPERADOR", "Nombre, correo o carné")
        operador.bind("<FocusOut>", lambda _e: self._resolver_operador(key))
        operador.bind("<Return>", lambda _e: self._resolver_operador(key))
        self.datetime_fields(row, 2, f'F{n}_Fecha', f'F{n}_Hora')
        return row

    def _resolver_operador(self, key):
        texto = self.vars[key].get().strip()
        usuarios = self.form.parent_app.usuarios
        campo, _valor = usuarios.identificar(texto)
        if campo is None:
            return  # Ya es un nombre: no hay nada que buscar.

        def aplicar(nombre):
            # Solo se sustituye si el operador no cambió el campo mientras tanto.
            if nombre and self.vars[key].get().strip() == texto:
                self.vars[key].set(nombre)

        self.form.en_segundo_plano(lambda: usuarios.nombre_operador(texto), aplicar)

    def datetime_fields(self, row, col, fecha_key, hora_key):
        """Campos de Fecha y Hora con un botón 'Hoy'.

        Solo aceptan números y los separadores del formato (`/` en la fecha;
        `:` y am/pm en la hora). Al salir del campo se pasan al formato
        canónico ("1/2/2026" -> "01/02/2026", "2:30 p.m." -> "02:30 PM",
        "14:30" -> "02:30 PM") para que siempre se puedan leer después.
        """
        self.label(row, col, "FECHA", "dd/mm/aaaa · hh:mm am/pm")
        cell = self.cell(row, col + 1, sticky="ew")
        fecha = self.restringir(self.entry(cell, fecha_key, width=105), PATRON_FECHA)
        fecha.pack(side="left")
        fecha.bind("<FocusOut>", lambda _e: self._normalizar(fecha_key, normalizar_fecha))
        ctk.CTkLabel(cell, text="HORA", font=theme.font(12, "bold"), text_color=theme.TEXT).pack(side="left", padx=(10, 6))
        hora = self.restringir(self.entry(cell, hora_key, width=90), PATRON_HORA)
        hora.pack(side="left")
        hora.bind("<FocusOut>", lambda _e: self._normalizar(hora_key, normalizar_hora))
        ctk.CTkButton(
            cell, text="Hoy", width=50, fg_color=self.color, hover_color=self.hover_color,
            command=lambda: self.form.set_datetime(fecha_key, hora_key),
        ).pack(side="left", padx=(8, 0))

    def _normalizar(self, key, normalizar):
        """Pasa `vars[key]` al formato canónico (solo si cambia, para no disparar avisos)."""
        valor = self.vars[key].get()
        normalizado = normalizar(valor)
        if normalizado != valor:
            self.vars[key].set(normalizado)

    def duration_field(self, row, col, key, text):
        """Etiqueta + dos campos (horas y minutos) que se guardan juntos como "H:MM" en `vars[key]`.

        Al teclear solo se aceptan números. Si las horas o los minutos no son números
        (p. ej. un valor viejo cargado del Excel), `vars[key]` queda vacío (y la
        validación de obligatorios lo marca). Los minutos de más se pasan a
        horas (0 h 90 min -> "1:30").
        """
        self.label(row, col, text, "Horas y minutos")
        cell = self.cell(row, col + 1, sticky="ew")
        var = self.vars[key] = tk.StringVar()
        horas, minutos = tk.StringVar(), tk.StringVar()
        sincronizando = [False]

        for parte, unidad, patron in ((horas, "h", PATRON_HORAS), (minutos, "min", PATRON_MINUTOS)):
            campo = ctk.CTkEntry(cell, textvariable=parte, width=60, border_color=theme.SEPARATOR,
                                 font=theme.font(12), justify="center")
            self.restringir(campo, patron).pack(side="left")
            ctk.CTkLabel(cell, text=unidad, font=theme.font(12), text_color=theme.TEXT).pack(side="left", padx=(4, 12))

        def desde_campos(*_):
            if sincronizando[0]:
                return
            h, m = horas.get().strip(), minutos.get().strip()
            sincronizando[0] = True
            try:
                if not h and not m:
                    var.set('')
                elif (h or "0").isdigit() and (m or "0").isdigit():
                    total = int(h or 0) * 60 + int(m or 0)
                    var.set(f"{total // 60}:{total % 60:02d}" if total else '')
                else:
                    var.set('')
            finally:
                sincronizando[0] = False

        def desde_variable(*_):
            if sincronizando[0]:
                return
            sincronizando[0] = True
            try:
                partes = var.get().strip().split(":")
                if len(partes) == 2:
                    horas.set(partes[0].strip())
                    minutos.set(partes[1].strip())
                else:
                    horas.set(var.get().strip())
                    minutos.set('')
            finally:
                sincronizando[0] = False

        horas.trace_add('write', desde_campos)
        minutos.trace_add('write', desde_campos)
        var.trace_add('write', desde_variable)
        return cell

    def text_area(self, row, key, text, hint=None, height=110):
        """Etiqueta + cuadro de texto multilínea que ocupa el resto de la fila.

        El contenido se sincroniza en ambos sentidos con `vars[key]`, así se
        guarda y se carga como cualquier otro campo.
        """
        self.label(row, 0, text, hint)
        var = self.vars[key] = tk.StringVar()
        box = ctk.CTkTextbox(self.body, height=height, wrap="word", border_width=1,
                             border_color=theme.SEPARATOR, font=theme.font(12))
        box.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(0, PAD_X), pady=PAD_Y)

        def desde_cuadro(_event=None):
            var.set(box.get("1.0", "end-1c"))

        def desde_variable(*_):
            if box.get("1.0", "end-1c") != var.get():
                box.delete("1.0", "end")
                box.insert("1.0", var.get())

        box.bind("<KeyRelease>", desde_cuadro)
        box.bind("<FocusOut>", desde_cuadro)
        var.trace_add('write', desde_variable)
        return box

    def radio_group(self, parent, key, options, per_row=None, command=None, default="", item_width=70,
                    labels=None):
        """Grupo de opciones (como las casillas de la boleta) ligado a `vars[key]`.

        `labels` (opcional) da un texto distinto al valor guardado de cada
        opción. Devuelve un diccionario valor -> botón.
        """
        self.vars[key] = tk.StringVar(value=default)
        per_row = per_row or len(options) or 1
        labels = labels or {}
        buttons = {}
        for i, option in enumerate(options):
            button = ctk.CTkRadioButton(
                parent, text=labels.get(str(option), str(option)), value=str(option),
                variable=self.vars[key], command=command,
                width=item_width, radiobutton_width=16, radiobutton_height=16,
                border_width_unchecked=2, border_width_checked=5,
                fg_color=self.color, hover_color=self.hover_color, font=theme.font(12),
            )
            button.grid(row=i // per_row, column=i % per_row, sticky="w", padx=(0, 10), pady=2)
            buttons[str(option)] = button
        return buttons

    def checkbox(self, parent, key, text, text_color=theme.TEXT):
        """Casilla de verificación ligada a una BooleanVar en `vars[key]`."""
        self.vars[key] = tk.BooleanVar()
        return ctk.CTkCheckBox(
            parent, text=text, variable=self.vars[key], onvalue=True, offvalue=False,
            checkbox_width=18, checkbox_height=18, border_width=2,
            fg_color=self.color, hover_color=self.hover_color,
            font=theme.font(12), text_color=text_color,
        )
