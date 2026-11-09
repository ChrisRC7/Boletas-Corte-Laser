"""Botón "Desde PrusaSlicer…" para llenar gramos y tiempo de una fase.

Lo usan las fases que registran material y tiempo (Revisión y Reimpresión).
Abre un selector de archivo, llama a `prusaslicer.leer_trabajo` en segundo
plano (slicear un modelo puede tardar) y escribe el resultado en las variables
de la fase. La lógica de lectura/sliceo está en `boletas/prusaslicer.py`.
"""

import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import prusaslicer
from . import theme

_TIPOS_ARCHIVO = [
    ("Archivos de PrusaSlicer", " ".join(f"*{e}" for e in prusaslicer.EXTENSIONES)),
    ("G-code", "*.gcode *.bgcode"),
    ("Proyecto 3MF", "*.3mf"),
    ("Modelo STL/OBJ", "*.stl *.obj"),
]


def boton_prusaslicer(section, parent, gramos_key, tiempo_key):
    """Crea (sin ubicar) el botón que llena `vars[gramos_key]` y `vars[tiempo_key]`."""
    boton = ctk.CTkButton(parent, text="Desde PrusaSlicer…", width=150,
                          fg_color=section.color, hover_color=section.hover_color)

    def importar():
        ruta = filedialog.askopenfilename(
            parent=section.form, title="G-code, proyecto 3MF o modelo de PrusaSlicer",
            filetypes=_TIPOS_ARCHIVO)
        if not ruta:
            return
        boton.configure(state="disabled", text="Leyendo…")

        def tarea():
            try:
                return prusaslicer.leer_trabajo(ruta)
            except prusaslicer.ErrorSlicer as error:
                return error

        section.form.en_segundo_plano(tarea, lambda resultado: terminar(ruta, resultado))

    def terminar(ruta, resultado):
        if boton.winfo_exists():
            boton.configure(state="normal", text="Desde PrusaSlicer…")
        if isinstance(resultado, Exception) or resultado is None:
            messagebox.showerror("PrusaSlicer", str(resultado or "No se pudo leer el archivo."),
                                 parent=section.form)
            return
        section.vars[gramos_key].set(resultado.gramos_texto)
        section.vars[tiempo_key].set(resultado.tiempo_hhmm)
        if resultado.gramos_estimados:
            messagebox.showinfo(
                "PrusaSlicer",
                f"«{os.path.basename(ruta)}»: el perfil no tiene densidad de filamento, así que los "
                f"{resultado.gramos_texto} g se estimaron con el volumen. Revise el valor.",
                parent=section.form)

    boton.configure(command=importar)
    return boton


def fila_prusaslicer(section, gramos_key, tiempo_key):
    """Fila completa con el botón y una ayuda, para poner bajo los campos de material."""
    row = section.new_row()
    section.label(row, 0, "PRUSASLICER", "Llena gramos y tiempo")
    celda = section.cell(row, 1, colspan=3)
    boton_prusaslicer(section, celda, gramos_key, tiempo_key).pack(side="left")
    ctk.CTkLabel(celda, text="G-code (.gcode/.bgcode), proyecto .3mf o modelo .stl",
                 font=theme.font(10), text_color=theme.HINT).pack(side="left", padx=(10, 0))
    return row
