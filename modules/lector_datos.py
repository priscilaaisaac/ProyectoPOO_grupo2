import pandas as pd
from abc import ABC, abstractmethod
from sqlalchemy import create_engine

import csv

def detectar_formato(origen):
    """Detecta el separador y si el archivo tiene encabezado usando csv.Sniffer."""
    if hasattr(origen, 'read'):
        chunk = origen.read(8192)
        if isinstance(chunk, bytes):
            chunk = chunk.decode('utf-8', errors='ignore')
        origen.seek(0)
    else:
        with open(origen, 'r', encoding='utf-8', errors='ignore') as f:
            chunk = f.read(8192)
            
    try:
        sniffer = csv.Sniffer()
        # csv.Sniffer requiere un string de delimitadores posibles
        dialect = sniffer.sniff(chunk, delimiters=',;\t|- ')
        tiene_encabezado = sniffer.has_header(chunk)
        return dialect.delimiter, tiene_encabezado
    except Exception:
        # Fallback si Sniffer falla
        separadores = [',', ';', '\t', '|', '-', ' ']
        conteo = {sep: chunk.count(sep) for sep in separadores}
        mejor_sep = max(conteo, key=conteo.get) if sum(conteo.values()) > 0 else ','
        return mejor_sep, True


# 1. Interfaz Base
class LectorDatos(ABC):
    @abstractmethod
    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        """Lee los datos desde el origen y retorna un DataFrame completo."""
        pass

# 2. Clase Concreta para Archivos (CSV, TXT, Excel)
class LectorCSV(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        nombre = origen.name.lower()
        if not nombre.endswith('.csv'):
            raise ValueError(f"El archivo provisto no tiene extensión CSV: {nombre}")
        
        sep, has_header = detectar_formato(origen)
        sep = kwargs.get('sep', sep)
        header_row = 0 if has_header else None
        
        return pd.read_csv(origen, sep=sep, header=header_row, engine='python', on_bad_lines='skip', skip_blank_lines=True)

class LectorTXT(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        nombre = origen.name.lower()
        if not nombre.endswith('.txt'):
            raise ValueError(f"El archivo provisto no tiene extensión TXT: {nombre}")
        
        sep, has_header = detectar_formato(origen)
        sep = kwargs.get('sep', sep)
        header_row = 0 if has_header else None
        
        return pd.read_csv(origen, sep=sep, header=header_row, engine='python', on_bad_lines='skip', skip_blank_lines=True)

class LectorExcel(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        nombre = origen.name.lower()
        if not nombre.endswith(('.xlsx', '.xltx', '.xltm')):
            raise ValueError(f"El archivo no es un formato de Excel válido: {nombre}")
        return pd.read_excel(origen)

# 3. Clase Concreta para Bases de Datos SQL
class LectorSQL(LectorDatos):
    def leer(self, origen: str, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
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