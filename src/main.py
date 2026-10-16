"""Punto de entrada de la aplicación de Control de Impresiones (Boletas Láser).

Ejecuta:  python main.py
Empaquetar:  python -m PyInstaller --onefile --windowed --strip --noupx --collect-data customtkinter main.py
"""

from boletas.ui.main_window import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
