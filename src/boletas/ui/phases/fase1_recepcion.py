"""Fase 1: Recepción.

Registra los datos del usuario y de la pieza. Tiene lógica propia: autocompleta
los datos del usuario a partir de la cuenta o el carné (historial o AD),
autocompleta el nombre de la pieza con el carné y habilita campos de detalle
según el "Uso" y el "Material" seleccionados.
"""

from ... import config
from ...directorio_ad import normalizar_cuenta
from .. import theme
from .base import PhaseSection, PAD_X, PAD_Y


class Phase1Recepcion(PhaseSection):
    index = 0

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.field(row, 0, 'Nombre_Usuario', "NOMBRE DEL USUARIO", "Se llena con la cuenta o el carné", colspan=3)

        # CUENTA y CARNÉ autocompletan los datos del usuario (historial o AD).
        row = self.new_row()
        cuenta_entry = self.field(row, 0, 'Cuenta', "CUENTA", config.AD_DOMINIO_CORREO)
        cuenta_entry.bind("<FocusOut>", lambda _e: self._autocompletar_usuario('Cuenta'))
        self.field(row, 2, 'Carrera', "CARRERA")

        row = self.new_row()
        carne_entry = self.field(row, 0, 'Carné', "CARNÉ")
        carne_entry.bind("<FocusOut>", self._on_carne_changed)
        self.field(row, 2, 'Teléfono', "TELÉFONO")
        self._ultima_busqueda = None

        # USO: opciones a la izquierda y el detalle (curso/evento) a la derecha.
        row = self.new_row()
        self.label(row, 0, "USO", "1 = Prioridad más alta\nCurso y Evento tienen\nla misma prioridad")
        opciones = self.cell(row, 1)
        self.radio_group(opciones, 'Uso', config.USO_OPTIONS, per_row=1,
                         command=self._on_uso_selected, item_width=220)
        self.label(row, 2, "INDICAR", "Curso / Evento")
        self.uso_detalle_entry = self.entry(frame, 'Uso_Detalle', state='disabled')
        self.uso_detalle_entry.grid(row=row, column=3, sticky="ew", padx=(0, PAD_X), pady=PAD_Y)

        row = self.new_row()
        self.field(row, 0, 'Nombre_Pieza', "ARCHIVO", "Nombre de la pieza")
        self.field(row, 2, 'Observaciones_Usuario', "OBSERVACIONES\nDEL USUARIO")

        row = self.new_row()
        self.label(row, 0, "CANTIDAD DE COPIAS", "Marcar 0 si es solo la original")
        copias = self.entry(frame, 'Cantidad_Copias', width=80)
        copias.grid(row=row, column=1, sticky="w", padx=(0, PAD_X), pady=PAD_Y)

        # MATERIAL: opciones en una línea + campo "Otro".
        row = self.new_row()
        self.label(row, 0, "MATERIAL", "sujeto a disponibilidad")
        materiales = self.cell(row, 1, colspan=3)
        self.radio_group(materiales, 'Material', config.MATERIAL_OPTIONS,
                         command=self._on_material_selected, item_width=60)
        self.material_detalle_entry = self.entry(materiales, 'Material_Otro_Detalle', width=160, state='disabled')
        self.material_detalle_entry.grid(row=0, column=len(config.MATERIAL_OPTIONS), padx=(0, 4))

        # RESOLUCIÓN | RELLENO lado a lado, como en la boleta.
        row = self.new_row()
        self.label(row, 0, "RESOLUCIÓN", "Grosor de capa en el eje Z\nMás pequeño = acabado más\nfino y más tiempo")
        self.radio_group(self.cell(row, 1), 'Resolucion', config.RESOLUCION_OPTIONS,
                         per_row=3, default=config.RESOLUCION_DEFAULT, item_width=60)
        self.label(row, 2, "RELLENO (%)", "Mayor porcentaje = piezas\nmás resistentes y más tiempo")
        self.radio_group(self.cell(row, 3), 'Relleno', config.RELLENO_OPTIONS,
                         per_row=7, default=config.RELLENO_DEFAULT, item_width=50)

        row = self.new_row()
        self.field(row, 0, 'Autoriza_Recoger', "AUTORIZA A RECOGER", "Nombre y # identificación", colspan=3)

    def on_populate(self, boleta_data):
        # Restaura el estado (habilitado/deshabilitado) de los campos de detalle.
        self._on_uso_selected()
        self._on_material_selected()

    # --- Callbacks propios de la fase -------------------------------------
    def _on_uso_selected(self):
        self._set_enabled(self.uso_detalle_entry, 'Uso_Detalle',
                          self.vars['Uso'].get() in config.USO_CON_DETALLE)

    def _on_material_selected(self):
        self._set_enabled(self.material_detalle_entry, 'Material_Otro_Detalle',
                          self.vars['Material'].get() == config.MATERIAL_OTRO)

    def _set_enabled(self, entry, key, enabled):
        if enabled:
            entry.configure(state='normal', fg_color=("#F9F9FA", "#343638"))
        else:
            self.vars[key].set('')
            entry.configure(state='disabled', fg_color=theme.BG)

    def _on_carne_changed(self, _event=None):
        self._update_part_name()
        self._autocompletar_usuario('Carné')

    def _autocompletar_usuario(self, campo):
        """Llena nombre, cuenta, carrera, carné y teléfono a partir de la cuenta o el carné.

        Primero busca en las boletas anteriores del usuario; si no tiene, lo
        consulta en el AD (en segundo plano). Solo se llenan los campos vacíos,
        para no pisar lo que el operador ya escribió.
        """
        valor = self.vars[campo].get().strip()
        if campo == 'Cuenta' and valor:
            valor = normalizar_cuenta(valor)  # Del correo solo se guarda el usuario.
            self.vars['Cuenta'].set(valor)
        if not valor or self._ultima_busqueda == (campo, valor):
            return
        self._ultima_busqueda = (campo, valor)

        usuarios = self.form.parent_app.usuarios
        datos = usuarios.datos_desde_historial(campo, valor)
        if datos:
            self._llenar_datos_usuario(datos)
            return

        def aplicar(datos_ad):
            # Se descarta si el operador cambió el campo mientras se consultaba el AD.
            if datos_ad and self.vars[campo].get().strip() == valor:
                self._llenar_datos_usuario(datos_ad)

        self.form.en_segundo_plano(lambda: usuarios.datos_desde_directorio(campo, valor), aplicar)

    def _llenar_datos_usuario(self, datos):
        for campo in config.CAMPOS_DATOS_USUARIO:
            if datos.get(campo) and not self.vars[campo].get().strip():
                self.vars[campo].set(datos[campo])
        self._update_part_name()

    def _update_part_name(self, _event=None):
        boleta_id = self.form.boleta_id if self.form.boleta_id is not None else self.form.parent_app.get_next_id()
        carne = self.vars['Carné'].get().strip()
        if not carne:
            return
        parts = self.vars['Nombre_Pieza'].get().split('-')
        manual_part = parts[2].strip() if len(parts) == 3 and parts[2].strip() != "" else ""
        self.vars['Nombre_Pieza'].set(f"{boleta_id}-{carne}-{manual_part}")
