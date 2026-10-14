import csv
import pandas as pd
from abc import ABC, abstractmethod
from sqlalchemy import create_engine


def detectar_formato(origen):
    """
    Detecta el separador y si el archivo tiene encabezado usando csv.Sniffer con
    un fallback robusto por análisis de frecuencias y consistencia entre líneas.
    Soporta rutas de archivo y streams/buffers de memoria (BytesIO, StringIO, UploadedFile).
    """
    chunk = ""
    pos_original = None

    if hasattr(origen, 'read'):
        if hasattr(origen, 'tell'):
            try:
                pos_original = origen.tell()
            except Exception:
                pos_original = 0
        raw = origen.read(16384)
        if isinstance(raw, bytes):
            try:
                chunk = raw.decode('utf-8')
            except UnicodeDecodeError:
                chunk = raw.decode('latin-1', errors='ignore')
        else:
            chunk = str(raw)
        
        if hasattr(origen, 'seek'):
            origen.seek(pos_original if pos_original is not None else 0)
    else:
        try:
            with open(origen, 'r', encoding='utf-8') as f:
                chunk = f.read(16384)
        except (UnicodeDecodeError, Exception):
            with open(origen, 'r', encoding='latin-1', errors='ignore') as f:
                chunk = f.read(16384)

    candidatos = [',', ';', '\t', '|']
    
    # Intento 1: csv.Sniffer estándar
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(chunk, delimiters=',;\t|')
        tiene_encabezado = sniffer.has_header(chunk)
        return dialect.delimiter, tiene_encabezado
    except Exception:
        pass

    # Intento 2: Fallback por consistencia y conteo de frecuencias
    lineas = [l for l in chunk.splitlines() if l.strip()][:15]
    if lineas:
        puntuaciones = {}
        for sep in candidatos:
            conteos = [l.count(sep) for l in lineas]
            if not conteos or sum(conteos) == 0:
                puntuaciones[sep] = 0
                continue
            # Si cada línea tiene exactamente el mismo número (> 0) de delimitadores, es consistente
            es_consistente = min(conteos) > 0 and len(set(conteos)) == 1
            if es_consistente:
                puntuaciones[sep] = sum(conteos) * 10
            else:
                puntuaciones[sep] = sum(conteos)
        mejor_sep = max(puntuaciones, key=puntuaciones.get) if any(v > 0 for v in puntuaciones.values()) else ','
    else:
        mejor_sep = ','

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
        nombre = getattr(origen, 'name', str(origen)).lower()
        if not nombre.endswith('.csv'):
            raise ValueError(f"El archivo provisto no tiene extensión CSV: {nombre}")

        sep, has_header = detectar_formato(origen)
        sep = kwargs.get('sep', sep)
        header_row = 0 if has_header else None

        if hasattr(origen, 'seek'):
            origen.seek(0)

        try:
            return pd.read_csv(origen, sep=sep, header=header_row, encoding='utf-8', engine='python', on_bad_lines='skip', skip_blank_lines=True)
        except (UnicodeDecodeError, Exception):
            if hasattr(origen, 'seek'):
                origen.seek(0)
            return pd.read_csv(origen, sep=sep, header=header_row, encoding='latin-1', engine='python', on_bad_lines='skip', skip_blank_lines=True)


class LectorTXT(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        nombre = getattr(origen, 'name', str(origen)).lower()
        if not nombre.endswith('.txt'):
            raise ValueError(f"El archivo provisto no tiene extensión TXT: {nombre}")

        sep, has_header = detectar_formato(origen)
        sep = kwargs.get('sep', sep)
        header_row = 0 if has_header else None

        if hasattr(origen, 'seek'):
            origen.seek(0)

        try:
            return pd.read_csv(origen, sep=sep, header=header_row, encoding='utf-8', engine='python', on_bad_lines='skip', skip_blank_lines=True)
        except (UnicodeDecodeError, Exception):
            if hasattr(origen, 'seek'):
                origen.seek(0)
            return pd.read_csv(origen, sep=sep, header=header_row, encoding='latin-1', engine='python', on_bad_lines='skip', skip_blank_lines=True)


class LectorExcel(LectorDatos):
    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        nombre = getattr(origen, 'name', str(origen)).lower()
        if not (nombre.endswith('.xlsx') or nombre.endswith('.xltx') or nombre.endswith('.xltm')):
            raise ValueError(f"El archivo no es un formato de Excel válido (.xlsx, .xltx, .xltm): {nombre}")

        if hasattr(origen, 'seek'):
            origen.seek(0)

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
        tipo = str(tipo_origen).upper()
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

    @staticmethod
    def obtener_lector_por_archivo(nombre_archivo: str) -> LectorDatos:
        """Determina y retorna la instancia de LectorDatos adecuada según la extensión del archivo."""
        nombre = str(nombre_archivo).lower()
        if nombre.endswith('.csv'):
            return LectorCSV()
        elif nombre.endswith('.txt'):
            return LectorTXT()
        elif nombre.endswith(('.xlsx', '.xltx', '.xltm')):
            return LectorExcel()
        else:
            raise ValueError(f"Extensión de archivo no soportada: {nombre_archivo}")