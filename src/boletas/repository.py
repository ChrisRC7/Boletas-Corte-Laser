"""Capa de acceso a datos (patrón Repository) sobre SQLite.

`BoletaRepository` es la *única* parte del programa que sabe que las boletas se
guardan en una base de datos SQLite. Toda la interfaz trabaja contra estos
métodos y recibe diccionarios `{columna: valor}` (los vacíos como '').

- Cada alta, edición o borrado es una transacción que se escribe al momento y
  solo toca la fila de esa boleta: dos PCs con la misma base de datos no se
  pisan los cambios de boletas distintas. Cada consulta lee la base de datos,
  así que siempre se ve lo último que guardó cualquier equipo.
- Todas las columnas (menos `ID Boleta`) se guardan como texto, igual que en el
  Excel original (True -> 'True').
- La primera vez, si no existe la base de datos pero sí el Excel anterior
  (`config.EXCEL_FILE`), se importa (ver `excel_antiguo.py`). El Excel no se
  modifica: queda como respaldo.

Los errores de SQLite se relanzan como `ErrorDatos`, con un mensaje apto para
mostrarse; la capa de UI lo traduce a un `messagebox`.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime

from . import catalogo, config, excel_antiguo
from .fechas import leer_fecha_hora

TABLA = "boletas"
ID = 'ID Boleta'
# Segundos que se espera si otro equipo está escribiendo en ese instante.
ESPERA_BLOQUEO = 10


class ErrorDatos(Exception):
    """No se pudo leer o escribir la base de datos. El mensaje es apto para mostrarse."""


def _q(nombre):
    """Nombre de columna entre comillas (tienen espacios y tildes: "ID Boleta", "Carné")."""
    return '"' + str(nombre).replace('"', '""') + '"'


class BoletaRepository:
    """Gestiona la lectura, escritura y consultas de las boletas."""

    def __init__(self, db_file=None, excel_file=None):
        # Se leen aquí (no como valor por defecto del parámetro) para respetar
        # las rutas cambiadas desde la Configuración.
        self.db_file = db_file or config.DB_FILE
        self.excel_file = excel_file or config.EXCEL_FILE
        # Boletas importadas del Excel anterior en este arranque (None = no hubo importación).
        self.importadas = None

    # --- Conexión -----------------------------------------------------------
    def _conectar(self):
        conexion = sqlite3.connect(self.db_file, timeout=ESPERA_BLOQUEO, isolation_level=None)
        conexion.row_factory = sqlite3.Row
        return conexion

    def _error(self, error):
        if isinstance(error, sqlite3.OperationalError) and 'locked' in str(error).lower():
            return ErrorDatos(f"La base de datos '{self.db_file}' está ocupada por otro equipo o programa.\n"
                              "Espere un momento y vuelva a intentarlo.")
        if isinstance(error, sqlite3.OperationalError) and 'readonly' in str(error).lower():
            return ErrorDatos(f"No hay permiso para escribir en '{self.db_file}'.")
        return ErrorDatos(f"Error en la base de datos '{self.db_file}': {error}")

    def _leer(self, sql, parametros=()):
        """Ejecuta una consulta y devuelve las filas como diccionarios (vacíos -> '')."""
        try:
            with closing(self._conectar()) as conexion:
                filas = conexion.execute(sql, parametros).fetchall()
        except sqlite3.Error as error:
            raise self._error(error) from None
        return [{clave: ('' if fila[clave] is None else fila[clave]) for clave in fila.keys()}
                for fila in filas]

    def _escribir(self, operacion):
        """Ejecuta `operacion(conexion)` en una transacción: o se guarda todo o nada."""
        try:
            with closing(self._conectar()) as conexion:
                conexion.execute("BEGIN IMMEDIATE")
                try:
                    resultado = operacion(conexion)
                    conexion.execute("COMMIT")
                except BaseException:
                    conexion.execute("ROLLBACK")
                    raise
                return resultado
        except sqlite3.Error as error:
            raise self._error(error) from None

    @staticmethod
    def _columnas(conexion):
        return [fila[1] for fila in conexion.execute(f"PRAGMA table_info({TABLA})")]

    # --- Arranque -----------------------------------------------------------
    def load(self):
        """Prepara la base de datos: la crea, importa el Excel anterior o la actualiza.

        Lanza `ErrorDatos` si la base de datos (o el Excel a importar) no se
        puede leer; en ese caso no se crea ni se modifica nada.
        """
        nueva = not os.path.exists(self.db_file)
        antiguas = None
        if nueva and os.path.exists(self.excel_file):
            try:
                antiguas = excel_antiguo.leer(self.excel_file)
            except excel_antiguo.ErrorExcel as error:
                raise ErrorDatos(str(error)) from None

        try:
            self._escribir(lambda conexion: self._preparar(conexion, antiguas))
        except ErrorDatos:
            if nueva and os.path.exists(self.db_file):
                os.remove(self.db_file)  # No dejar una base de datos vacía a medio crear.
            raise
        self.importadas = len(antiguas) if antiguas is not None else None

    def _preparar(self, conexion, antiguas):
        columnas = ", ".join(f"{_q(c)} TEXT" for c in config.COLUMNAS if c != ID)
        conexion.execute(f"CREATE TABLE IF NOT EXISTS {TABLA} ({_q(ID)} INTEGER PRIMARY KEY, {columnas})")
        # Columnas añadidas en versiones nuevas del programa.
        existentes = self._columnas(conexion)
        for columna in config.COLUMNAS:
            if columna not in existentes:
                conexion.execute(f"ALTER TABLE {TABLA} ADD COLUMN {_q(columna)} TEXT")
        # Fases que cambiaron de nombre (`Fase Actual` guarda el nombre tal cual).
        for vieja, actual in config.FASES_RENOMBRADAS.items():
            conexion.execute(f'UPDATE {TABLA} SET "Fase Actual" = ? WHERE "Fase Actual" = ?', (actual, vieja))
        for registro in antiguas or []:
            self._insertar(conexion, registro)

    def _insertar(self, conexion, registro):
        """Inserta una fila; las columnas que no existan (datos de fases eliminadas) se crean."""
        existentes = self._columnas(conexion)
        for columna in registro:
            if columna not in existentes:
                conexion.execute(f"ALTER TABLE {TABLA} ADD COLUMN {_q(columna)} TEXT")
        claves = list(registro)
        conexion.execute(
            f"INSERT INTO {TABLA} ({', '.join(_q(c) for c in claves)}) VALUES ({', '.join('?' for _ in claves)})",
            [int(registro[c]) if c == ID else self._como_texto(registro[c]) for c in claves])

    @staticmethod
    def _como_texto(valor):
        """Valor listo para guardar: todo se guarda como texto (True -> 'True', None -> '')."""
        return '' if valor is None else str(valor)

    # --- Consultas --------------------------------------------------------
    def all(self):
        """Todas las boletas (lista de diccionarios), por número de boleta."""
        return self._leer(f"SELECT * FROM {TABLA} ORDER BY {_q(ID)}")

    def registros(self):
        """Todas las boletas como lista de diccionarios (valores vacíos -> '')."""
        return self.all()

    def search(self, field, term):
        """Filtra boletas por un campo y un término.

        - "ID Boleta": el número exacto (buscar 1 no devuelve la 10 ni la 11).
        - "Operador": busca en las columnas de operador de todas las fases.
        - El resto: el texto tal cual, en cualquier parte, sin distinguir mayúsculas.
        """
        term = str(term).strip()
        if field == ID:
            try:
                numero = int(term.lstrip('#'))
            except ValueError:
                return []
            boleta = self.get_by_id(numero)
            return [boleta] if boleta else []
        columnas = config.COLUMNAS_OPERADOR if field == "Operador" else [field]
        buscado = term.lower()
        return [boleta for boleta in self.all()
                if any(buscado in str(boleta.get(columna, '')).lower() for columna in columnas)]

    def filter_by_phase(self, fase):
        """Devuelve las boletas de una fase.

        En las fases con prioridad de impresión (Revisión e Impresión), el
        resultado se ordena por prioridad de uso y luego por fecha de recepción.
        """
        boletas = self._leer(f'SELECT * FROM {TABLA} WHERE "Fase Actual" = ? ORDER BY {_q(ID)}', (fase,))
        if fase in config.FASES_CON_PRIORIDAD:
            boletas.sort(key=lambda b: (
                catalogo.prioridad_uso(str(b.get('Uso', '')).strip()),
                leer_fecha_hora(b.get('F1_Fecha', ''), b.get('F1_Hora', '')) or datetime.max,
                b[ID]))
        return boletas

    def numero_impresion(self, carne, boleta_id):
        """Número de impresión del usuario para una boleta: 1 si es su primera.

        Cuenta las boletas del mismo carné con un ID menor que `boleta_id`.
        """
        carne = str(carne).strip()
        if not carne:
            return 1
        filas = self._leer(f'SELECT COUNT(*) AS n FROM {TABLA} WHERE TRIM("Carné") = ? AND {_q(ID)} < ?',
                           (carne, int(boleta_id)))
        return int(filas[0]['n']) + 1

    def get_next_id(self):
        """Calcula el siguiente ID de boleta disponible."""
        filas = self._leer(f"SELECT MAX({_q(ID)}) AS maximo FROM {TABLA}")
        return int(filas[0]['maximo'] or 0) + 1

    def get_by_id(self, boleta_id):
        """Devuelve los datos de una boleta como diccionario (vacíos -> ''), o None."""
        filas = self._leer(f"SELECT * FROM {TABLA} WHERE {_q(ID)} = ?", (int(boleta_id),))
        return filas[0] if filas else None

    def buscar_datos_usuario(self, campo, valor):
        """Datos del usuario (nombre, cuenta, carrera, carné, teléfono) de su boleta más reciente.

        `campo` es 'Carné' o 'Cuenta'. La comparación ignora mayúsculas y
        espacios. Devuelve un diccionario solo con los campos que tienen valor,
        o None si el usuario no tiene boletas anteriores.
        """
        valor = str(valor).strip().lower()
        if not valor or campo not in ('Carné', 'Cuenta'):
            return None
        coincidencias = [b for b in self.all() if str(b.get(campo, '')).strip().lower() == valor]
        if not coincidencias:
            return None
        ultima = coincidencias[-1]
        datos = {columna: str(ultima.get(columna, '')).strip() for columna in config.CAMPOS_DATOS_USUARIO}
        return {columna: dato for columna, dato in datos.items() if dato} or None

    # --- Modificaciones (se guardan en la base de datos al momento) --------
    def add(self, record):
        """Añade una boleta nueva (diccionario campo -> valor).

        Si no se puede guardar, la boleta no queda añadida y se lanza `ErrorDatos`.
        """
        try:
            self._escribir(lambda conexion: self._insertar(conexion, record))
        except ErrorDatos as error:
            if 'UNIQUE' in str(error):
                raise ErrorDatos(f"La boleta #{record.get(ID)} ya existe: otro equipo acaba de crearla.\n"
                                 "Vuelva a pulsar Guardar para usar el siguiente número.") from None
            raise

    def update(self, boleta_id, form_data):
        """Actualiza los campos de una boleta existente.

        Devuelve True si se encontró y actualizó, False si no existe. Si no se
        puede guardar, la boleta queda como estaba y se lanza `ErrorDatos`.
        """
        def cambio(conexion):
            existentes = self._columnas(conexion)
            claves = [c for c in form_data if c in existentes and c != ID]
            if not claves:
                return conexion.execute(f"SELECT 1 FROM {TABLA} WHERE {_q(ID)} = ?",
                                        (int(boleta_id),)).fetchone() is not None
            cursor = conexion.execute(
                f"UPDATE {TABLA} SET {', '.join(f'{_q(c)} = ?' for c in claves)} WHERE {_q(ID)} = ?",
                [self._como_texto(form_data[c]) for c in claves] + [int(boleta_id)])
            return cursor.rowcount > 0

        return self._escribir(cambio)

    def delete(self, boleta_id):
        """Borra una boleta por su ID. Devuelve True si existía."""
        return self._escribir(lambda conexion: conexion.execute(
            f"DELETE FROM {TABLA} WHERE {_q(ID)} = ?", (int(boleta_id),)).rowcount > 0)
