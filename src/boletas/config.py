"""Configuración y constantes de la aplicación de boletas.

Centraliza en un único lugar todo lo que define el "qué" del dominio (fases,
columnas del Excel, opciones de los desplegables, valores por defecto y
precio). Así, para cambiar una fase o una opción no hay que tocar la lógica ni
la interfaz: basta con editar este archivo.
"""

# --- Persistencia ---------------------------------------------------------
# Archivo Excel donde se guardan todas las boletas. Es una ruta relativa al
# directorio de trabajo desde donde se ejecuta la aplicación.
EXCEL_FILE = "control_impresiones.xlsx"

# --- Active Directory (solo lectura) --------------------------------------
# Dominio de los correos institucionales: en el AD solo se guarda el usuario.
AD_DOMINIO_CORREO = "@estudiantec.cr"
# Tiempo máximo de espera de una búsqueda en el AD.
AD_TIMEOUT_SEGUNDOS = 8

# Datos del usuario (estudiante) que se autocompletan en la Recepción.
CAMPOS_DATOS_USUARIO = ['Cuenta', 'Carrera', 'Carné', 'Teléfono']

# Precio cobrado por cada gramo de material usado (en colones).
PRECIO_POR_GRAMO = 50


# --- Fases del flujo de una boleta ----------------------------------------
# El orden de esta lista define el avance natural de una boleta. El índice de
# cada fase (0..6) se usa para validaciones y para los prefijos F1..F7.
FASES = [
    "1. Recepción",
    "2. Revisión y Preparación",
    "3. Impresión",
    "4. Despegado de Piezas",
    "5. Entrega de Piezas",
    "6. Reimpresión",
    "7. Cancelación",
]

# Nombres viejos de fases -> nombre actual. El repositorio los migra al cargar
# el Excel, porque `Fase Actual` guarda el nombre de la fase tal cual.
FASES_RENOMBRADAS = {
    "7. Cancelada": "7. Cancelación",
}

# Fases en las que aplica el ordenamiento por prioridad de impresión.
FASES_CON_PRIORIDAD = ["2. Revisión y Preparación", "3. Impresión"]

# Prioridad de impresión según el tipo de uso (menor número = más prioritario).
# Las claves deben coincidir exactamente con USO_OPTIONS.
PRIORIDAD_USO = {
    "1. Curso": 1,
    "1. Evento de participación": 1,
    "2. Asistencia": 2,
    "3. Personal": 3,
}
PRIORIDAD_POR_DEFECTO = 4


# --- Columnas del Excel ---------------------------------------------------
# Orden canónico de las columnas con las que se guarda el archivo.
COLUMNAS = [
    'ID Boleta', 'Fase Actual',
    # Fase 1
    'F1_Operador', 'F1_Fecha', 'F1_Hora', 'Cuenta', 'Carrera', 'Carné', 'Teléfono',
    'Uso', 'Uso_Detalle', 'Nombre_Pieza', 'Observaciones_Usuario', 'Cantidad_Copias',
    'Material', 'Material_Otro_Detalle', 'Resolucion', 'Relleno', 'Autoriza_Recoger',
    # Fase 2
    'F2_Operador', 'F2_Fecha', 'F2_Hora', 'Uso_Material_g', 'Tiempo_Impresion_HHMM', 'Precio',
    # Fase 3
    'F3_Operador', 'F3_Fecha', 'F3_Hora', 'Confirmacion_Usuario', 'Impresora_Num', 'F3_Envio_Correo',
    'Fallo_Lista', 'F3_Notas',
    # Fase 4 (Despegado)
    'F4_Operador', 'F4_Fecha', 'F4_Hora', 'Observaciones_Despegado', 'F4_Imprimio_Correctamente', 'F4_Envio_Correo',
    # Fase 5 (Entrega)
    'F5_Operador', 'F5_Fecha', 'F5_Hora', 'Verificacion_Cobro', 'Recibido_Conforme',
    # Fase 6 (Reimpresión)
    'F6_Operador', 'F6_Fecha', 'F6_Hora', 'F6_Observaciones', 'F6_Uso_Material_g', 'F6_Tiempo_Impresion_HHMM', 'F6_Precio',
    # Fase 7 (Cancelación)
    'F7_Operador', 'F7_Fecha', 'F7_Hora', 'F7_Motivo_Cancelacion',
]

# Campos por los que se puede buscar desde la ventana principal.
CAMPOS_BUSQUEDA = ["ID Boleta", "Carné", "Operador", "Cuenta"]

