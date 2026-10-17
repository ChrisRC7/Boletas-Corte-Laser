"""Ventana principal: listado, búsqueda, filtros y acciones sobre boletas.

Esta clase es el "controlador" de la interfaz: reacciona a los botones y delega
el acceso a datos en `BoletaRepository` y la edición en `BoletaForm`. No conoce
detalles de pandas ni del Excel.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

from .. import config
from ..repository import BoletaRepository
from . import theme
from .boleta_form import BoletaForm


class App(ctk.CTk):
    """Ventana principal de la aplicación de Control de Impresiones."""

    FILTRO_TODOS = "Todos"

    def __init__(self):
        theme.setup()
        super().__init__()
        self.title("LAIMI - Control de Impresiones")
        self.geometry("1200x650")
        self.configure(fg_color=theme.BG)

        self.repo = BoletaRepository()
        self.repo.load()

        self.create_widgets()
        self.show_all_boletas()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- Ciclo de vida ----------------------------------------------------
    def on_closing(self):
        self.save_data()
        self.destroy()

    def save_data(self):
        """Guarda los cambios, traduciendo los errores a mensajes para el usuario."""
        try:
            self.repo.save()
        except PermissionError:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar el archivo '{self.repo.excel_file}'.\n"
                "Asegúrese de que no esté abierto.",
            )
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Ocurrió un error al guardar: {e}")

    # --- Construcción de la interfaz --------------------------------------
    def create_widgets(self):
        # Encabezado con las acciones principales
        banner = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=0)
        banner.pack(fill="x")
        ctk.CTkLabel(banner, text="▪ ▚ LAIMI", font=theme.font(24, "bold"),
                     text_color=theme.TEXT).pack(side="left", padx=(20, 30), pady=12)
        ctk.CTkLabel(banner, text="CONTROL DE IMPRESIONES", font=theme.font(22),
                     text_color=theme.TEXT).pack(side="left", pady=12)

        ctk.CTkButton(banner, text="✚  Añadir", width=110, font=theme.font(13, "bold"),
                      fg_color=theme.SUCCESS, hover_color=theme.darken(theme.SUCCESS),
                      command=self.open_new_boleta_window).pack(side="right", padx=(6, 20))
        ctk.CTkButton(banner, text="🗑  Borrar", width=110, font=theme.font(13, "bold"),
                      fg_color=theme.DANGER, hover_color=theme.darken(theme.DANGER),
                      command=self.delete_selected_boleta).pack(side="right", padx=6)

        # Búsqueda
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(search_frame, text="Buscar por:", font=theme.font(12, "bold"),
                     text_color=theme.TEXT).pack(side="left", padx=(0, 6))

        self.search_field = tk.StringVar(value=config.CAMPOS_BUSQUEDA[0])
        ctk.CTkOptionMenu(search_frame, variable=self.search_field, values=config.CAMPOS_BUSQUEDA,
                          width=130, font=theme.font(12)).pack(side="left")

        self.search_term = tk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_term, width=300, font=theme.font(12))
        search_entry.pack(side="left", padx=6, fill="x", expand=True)
        search_entry.bind("<Return>", lambda _event: self._search_boletas())

        ctk.CTkButton(search_frame, text="Buscar", width=90, command=self._search_boletas).pack(side="left", padx=(0, 6))
        ctk.CTkButton(search_frame, text="Limpiar", width=90, fg_color=theme.NEUTRAL,
                      hover_color=theme.darken(theme.NEUTRAL), command=self.show_all_boletas).pack(side="left")

        # Filtros por fase (cada botón con el color de su fase)
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(filter_frame, text="Filtrar por Fase:", font=theme.font(12, "bold"),
                     text_color=theme.TEXT).pack(side="left", padx=(0, 8))
        # El filtro activo conserva su color completo y lleva "✔"; los demás se ven atenuados.
        self.filter_buttons = {}
        opciones = [(self.FILTRO_TODOS, theme.NEUTRAL)] + list(zip(config.FASES, theme.PHASE_COLORS))
        for fase, color in opciones:
            if fase == self.FILTRO_TODOS:
                command = self.show_all_boletas
            else:
                command = lambda f=fase: self.filter_boletas(f)
            button = ctk.CTkButton(
                filter_frame, text=fase, width=0, height=30, font=theme.font(12),
                fg_color=color, hover_color=theme.darken(color), command=command,
            )
            button.pack(side="left", padx=2)
            self.filter_buttons[fase] = (button, color)

        # Tabla
        self._style_treeview()
        tree_frame = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=6)
        tree_frame.pack(expand=True, fill="both", padx=12, pady=(6, 12))

        self.tree = ttk.Treeview(tree_frame, columns=('ID', 'Cuenta', 'Fecha', 'Fase', 'Uso'), show='headings')
        self.tree.heading('ID', text='ID Boleta')
        self.tree.heading('Cuenta', text='Cuenta')
        self.tree.heading('Fecha', text='Fecha Creación')
        self.tree.heading('Fase', text='Fase Actual')
        self.tree.heading('Uso', text='Tipo de Uso')
        self.tree.column('ID', width=80, anchor='center')
        self.tree.column('Cuenta', width=200)
        self.tree.column('Fecha', width=120, anchor='center')
        self.tree.column('Fase', width=200)
        self.tree.column('Uso', width=150)
        # Cada fila lleva un tinte suave del color de su fase.
        for fase, color in zip(config.FASES, theme.PHASE_COLORS):
            self.tree.tag_configure(fase, background=theme.lighten(color, 0.82))

        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", expand=True, fill="both", padx=(6, 0), pady=6)
        scrollbar.pack(side="right", fill="y", pady=6)
        self.tree.bind("<Double-1>", self.on_double_click)

    def _style_treeview(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=theme.PAPER, fieldbackground=theme.PAPER,
                        foreground=theme.TEXT, rowheight=28, borderwidth=0,
                        font=(theme.FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background=theme.PHASE_COLORS[0], foreground="white",
                        relief="flat", font=(theme.FONT_FAMILY, 10, "bold"), padding=6)
        style.map("Treeview.Heading", background=[("active", theme.darken(theme.PHASE_COLORS[0]))])
        style.map("Treeview", background=[("selected", "#1F3B63")], foreground=[("selected", "white")])

    def refresh_treeview(self, data_df):
        self.tree.delete(*self.tree.get_children())
        for _, row in data_df.iterrows():
            values = (
                row.get('ID Boleta', ''),
                row.get('Cuenta', ''),
                row.get('F1_Fecha', ''),
                row.get('Fase Actual', ''),
                row.get('Uso', ''),
            )
            self.tree.insert('', 'end', values=values, tags=(str(row.get('Fase Actual', '')),))

    # --- Acciones de listado / búsqueda -----------------------------------
    def _search_boletas(self):
        field = self.search_field.get()
        term = self.search_term.get().strip()
        if not term:
            messagebox.showwarning("Búsqueda Vacía", "Por favor ingrese un término para buscar.")
            return
        self._set_active_filter(None)
        self.refresh_treeview(self.repo.search(field, term))

    def show_all_boletas(self):
        self.search_term.set("")
        self._set_active_filter(self.FILTRO_TODOS)
        self.refresh_treeview(self.repo.all())

    def filter_boletas(self, fase):
        self._set_active_filter(fase)
        self.refresh_treeview(self.repo.filter_by_phase(fase))

    def _set_active_filter(self, fase):
        """Resalta el botón del filtro activo (None = ninguno, p. ej. tras una búsqueda)."""
        for nombre, (button, color) in self.filter_buttons.items():
            activo = nombre == fase
            button.configure(
                text=f"✔ {nombre}" if activo else nombre,
                fg_color=color if activo else theme.lighten(color, 0.6),
                text_color="white" if activo else theme.TEXT,
                font=theme.font(12, "bold") if activo else theme.font(12),
            )

    # --- Acciones sobre una boleta ----------------------------------------
    def open_new_boleta_window(self):
        BoletaForm(self)

    def on_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        item_values = self.tree.item(item_id, 'values')
        if not item_values:
            return
        BoletaForm(self, boleta_id=int(item_values[0]))

    def delete_selected_boleta(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Sin selección", "Por favor, seleccione una boleta para borrar.")
            return
        boleta_id = int(self.tree.item(selected_item, 'values')[0])
        if not messagebox.askyesno(
            "Confirmar Borrado",
            f"¿Está seguro de que desea borrar permanentemente la boleta #{boleta_id}?",
        ):
            return
        if self.repo.delete(boleta_id):
            self.show_all_boletas()
            messagebox.showinfo("Éxito", f"La boleta #{boleta_id} ha sido borrada.")
        else:
            messagebox.showerror("Error", f"No se pudo encontrar la boleta #{boleta_id} para borrar.")

    # --- API usada por BoletaForm -----------------------------------------
    def get_next_id(self):
        return self.repo.get_next_id()

    def get_boleta_by_id(self, boleta_id):
        return self.repo.get_by_id(boleta_id)

    def add_new_record(self, record_dict):
        self.repo.add(record_dict)
        self.show_all_boletas()

    def update_record(self, boleta_id, form_data):
        if not self.repo.update(boleta_id, form_data):
            messagebox.showerror("Error", "No se pudo encontrar el índice para actualizar.")
            return
        self.show_all_boletas()
