"""Configuración y constantes de la aplicación de boletas.

Centraliza en un único lugar todo lo que define el "qué" del dominio (fases,
columnas del Excel, opciones de los desplegables, valores por defecto y
precio). Así, para cambiar una fase o una opción no hay que tocar la lógica ni
la interfaz: basta con editar este archivo.

Los valores marcados como "editables" (ver `ajustes.EDITABLES`) son solo los
valores **por defecto**: desde la ventana "⚙ Configuración" de la aplicación se
pueden cambiar y se guardan en `configuracion.json`, que se aplica encima de
este archivo al arrancar. Así se pueden ajustar sin recompilar el `.exe`.
Las consultas derivadas (opciones de uso, colores disponibles...) están en
`catalogo.py`.
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
CAMPOS_DATOS_USUARIO = ['Nombre_Usuario', 'Cuenta', 'Carrera', 'Carné', 'Teléfono']

# Precio cobrado por cada gramo de material usado (en colones).
PRECIO_POR_GRAMO = 50

# Gramos de material que trae un rollo de filamento (para el orden de impresión).
GRAMOS_POR_ROLLO = 1000


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

# Tipos de uso, en el orden en que se muestran. `prioridad`: menor número =
# más prioritario. `detalle`: habilita el campo "Indicar" (curso/evento).
USOS = [
    {"nombre": "1. Curso", "prioridad": 1, "detalle": True},
    {"nombre": "1. Evento de participación", "prioridad": 1, "detalle": True},
    {"nombre": "2. Asistencia", "prioridad": 2, "detalle": False},
    {"nombre": "3. Personal", "prioridad": 3, "detalle": False},
]
PRIORIDAD_POR_DEFECTO = 4


# --- Columnas del Excel ---------------------------------------------------
# Orden canónico de las columnas con las que se guarda el archivo.
COLUMNAS = [
    'ID Boleta', 'Fase Actual',
    # Fase 1
    'F1_Operador', 'F1_Fecha', 'F1_Hora', 'Nombre_Usuario', 'Cuenta', 'Carrera', 'Carné', 'Teléfono',
    'Uso', 'Uso_Detalle', 'Nombre_Pieza', 'Observaciones_Usuario', 'Cantidad_Copias',
    'Material', 'Material_Otro_Detalle', 'Color_Filamento', 'Resolucion', 'Relleno', 'Autoriza_Recoger',
    # Fase 2
    'F2_Operador', 'F2_Fecha', 'F2_Hora', 'Uso_Material_g', 'Tiempo_Impresion_HHMM', 'Precio',
    'Tipo_Impresora',
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
    'F1_Operador': 'Operador (Recepción)', 'Nombre_Usuario': 'Nombre del Usuario', 'Carné': 'Carné', 'Cuenta': 'Cuenta',
    'Uso': 'Uso', 'Nombre_Pieza': 'Nombre de la Pieza', 'Material': 'Material',
    'F1_Fecha': 'Fecha (Recepción)', 'F1_Hora': 'Hora (Recepción)',
    'Teléfono': 'Teléfono', 'Cantidad_Copias': 'Cantidad de Copias',
    'Resolucion': 'Resolución', 'Relleno': 'Relleno', 'Color_Filamento': 'Color del Filamento',

    'F2_Operador': 'Operador (Revisión)', 'Uso_Material_g': 'Uso de Material (g)',
    'F2_Fecha': 'Fecha (Revisión)', 'F2_Hora': 'Hora (Revisión)',
    'Tiempo_Impresion_HHMM': 'Tiempo de Impresión', 'Tipo_Impresora': 'Tipo de Impresora',

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
# 'Tipo_Impresora' solo se exige si USAR_TIPO_IMPRESORA está activo (lo
# resuelve `catalogo.campos_obligatorios`).
REQUIRED_FIELDS = {
    0: ['F1_Operador', 'F1_Fecha', 'F1_Hora', 'Carné', 'Cuenta', 'Uso', 'Nombre_Pieza', 'Teléfono', 'Cantidad_Copias', 'Material', 'Color_Filamento', 'Resolucion', 'Relleno'],
    1: ['F2_Operador', 'F2_Fecha', 'F2_Hora', 'Uso_Material_g', 'Tiempo_Impresion_HHMM', 'Tipo_Impresora'],
    2: ['F3_Operador', 'F3_Fecha', 'F3_Hora', 'Impresora_Num'],
    3: ['F4_Operador', 'F4_Fecha', 'F4_Hora'],
    4: ['F5_Operador', 'F5_Fecha', 'F5_Hora'],
    5: ['F6_Operador', 'F6_Fecha', 'F6_Hora', 'F6_Uso_Material_g', 'F6_Tiempo_Impresion_HHMM'],
    6: ['F7_Operador', 'F7_Fecha', 'F7_Hora', 'F7_Motivo_Cancelacion'],
}


# Fases a las que se puede pasar desde cualquier punto (sin completar las
# intermedias), siempre que la Recepción esté completa.
FASES_SIN_ORDEN = ["7. Cancelación"]


# --- Opciones de los desplegables del formulario --------------------------
MATERIAL_OPTIONS = ["PLA", "PETG", "ABS", "Flex (TPU)", "ASA", "Otro"]
MATERIAL_OTRO = "Otro"

RESOLUCION_OPTIONS = [0.28, 0.2, 0.15, 0.10, 0.07, 0.05]
RESOLUCION_DEFAULT = '0.2'

RELLENO_OPTIONS = [0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
RELLENO_DEFAULT = '10'

# Colores de filamento por material. `disponible` = False lo oculta de la
# lista (p. ej. cuando se acaba ese color). Un material sin colores (como
# "Otro") permite escribir el color a mano.
COLORES_POR_MATERIAL = {
    "PLA": [
        {"color": "Negro", "disponible": True},
        {"color": "Blanco", "disponible": True},
        {"color": "Gris", "disponible": True},
        {"color": "Rojo", "disponible": True},
        {"color": "Azul", "disponible": True},
        {"color": "Verde", "disponible": True},
        {"color": "Amarillo", "disponible": True},
    ],
    "PETG": [
        {"color": "Negro", "disponible": True},
        {"color": "Blanco", "disponible": True},
        {"color": "Transparente", "disponible": True},
    ],
    "ABS": [
        {"color": "Negro", "disponible": True},
        {"color": "Blanco", "disponible": True},
    ],
    "Flex (TPU)": [
        {"color": "Negro", "disponible": True},
        {"color": "Blanco", "disponible": True},
    ],
    "ASA": [
        {"color": "Negro", "disponible": True},
    ],
}

# --- Impresoras -------------------------------------------------------------
# Tipos (modelos) de impresora. Si USAR_TIPO_IMPRESORA es False, en la Revisión
# no se pide el tipo y en la Impresión se puede usar cualquier impresora.
TIPOS_IMPRESORA = ["MK4S", "Core One Plus"]
USAR_TIPO_IMPRESORA = True
# Valor de "Tipo de impresora" que significa que sirve cualquiera (ambas).
TIPO_IMPRESORA_CUALQUIERA = "Cualquiera"

# Impresoras del laboratorio. `activa` = False la saca de la lista (p. ej. en
# mantenimiento) sin perder su número.
IMPRESORAS = [
    {"numero": 1, "tipo": "MK4S", "activa": True},
    {"numero": 2, "tipo": "MK4S", "activa": True},
    {"numero": 3, "tipo": "MK4S", "activa": True},
    {"numero": 4, "tipo": "MK4S", "activa": True},
    {"numero": 5, "tipo": "Core One Plus", "activa": True},
    {"numero": 6, "tipo": "Core One Plus", "activa": True},
    {"numero": 7, "tipo": "Core One Plus", "activa": True},
]

# Cómo confirmó el usuario el inicio de la impresión (Fase 3).
CONFIRMACION_OPTIONS = ["Correo Institucional", "En persona (requiere firma)"]


# --- Formatos de fecha/hora ------------------------------------------------
FORMATO_FECHA = "%d/%m/%Y"
FORMATO_HORA = "%I:%M %p"
