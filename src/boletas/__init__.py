"""Paquete de la aplicación de Control de Impresiones (Boletas de Corte Láser).

Organización por capas (separación de responsabilidades):

    config       -> constantes y configuración (fases, columnas, opciones...)
    repository   -> acceso a datos (lectura/escritura del Excel)  [patrón Repository]
    services     -> lógica de negocio reutilizable (precios, detección de fase)
    ui           -> interfaz gráfica (ventana principal y formulario)
"""
