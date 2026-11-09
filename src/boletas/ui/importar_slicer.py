"""Botón "Desde PrusaSlicer…": llena datos de la boleta a partir del slicer.

Según la fase donde se ponga, el botón llena:
- **gramos y tiempo** (`gramos_key`, `tiempo_key`): Revisión.
- **parámetros** (`parametros=True`): material, resolución (altura de capa) y
  relleno de la Recepción. La capa y el relleno se ajustan a la opción más
  cercana de la boleta; un filamento que no está en la lista va a "Otro".

Abre un selector de archivo, llama a `prusaslicer.leer_trabajo` en segundo
plano (slicear un modelo puede tardar) y escribe el resultado en las variables
del formulario. Si cambia algo que ya estaba lleno o tuvo que aproximar un
valor, lo avisa. La lectura está en `boletas/prusaslicer.py` y la conversión a
opciones en `boletas/catalogo.py`.
"""

import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import catalogo, config, prusaslicer
from . import theme

TEXTO_BOTON = "Desde PrusaSlicer…"

_TIPOS_ARCHIVO = [
    ("Archivos de PrusaSlicer", " ".join(f"*{e}" for e in prusaslicer.EXTENSIONES)),
    ("G-code", "*.gcode *.bgcode"),
    ("Proyecto 3MF", "*.3mf"),
    ("Modelo STL/OBJ", "*.stl *.obj"),
]


def fila_prusaslicer(section, gramos_key=None, tiempo_key=None, parametros=False):
    """Fila con el botón y una ayuda que dice qué se va a llenar."""
    que = []
    if parametros:
        que.append("material, resolución y relleno")
    if gramos_key:
        que.append("gramos y tiempo")
    row = section.new_row()
    section.label(row, 0, "PRUSASLICER", "Llena " + " + ".join(que))
    celda = section.cell(row, 1, colspan=3)
    boton_prusaslicer(section, celda, gramos_key, tiempo_key, parametros).pack(side="left")
    ctk.CTkLabel(celda, text="G-code (.gcode/.bgcode), proyecto .3mf o modelo .stl",
                 font=theme.font(10), text_color=theme.HINT).pack(side="left", padx=(10, 0))
    return row


def boton_prusaslicer(section, parent, gramos_key=None, tiempo_key=None, parametros=False):
    """Crea (sin ubicar) el botón de importar desde PrusaSlicer."""
    boton = ctk.CTkButton(parent, text=TEXTO_BOTON, width=150,
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
            boton.configure(state="normal", text=TEXTO_BOTON)
        if isinstance(resultado, Exception) or resultado is None:
            messagebox.showerror("PrusaSlicer", str(resultado or "No se pudo leer el archivo."),
                                 parent=section.form)
            return

        nuevos, avisos = {}, []
        if gramos_key and tiempo_key:
            nuevos[gramos_key] = resultado.gramos_texto
            nuevos[tiempo_key] = resultado.tiempo_hhmm
            if resultado.gramos_estimados:
                avisos.append(f"El perfil no tiene densidad de filamento: los {resultado.gramos_texto} g "
                              "se estimaron con el volumen.")
        if parametros:
            parametros_nuevos, avisos_parametros = _parametros(resultado)
            nuevos.update(parametros_nuevos)
            avisos += avisos_parametros

        avisos = _aplicar(section.form, nuevos) + avisos
        if avisos:
            messagebox.showinfo(
                "PrusaSlicer",
                f"Datos tomados de «{os.path.basename(ruta)}».\n\n" + "\n".join(f"• {a}" for a in avisos),
                parent=section.form)

    boton.configure(command=importar)
    return boton


def _parametros(resultado):
    """Material, resolución y relleno del trabajo como opciones de la boleta, más avisos."""
    nuevos, avisos = {}, []

    material, detalle = catalogo.material_desde_slicer(resultado.filamento)
    if material:
        nuevos['Material'] = material
        nuevos['Material_Otro_Detalle'] = detalle
    elif resultado.filamento:
        avisos.append(f"El filamento «{resultado.filamento}» no corresponde a ningún material.")

    for clave, valor, opciones, unidad in (
            ('Resolucion', resultado.capa, config.RESOLUCION_OPTIONS, " mm"),
            ('Relleno', resultado.relleno, config.RELLENO_OPTIONS, " %")):
        opcion = catalogo.opcion_cercana(opciones, valor)
        if not opcion:
            continue
        nuevos[clave] = opcion
        if float(opcion) != float(valor):
            avisos.append(f"{config.FIELD_NAMES.get(clave, clave)}: el archivo usa {valor:g}{unidad}; "
                          f"se marcó {opcion}{unidad}, la opción más cercana.")
    return nuevos, avisos


def _aplicar(form, nuevos):
    """Escribe los valores y avisa a las fases. Devuelve los cambios sobre valores ya llenos.

    No se avisa si el valor anterior era el predeterminado de una boleta nueva.
    """
    por_defecto = {'Resolucion': config.RESOLUCION_DEFAULT, 'Relleno': config.RELLENO_DEFAULT}
    cambios = []
    for clave, valor in nuevos.items():
        anterior = form.vars[clave].get().strip()
        if (anterior and anterior != valor and anterior != por_defecto.get(clave)
                and clave != 'Material_Otro_Detalle'):
            cambios.append(f"{config.FIELD_NAMES.get(clave, clave)}: {anterior} → {valor}")
        form.vars[clave].set(valor)
    for fase in form.phases:
        fase.on_valores_externos(set(nuevos))
    return cambios
