"""Ventana de Configuración: edita los ajustes de `config.py` sin recompilar.

Muestra los valores editables (`ajustes.EDITABLES`) en pestañas, los valida
con `ajustes.validar` y los guarda con `ajustes.guardar` en
`configuracion.json`. No contiene reglas de negocio: solo convierte lo que se
escribe en los widgets a valores de Python.

Los cambios se aplican a las boletas que se abran después de guardar. El
cambio del archivo de datos (Excel) requiere reiniciar la aplicación.
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .. import ajustes, config
from . import theme
from .tabla_editable import TablaEditable

COLOR = theme.PHASE_COLORS[0]


def _lista_texto(valores):
    return ", ".join(str(v) for v in valores)


def _lista_desde_texto(texto, convertir=str):
    return [convertir(parte.strip()) for parte in texto.split(",") if parte.strip()]


def _numero(texto):
    """'50' -> 50, '2.5' -> 2.5 (los enteros se guardan como enteros)."""
    valor = float(texto.strip().replace(",", "."))
    return int(valor) if valor.is_integer() else valor


class ConfigWindow(ctk.CTkToplevel):

    def __init__(self, parent_app, al_guardar=None):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.al_guardar = al_guardar
        self.title("Configuración")
        self.geometry("860x640")
        self.minsize(760, 520)
        self.configure(fg_color=theme.BG)
        self.campos = {}  # nombre -> tk.Variable de los campos sencillos

        self._construir(ajustes.valores_actuales())
        self.after(200, self._al_frente)

    def _al_frente(self):
        self.lift()
        self.focus_force()

    # --- Construcción -------------------------------------------------------
    def _construir(self, valores):
        for hijo in self.winfo_children():
            hijo.destroy()
        self.campos = {}

        botones = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=0)
        botones.pack(side="bottom", fill="x")
        neutral = dict(fg_color=theme.NEUTRAL, hover_color=theme.darken(theme.NEUTRAL))
        ctk.CTkButton(botones, text="Restaurar valores por defecto", width=200, command=self._restaurar,
                      **neutral).pack(side="left", padx=12, pady=10)
        ctk.CTkButton(botones, text="💾  Guardar", width=130, font=theme.font(13, "bold"),
                      fg_color=theme.SUCCESS, hover_color=theme.darken(theme.SUCCESS),
                      command=self._guardar).pack(side="right", padx=12, pady=10)
        ctk.CTkButton(botones, text="Cancelar", width=100, command=self.destroy,
                      **neutral).pack(side="right", pady=10)

        self.pestanas = ctk.CTkTabview(self, fg_color=theme.PAPER, segmented_button_selected_color=COLOR,
                                       command=self._al_cambiar_pestana)
        self.pestanas.pack(expand=True, fill="both", padx=10, pady=(6, 4))
        self._pestana_general(self._pagina("General"), valores)
        self._pestana_opciones(self._pagina("Opciones"), valores)
        self._pestana_usos(self._pagina("Usos"), valores)
        self._pestana_impresoras(self._pagina("Impresoras"), valores)
        self._pestana_colores(self._pagina("Colores"), valores)

    def _pagina(self, nombre):
        pestana = self.pestanas.add(nombre)
        pagina = ctk.CTkScrollableFrame(pestana, fg_color=theme.PAPER)
        pagina.pack(expand=True, fill="both")
        pagina.grid_columnconfigure(1, weight=1)
        return pagina

    def _fila(self, pagina, fila, nombre, titulo, valor, ayuda=None):
        """Etiqueta + campo de texto ligado a self.campos[nombre]."""
        ctk.CTkLabel(pagina, text=titulo, font=theme.font(12, "bold"), text_color=theme.TEXT,
                     anchor="w").grid(row=fila, column=0, sticky="w", padx=(8, 12), pady=(8, 0))
        self.campos[nombre] = tk.StringVar(value=str(valor))
        ctk.CTkEntry(pagina, textvariable=self.campos[nombre], font=theme.font(12),
                     border_color=theme.SEPARATOR).grid(row=fila, column=1, sticky="ew", padx=(0, 8), pady=(8, 0))
        if ayuda:
            ctk.CTkLabel(pagina, text=ayuda, font=theme.font(10), text_color=theme.HINT, anchor="w",
                         justify="left").grid(row=fila + 1, column=1, sticky="w", padx=(0, 8))

    def _nota(self, pagina, fila, texto):
        ctk.CTkLabel(pagina, text=texto, font=theme.font(11), text_color=theme.HINT, anchor="w",
                     justify="left", wraplength=760).grid(row=fila, column=0, columnspan=2, sticky="w",
                                                          padx=8, pady=(4, 8))

    def _pestana_general(self, p, v):
        self._fila(p, 0, 'EXCEL_FILE', "Archivo de datos", v['EXCEL_FILE'],
                   "Ruta del Excel de boletas. Si la cambia, reinicie la aplicación.")
        self._fila(p, 2, 'PRECIO_POR_GRAMO', "Precio por gramo (₡)", v['PRECIO_POR_GRAMO'])
        self._fila(p, 4, 'GRAMOS_POR_ROLLO', "Gramos por rollo", v['GRAMOS_POR_ROLLO'],
                   "Material que trae un rollo de filamento (se usa para el orden de impresión).")
        self._fila(p, 6, 'AD_DOMINIO_CORREO', "Dominio de los correos", v['AD_DOMINIO_CORREO'])
        self._fila(p, 8, 'AD_TIMEOUT_SEGUNDOS', "Espera máxima del AD (s)", v['AD_TIMEOUT_SEGUNDOS'])
        self._fila(p, 10, 'PRUSASLICER_RUTA', "PrusaSlicer (consola)", v['PRUSASLICER_RUTA'],
                   "Ruta de prusa-slicer-console.exe. Vacío = buscarlo en Archivos de programa.")
        self._fila(p, 12, 'PRUSASLICER_PERFIL', "Perfil para STL (.ini)", v['PRUSASLICER_PERFIL'],
                   "PrusaSlicer > Archivo > Exportar > Exportar configuración. "
                   "Los .3mf y G-code no lo necesitan.")
        self._fila(p, 14, 'PRUSASLICER_TIMEOUT_SEGUNDOS', "Espera máxima del slicer (s)",
                   v['PRUSASLICER_TIMEOUT_SEGUNDOS'])
        self._fila(p, 16, 'DENSIDAD_FILAMENTO', "Densidad del filamento (g/cm³)", v['DENSIDAD_FILAMENTO'],
                   "Solo si el perfil de PrusaSlicer no la trae y reporta 0 g.")

    def _pestana_opciones(self, p, v):
        self._nota(p, 0, "Escriba las opciones separadas por comas, en el orden en que se muestran.")
        self._fila(p, 1, 'MATERIAL_OPTIONS', "Materiales", _lista_texto(v['MATERIAL_OPTIONS']),
                   f"«{config.MATERIAL_OTRO}» habilita un campo para escribir otro material.")
        self._fila(p, 3, 'RESOLUCION_OPTIONS', "Resoluciones (mm)", _lista_texto(v['RESOLUCION_OPTIONS']))
        self._fila(p, 5, 'RESOLUCION_DEFAULT', "Resolución por defecto", v['RESOLUCION_DEFAULT'])
        self._fila(p, 7, 'RELLENO_OPTIONS', "Rellenos (%)", _lista_texto(v['RELLENO_OPTIONS']))
        self._fila(p, 9, 'RELLENO_DEFAULT', "Relleno por defecto", v['RELLENO_DEFAULT'])
        self._fila(p, 11, 'CONFIRMACION_OPTIONS', "Confirmación del usuario",
                   _lista_texto(v['CONFIRMACION_OPTIONS']), "Opciones de la Fase 3 (Impresión).")

    def _pestana_usos(self, p, v):
        self._nota(p, 0, "Prioridad: menor número = se imprime antes. «Pide detalle» habilita el campo "
                         "«Indicar» (curso o evento).")
        self.tabla_usos = TablaEditable(p, [
            {"clave": "nombre", "titulo": "Uso", "tipo": "texto", "ancho": 280},
            {"clave": "prioridad", "titulo": "Prioridad", "tipo": "entero", "ancho": 90},
            {"clave": "detalle", "titulo": "Pide detalle", "tipo": "bool", "ancho": 100, "defecto": False},
        ], v['USOS'], COLOR)
        self.tabla_usos.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4)
        self._fila(p, 2, 'PRIORIDAD_POR_DEFECTO', "Prioridad sin uso", v['PRIORIDAD_POR_DEFECTO'],
                   "Para boletas cuyo uso no está en la lista.")

    def _pestana_impresoras(self, p, v):
        self.campos['USAR_TIPO_IMPRESORA'] = tk.BooleanVar(value=v['USAR_TIPO_IMPRESORA'])
        ctk.CTkCheckBox(p, text="Distinguir tipos de impresora (se pide en la Revisión y se muestra en la Impresión)",
                        variable=self.campos['USAR_TIPO_IMPRESORA'], font=theme.font(12),
                        fg_color=COLOR, hover_color=theme.darken(COLOR)).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 0))
        self._fila(p, 1, 'TIPOS_IMPRESORA', "Tipos de impresora", _lista_texto(v['TIPOS_IMPRESORA']),
                   f"Separados por comas. En la Revisión se añade la opción «{config.TIPO_IMPRESORA_CUALQUIERA}».")
        self._nota(p, 3, "«Activa» desmarcada saca la impresora de la Fase 3 y del orden de impresión "
                         "(p. ej. si está en mantenimiento).")
        self.tabla_impresoras = TablaEditable(p, [
            {"clave": "numero", "titulo": "Número", "tipo": "entero", "ancho": 80},
            {"clave": "tipo", "titulo": "Tipo", "tipo": "opcion", "ancho": 200, "opciones": self._tipos_escritos},
            {"clave": "activa", "titulo": "Activa", "tipo": "bool", "ancho": 70},
        ], v['IMPRESORAS'], COLOR)
        self.tabla_impresoras.grid(row=4, column=0, columnspan=2, sticky="ew", padx=4)

    def _pestana_colores(self, p, v):
        self._nota(p, 0, "Colores que se ofrecen en la Recepción según el material. Desmarque «Disponible» "
                         "cuando se acabe un color. Un material sin colores permite escribir el color a mano.")
        filas = [dict(c, material=material)
                 for material, colores in v['COLORES_POR_MATERIAL'].items() for c in colores]
        self.tabla_colores = TablaEditable(p, [
            {"clave": "material", "titulo": "Material", "tipo": "opcion", "ancho": 180,
             "opciones": self._materiales_escritos},
            {"clave": "color", "titulo": "Color", "tipo": "texto", "ancho": 200},
            {"clave": "disponible", "titulo": "Disponible", "tipo": "bool", "ancho": 90},
        ], filas, COLOR)
        self.tabla_colores.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4)

    # --- Opciones dependientes de otras pestañas ---------------------------
    def _tipos_escritos(self):
        return _lista_desde_texto(self.campos['TIPOS_IMPRESORA'].get()) if 'TIPOS_IMPRESORA' in self.campos else []

    def _materiales_escritos(self):
        return _lista_desde_texto(self.campos['MATERIAL_OPTIONS'].get())

    def _al_cambiar_pestana(self):
        self.tabla_impresoras.actualizar_opciones()
        self.tabla_colores.actualizar_opciones()

    # --- Guardar / restaurar -----------------------------------------------
    def _recolectar(self):
        """Convierte lo escrito en valores. Lanza ValueError con un mensaje legible."""
        c = {nombre: var.get() for nombre, var in self.campos.items()}
        try:
            valores = {
                'EXCEL_FILE': c['EXCEL_FILE'].strip(),
                'AD_DOMINIO_CORREO': c['AD_DOMINIO_CORREO'].strip(),
                'AD_TIMEOUT_SEGUNDOS': int(_numero(c['AD_TIMEOUT_SEGUNDOS'])),
                'PRECIO_POR_GRAMO': _numero(c['PRECIO_POR_GRAMO']),
                'GRAMOS_POR_ROLLO': _numero(c['GRAMOS_POR_ROLLO']),
                'PRUSASLICER_RUTA': c['PRUSASLICER_RUTA'].strip().strip('"'),
                'PRUSASLICER_PERFIL': c['PRUSASLICER_PERFIL'].strip().strip('"'),
                'PRUSASLICER_TIMEOUT_SEGUNDOS': int(_numero(c['PRUSASLICER_TIMEOUT_SEGUNDOS'])),
                'DENSIDAD_FILAMENTO': float(_numero(c['DENSIDAD_FILAMENTO'])),
                'PRIORIDAD_POR_DEFECTO': int(_numero(c['PRIORIDAD_POR_DEFECTO'])),
                'MATERIAL_OPTIONS': _lista_desde_texto(c['MATERIAL_OPTIONS']),
                'RESOLUCION_OPTIONS': _lista_desde_texto(c['RESOLUCION_OPTIONS'], _numero),
                'RESOLUCION_DEFAULT': str(_numero(c['RESOLUCION_DEFAULT'])),
                'RELLENO_OPTIONS': _lista_desde_texto(c['RELLENO_OPTIONS'], lambda t: int(_numero(t))),
                'RELLENO_DEFAULT': str(int(_numero(c['RELLENO_DEFAULT']))),
                'CONFIRMACION_OPTIONS': _lista_desde_texto(c['CONFIRMACION_OPTIONS']),
                'USAR_TIPO_IMPRESORA': bool(c['USAR_TIPO_IMPRESORA']),
                'TIPOS_IMPRESORA': _lista_desde_texto(c['TIPOS_IMPRESORA']),
            }
        except ValueError:
            raise ValueError("Revise los números: hay un valor numérico que no es válido.") from None

        try:
            valores['USOS'] = self.tabla_usos.valores()
        except ValueError as error:
            raise ValueError(f"Usos — {error}") from None
        try:
            valores['IMPRESORAS'] = self.tabla_impresoras.valores()
        except ValueError as error:
            raise ValueError(f"Impresoras — {error}") from None
        try:
            colores = {}
            for fila in self.tabla_colores.valores():
                colores.setdefault(fila['material'], []).append(
                    {"color": fila['color'], "disponible": fila['disponible']})
            valores['COLORES_POR_MATERIAL'] = colores
        except ValueError as error:
            raise ValueError(f"Colores — {error}") from None
        return valores

    def _guardar(self):
        try:
            valores = self._recolectar()
        except ValueError as error:
            messagebox.showwarning("Configuración", str(error), parent=self)
            return
        errores = ajustes.validar(valores)
        if errores:
            messagebox.showwarning("Configuración", "Corrija lo siguiente:\n\n"
                                   + "\n".join(f"• {e}" for e in errores), parent=self)
            return

        excel_anterior = config.EXCEL_FILE
        try:
            ajustes.guardar(valores)
        except OSError as error:
            messagebox.showerror("Configuración", f"No se pudo guardar la configuración: {error}", parent=self)
            return

        mensaje = "Configuración guardada. Se aplica a las boletas que abra a partir de ahora."
        if config.EXCEL_FILE != excel_anterior:
            mensaje += "\n\nCambió el archivo de datos: reinicie la aplicación para usarlo."
        messagebox.showinfo("Configuración", mensaje, parent=self)
        if self.al_guardar:
            self.al_guardar()
        self.destroy()

    def _restaurar(self):
        if not messagebox.askyesno("Configuración", "¿Volver a los valores por defecto?\n"
                                   "Se perderán los cambios guardados en la configuración.", parent=self):
            return
        try:
            ajustes.restaurar()
        except OSError as error:
            messagebox.showerror("Configuración", f"No se pudo restaurar: {error}", parent=self)
            return
        self._construir(ajustes.valores_actuales())
        if self.al_guardar:
            self.al_guardar()