# Columnas de operador de cada fase (para búsquedas por "Operador").
COLUMNAS_OPERADOR = [
    'F1_Operador', 'F2_Operador', 'F3_Operador',
    'F4_Operador', 'F5_Operador', 'F6_Operador',
]


# --- Etiquetas legibles de los campos (para mensajes de validación) -------
FIELD_NAMES = {
    'F1_Operador': 'Operador (Recepción)', 'Carné': 'Carné', 'Cuenta': 'Cuenta',
    'Uso': 'Uso', 'Nombre_Pieza': 'Nombre de la Pieza', 'Material': 'Material',
    'F1_Fecha': 'Fecha (Recepción)', 'F1_Hora': 'Hora (Recepción)',
    'Teléfono': 'Teléfono', 'Cantidad_Copias': 'Cantidad de Copias',
    'Resolucion': 'Resolución', 'Relleno': 'Relleno',

    'F2_Operador': 'Operador (Revisión)', 'Uso_Material_g': 'Uso de Material (g)',
    'F2_Fecha': 'Fecha (Revisión)', 'F2_Hora': 'Hora (Revisión)',
    'Tiempo_Impresion_HHMM': 'Tiempo de Impresión',

    'F3_Operador': 'Operador (Impresión)', 'Impresora_Num': 'Número de Impresora',
    'F3_Fecha': 'Fecha (Impresión)', 'F3_Hora': 'Hora (Impresión)',

    'F4_Operador': 'Operador (Despegado)',
    'F4_Fecha': 'Fecha (Despegado)', 'F4_Hora': 'Hora (Despegado)',

    'F5_Operador': 'Operador (Entrega)',
    'F5_Fecha': 'Fecha (Entrega)', 'F5_Hora': 'Hora (Entrega)',

    'F6_Operador': 'Operador (Reimpresión)',
    'F6_Fecha': 'Fecha (Reimpresión)', 'F6_Hora': 'Hora (Reimpresión)',
    'F6_Uso_Material_g': 'Uso de Material (g)',
    'F6_Tiempo_Impresion_HHMM': 'Tiempo de Impresión',

    'F7_Operador': 'Operador (Cancelación)',
    'F7_Fecha': 'Fecha (Cancelación)', 'F7_Hora': 'Hora (Cancelación)',
    'F7_Motivo_Cancelacion': 'Motivo de Cancelación',
}

# Campos obligatorios por índice de fase (0 = Recepción, 1 = Revisión, ...).
REQUIRED_FIELDS = {
    0: ['F1_Operador', 'F1_Fecha', 'F1_Hora', 'Carné', 'Cuenta', 'Uso', 'Nombre_Pieza', 'Teléfono', 'Cantidad_Copias', 'Material', 'Resolucion', 'Relleno'],
    1: ['F2_Operador', 'F2_Fecha', 'F2_Hora', 'Uso_Material_g', 'Tiempo_Impresion_HHMM'],
    2: ['F3_Operador', 'F3_Fecha', 'F3_Hora', 'Impresora_Num'],
    3: ['F4_Operador', 'F4_Fecha', 'F4_Hora'],
    4: ['F5_Operador', 'F5_Fecha', 'F5_Hora'],
    5: ['F6_Operador', 'F6_Fecha', 'F6_Hora', 'F6_Uso_Material_g', 'F6_Tiempo_Impresion_HHMM'],
    6: ['F7_Operador', 'F7_Fecha', 'F7_Hora', 'F7_Motivo_Cancelacion'],
}


# --- Opciones de los desplegables del formulario --------------------------
USO_OPTIONS = ["1. Curso", "1. Evento de participación", "2. Asistencia", "3. Personal"]
# Valores de "Uso" que habilitan el campo de detalle (curso/evento).
USO_CON_DETALLE = ["1. Curso", "1. Evento de participación"]

MATERIAL_OPTIONS = ["PLA", "PETG", "ABS", "Flex (TPU)", "ASA", "Otro"]
MATERIAL_OTRO = "Otro"

RESOLUCION_OPTIONS = [0.28, 0.2, 0.15, 0.10, 0.07, 0.05]
RESOLUCION_DEFAULT = '0.2'

RELLENO_OPTIONS = [0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
RELLENO_DEFAULT = '10'

IMPRESORA_OPTIONS = [1, 2, 3, 4, 5, 6, 7]

# Cómo confirmó el usuario el inicio de la impresión (Fase 3).
CONFIRMACION_OPTIONS = ["Correo Institucional", "En persona (requiere firma)"]


# --- Formatos de fecha/hora ------------------------------------------------
FORMATO_FECHA = "%d/%m/%Y"
FORMATO_HORA = "%I:%M %p"
