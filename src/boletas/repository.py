"""Capa de acceso a datos (patrón Repository).

`BoletaRepository` es la *única* parte del programa que sabe que las boletas se
guardan en un archivo Excel con pandas. Toda la interfaz gráfica trabaja contra
estos métodos, sin tocar directamente el DataFrame ni openpyxl. Si el día de
mañana se quisiera migrar a una base de datos, solo habría que reescribir esta
clase.
"""

import os

import pandas as pd

from . import config


class BoletaRepository:
    """Gestiona la lectura, escritura y consultas de las boletas."""

    def __init__(self, excel_file=config.EXCEL_FILE):
        self.excel_file = excel_file
        self.df = pd.DataFrame(columns=config.COLUMNAS)

    # --- Persistencia -----------------------------------------------------
    def load(self):
        """Carga las boletas desde el Excel (o crea una tabla vacía)."""
        if os.path.exists(self.excel_file):
            self.df = pd.read_excel(self.excel_file, engine='openpyxl', dtype=str)
            self.df['ID Boleta'] = (
                pd.to_numeric(self.df['ID Boleta'], errors='coerce')
                .fillna(0)
                .astype(int)
            )
            self._migrar()
        else:
            self.df = pd.DataFrame(columns=config.COLUMNAS)

    def _migrar(self):
        """Adapta un Excel de una versión anterior a la estructura actual.

        - Añade las columnas nuevas que falten (si no, sus valores no se
          guardarían al actualizar una boleta).
        - Renombra las fases que cambiaron de nombre (`config.FASES_RENOMBRADAS`).
        """
        for columna in config.COLUMNAS:
            if columna not in self.df.columns:
                self.df[columna] = pd.NA
        self.df['Fase Actual'] = self.df['Fase Actual'].replace(config.FASES_RENOMBRADAS)

    def save(self):
        """Guarda las boletas en el Excel respetando el orden de columnas.

        Lanza la excepción correspondiente si falla (la capa de UI la traduce
        a un mensaje para el usuario).
        """
        df_to_save = self.df.reindex(columns=config.COLUMNAS)
        df_to_save.to_excel(self.excel_file, index=False, engine='openpyxl')

    # --- Consultas --------------------------------------------------------
    def all(self):
        """Devuelve todas las boletas."""
        return self.df

    def search(self, field, term):
        """Filtra boletas por un campo y un término (insensible a mayúsculas).

        El campo especial "Operador" busca en las columnas de operador de todas
        las fases.
        """
        term = term.strip()
        if field == "Operador":
            mask = False
            for columna in config.COLUMNAS_OPERADOR:
                mask = mask | self.df[columna].str.contains(term, case=False, na=False)
            return self.df[mask]
        return self.df[self.df[field].astype(str).str.contains(term, case=False, na=False)]

    def filter_by_phase(self, fase):
        """Devuelve las boletas de una fase.

        En las fases con prioridad de impresión (Revisión e Impresión), el
        resultado se ordena por prioridad de uso y luego por fecha de recepción.
        """
        if self.df.empty:
            return self.df

        filtered = self.df[self.df['Fase Actual'] == fase].copy()

        if fase in config.FASES_CON_PRIORIDAD:
            filtered['Prioridad'] = filtered['Uso'].map(config.PRIORIDAD_USO).fillna(config.PRIORIDAD_POR_DEFECTO)
            filtered['Fecha_Orden'] = pd.to_datetime(
                filtered['F1_Fecha'], format=config.FORMATO_FECHA, errors='coerce'
            )
            filtered.sort_values(by=['Prioridad', 'Fecha_Orden'], ascending=[True, True], inplace=True)

        return filtered

    def get_next_id(self):
        """Calcula el siguiente ID de boleta disponible."""
        if self.df.empty or 'ID Boleta' not in self.df.columns or self.df['ID Boleta'].isnull().all():
            return 1
        return int(self.df['ID Boleta'].max() + 1)

    def get_by_id(self, boleta_id):
        """Devuelve los datos de una boleta como diccionario, o None."""
        if self.df.empty:
            return None
        rows = self.df[self.df['ID Boleta'] == boleta_id]
        if rows.empty:
            return None
        return rows.iloc[0].to_dict()

    def buscar_datos_usuario(self, campo, valor):
        """Datos del usuario (nombre, cuenta, carrera, carné, teléfono) de su boleta más reciente.

        `campo` es 'Carné' o 'Cuenta'. La comparación ignora mayúsculas y
        espacios. Devuelve un diccionario solo con los campos que tienen valor,
        o None si el usuario no tiene boletas anteriores.
        """
        valor = str(valor).strip().lower()
        if self.df.empty or not valor or campo not in self.df.columns:
            return None
        coincidencias = self.df[self.df[campo].astype(str).str.strip().str.lower() == valor]
        if coincidencias.empty:
            return None
        ultima = coincidencias.sort_values('ID Boleta').iloc[-1]
        datos = {}
        for columna in config.CAMPOS_DATOS_USUARIO:
            dato = ultima.get(columna)
            if not pd.isna(dato) and str(dato).strip():
                datos[columna] = str(dato).strip()
        return datos or None

    # --- Modificaciones ---------------------------------------------------
    def add(self, record):
        """Añade una boleta nueva (diccionario campo -> valor)."""
        nuevo = pd.DataFrame([record])
        self.df = pd.concat([self.df, nuevo], ignore_index=True)

    def update(self, boleta_id, form_data):
        """Actualiza los campos de una boleta existente.

        Devuelve True si se encontró y actualizó, False si no existe.
        """
        idx_list = self.df.index[self.df['ID Boleta'] == boleta_id].tolist()
        if not idx_list:
            return False
        idx = idx_list[0]
        for key, value in form_data.items():
            if key in self.df.columns:
                self.df.loc[idx, key] = value
        return True

    def delete(self, boleta_id):
        """Borra una boleta por su ID. Devuelve True si existía y la guarda."""
        idx_to_drop = self.df.index[self.df['ID Boleta'] == boleta_id]
        if idx_to_drop.empty:
            return False
        self.df.drop(idx_to_drop, inplace=True)
        self.save()
        return True
