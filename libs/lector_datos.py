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
class LectorArchivo(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None) -> pd.DataFrame:
        nombre = origen.name.lower()
        if nombre.endswith(('.csv', '.txt')):
            return pd.read_csv(origen)
        elif nombre.endswith(('.xlsx', '.xltx', '.xltm')):
            return pd.read_excel(origen)
        else:
            raise ValueError(f"Formato no soportado: {nombre}")

# 3. Clase Concreta para Bases de Datos SQL
class LectorSQL(LectorDatos):
    def leer(self, origen: str, nombre_tabla: str = None) -> pd.DataFrame:
        if not nombre_tabla:
            raise ValueError("Se requiere el nombre de la tabla para bases de datos SQL.")
        
        # SQLAlchemy gestiona la conexión con motores como SQLite, PostgreSQL, MySQL
        engine = create_engine(origen)
        query = f"SELECT * FROM {nombre_tabla}"
        return pd.read_sql(query, con=engine)

# 4. Factory
class FactoryLectorDatos:
    @staticmethod
    def obtener_lector(tipo_origen: str) -> LectorDatos:
        """
        Retorna la instancia adecuada según el tipo de origen.
        tipo_origen debe ser 'CSV' o 'SQL'.
        """
        if tipo_origen == "CSV":
            return LectorArchivo()
        elif tipo_origen == "SQL":
            return LectorSQL()
        else:
            raise ValueError(f"Tipo de origen desconocido: {tipo_origen}")