import pandas as pd
from abc import ABC, abstractmethod
from sqlalchemy import create_engine

# 1. Interfaz Base
class LectorDatos(ABC):
    @abstractmethod
    def leer(self, origen, nombre_tabla: str = None) -> pd.DataFrame:
        """Lee los datos desde el origen y retorna un DataFrame completo."""
        pass

# 2. Clase Concreta para Archivos (CSV, TXT, Excel)
class LectorCSV(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None) -> pd.DataFrame:
        nombre = origen.name.lower()
        if not nombre.endswith('.csv'):
            raise ValueError(f"El archivo provisto no tiene extensión CSV: {nombre}")
        return pd.read_csv(origen, sep=r'[,;\t-]', engine='python')

class LectorTXT(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None) -> pd.DataFrame:
        nombre = origen.name.lower()
        if not nombre.endswith('.txt'):
            raise ValueError(f"El archivo provisto no tiene extensión TXT: {nombre}")
        return pd.read_csv(origen, sep=r'[,;\t-]', engine='python')

class LectorExcel(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None) -> pd.DataFrame:
        nombre = origen.name.lower()
        if not nombre.endswith(('.xlsx', '.xltx', '.xltm')):
            raise ValueError(f"El archivo no es un formato de Excel válido: {nombre}")
        return pd.read_excel(origen)

# 3. Clase Concreta para Bases de Datos SQL
class LectorSQL(LectorDatos):
    def leer(self, origen: str, nombre_tabla: str = None) -> pd.DataFrame:
        if not nombre_tabla:
            raise ValueError("Se requiere el nombre de la tabla para bases de datos SQL.")
        
        engine = create_engine(origen)
        query = f"SELECT * FROM {nombre_tabla}"
        return pd.read_sql(query, con=engine)

# 4. Factory
class FactoryLectorDatos:
    @staticmethod
    def obtener_lector(tipo_origen: str) -> LectorDatos:
        """
        Retorna la instancia adecuada según el tipo de origen.
        tipo_origen debe ser 'CSV', 'TXT', 'EXCEL' o 'SQL'.
        """
        tipo = tipo_origen.upper()
        if tipo == "CSV":
            return LectorCSV()
        elif tipo == "TXT":
            return LectorTXT()
        elif tipo == "EXCEL":
            return LectorExcel()
        elif tipo == "SQL":
            return LectorSQL()
        else:
            raise ValueError(f"Tipo de origen desconocido: {tipo_origen}")