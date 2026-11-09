"""Tabla editable genérica (filas de campos con botones para agregar y quitar).

La usa la ventana de Configuración para editar listas de registros como los
usos, las impresoras o los colores de filamento. Cada columna se describe con
un diccionario:

    {"clave": "numero", "titulo": "Número", "tipo": "entero", "ancho": 80}

Tipos: "texto", "entero", "decimal", "bool" (casilla) y "opcion" (lista
desplegable editable; `opciones` es una función que devuelve los valores, así
se pueden refrescar con `actualizar_opciones()`).
"""

import tkinter as tk

import customtkinter as ctk

from . import theme


class TablaEditable(ctk.CTkFrame):

    def __init__(self, parent, columnas, filas, color, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.columnas = columnas
        self.color = color
        self.filas = []  # [(marco, {clave: variable}, {clave: widget})]

        encabezado = ctk.CTkFrame(self, fg_color="transparent")
        encabezado.pack(fill="x")
        for columna in columnas:
            ctk.CTkLabel(encabezado, text=columna["titulo"], width=columna.get("ancho", 120),
                         anchor="w", font=theme.font(12, "bold"), text_color=theme.TEXT).pack(side="left", padx=4)

        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="x")
        ctk.CTkButton(self, text="+ Agregar fila", width=120, fg_color=color,
                      hover_color=theme.darken(color), command=self.agregar).pack(anchor="w", pady=(6, 0), padx=4)

        for fila in filas:
            self.agregar(fila)

    # --- Filas --------------------------------------------------------------
    def agregar(self, valores=None):
        valores = valores or {}
        marco = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        marco.pack(fill="x", pady=1)
        variables, widgets = {}, {}
        for columna in self.columnas:
            clave, tipo, ancho = columna["clave"], columna["tipo"], columna.get("ancho", 120)
            if tipo == "bool":
                variable = tk.BooleanVar(value=bool(valores.get(clave, columna.get("defecto", True))))
                widget = ctk.CTkCheckBox(marco, text="", variable=variable, width=ancho,
                                         checkbox_width=18, checkbox_height=18,
                                         fg_color=self.color, hover_color=theme.darken(self.color))
            else:
                variable = tk.StringVar(value=str(valores.get(clave, columna.get("defecto", ""))))
                if tipo == "opcion":
                    widget = ctk.CTkComboBox(marco, variable=variable, width=ancho, font=theme.font(12),
                                             values=[str(o) for o in columna["opciones"]()])
                else:
                    widget = ctk.CTkEntry(marco, textvariable=variable, width=ancho, font=theme.font(12),
                                          border_color=theme.SEPARATOR)
            widget.pack(side="left", padx=4)
            variables[clave], widgets[clave] = variable, widget

        fila = (marco, variables, widgets)
        ctk.CTkButton(marco, text="✕", width=28, fg_color=theme.DANGER, hover_color=theme.darken(theme.DANGER),
                      command=lambda: self._quitar(fila)).pack(side="left", padx=4)
        self.filas.append(fila)

    def _quitar(self, fila):
        fila[0].destroy()
        self.filas.remove(fila)

    def actualizar_opciones(self):
        """Vuelve a leer las opciones de las columnas desplegables."""
        for _marco, _variables, widgets in self.filas:
            for columna in self.columnas:
                if columna["tipo"] == "opcion":
                    widgets[columna["clave"]].configure(values=[str(o) for o in columna["opciones"]()])

    # --- Lectura ------------------------------------------------------------
    def valores(self):
        """Lista de diccionarios con los valores convertidos. Lanza ValueError si hay errores."""
        resultado = []
        for n, (_marco, variables, _widgets) in enumerate(self.filas, 1):
            fila = {}
            for columna in self.columnas:
                clave, tipo, titulo = columna["clave"], columna["tipo"], columna["titulo"]
                if tipo == "bool":
                    fila[clave] = bool(variables[clave].get())
                    continue
                texto = variables[clave].get().strip()
                if not texto:
                    raise ValueError(f"Fila {n}: falta «{titulo}».")
                try:
                    if tipo == "entero":
                        fila[clave] = int(texto)
                    elif tipo == "decimal":
                        fila[clave] = float(texto.replace(",", "."))
                    else:
                        fila[clave] = texto
                except ValueError:
                    raise ValueError(f"Fila {n}: «{titulo}» debe ser un número.") from None
            resultado.append(fila)
        return resultado
