"""Fase 1: Recepción.

Registra los datos del usuario y de la pieza. Tiene lógica propia:

- Autocompleta los datos del usuario a partir de la cuenta o el carné
  (historial o AD). En NOMBRE DEL USUARIO también se puede escribir el correo
  o el carné: se pasan a su campo, se autocompleta todo y el nombre se
  sustituye por el nombre real del estudiante.
- Autocompleta el nombre de la pieza con el carné.
- Habilita campos de detalle según el "Uso" y el "Material" seleccionados.
- Ofrece los colores disponibles del material elegido (`config.COLORES_POR_MATERIAL`).
- Material, resolución y relleno se pueden tomar de PrusaSlicer (botón
  «Desde PrusaSlicer…», ver `ui/importar_slicer.py`).
"""

import tkinter as tk

import customtkinter as ctk

from ... import catalogo, config
from ...directorio_ad import es_carne, es_correo, es_cuenta, normalizar_cuenta
from .. import theme
from ..importar_slicer import fila_prusaslicer
from .base import PhaseSection, PAD_X, PAD_Y


class Phase1Recepcion(PhaseSection):
    index = 0

    def build_widgets(self, frame):
        # Último valor buscado por campo ('Carné'/'Cuenta'): solo se busca si cambia.
        self._buscado = {}
        # Valores que puso el autocompletado (se pueden reemplazar o borrar al
        # cambiar de usuario; lo escrito a mano después no se toca).
        self._autollenados = {}
        # Lo que se escribió en NOMBRE DEL USUARIO si era un correo o un carné:
        # mientras siga ahí, el autocompletado lo puede reemplazar por el nombre.
        self._nombre_provisional = None

        self.operator_row()

        row = self.new_row()
        nombre_entry = self.field(row, 0, 'Nombre_Usuario', "NOMBRE DEL USUARIO",
                                  "Nombre, correo o carné", colspan=3)
        nombre_entry.bind("<FocusOut>", self._on_nombre_changed)
        nombre_entry.bind("<Return>", self._on_nombre_changed)

        # CUENTA y CARNÉ autocompletan los datos del usuario (historial o AD).
        row = self.new_row()
        cuenta_entry = self.field(row, 0, 'Cuenta', "CUENTA", config.AD_DOMINIO_CORREO)
        cuenta_entry.bind("<FocusOut>", lambda _e: self._autocompletar_usuario('Cuenta'))
        self.field(row, 2, 'Carrera', "CARRERA")

        row = self.new_row()
        carne_entry = self.field(row, 0, 'Carné', "CARNÉ")
        carne_entry.bind("<FocusOut>", self._on_carne_changed)
        self.field(row, 2, 'Teléfono', "TELÉFONO")

        # USO: opciones a la izquierda y el detalle (curso/evento) a la derecha.
        row = self.new_row()
        self.label(row, 0, "USO", "1 = Prioridad más alta\nCurso y Evento tienen\nla misma prioridad")
        opciones = self.cell(row, 1)
        self.radio_group(opciones, 'Uso', catalogo.opciones_uso(), per_row=1,
                         command=self._on_uso_selected, item_width=220)
        self.label(row, 2, "INDICAR", "Curso / Evento")
        self.uso_detalle_entry = self.entry(frame, 'Uso_Detalle', state='disabled')
        self.uso_detalle_entry.grid(row=row, column=3, sticky="ew", padx=(0, PAD_X), pady=PAD_Y)

        row = self.new_row()
        self.field(row, 0, 'Nombre_Pieza', "ARCHIVO", "Boleta-carné-n.º de impresión")
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

        # COLOR: debajo del material, con los colores disponibles de ese material.
        row = self.new_row()
        self.label(row, 0, "COLOR DEL\nFILAMENTO", "Según el material")
        self.vars['Color_Filamento'] = tk.StringVar()
        self.color_combo = ctk.CTkComboBox(
            frame, variable=self.vars['Color_Filamento'], values=[], state='disabled', width=200,
            border_color=theme.SEPARATOR, button_color=self.color, button_hover_color=self.hover_color,
            font=theme.font(12), dropdown_font=theme.font(12),
        )
        self.color_combo.grid(row=row, column=1, sticky="w", padx=(0, PAD_X), pady=PAD_Y)

        # RESOLUCIÓN | RELLENO lado a lado, como en la boleta.
        row = self.new_row()
        self.label(row, 0, "RESOLUCIÓN", "Grosor de capa en el eje Z\nMás pequeño = acabado más\nfino y más tiempo")
        self.radio_group(self.cell(row, 1), 'Resolucion', config.RESOLUCION_OPTIONS,
                         per_row=3, default=config.RESOLUCION_DEFAULT, item_width=60)
        self.label(row, 2, "RELLENO (%)", "Mayor porcentaje = piezas\nmás resistentes y más tiempo")
        self.radio_group(self.cell(row, 3), 'Relleno', config.RELLENO_OPTIONS,
                         per_row=7, default=config.RELLENO_DEFAULT, item_width=50)

        fila_prusaslicer(self, parametros=True)

        row = self.new_row()
        self.field(row, 0, 'Autoriza_Recoger', "AUTORIZA A RECOGER", "Nombre y # identificación", colspan=3)

    def on_populate(self, boleta_data):
        # Restaura el estado (habilitado/deshabilitado) de los campos de detalle
        # sin borrar el color guardado aunque ya no esté disponible.
        self._on_uso_selected()
        self._set_enabled(self.material_detalle_entry, 'Material_Otro_Detalle',
                          self.vars['Material'].get() == config.MATERIAL_OTRO)
        self._actualizar_colores(limpiar=False)
        # Los datos guardados del usuario se tratan como autocompletados: si se
        # cambia el carné o la cuenta por los de otra persona, se reemplazan.
        self._buscado = {llave: self.vars[llave].get().strip() for llave in ('Carné', 'Cuenta')}
        self._autollenados = {c: self.vars[c].get().strip() for c in config.CAMPOS_DATOS_USUARIO
                              if self.vars[c].get().strip()}

    def on_valores_externos(self, claves):
        # El material llegó desde PrusaSlicer: igual que si se hubiera elegido a mano.
        if 'Material' in claves:
            self._on_material_selected()

    # --- Callbacks propios de la fase -------------------------------------
    def _on_uso_selected(self):
        self._set_enabled(self.uso_detalle_entry, 'Uso_Detalle',
                          self.vars['Uso'].get() in catalogo.usos_con_detalle())

    def _on_material_selected(self):
        self._set_enabled(self.material_detalle_entry, 'Material_Otro_Detalle',
                          self.vars['Material'].get() == config.MATERIAL_OTRO)
        self._actualizar_colores(limpiar=True)

    def _actualizar_colores(self, limpiar):
        """Carga en la lista los colores disponibles del material elegido.

        Si el material no tiene colores configurados (p. ej. "Otro"), el color
        se escribe a mano. Con `limpiar`, se borra un color que no corresponde
        al material nuevo.
        """
        material = self.vars['Material'].get()
        color = self.vars['Color_Filamento']
        if not material:
            self.color_combo.configure(values=[], state='disabled')
            return
        if not catalogo.material_tiene_colores(material):
            self.color_combo.configure(values=[], state='normal')
            return
        colores = catalogo.colores_disponibles(material)
        self.color_combo.configure(values=colores, state='readonly')
        if limpiar and color.get() not in colores:
            color.set(colores[0] if len(colores) == 1 else '')

    def _set_enabled(self, entry, key, enabled):
        if enabled:
            entry.configure(state='normal', fg_color=("#F9F9FA", "#343638"))
        else:
            self.vars[key].set('')
            entry.configure(state='disabled', fg_color=theme.BG)

    # --- Autocompletado del usuario ---------------------------------------
    def _on_nombre_changed(self, _event=None):
        """Si en el nombre se escribió un correo, una cuenta o un carné, se usa para autocompletar.

        Los correos se asumen de `config.AD_DOMINIO_CORREO`, así que basta con el
        usuario (p. ej. "chrodriguez"). Como una sola palabra también puede ser
        un nombre, en ese caso solo se reemplaza si la cuenta existe.
        """
        texto = self.vars['Nombre_Usuario'].get().strip()
        if es_carne(texto):
            campo, valor = 'Carné', texto
        elif es_correo(texto):
            campo, valor = 'Cuenta', normalizar_cuenta(texto)
        elif es_cuenta(texto):
            self._probar_cuenta_en_nombre(texto)
            return
        else:
            return  # Es un nombre: se deja tal cual.
        self._nombre_provisional = texto
        self.vars[campo].set(valor)
        if campo == 'Carné':
            self._update_part_name()
        self._autocompletar_usuario(campo, forzar=True)

    def _probar_cuenta_en_nombre(self, texto):
        """Busca `texto` como cuenta; si existe, la usa. Si no, se queda como nombre."""
        cuenta = normalizar_cuenta(texto)
        usuarios = self.form.parent_app.usuarios

        def aplicar(datos):
            # Se descarta si el operador cambió el nombre mientras se buscaba.
            if not datos or self.vars['Nombre_Usuario'].get().strip() != texto:
                return
            self.vars['Cuenta'].set(cuenta)
            self._buscado['Cuenta'] = cuenta
            self._nombre_provisional = texto
            self._llenar_datos_usuario(datos, 'Cuenta')

        datos = usuarios.datos_desde_historial('Cuenta', cuenta)
        if datos:
            aplicar(datos)
        else:
            self.form.en_segundo_plano(lambda: usuarios.datos_desde_directorio('Cuenta', cuenta), aplicar)

    def _on_carne_changed(self, _event=None):
        self._update_part_name()
        self._autocompletar_usuario('Carné')

    def _autocompletar_usuario(self, campo, forzar=False):
        """Llena nombre, cuenta, carrera, carné y teléfono a partir de la cuenta o el carné.

        Primero busca en las boletas anteriores del usuario; si no tiene, lo
        consulta en el AD (en segundo plano). Solo se busca cuando el valor
        cambió. Los datos encontrados **reemplazan** a los que había (así, si se
        escribió el carné de otra persona, basta con corregirlo); lo que el
        usuario nuevo no tenga se borra si venía de un autocompletado anterior.
        """
        valor = self.vars[campo].get().strip()
        if campo == 'Cuenta' and valor:
            valor = normalizar_cuenta(valor)  # Del correo solo se guarda el usuario.
            self.vars['Cuenta'].set(valor)
        if not valor or (self._buscado.get(campo) == valor and not forzar):
            return
        self._buscado[campo] = valor

        usuarios = self.form.parent_app.usuarios
        datos = usuarios.datos_desde_historial(campo, valor)
        if datos:
            self._llenar_datos_usuario(datos, campo)
            return

        def aplicar(datos_ad):
            # Se descarta si el operador cambió el campo mientras se consultaba el AD.
            if self.vars[campo].get().strip() != valor:
                return
            if datos_ad:
                self._llenar_datos_usuario(datos_ad, campo)
            else:
                # Usuario no encontrado: no se dejan los datos de la persona anterior.
                self._limpiar_autollenados(campo)
                self._descartar_nombre_provisional()

        self.form.en_segundo_plano(lambda: usuarios.datos_desde_directorio(campo, valor), aplicar)

    def _es_nombre_provisional(self):
        actual = self.vars['Nombre_Usuario'].get().strip()
        return self._nombre_provisional is not None and actual == self._nombre_provisional

    def _llenar_datos_usuario(self, datos, origen):
        """Reemplaza los datos del usuario por `datos` (menos el campo con el que se buscó)."""
        self._limpiar_autollenados(origen, excepto=datos)
        for campo in config.CAMPOS_DATOS_USUARIO:
            if campo != origen and datos.get(campo):
                self.vars[campo].set(datos[campo])
        self._autollenados = {c: datos[c] for c in config.CAMPOS_DATOS_USUARIO if c != origen and datos.get(c)}
        # La otra llave (cuenta/carné) ya corresponde a este usuario: no hace falta buscarla.
        for llave in ('Carné', 'Cuenta'):
            self._buscado[llave] = self.vars[llave].get().strip()
        self._nombre_provisional = None
        self._update_part_name()

    def _limpiar_autollenados(self, origen, excepto=None):
        """Borra los campos que siguen con un valor autocompletado antes (no los escritos a mano)."""
        excepto = excepto or {}
        for campo, valor in self._autollenados.items():
            if campo != origen and not excepto.get(campo) and self.vars[campo].get().strip() == valor:
                self.vars[campo].set('')
        self._autollenados = {}

    def _descartar_nombre_provisional(self):
        """Si el nombre sigue siendo el correo/carné escrito (no se encontró al usuario), se borra."""
        if self._es_nombre_provisional():
            self.vars['Nombre_Usuario'].set('')
        self._nombre_provisional = None

    # --- Nombre del archivo ------------------------------------------------
    def _nombre_archivo(self, boleta_id):
        """'<boleta>-<carné>-<n.º de impresión del usuario>', o None sin carné."""
        carne = self.vars['Carné'].get().strip()
        if not carne:
            return None
        numero = self.form.parent_app.numero_impresion(carne, boleta_id)
        return f"{boleta_id}-{carne}-{numero}"

    def _update_part_name(self, _event=None):
        boleta_id = self.form.boleta_id if self.form.boleta_id is not None else self.form.parent_app.get_next_id()
        nombre = self._nombre_archivo(boleta_id)
        if nombre:
            self.vars['Nombre_Pieza'].set(nombre)

    def on_collect(self, form_data):
        # En una boleta nueva el ID definitivo se asigna al guardar: el nombre
        # del archivo se recalcula con él (por si se abrieron dos boletas nuevas).
        if self.form.boleta_id is None and form_data.get('ID Boleta'):
            nombre = self._nombre_archivo(form_data['ID Boleta'])
            if nombre:
                form_data['Nombre_Pieza'] = nombre
