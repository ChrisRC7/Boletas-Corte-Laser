"""Reporte en Excel de las boletas: resumen, gráficos y detalle (sin interfaz).

`generar(registros, ruta)` escribe un libro de Excel con estas hojas:

- **Resumen**: indicadores principales (boletas, entregas, material, horas,
  monto...) y los gráficos.
- **Estadísticas**: las tablas de los gráficos (por fase, uso, material, color,
  mes, impresora, carrera y operador).
- **Boletas**: el detalle completo, una fila por boleta con todas sus columnas
  (números y fechas como tales, para poder filtrar y sumar en Excel).
- **Usuarios**: una fila por usuario con sus totales.
- **Fallos**: una fila por cada fallo de impresión registrado.

Los números salen de `metricas.calcular`; aquí solo se les da forma. Es una
exportación: el libro no se vuelve a leer y editarlo no cambia las boletas.
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from . import config, metricas
from .fechas import leer_fecha_hora

# --- Apariencia ----------------------------------------------------------------
AZUL = "3E73B9"          # Color principal (el de la Recepción en la boleta)
AZUL_CLARO = "E8EEF7"
TEXTO = "1F2937"
GRIS = "6B7280"
LINEA = "D5DAE1"
FUENTE = "Segoe UI"
ESTILO_TABLA = "TableStyleMedium2"

FORMATO_ENTERO = '#,##0'
FORMATO_GRAMOS = '#,##0.0" g"'
FORMATO_MONTO = '"₡"#,##0'
FORMATO_HORAS = '#,##0.0" h"'
FORMATO_FECHA = 'DD/MM/YYYY'

# Etiquetas de las columnas que no están en `config.FIELD_NAMES`.
ETIQUETAS = {
    'ID Boleta': 'Boleta', 'Fase Actual': 'Fase actual', 'Carrera': 'Carrera',
    'Uso_Detalle': 'Curso / Evento', 'Observaciones_Usuario': 'Observaciones del usuario',
    'Material_Otro_Detalle': 'Otro material', 'Autoriza_Recoger': 'Autoriza a recoger',
    'Precio': 'Precio (₡)', 'Confirmacion_Usuario': 'Confirmación del usuario',
    'F3_Envio_Correo': 'Correo de inicio enviado', 'Fallo_Lista': 'N.º de fallos',
    'F3_Notas': 'Notas de impresión', 'Observaciones_Despegado': 'Observaciones del despegado',
    'F4_Imprimio_Correctamente': 'Se imprimió correctamente', 'F4_Envio_Correo': 'Correo de finalización enviado',
    'Verificacion_Cobro': 'Cobro verificado', 'Recibido_Conforme': 'Recibido conforme',
}
COLUMNAS_ENTERAS = {'Cantidad_Copias', 'Relleno', 'Impresora_Num'}
COLUMNAS_DECIMALES = {'Uso_Material_g': FORMATO_GRAMOS, 'Precio': FORMATO_MONTO, 'Resolucion': '0.00'}
COLUMNAS_SI_NO = {'F3_Envio_Correo', 'F4_Imprimio_Correctamente', 'F4_Envio_Correo',
                  'Verificacion_Cobro', 'Recibido_Conforme'}
COLUMNAS_ANCHAS = {'Nombre_Usuario': 30, 'Carrera': 30, 'Observaciones_Usuario': 40, 'F3_Notas': 40,
                   'Observaciones_Despegado': 40, 'F6_Motivo_Cancelacion': 40, 'Autoriza_Recoger': 30,
                   'Nombre_Pieza': 24, 'Fase Actual': 26, 'Uso': 26}

# Rejilla del Resumen: 17 columnas iguales; dos mitades (A-H y J-Q) con la I de separación.
COLUMNAS_RESUMEN = 17
ANCHO_COLUMNA_RESUMEN = 11
MITADES = (1, 10)            # Columna donde empieza cada mitad
ANCHO_GRAFICO_CM = 17.2      # 8 columnas de la rejilla
ALTO_GRAFICO_CM = 8.2
FILAS_POR_GRAFICO = 18


# --- Entrada principal ---------------------------------------------------------
def generar(registros, ruta, generado=None):
    """Escribe el reporte de `registros` (boletas del repositorio) en `ruta`. Lanza OSError si no puede."""
    generado = generado or datetime.now()
    resumen = metricas.calcular(registros)

    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = "Resumen"
    tablas = _hoja_estadisticas(libro.create_sheet("Estadísticas"), resumen)
    _hoja_resumen(hoja_resumen, resumen, tablas, generado)
    _hoja_boletas(libro.create_sheet("Boletas"), resumen, registros)
    _hoja_usuarios(libro.create_sheet("Usuarios"), resumen)
    _hoja_fallos(libro.create_sheet("Fallos"), resumen)
    libro.save(ruta)


# --- Utilidades de formato -------------------------------------------------------
def _fuente(tamano=10, negrita=False, color=TEXTO):
    return Font(name=FUENTE, size=tamano, bold=negrita, color=color)


def _relleno(color):
    return PatternFill("solid", start_color=color, end_color=color)


def _titulo_hoja(hoja, titulo, subtitulo, columnas):
    """Banda de título en las dos primeras filas de una hoja."""
    hoja.sheet_view.showGridLines = False
    for fila, texto, fuente, alto in ((1, titulo, _fuente(16, True, "FFFFFF"), 30),
                                      (2, subtitulo, _fuente(10, False, "FFFFFF"), 18)):
        hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=columnas)
        celda = hoja.cell(row=fila, column=1, value=texto)
        celda.font = fuente
        celda.alignment = Alignment(vertical="center", indent=1)
        hoja.row_dimensions[fila].height = alto
        for columna in range(1, columnas + 1):
            hoja.cell(row=fila, column=columna).fill = _relleno(AZUL)


def _tabla(hoja, nombre, fila, encabezados, filas, formatos=None, anchos=None):
    """Escribe una tabla de Excel (con filtros y bandas) a partir de `fila`. Devuelve la última fila.

    `formatos`: {índice de columna (0..): formato de número}. Sin filas, deja una nota.
    """
    formatos = formatos or {}
    for c, texto in enumerate(encabezados, 1):
        celda = hoja.cell(row=fila, column=c, value=texto)
        celda.font = _fuente(10, True, "FFFFFF")
        celda.fill = _relleno(AZUL)
        celda.alignment = Alignment(vertical="center", wrap_text=True)
    hoja.row_dimensions[fila].height = 30
    if not filas:
        hoja.cell(row=fila + 1, column=1, value="(sin datos)").font = _fuente(10, False, GRIS)
        return fila + 1

    for f, valores in enumerate(filas, fila + 1):
        for c, valor in enumerate(valores, 1):
            celda = hoja.cell(row=f, column=c, value=valor)
            celda.font = _fuente(10)
            celda.alignment = Alignment(vertical="top", wrap_text=isinstance(valor, str) and len(valor) > 40)
            if (c - 1) in formatos and isinstance(valor, (int, float)):
                celda.number_format = formatos[c - 1]
            elif isinstance(valor, datetime):
                celda.number_format = FORMATO_FECHA
    ultima = fila + len(filas)
    tabla = Table(displayName=nombre, ref=f"A{fila}:{get_column_letter(len(encabezados))}{ultima}")
    tabla.tableStyleInfo = TableStyleInfo(name=ESTILO_TABLA, showRowStripes=True)
    hoja.add_table(tabla)

    for c, texto in enumerate(encabezados, 1):
        ancho = (anchos or {}).get(c - 1)
        if ancho is None:
            largos = [len(str(texto))] + [len(str(v[c - 1])) for v in filas[:200] if v[c - 1] is not None]
            ancho = min(max(largos) + 4, 45)
        hoja.column_dimensions[get_column_letter(c)].width = max(ancho, 9)
    return ultima


def _fecha(texto):
    """'13/11/2026' -> datetime (para que Excel la trate como fecha); el texto tal cual si no se entiende."""
    return leer_fecha_hora(texto, '') or texto


def _si_no(texto):
    return {'true': 'Sí', 'false': 'No'}.get(str(texto).strip().lower(), texto)


def _periodo(resumen):
    if not resumen.desde:
        return "Sin boletas con fecha de recepción"
    return (f"Boletas recibidas del {resumen.desde.strftime(config.FORMATO_FECHA)} "
            f"al {resumen.hasta.strftime(config.FORMATO_FECHA)}")


# --- Hoja «Estadísticas» -----------------------------------------------------------
def _hoja_estadisticas(hoja, resumen):
    """Escribe las tablas de los desgloses. Devuelve {nombre: (fila de encabezado, última fila)}."""
    _titulo_hoja(hoja, "Estadísticas", "Tablas de los gráficos del Resumen. Material, horas y monto no "
                                       "incluyen las boletas canceladas.", 5)
    for columna, ancho in zip("ABCDE", (38, 14, 16, 16, 14)):
        hoja.column_dimensions[columna].width = ancho

    secciones = [
        ("fase", "Boletas por fase actual", ["Fase", "Boletas"], resumen.por_fase, {1: FORMATO_ENTERO}),
        ("uso", "Boletas por tipo de uso", ["Uso", "Boletas", "Material (g)", "Monto (₡)"], resumen.por_uso,
         {1: FORMATO_ENTERO, 2: FORMATO_GRAMOS, 3: FORMATO_MONTO}),
        ("material", "Material", ["Material", "Boletas", "Material (g)"], resumen.por_material,
         {1: FORMATO_ENTERO, 2: FORMATO_GRAMOS}),
        ("color", "Material y color del filamento", ["Filamento", "Boletas", "Material (g)"], resumen.por_color,
         {1: FORMATO_ENTERO, 2: FORMATO_GRAMOS}),
        ("mes", "Por mes de recepción", ["Mes", "Boletas", "Material (g)", "Monto (₡)", "Horas"], resumen.por_mes,
         {1: FORMATO_ENTERO, 2: FORMATO_GRAMOS, 3: FORMATO_MONTO, 4: FORMATO_HORAS}),
        ("impresora", "Por impresora (incluye trabajos cancelados)",
         ["Impresora", "Trabajos", "Horas", "Material (g)"], resumen.por_impresora,
         {1: FORMATO_ENTERO, 2: FORMATO_HORAS, 3: FORMATO_GRAMOS}),
        ("carrera", "Por carrera", ["Carrera", "Boletas", "Material (g)"], resumen.por_carrera,
         {1: FORMATO_ENTERO, 2: FORMATO_GRAMOS}),
        ("operador", "Fases atendidas por operador", ["Operador", "Fases atendidas"], resumen.por_operador,
         {1: FORMATO_ENTERO}),
    ]
    posiciones, fila = {}, 4
    for nombre, titulo, encabezados, filas, formatos in secciones:
        hoja.cell(row=fila, column=1, value=titulo).font = _fuente(12, True, AZUL)
        fila += 1
        for c, texto in enumerate(encabezados, 1):
            celda = hoja.cell(row=fila, column=c, value=texto)
            celda.font = _fuente(10, True, "FFFFFF")
            celda.fill = _relleno(AZUL)
            celda.alignment = Alignment(horizontal="left" if c == 1 else "right")
        inicio = fila
        for valores in filas:
            fila += 1
            for c, valor in enumerate(valores, 1):
                celda = hoja.cell(row=fila, column=c, value=valor)
                celda.font = _fuente(10)
                celda.border = Border(bottom=Side(style="thin", color=LINEA))
                if (c - 1) in formatos:
                    celda.number_format = formatos[c - 1]
        if not filas:
            fila += 1
            hoja.cell(row=fila, column=1, value="(sin datos)").font = _fuente(10, False, GRIS)
        posiciones[nombre] = (inicio, fila if filas else inicio)
        fila += 3
    return posiciones


# --- Hoja «Resumen» -----------------------------------------------------------------
def _hoja_resumen(hoja, resumen, tablas, generado):
    _titulo_hoja(hoja, "LAIMI · Control de Impresiones — Reporte",
                 f"Generado el {generado.strftime(config.FORMATO_FECHA)} a las "
                 f"{generado.strftime(config.FORMATO_HORA)}   ·   {_periodo(resumen)}", COLUMNAS_RESUMEN)
    for columna in range(1, COLUMNAS_RESUMEN + 1):
        hoja.column_dimensions[get_column_letter(columna)].width = ANCHO_COLUMNA_RESUMEN

    dias = resumen.dias_entrega_promedio
    con_fallos = resumen.boletas_con_fallos / resumen.total if resumen.total else 0
    tarjetas = [
        ("BOLETAS", resumen.total, FORMATO_ENTERO, "en total"),
        ("ENTREGADAS", resumen.entregadas, FORMATO_ENTERO, "piezas retiradas"),
        ("EN PROCESO", resumen.en_proceso, FORMATO_ENTERO, "sin entregar ni cancelar"),
        ("CANCELADAS", resumen.canceladas, FORMATO_ENTERO, "no suman material ni monto"),
        ("MATERIAL", resumen.gramos, FORMATO_GRAMOS, "filamento usado"),
        ("TIEMPO DE IMPRESIÓN", resumen.minutos / 60, FORMATO_HORAS, "horas estimadas"),
        ("MONTO", resumen.monto, FORMATO_MONTO, f"cobro verificado: ₡{resumen.monto_cobrado:,.0f}".replace(",", " ")),
        ("USUARIOS", resumen.usuarios_distintos, FORMATO_ENTERO, "personas distintas"),
    ]
    fila = 4
    for n, tarjeta in enumerate(tarjetas):
        _tarjeta(hoja, fila + (n // 4) * 4, 1 + (n % 4) * 4 + (1 if n % 4 >= 2 else 0), *tarjeta)

    fila = 13
    notas = [
        ("Material promedio por boleta", resumen.gramos / max(resumen.total - resumen.canceladas, 1), FORMATO_GRAMOS),
        ("Días promedio de la recepción a la entrega", dias if dias is not None else "sin entregas", '0.0'),
        ("Boletas con fallos de impresión", con_fallos, '0%'),
        ("Fallos registrados", resumen.total_fallos, FORMATO_ENTERO),
    ]
    for n, (texto, valor, formato) in enumerate(notas):
        columna = MITADES[n % 2]
        f = fila + n // 2
        hoja.merge_cells(start_row=f, start_column=columna, end_row=f, end_column=columna + 5)
        hoja.cell(row=f, column=columna, value=texto).font = _fuente(10, False, GRIS)
        hoja.merge_cells(start_row=f, start_column=columna + 6, end_row=f, end_column=columna + 7)
        celda = hoja.cell(row=f, column=columna + 6, value=valor)
        celda.font = _fuente(10, True)
        celda.number_format = formato
        celda.alignment = Alignment(horizontal="right")

    # Gráficos: un solo dato por gráfico y un solo eje (nada de dos escalas).
    graficos = [
        ("fase", 2, "Boletas por fase actual", False, FORMATO_ENTERO),
        ("uso", 2, "Boletas por tipo de uso", True, FORMATO_ENTERO),
        ("mes", 2, "Boletas recibidas por mes", False, FORMATO_ENTERO),
        ("mes", 3, "Material usado por mes (g)", False, FORMATO_ENTERO),
        ("mes", 4, "Monto por mes (₡)", False, FORMATO_ENTERO),
        ("material", 3, "Material usado por tipo (g)", False, FORMATO_ENTERO),
        ("impresora", 3, "Horas de impresión por impresora", False, '0.0'),
        ("carrera", 2, "Boletas por carrera (10 principales)", True, FORMATO_ENTERO),
    ]
    origen = hoja.parent["Estadísticas"]
    fila, colocados = 17, 0
    for nombre, columna, titulo, horizontal, formato in graficos:
        inicio, fin = tablas[nombre]
        if fin <= inicio or not resumen.total:
            continue  # Sin datos: no se dibuja un gráfico vacío.
        if nombre == "carrera":
            fin = min(fin, inicio + 10)
        grafico = _grafico_barras(origen, inicio, fin, columna, titulo, horizontal, formato)
        ancla = f"{get_column_letter(MITADES[colocados % 2])}{fila + (colocados // 2) * FILAS_POR_GRAFICO}"
        hoja.add_chart(grafico, ancla)
        colocados += 1
    if not colocados:
        hoja.cell(row=fila, column=1, value="Todavía no hay boletas para graficar.").font = _fuente(11, False, GRIS)

    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.page_setup.orientation = "landscape"
    hoja.page_setup.fitToHeight = 0


def _tarjeta(hoja, fila, columna, etiqueta, valor, formato, nota):
    """Indicador grande: etiqueta, valor y una nota, en un bloque de 4 columnas x 3 filas."""
    for f in range(fila, fila + 3):
        for c in range(columna, columna + 4):
            hoja.cell(row=f, column=c).fill = _relleno(AZUL_CLARO)
        hoja.merge_cells(start_row=f, start_column=columna, end_row=f, end_column=columna + 3)
    partes = ((etiqueta, _fuente(9, True, GRIS), 16, None),
              (valor, _fuente(20, True, AZUL), 32, formato),
              (nota, _fuente(9, False, GRIS), 16, None))
    for desplazamiento, (contenido, fuente, alto, formato_numero) in enumerate(partes):
        celda = hoja.cell(row=fila + desplazamiento, column=columna, value=contenido)
        celda.font = fuente
        celda.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        if formato_numero:
            celda.number_format = formato_numero
        hoja.row_dimensions[fila + desplazamiento].height = alto
    hoja.row_dimensions[fila + 3].height = 8  # Separación con la fila de tarjetas siguiente.


def _grafico_barras(origen, inicio, fin, columna, titulo, horizontal, formato):
    """Gráfico de barras de una sola serie: categorías en la columna A, valores en `columna`."""
    grafico = BarChart()
    grafico.type = "bar" if horizontal else "col"
    grafico.style = 10
    grafico.title = titulo
    grafico.title.overlay = False    # El título no se monta sobre el área del gráfico.
    grafico.legend = None            # Una sola serie: el título ya dice qué es.
    grafico.roundedCorners = False
    grafico.width, grafico.height = ANCHO_GRAFICO_CM, ALTO_GRAFICO_CM
    grafico.gapWidth = 60
    grafico.add_data(Reference(origen, min_col=columna, min_row=inicio, max_row=fin), titles_from_data=True)
    grafico.set_categories(Reference(origen, min_col=1, min_row=inicio + 1, max_row=fin))

    serie = grafico.series[0]
    serie.graphicalProperties = GraphicalProperties(solidFill=AZUL)
    serie.graphicalProperties.line.solidFill = AZUL
    serie.dLbls = DataLabelList()
    serie.dLbls.showVal = True
    serie.dLbls.showSerName = serie.dLbls.showCatName = serie.dLbls.showLegendKey = False
    serie.dLbls.showPercent = False
    serie.dLbls.numFmt = formato

    # openpyxl marca los ejes como eliminados si no se indica lo contrario.
    grafico.x_axis.delete = False
    grafico.y_axis.delete = False
    grafico.y_axis.numFmt = formato
    grafico.y_axis.scaling.min = 0   # Las barras siempre parten de cero: si no, exageran las diferencias.
    grafico.y_axis.majorGridlines.spPr = GraphicalProperties(ln=None)
    grafico.y_axis.majorGridlines.spPr.line.solidFill = LINEA
    if horizontal:
        grafico.x_axis.scaling.orientation = "maxMin"  # La primera categoría arriba...
        grafico.y_axis.crosses = "max"                 # ...y la escala de valores sigue abajo.
    return grafico


# --- Hoja «Boletas» -------------------------------------------------------------------
def _etiqueta(columna):
    return ETIQUETAS.get(columna) or config.FIELD_NAMES.get(columna) or columna.replace('_', ' ')


def _valor_boleta(columna, boleta):
    texto = boleta.texto(columna)
    if columna == 'ID Boleta':
        return boleta.numero
    if columna == 'Fase Actual':
        return boleta.fase
    if columna == 'Fallo_Lista':
        return len(boleta.fallos)
    if not texto:
        return None
    if columna in COLUMNAS_SI_NO:
        return _si_no(texto)
    if columna.endswith('_Fecha'):
        return _fecha(texto)
    if columna in COLUMNAS_ENTERAS or columna in COLUMNAS_DECIMALES:
        try:
            numero = float(texto.replace(',', '.'))
        except ValueError:
            return texto
        return int(numero) if columna in COLUMNAS_ENTERAS and numero.is_integer() else numero
    return texto


def _hoja_boletas(hoja, resumen, registros):
    extra = []
    for registro in registros:
        extra += [c for c in registro if c not in config.COLUMNAS and c not in extra]
    columnas = list(config.COLUMNAS) + extra
    # «Estado» va junto a la fase: resume en una palabra cómo terminó la boleta.
    posicion = columnas.index('Fase Actual') + 1
    encabezados = [_etiqueta(c) for c in columnas]
    encabezados.insert(posicion, "Estado")
    encabezados = _sin_repetidos(encabezados)

    filas = []
    for boleta in resumen.boletas:
        valores = [_valor_boleta(c, boleta) for c in columnas]
        valores.insert(posicion, boleta.estado)
        filas.append(valores)

    _titulo_hoja(hoja, "Boletas — detalle completo",
                 f"{resumen.total} boletas · una fila por boleta, con todas las fases", min(len(encabezados), 12))
    desplazadas = columnas[:posicion] + ['Estado'] + columnas[posicion:]
    formatos = {i: (FORMATO_ENTERO if c in COLUMNAS_ENTERAS else COLUMNAS_DECIMALES[c])
                for i, c in enumerate(desplazadas) if c in COLUMNAS_ENTERAS or c in COLUMNAS_DECIMALES}
    anchos = {i: COLUMNAS_ANCHAS[c] for i, c in enumerate(desplazadas) if c in COLUMNAS_ANCHAS}
    _tabla(hoja, "TablaBoletas", 4, encabezados, filas, formatos, anchos)
    hoja.freeze_panes = "C5"   # Quedan fijos el encabezado y el número de boleta.


def _sin_repetidos(encabezados):
    """Una tabla de Excel no admite dos columnas con el mismo título."""
    vistos, resultado = {}, []
    for texto in encabezados:
        vistos[texto] = vistos.get(texto, 0) + 1
        resultado.append(texto if vistos[texto] == 1 else f"{texto} ({vistos[texto]})")
    return resultado


# --- Hojas «Usuarios» y «Fallos» --------------------------------------------------------
def _hoja_usuarios(hoja, resumen):
    _titulo_hoja(hoja, "Usuarios", f"{resumen.usuarios_distintos} personas · ordenadas por número de boletas", 10)
    filas = [[u['carne'] or None, u['nombre'] or None, u['cuenta'] or None, u['carrera'] or None,
              u['boletas'], u['entregadas'], u['canceladas'], u['gramos'], u['monto'], u['ultima']]
             for u in resumen.usuarios]
    _tabla(hoja, "TablaUsuarios", 4,
           ["Carné", "Nombre", "Cuenta", "Carrera", "Boletas", "Entregadas", "Canceladas",
            "Material (g)", "Monto (₡)", "Última recepción"],
           filas, {4: FORMATO_ENTERO, 5: FORMATO_ENTERO, 6: FORMATO_ENTERO, 7: FORMATO_GRAMOS, 8: FORMATO_MONTO},
           {1: 32, 3: 32, 9: 17})
    hoja.freeze_panes = "A5"


def _hoja_fallos(hoja, resumen):
    _titulo_hoja(hoja, "Fallos de impresión",
                 f"{resumen.total_fallos} fallos en {resumen.boletas_con_fallos} boletas", 9)
    filas = [[f['boleta'], _fecha(f['fecha']) if f['fecha'] else None, f['hora'] or None, f['operador'] or None,
              f['impresora'] or None, f['material'], f['usuario'] or None, f['archivo'] or None, f['descripcion']]
             for f in resumen.fallos]
    _tabla(hoja, "TablaFallos", 4,
           ["Boleta", "Fecha", "Hora", "Operador", "Impresora", "Material", "Usuario", "Archivo", "Descripción"],
           filas, {0: FORMATO_ENTERO}, {1: 13, 8: 70})
    hoja.freeze_panes = "A5"
