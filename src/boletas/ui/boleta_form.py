"""Formulario de creación/edición de una boleta (una sola vista con fases desplegables).

Imita la boleta impresa: todas las fases están en la misma ventana, una debajo de
otra, cada una con su barra de color que se despliega u oculta al hacer clic.

Esta clase es el **orquestador**: arma la ventana, la navegación entre fases y la
carga/guardado de datos, pero NO conoce los detalles de cada fase. Cada fase es
una clase independiente en `ui/phases/` (ver ese paquete). Para cambiar o añadir
una fase no se toca este archivo, solo el de la fase correspondiente.

Reglas de navegación:
- Una fase se puede abrir si todas las anteriores están completas (o si ya se
  llegó a ella). Al completar una fase, la siguiente se abre con un clic en su
  barra (equivale a "Siguiente"). Las fases de `config.FASES_SIN_ORDEN`
  (Cancelación) solo exigen la Recepción completa.
- La Cancelación no desbloquea nada: estando en ella, las demás fases siguen
  tan bloqueadas como antes, "Anterior" vuelve a la fase más avanzada a la que
  se había llegado y "Siguiente" termina en la Entrega (no pasa a Cancelación).
- Volver a una fase anterior no "retrocede" la boleta: al guardar, `Fase Actual`
  es la fase más avanzada a la que se llegó (o la detectada por operadores).
"""

import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

import customtkinter as ctk

from .. import catalogo, config, fechas
from ..services import PhaseDetector
from . import theme
from .phases import build_phases


