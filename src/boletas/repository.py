"""Capa de acceso a datos (patrón Repository).

`BoletaRepository` es la *única* parte del programa que sabe que las boletas se
guardan en un archivo Excel con pandas. Toda la interfaz gráfica trabaja contra
estos métodos, sin tocar directamente el DataFrame ni openpyxl. Si el día de
mañana se quisiera migrar a una base de datos, solo habría que reescribir esta
clase.

Cada alta, edición o borrado se escribe en el Excel en el momento (no al cerrar
la aplicación). Si la escritura falla (p. ej. el Excel está abierto), el cambio
se deshace también en memoria y se lanza la excepción: así lo que se ve en la
aplicación es siempre lo que hay en el archivo.
"""

import os
import tempfile

import pandas as pd

from . import catalogo, config


class BoletaRepository:
    """Gestiona la lectura, escritura y consultas de las boletas."""

    def __init__(self, excel_file=None):
        # Se lee aquí (no como valor por defecto del parámetro) para respetar
        # la ruta cambiada desde la Configuración.
        self.excel_file = excel_file or config.EXCEL_FILE
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

        - Renombra las columnas del formato con 7 fases (`config.COLUMNAS_RENOMBRADAS`):
          la Cancelación pasa de F7 a F6 y la antigua Reimpresión se conserva
          en columnas `Reimpresion_Antigua_*` (se descartan si están vacías).
        - Añade las columnas nuevas que falten (si no, sus valores no se
          guardarían al actualizar una boleta).
        - Renombra las fases que cambiaron de nombre (`config.FASES_RENOMBRADAS`).
        """
        if config.COLUMNA_FORMATO_VIEJO in self.df.columns:
            self.df = self.df.rename(columns=config.COLUMNAS_RENOMBRADAS)
            antiguas = [c for c in config.COLUMNAS_RENOMBRADAS.values()
                        if c not in config.COLUMNAS and c in self.df.columns]
            vacias = [c for c in antiguas
                      if self.df[c].fillna('').astype(str).str.strip().eq('').all()]
            self.df = self.df.drop(columns=vacias)
        for columna in config.COLUMNAS:
            if columna not in self.df.columns:
                self.df[columna] = pd.NA
        self.df['Fase Actual'] = self.df['Fase Actual'].replace(config.FASES_RENOMBRADAS)

    def save(self):
        """Guarda las boletas en el Excel respetando el orden de columnas.

        Las columnas que no son de `config.COLUMNAS` (p. ej. datos de una fase
        eliminada) se conservan al final. Se escribe primero un archivo
        temporal y luego se reemplaza el Excel: si algo falla a mitad, el
        archivo anterior queda intacto.

        Lanza la excepción correspondiente si falla (la capa de UI la traduce
        a un mensaje para el usuario).
        """
        extra = [c for c in self.df.columns if c not in config.COLUMNAS]
        df_to_save = self.df.reindex(columns=config.COLUMNAS + extra)
        carpeta = os.path.dirname(os.path.abspath(self.excel_file))
        descriptor, temporal = tempfile.mkstemp(prefix='~boletas_', suffix='.xlsx', dir=carpeta)
        os.close(descriptor)
        try:
            df_to_save.to_excel(temporal, index=False, engine='openpyxl')
            os.replace(temporal, self.excel_file)
        finally:
            if os.path.exists(temporal):
                os.remove(temporal)

    def _modificar_y_guardar(self, cambio):
        """Aplica `cambio()` sobre la tabla y guarda.

        Si falla el cambio o el guardado, la tabla vuelve a como estaba y se
        relanza el error: lo que hay en memoria nunca queda a medias.
        """
        anterior = self.df.copy()
        try:
            cambio()
            self.save()
        except Exception:
            self.df = anterior
            raise

    @staticmethod
    def _como_texto(valor):
        """Valor listo para guardar: todo se guarda como texto (True -> 'True').

        Con pandas 3 las columnas leídas con `dtype=str` solo aceptan texto o
        vacío; un booleano (p. ej. de una casilla) lanzaría TypeError.
        """
        if valor is None or isinstance(valor, str):
            return valor
        try:
            if pd.isna(valor):
                return valor
        except (TypeError, ValueError):
            pass
        return str(valor)

    # --- Consultas --------------------------------------------------------
    def all(self):
        """Devuelve todas las boletas."""
        return self.df

    def search(self, field, term):
        """Filtra boletas por un campo y un término (insensible a mayúsculas).

        El campo especial "Operador" busca en las columnas de operador de todas
        las fases.
        """
        # regex=False: se busca el texto tal cual ("(" o "." no son patrones).
        term = term.strip()
        if field == "Operador":
            mask = False
            for columna in config.COLUMNAS_OPERADOR:
                mask = mask | self.df[columna].astype(str).str.contains(term, case=False, na=False, regex=False)
            return self.df[mask]
        return self.df[self.df[field].astype(str).str.contains(term, case=False, na=False, regex=False)]

    def filter_by_phase(self, fase):
        """Devuelve las boletas de una fase.

        En las fases con prioridad de impresión (Revisión e Impresión), el
        resultado se ordena por prioridad de uso y luego por fecha de recepción.
        """
        if self.df.empty:
            return self.df

        filtered = self.df[self.df['Fase Actual'] == fase].copy()

        if fase in config.FASES_CON_PRIORIDAD:
            filtered['Prioridad'] = filtered['Uso'].map(catalogo.mapa_prioridades()).fillna(config.PRIORIDAD_POR_DEFECTO)
            filtered['Fecha_Orden'] = pd.to_datetime(
                filtered['F1_Fecha'], format=config.FORMATO_FECHA, errors='coerce'
            )
            filtered.sort_values(by=['Prioridad', 'Fecha_Orden'], ascending=[True, True], inplace=True)

        return filtered

    def numero_impresion(self, carne, boleta_id):
        """Número de impresión del usuario para una boleta: 1 si es su primera.

        Cuenta las boletas del mismo carné con un ID menor que `boleta_id`.
        """
        carne = str(carne).strip()
        if self.df.empty or not carne:
            return 1
        mismo_usuario = self.df['Carné'].astype(str).str.strip() == carne
        anteriores = self.df['ID Boleta'] < int(boleta_id)
        return int((mismo_usuario & anteriores).sum()) + 1

    def registros(self):
        """Todas las boletas como lista de diccionarios (valores vacíos -> '')."""
        return self.df.fillna('').to_dict('records')

    def get_next_id(self):
        """Calcula el siguiente ID de boleta disponible."""
        if self.df.empty or 'ID Boleta' not in self.df.columns or self.df['ID Boleta'].isnull().all():
            return 1
        return int(self.df['ID Boleta'].max() + 1)

    def get_by_id(self, boleta_id):
        """Devuelve los datos de una boleta como diccionario (vacíos -> ''), o None.

        Los vacíos se devuelven como '' y no como NaN: un NaN es "verdadero" en
        Python y, p. ej., `PhaseDetector` lo tomaría como un operador escrito.
        """
        if self.df.empty:
            return None
        rows = self.df[self.df['ID Boleta'] == boleta_id]
        if rows.empty:
            return None
        return rows.iloc[0].fillna('').to_dict()

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

    # --- Modificaciones (se guardan en el Excel al momento) --------------
    def add(self, record):
        """Añade una boleta nueva (diccionario campo -> valor) y guarda.

        Si no se puede guardar, la boleta no queda añadida y se lanza el error.
        """
        fila = {clave: valor if clave == 'ID Boleta' else self._como_texto(valor)
                for clave, valor in record.items()}

        def cambio():
            self.df = pd.concat([self.df, pd.DataFrame([fila])], ignore_index=True)

        self._modificar_y_guardar(cambio)

    def update(self, boleta_id, form_data):
        """Actualiza los campos de una boleta existente y guarda.

        Devuelve True si se encontró y actualizó, False si no existe. Si no se
        puede guardar, la boleta queda como estaba y se lanza el error.
        """
        idx_list = self.df.index[self.df['ID Boleta'] == boleta_id].tolist()
        if not idx_list:
            return False
        idx = idx_list[0]

        def cambio():
            for key, value in form_data.items():
                if key in self.df.columns and key != 'ID Boleta':
                    self.df.loc[idx, key] = self._como_texto(value)

        self._modificar_y_guardar(cambio)
        return True

    def delete(self, boleta_id):
        """Borra una boleta por su ID y guarda. Devuelve True si existía.

        Si no se puede guardar, la boleta no se borra y se lanza el error.
        """
        idx_to_drop = self.df.index[self.df['ID Boleta'] == boleta_id]
        if idx_to_drop.empty:
            return False
        def cambio():
            self.df = self.df.drop(idx_to_drop)

        self._modificar_y_guardar(cambio)
        return True
