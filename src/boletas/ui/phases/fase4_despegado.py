"""Fase 4: Despegado de Piezas.

El botón «Correo de finalización» abre en Outlook el aviso de que la pieza
está lista para retirar y marca la casilla de notificación de finalización.
"""

from ... import correos
from .. import theme
from ..enviar_correo import boton_correo
from .base import PhaseSection, PAD_X, PAD_Y


class Phase4Despegado(PhaseSection):
    index = 3

    def build_widgets(self, frame):
        self.operator_row()

        row = self.new_row()
        self.field(row, 0, 'Observaciones_Despegado', "OBSERVACIONES", "Fecha - Hora - Observación", colspan=3)

        row = self.new_row()
        self.checkbox(frame, 'F4_Imprimio_Correctamente', "Se imprimió correctamente").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PAD_X, pady=PAD_Y)
        correo = self.cell(row, 2, colspan=2)
        self.checkbox(correo, 'F4_Envio_Correo', "Envío de correo de notificación de finalización",
                      text_color=theme.ACCENT_RED).pack(side="left")
        boton_correo(self, correo, correos.FINALIZACION, "✉  Correo de finalización", width=170,
                     al_abrir=lambda: self.vars['F4_Envio_Correo'].set(True)).pack(side="left", padx=(10, 0))
