"""Ventana "Orden de impresión": muestra e imprime el plan del día.

Pide el estado al `PlanificadorService` (trabajos pendientes e impresoras
ocupadas), calcula el plan con `planificador.planificar` y lo muestra por
impresora. El operador puede sacar impresoras del plan (p. ej. si una está
ocupada con algo que no está en las boletas) y recalcular. El botón Imprimir
manda el reporte en texto a la impresora predeterminada de Windows.
"""

import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

from .. import planificador
from . import theme

COLOR = theme.PHASE_COLORS[2]


class PlanWindow(ctk.CTkToplevel):

    def __init__(self, parent_app, servicio):
        super().__init__(parent_app)
        self.servicio = servicio
        self.plan = None
        self.title("Orden de impresión del día")
        self.geometry("1180x700")
        self.minsize(900, 520)
        self.configure(fg_color=theme.BG)

        self._construir()
        self.recalcular(releer=True)
        self.after(200, self._al_frente)

    def _al_frente(self):
        self.lift()
        self.focus_force()

    # --- Construcción -------------------------------------------------------
    def _construir(self):
        encabezado = ctk.CTkFrame(self, fg_color=COLOR, corner_radius=0)
        encabezado.pack(fill="x")
        ctk.CTkLabel(encabezado, text="ORDEN DE IMPRESIÓN", font=theme.font(16, "bold"),
                     text_color="white").pack(side="left", padx=16, pady=8)
        self.generado_label = ctk.CTkLabel(encabezado, text="", font=theme.font(12), text_color="white")
        self.generado_label.pack(side="right", padx=16)

        botones = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=0)
        botones.pack(side="bottom", fill="x")
        neutral = dict(fg_color=theme.NEUTRAL, hover_color=theme.darken(theme.NEUTRAL))
        ctk.CTkButton(botones, text="🔄  Recalcular", width=130, command=lambda: self.recalcular(releer=True),
                      **neutral).pack(side="left", padx=12, pady=10)
        ctk.CTkButton(botones, text="Cerrar", width=100, command=self.destroy,
                      **neutral).pack(side="right", padx=12, pady=10)
        ctk.CTkButton(botones, text="🖨  Imprimir", width=130, font=theme.font(13, "bold"),
                      fg_color=COLOR, hover_color=theme.darken(COLOR),
                      command=self.imprimir).pack(side="right", pady=10)

        # Impresoras: casilla para incluir/excluir cada una del plan.
        marco = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=6)
        marco.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(marco, text="IMPRESORAS", font=theme.font(12, "bold"), text_color=theme.TEXT).grid(
            row=0, column=0, sticky="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(marco, text="Desmarque las que no se deben usar hoy. Las ocupadas se toman de las boletas "
                                 "en Impresión (inicio + tiempo estimado).",
                     font=theme.font(10), text_color=theme.HINT).grid(row=0, column=1, columnspan=3, sticky="w")
        self.impresoras_frame = ctk.CTkFrame(marco, fg_color="transparent")
        self.impresoras_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=6, pady=(0, 6))
        self.disponibles = {}  # número -> BooleanVar

        # Plan por impresora.
        tabla_frame = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=6)
        tabla_frame.pack(expand=True, fill="both", padx=12, pady=4)
        columnas = ('Impresora', 'Orden', 'Inicio', 'Fin', 'Boleta', 'Usuario', 'Filamento',
                    'Gramos', 'Tiempo', 'Prioridad', 'Nota')
        anchos = (150, 55, 110, 110, 60, 200, 150, 65, 65, 70, 160)
        self.tabla = ttk.Treeview(tabla_frame, columns=columnas, show='headings')
        for columna, ancho in zip(columnas, anchos):
            self.tabla.heading(columna, text=columna)
            self.tabla.column(columna, width=ancho, minwidth=40,
                              anchor='w' if columna in ('Impresora', 'Usuario', 'Filamento', 'Nota') else 'center')
        self.tabla.tag_configure('par', background=theme.lighten(COLOR, 0.85))
        self.tabla.tag_configure('impar', background=theme.PAPER)
        barra = ctk.CTkScrollbar(tabla_frame, command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", expand=True, fill="both", padx=(6, 0), pady=6)
        barra.pack(side="right", fill="y", pady=6)

        # Resumen: rollos y boletas sin programar.
        self.resumen = ctk.CTkTextbox(self, height=120, font=(theme.FONT_FAMILY, 11), wrap="word",
                                      fg_color=theme.PAPER, border_width=0)
        self.resumen.pack(fill="x", padx=12, pady=(4, 8))

    # --- Cálculo ------------------------------------------------------------
    def recalcular(self, releer=False):
        """Recalcula el plan. Con `releer` vuelve a leer las boletas y las impresoras."""
        if releer or self.plan is None:
            self.trabajos, self.impresoras, self.sin_programar = self.servicio.estado_actual()
            self._mostrar_impresoras()
        for impresora in self.impresoras:
            impresora.disponible = self.disponibles[impresora.numero].get()
        self.plan = planificador.planificar(self.trabajos, self.impresoras, self.sin_programar)
        self._mostrar_plan()

    def _mostrar_impresoras(self):
        anteriores = {numero: var.get() for numero, var in self.disponibles.items()}
        for hijo in self.impresoras_frame.winfo_children():
            hijo.destroy()
        self.disponibles = {}
        for n, impresora in enumerate(self.impresoras):
            if impresora.libre_en > 0:
                estado = f"ocupada (boleta {impresora.boleta_en_curso})"
            else:
                estado = "libre"
            var = tk.BooleanVar(value=anteriores.get(impresora.numero, True))
            self.disponibles[impresora.numero] = var
            ctk.CTkCheckBox(
                self.impresoras_frame, text=f"{impresora.numero} · {impresora.tipo} — {estado}",
                variable=var, command=self.recalcular, font=theme.font(11), width=260,
                checkbox_width=18, checkbox_height=18, fg_color=COLOR, hover_color=theme.darken(COLOR),
            ).grid(row=n // 4, column=n % 4, sticky="w", padx=4, pady=2)

    def _mostrar_plan(self):
        plan = self.plan
        self.generado_label.configure(text=f"Calculado: {plan.hora(0)}")

        self.tabla.delete(*self.tabla.get_children())
        for n, impresora in enumerate([i for i in plan.impresoras if i.disponible]):
            propias = [a for a in plan.asignaciones if a.impresora is impresora]
            etiqueta = 'par' if n % 2 == 0 else 'impar'
            if impresora.libre_en > 0:
                self.tabla.insert('', 'end', tags=(etiqueta,), values=(
                    f"{impresora.numero} · {impresora.tipo}", "—", "ahora", plan.hora(impresora.libre_en),
                    impresora.boleta_en_curso, "(imprimiendo)",
                    planificador.nombre_filamento(impresora.filamento) if impresora.filamento else "",
                    "", "", "", "En curso"))
            for orden, a in enumerate(propias, 1):
                t = a.trabajo
                notas = []
                if a.cambio_filamento:
                    notas.append("Cambiar rollo")
                self.tabla.insert('', 'end', tags=(etiqueta,), values=(
                    f"{impresora.numero} · {impresora.tipo}", orden, plan.hora(a.inicio), plan.hora(a.fin),
                    t.boleta_id, t.usuario, planificador.nombre_filamento(t.filamento),
                    f"{t.gramos:.0f}", planificador.duracion_texto(t.minutos), t.prioridad, " · ".join(notas)))

        lineas = ["ROLLOS DEL DÍA (máximo abiertos a la vez por material y color):"]
        lineas += [f"   • {planificador.nombre_filamento(f)}: {g:.0f} g → {r} rollo(s)" for f, g, r in plan.rollos]
        if not plan.rollos:
            lineas.append("   (no hay trabajos pendientes)")
        if plan.sin_programar:
            lineas.append("")
            lineas.append("SIN PROGRAMAR:")
            lineas += [f"   • Boleta {b}: {motivo}" for b, motivo in sorted(plan.sin_programar)]
        self.resumen.configure(state="normal")
        self.resumen.delete("1.0", "end")
        self.resumen.insert("1.0", "\n".join(lineas))
        self.resumen.configure(state="disabled")

    # --- Impresión ----------------------------------------------------------
    def imprimir(self):
        """Guarda el reporte como .txt y lo manda a la impresora predeterminada."""
        nombre = f"orden_impresion_{self.plan.generado.strftime('%Y%m%d_%H%M')}.txt"
        ruta = os.path.join(tempfile.gettempdir(), nombre)
        try:
            with open(ruta, "w", encoding="utf-8-sig") as archivo:
                archivo.write(planificador.plan_a_texto(self.plan))
        except OSError as error:
            messagebox.showerror("Imprimir", f"No se pudo crear el reporte: {error}", parent=self)
            return

        if sys.platform != "win32":
            messagebox.showinfo("Imprimir", f"Reporte guardado en:\n{ruta}", parent=self)
            return
        try:
            os.startfile(ruta, "print")
        except OSError:
            # Sin impresora predeterminada: se abre el reporte para imprimirlo a mano.
            os.startfile(ruta)
            messagebox.showinfo("Imprimir", "No se pudo enviar a la impresora; se abrió el reporte "
                                            "para imprimirlo manualmente.", parent=self)
