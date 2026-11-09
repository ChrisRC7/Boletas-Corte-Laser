"""Botón «✉ …» que abre en Outlook el correo de notificación de una fase.

Junta los datos del formulario, revisa que no falte nada (`correos.faltantes`),
arma el correo (`correos.armar`) y lo abre como borrador en Outlook
(`outlook.abrir_borrador`) en segundo plano. Cuando el borrador se abrió,
llama a `al_abrir()` para que la fase marque su casilla de "correo enviado".
"""

from tkinter import messagebox

import customtkinter as ctk

from .. import correos, outlook


def boton_correo(section, parent, tipo, texto, al_abrir=None, antes=None, width=170):
    """Crea (sin ubicar) el botón del correo `tipo` (ver `correos`).

    `antes()` (opcional) se llama justo antes de armar el correo, p. ej. para
    poner la fecha y hora de ahora si están vacías.
    """
    boton = ctk.CTkButton(parent, text=texto, width=width,
                          fg_color=section.color, hover_color=section.hover_color)

    def abrir():
        if antes:
            antes()
        form = section.form
        datos = {clave: var.get() for clave, var in form.vars.items()}
        datos['ID Boleta'] = form.boleta_id if form.boleta_id is not None else form.parent_app.get_next_id()
        faltan = correos.faltantes(tipo, datos)
        if faltan:
            messagebox.showwarning(
                "Faltan datos para el correo",
                "Complete estos datos antes de abrir el correo:\n\n"
                + "\n".join(f"• {campo}" for campo in faltan),
                parent=form,
            )
            return
        correo = correos.armar(tipo, datos)
        boton.configure(state="disabled", text="Abriendo Outlook…")

        def tarea():
            try:
                outlook.abrir_borrador(correo)
            except outlook.OutlookError as error:
                return error
            return None

        def terminar(error):
            boton.configure(state="normal", text=texto)
            if error:
                messagebox.showerror("Outlook", str(error), parent=form)
            elif al_abrir:
                al_abrir()

        form.en_segundo_plano(tarea, terminar)

    boton.configure(command=abrir)
    return boton