class BoletaForm(ctk.CTkToplevel):
    """Ventana para crear o editar una boleta."""

    def __init__(self, parent_app, boleta_id=None, copiar_de=None):
        """`copiar_de`: ID de una boleta cuya Recepción se copia en esta (nueva)."""
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.boleta_id = boleta_id
        self.vars = {'Fase Actual': tk.StringVar(value=config.FASES[0])}
        # Última fase actual aceptada (para revertir el selector si no se puede avanzar).
        self._fase_confirmada = 0
        # Fase más avanzada a la que se llegó (sin contar Cancelación): es la
        # que se guarda como `Fase Actual` aunque se vuelva a fases anteriores.
        self._fase_maxima = 0
        self._refresco_pendiente = False

        if self.boleta_id:
            self.title(f"Editando Boleta #{self.boleta_id}")
        elif copiar_de:
            self.title(f"Nueva Boleta (copia de la #{copiar_de})")
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
            antes = set(self.vars)
            phase.build(self.scroll)
            phase.keys = set(self.vars) - antes  # Campos propios de la fase.
        for nombre, var in self.vars.items():
            if nombre != 'Fase Actual':
                var.trace_add('write', self._programar_refresco)

        # En Windows, CTkToplevel a veces se abre detrás de la ventana principal.
        self.after(200, self._bring_to_front)

        if self.boleta_id:
            if not self.populate_form():
                return
        else:
            self.set_datetime('F1_Fecha', 'F1_Hora')
            self.set_current_phase(0)
            if copiar_de:
                self.copiar_recepcion(copiar_de)

        # Datos tal como se abrieron: al cerrar con la X se avisa si cambiaron.
        self._datos_iniciales = self._datos_formulario()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    # --- Cierre ---------------------------------------------------------------
    def _datos_formulario(self):
        """Lo que se guardaría ahora (variables + datos propios de cada fase, como los fallos)."""
        datos = {key: var.get() for key, var in self.vars.items()}
        for phase in self.phases:
            phase.on_collect(datos)
        return datos

    def _al_cerrar(self):
        """Cerrar con la X: si hay cambios sin guardar, se pide confirmación."""
        if self._datos_formulario() != self._datos_iniciales and not messagebox.askyesno(
                "Cambios sin guardar",
                "Hay cambios sin guardar en esta boleta.\n\n¿Cerrar de todas formas y descartarlos?",
                icon="warning", parent=self):
            return
        self.destroy()

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
            command=self._on_fase_menu,
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
        # La ventana pudo cerrarse antes (p. ej. si la boleta no existía).
        if not self.winfo_exists():
            return
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
        """Índice (0..5) de la fase marcada como actual."""
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

    @staticmethod
    def _sin_orden(index):
        """True si la fase (p. ej. Cancelación) no forma parte del avance normal."""
        return config.FASES[index] in config.FASES_SIN_ORDEN

    def phase_accessible(self, index):
        """Se puede abrir si ya se llegó a ella o si las fases previas están completas.

        Estar en la Cancelación no cuenta como "haber llegado" a las fases
        anteriores: solo cuenta la fase más avanzada del avance normal.
        """
        if self._sin_orden(index):
            return index == self.current_index() or self.primera_fase_incompleta(index) is None
        if index <= self._fase_maxima:
            return True
        return self.primera_fase_incompleta(index) is None

    def primera_fase_incompleta(self, index):
        """Primera fase que falta completar para abrir `index` (o None)."""
        previas = [0] if config.FASES[index] in config.FASES_SIN_ORDEN else range(index)
        for indice in previas:
            if config.FASES[indice] in config.FASES_SIN_ORDEN:
                continue
            if self._campos_faltantes(indice):
                return indice
        return None

    def open_phase(self, index):
        """Clic en la barra de una fase desbloqueada.

        Si está más adelante que la actual, pasa a ser la fase actual (como
        pulsar "Siguiente"); la Cancelación solo se despliega.
        """
        if index > self.current_index() and config.FASES[index] not in config.FASES_SIN_ORDEN:
            self.phases[self.current_index()].collapse()
            self.set_current_phase(index)
        else:
            self.phases[index].expand()

    def _programar_refresco(self, *_):
        """Al escribir en cualquier campo, actualiza los candados (una vez por ciclo)."""
        if not self._refresco_pendiente:
            self._refresco_pendiente = self.after_idle(self._refrescar_barras)

    def _refrescar_barras(self):
        self._refresco_pendiente = False
        if self.winfo_exists():
            for phase in self.phases:
                phase.refresh_header()

    def destroy(self):
        # Un refresco pendiente (p. ej. tras normalizar la hora al guardar) no
        # debe ejecutarse sobre widgets ya destruidos.
        if self._refresco_pendiente:
            self.after_cancel(self._refresco_pendiente)
            self._refresco_pendiente = False
        super().destroy()

    def expand_all(self):
        for phase in self.phases:
            phase.expand()  # Las fases bloqueadas no se despliegan.

    def collapse_all(self):
        for phase in self.phases:
            phase.collapse()

    # --- Navegación entre fases -------------------------------------------
    def set_current_phase(self, index):
        self.vars['Fase Actual'].set(config.FASES[index])
        self._on_current_phase_changed()

    def _on_fase_menu(self, eleccion):
        """Cambio desde el selector: para ir hacia adelante hay que cumplir las fases previas."""
        destino = config.FASES.index(eleccion)
        # Se avanza desde la fase más avanzada alcanzada (no desde la Cancelación,
        # que si no serviría de atajo para saltarse las fases intermedias).
        if self._sin_orden(destino):
            avanza = destino != self._fase_confirmada
        else:
            avanza = destino > self._fase_maxima
        if avanza and not self._puede_avanzar(self._fase_maxima, destino):
            self.vars['Fase Actual'].set(config.FASES[self._fase_confirmada])
            return
        self._on_current_phase_changed()

    def _puede_avanzar(self, origen, destino):
        """Valida las fases que hay que completar para pasar de `origen` a `destino`."""
        if config.FASES[destino] in config.FASES_SIN_ORDEN:
            requeridas = [0]  # Solo la Recepción.
        else:
            requeridas = range(origen, destino)
        for indice in requeridas:
            if not self._validate_phase(indice):
                if self.phase_accessible(indice):
                    self.show_phase(indice)
                return False
        return True

    def _on_current_phase_changed(self):
        index = self.current_index()
        self._fase_confirmada = index
        if config.FASES[index] not in config.FASES_SIN_ORDEN:
            self._fase_maxima = max(self._fase_maxima, index)
        color = theme.PHASE_COLORS[index]
        self.fase_menu.configure(fg_color=color, button_color=theme.darken(color, 0.1),
                                 button_hover_color=theme.darken(color, 0.25))
        for phase in self.phases:
            if phase.is_locked():
                phase.collapse()
            phase.refresh_header()
        self.prev_button.configure(state='normal' if self._fase_anterior(index) is not None else 'disabled')
        self.next_button.configure(state='normal' if self._fase_siguiente(index) is not None else 'disabled')
        self.show_phase(index)

    def _fase_siguiente(self, index):
        """Fase a la que lleva "Siguiente" (None si no hay): nunca a la Cancelación."""
        siguiente = index + 1
        if self._sin_orden(index) or siguiente >= len(config.FASES) or self._sin_orden(siguiente):
            return None
        return siguiente

    def _fase_anterior(self, index):
        """Fase a la que lleva "Anterior" (None si no hay).

        Desde la Cancelación se vuelve a la fase más avanzada a la que se llegó.
        """
        if self._sin_orden(index):
            return self._fase_maxima
        return index - 1 if index > 0 else None

    def _next_phase(self):
        current_index = self.current_index()
        siguiente = self._fase_siguiente(current_index)
        if siguiente is None:
            return
        if not self._validate_phase(current_index):
            self.show_phase(current_index)
            return
        self.phases[current_index].collapse()
        self.set_current_phase(siguiente)

    def _previous_phase(self):
        anterior = self._fase_anterior(self.current_index())
        if anterior is not None:
            self.set_current_phase(anterior)

    def _validate_phase(self, phase_index):
        """Valida los campos obligatorios y el formato de fecha/hora de una fase. True si está bien."""
        self._normalizar_fecha_hora(phase_index)
        problemas = [f"Falta: {name}" for name in self._campos_faltantes(phase_index)]
        problemas += self._formatos_invalidos(phase_index)
        problemas += self.phases[phase_index].problemas()
        if problemas:
            messagebox.showwarning(
                "Campos Obligatorios",
                f"Por favor, corrija lo siguiente en la fase "
                f"«{config.FASES[phase_index]}» antes de continuar:\n\n"
                + "\n".join(f"• {problema}" for problema in problemas),
                parent=self,
            )
            return False
        return True

    @staticmethod
    def _claves_fecha_hora(phase_index):
        n = phase_index + 1
        return f'F{n}_Fecha', f'F{n}_Hora'

    def _normalizar_fecha_hora(self, phase_index):
        """Pasa la fecha y la hora de la fase al formato canónico (p. ej. "2:30 p.m." -> "02:30 PM")."""
        for key, normalizar in zip(self._claves_fecha_hora(phase_index),
                                   (fechas.normalizar_fecha, fechas.normalizar_hora)):
            if key in self.vars:
                valor = self.vars[key].get()
                if normalizar(valor) != valor:
                    self.vars[key].set(normalizar(valor))

    def _formatos_invalidos(self, phase_index):
        """Mensajes de fecha u hora escritas que no se pueden leer."""
        problemas = []
        for key, valida, formato in zip(self._claves_fecha_hora(phase_index),
                                        (fechas.fecha_valida, fechas.hora_valida),
                                        ("dd/mm/aaaa", "hh:mm am/pm")):
            texto = self.vars[key].get().strip() if key in self.vars else ''
            if texto and not valida(texto):
                problemas.append(f"{config.FIELD_NAMES.get(key, key)} no es válida "
                                 f"(«{texto}»; use {formato}).")
        return problemas

    def _campos_faltantes(self, phase_index):
        """Nombres legibles de los campos obligatorios vacíos de una fase."""
        return [
            config.FIELD_NAMES.get(key, key)
            for key in catalogo.campos_obligatorios(phase_index)
            if key in self.vars and not self.vars[key].get().strip()
        ]

    def _fase_alcanzada(self, boleta_data):
        """Fase más avanzada del avance normal (sin contar Cancelación) de una boleta guardada.

        Normalmente la más avanzada con operador. Si la fase guardada en
        `Fase Actual` va más adelante (se pulsó "Siguiente" y se guardó) y las
        fases previas están completas, se respeta esa.
        """
        alcanzada = 0
        for indice in range(len(config.FASES)):
            operador = boleta_data.get(f'F{indice + 1}_Operador')
            if not self._sin_orden(indice) and operador and str(operador).strip():
                alcanzada = indice
        guardada = str(boleta_data.get('Fase Actual', '') or '')
        if guardada in config.FASES:
            destino = config.FASES.index(guardada)
            if (not self._sin_orden(destino) and destino > alcanzada
                    and all(not self._campos_faltantes(i) for i in range(destino))):
                alcanzada = destino
        return alcanzada

    def _fase_al_abrir(self, boleta_data):
        """Fase con la que se abre una boleta guardada: la Cancelación si está cancelada, o la alcanzada."""
        detectada = config.FASES.index(PhaseDetector.detectar_fase_actual(boleta_data))
        return detectada if self._sin_orden(detectada) else self._fase_maxima

    # --- Carga / guardado --------------------------------------------------
    def populate_form(self):
        """Carga la boleta guardada. Devuelve False (y cierra la ventana) si no existe."""
        boleta_data = self.parent_app.get_boleta_by_id(self.boleta_id)
        if boleta_data is None:
            messagebox.showerror("Error", "No se encontró la boleta.", parent=self)
            self.destroy()
            return False

        self._cargar_valores(boleta_data, self.vars)

        # Carga específica de cada fase (fallos, motivo de cancelación, etc.).
        for phase in self.phases:
            phase.on_populate(boleta_data)

        self._fase_maxima = self._fase_alcanzada(boleta_data)
        self.set_current_phase(self._fase_al_abrir(boleta_data))
        return True

    def _cargar_valores(self, boleta_data, keys):
        """Pone en las variables `keys` los valores de una boleta guardada."""
        for key in keys:
            var = self.vars[key]
            # El repositorio ya devuelve los vacíos como '' (nunca NaN).
            value = boleta_data.get(key, '')
            if value is None:
                value = ''
            if isinstance(var, tk.BooleanVar):
                var.set(str(value).lower() == 'true')
            else:
                var.set(str(value))

    def copiar_recepcion(self, boleta_id):
        """Copia toda la Recepción de otra boleta (para usuarios con varias impresiones).

        La fecha y hora quedan las de ahora y el nombre del archivo se
        recalcula con el número de boleta y de impresión siguientes.
        """
        boleta_data = self.parent_app.get_boleta_by_id(boleta_id)
        if boleta_data is None:
            return
        recepcion = self.phases[0]
        self._cargar_valores(boleta_data, recepcion.keys - {'F1_Fecha', 'F1_Hora'})
        recepcion.on_populate(boleta_data)
        recepcion._update_part_name(forzar=True)

    def guardar_cambios(self):
        # La Recepción siempre debe estar completa (si no, se guardarían boletas
        # vacías); las demás fases, solo si ya tienen operador asignado.
        for i in range(len(config.FASES)):
            operator_key = f'F{i + 1}_Operador'
            iniciada = operator_key in self.vars and self.vars[operator_key].get().strip()
            if (i == 0 or iniciada) and not self._validate_phase(i):
                self.show_phase(i)
                return

        form_data = {key: var.get() for key, var in self.vars.items()}
        # Si se volvió a una fase anterior, la boleta sigue en la más avanzada.
        detectada = config.FASES.index(PhaseDetector.detectar_fase_actual(form_data))
        form_data['Fase Actual'] = config.FASES[max(self._fase_maxima, detectada)]
        if not self.boleta_id:
            form_data['ID Boleta'] = self.parent_app.get_next_id()

        # Datos específicos de cada fase (p. ej. la lista de fallos en JSON).
        for phase in self.phases:
            phase.on_collect(form_data)

        # Si no se pudo guardar (p. ej. la base de datos está ocupada), la ventana sigue
        # abierta con los datos para volver a intentarlo.
        if self.boleta_id:
            if not self.parent_app.update_record(self.boleta_id, form_data, parent=self):
                return
            messagebox.showinfo("Éxito", f"Boleta #{self.boleta_id} actualizada correctamente.", parent=self)
        else:
            if not self.parent_app.add_new_record(form_data, parent=self):
                return
            messagebox.showinfo("Éxito", f"Boleta #{form_data['ID Boleta']} creada correctamente.", parent=self)
        self.destroy()
