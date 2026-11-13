"""Lectura del Excel de boletas anterior a SQLite (`control_impresiones.xlsx`).

Solo se usa una vez: cuando todavía no existe la base de datos, el repositorio
importa de aquí las boletas que ya había. No tiene interfaz ni escribe nada:
el Excel queda intacto como respaldo.

Además de leer, adapta los formatos viejos del Excel a la estructura actual:

- Columnas del formato con 7 fases (`config.COLUMNAS_RENOMBRADAS`): la
  Cancelación pasa de F7 a F6 y la antigua Reimpresión se conserva en columnas
  `Reimpresion_Antigua_*` (se descartan si están vacías).
- Fases que cambiaron de nombre (`config.FASES_RENOMBRADAS`).
- Boletas sin número o con el número repetido: reciben un número nuevo al
  final, para no perderlas.
"""

from datetime import date, datetime, time

from . import config

ID = 'ID Boleta'


class ErrorExcel(Exception):
    """El Excel no se pudo leer. El mensaje es apto para mostrarse."""


def leer(ruta):
    """Boletas del Excel como lista de diccionarios `{columna: texto}` (con `ID Boleta` entero)."""
    try:
        from openpyxl import load_workbook
        libro = load_workbook(ruta, read_only=True, data_only=True)
        try:
            filas = list(libro.worksheets[0].iter_rows(values_only=True))
        finally:
            libro.close()
    except Exception as error:  # openpyxl lanza tipos muy variados (zip, XML, permisos...).
        raise ErrorExcel(f"No se pudo leer el Excel '{ruta}' para importarlo a la base de datos:\n{error}\n\n"
                         "Si el archivo está dañado, restaure una copia; si ya no lo necesita, "
                         "muévalo a otra carpeta.") from None
    if not filas:
        return []

    encabezados = [str(c).strip() if c is not None else '' for c in filas[0]]
    if ID not in encabezados:
        raise ErrorExcel(f"El Excel '{ruta}' no tiene la columna «{ID}»: no parece el archivo de boletas.\n\n"
                         "Corrija la ruta en configuracion.json o mueva ese archivo a otra carpeta.")
    if config.COLUMNA_FORMATO_VIEJO in encabezados:
        encabezados = [config.COLUMNAS_RENOMBRADAS.get(c, c) for c in encabezados]

    registros = []
    for fila in filas[1:]:
        registro = {columna: _texto(valor) for columna, valor in zip(encabezados, fila) if columna}
        if any(registro.values()):
            registros.append(registro)

    _descartar_columnas_vacias(registros)
    _numerar(registros)
    for registro in registros:
        fase = registro.get('Fase Actual', '')
        registro['Fase Actual'] = config.FASES_RENOMBRADAS.get(fase, fase)
    return registros


def _texto(valor):
    """Valor de una celda como texto, con los formatos de la boleta."""
    if valor is None:
        return ''
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, float):
        return str(int(valor)) if valor.is_integer() else str(valor)
    if isinstance(valor, datetime):
        return valor.strftime(config.FORMATO_FECHA)
    if isinstance(valor, date):
        return valor.strftime(config.FORMATO_FECHA)
    if isinstance(valor, time):
        return valor.strftime(config.FORMATO_HORA)
    texto = str(valor).strip()
    return '' if texto.lower() == 'nan' else texto


def _descartar_columnas_vacias(registros):
    """Quita las columnas que no son de la boleta actual y no tienen ningún dato."""
    extra = {c for registro in registros for c in registro if c not in config.COLUMNAS}
    vacias = {c for c in extra if not any(registro.get(c) for registro in registros)}
    for registro in registros:
        for columna in vacias:
            registro.pop(columna, None)


def _numerar(registros):
    """Deja en cada registro un `ID Boleta` entero y único."""
    usados, pendientes = set(), []
    for registro in registros:
        try:
            numero = int(float(registro.get(ID, '')))
        except ValueError:
            numero = 0
        if numero > 0 and numero not in usados:
            usados.add(numero)
            registro[ID] = numero
        else:
            pendientes.append(registro)
    siguiente = max(usados, default=0) + 1
    for registro in pendientes:
        registro[ID] = siguiente
        siguiente += 1
