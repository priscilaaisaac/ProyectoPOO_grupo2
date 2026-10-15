"""
Módulo Base para la Ingestión y Lectura de Datos.
Contiene la interfaz abstracta LectorDatos y las funciones auxiliares
de detección de delimitadores y saneamiento/validación tabular.
"""

import csv
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Any


DELIMITADORES_VALIDOS = (',', ';', '\t', '|', ' ')


def detectar_separador(origen, delimitadores_validos=DELIMITADORES_VALIDOS, default=',') -> str:
    """
    Detecta el delimitador usando csv.Sniffer().sniff() de la librería estándar,
    leyendo los primeros 1024 bytes del archivo (.read(1024)).
    Restringe estrictamente los delimitadores válidos a [',', ';', '\t', '|', ' '] para evitar
    que símbolos internos como el guion (-) en 'FL-9768' rompan las columnas.
    Aplica .seek(0) inmediatamente después del sniff.
    """
    delimiters_str = ''.join(delimitadores_validos)
    chunk = ""

    if hasattr(origen, 'read'):
        if hasattr(origen, 'seek'):
            try:
                origen.seek(0)
            except Exception:
                pass
        raw = origen.read(1024)
        if isinstance(raw, bytes):
            try:
                chunk = raw.decode('utf-8')
            except UnicodeDecodeError:
                chunk = raw.decode('latin-1', errors='ignore')
        else:
            chunk = str(raw)

        if hasattr(origen, 'seek'):
            try:
                origen.seek(0)
            except Exception:
                pass
    else:
        try:
            with open(origen, 'r', encoding='utf-8') as f:
                chunk = f.read(1024)
        except (UnicodeDecodeError, Exception):
            try:
                with open(origen, 'r', encoding='latin-1', errors='ignore') as f:
                    chunk = f.read(1024)
            except Exception:
                chunk = ""

    if not chunk or not chunk.strip():
        return default

    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(chunk, delimiters=delimiters_str)
        if dialect.delimiter in delimitadores_validos:
            return dialect.delimiter
    except Exception:
        pass

    # Respaldo si csv.Sniffer falla (por ejemplo con múltiples espacios consecutivos o tablas):
    lines = [l.strip() for l in chunk.splitlines() if l.strip()]
    if lines:
        # Priorizar delimitadores estándar si aparecen consistentemente en las líneas
        for d in (',', ';', '\t', '|'):
            if d in delimitadores_validos:
                conteo_primera = lines[0].count(d)
                if conteo_primera > 0 and all(l.count(d) == conteo_primera for l in lines[:5]):
                    return d

        # Si no hay delimitadores explícitos pero las líneas tienen columnas separadas por espacios
        if ' ' in delimitadores_validos:
            num_tokens = [len(l.split()) for l in lines[:5]]
            if len(num_tokens) > 0 and num_tokens[0] >= 2 and len(set(num_tokens)) == 1:
                return ' '

    return default


def detectar_formato(origen) -> Tuple[str, bool]:
    """
    Detecta el separador y si el archivo tiene encabezado usando csv.Sniffer restringido
    a [',', ';', '\t', '|', ' '].
    Soporta rutas de archivo y streams/buffers de memoria (BytesIO, StringIO, UploadedFile).
    """
    sep = detectar_separador(origen)
    has_header = True
    chunk = ""

    if hasattr(origen, 'read'):
        if hasattr(origen, 'seek'):
            try:
                origen.seek(0)
            except Exception:
                pass
        raw = origen.read(1024)
        if isinstance(raw, bytes):
            try:
                chunk = raw.decode('utf-8')
            except UnicodeDecodeError:
                chunk = raw.decode('latin-1', errors='ignore')
        else:
            chunk = str(raw)

        if hasattr(origen, 'seek'):
            try:
                origen.seek(0)
            except Exception:
                pass
    else:
        try:
            with open(origen, 'r', encoding='utf-8') as f:
                chunk = f.read(1024)
        except (UnicodeDecodeError, Exception):
            try:
                with open(origen, 'r', encoding='latin-1', errors='ignore') as f:
                    chunk = f.read(1024)
            except Exception:
                chunk = ""

    if chunk and chunk.strip():
        try:
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(chunk)
        except Exception:
            has_header = True

    return sep, has_header


def sanear_dataframe_individual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica limpieza estricta de espacios en blanco sobre cabeceras y contenido:
    1. df.columns = df.columns.str.strip() para eliminar espacios invisibles en nombres.
    2. .apply(strip) a todas las columnas de texto (object/string) preservando valores nulos.
    """
    if df is None or df.empty:
        return df

    # Limpieza absoluta de cabeceras
    df.columns = [str(col).strip() for col in df.columns]
    if hasattr(df.columns, 'str'):
        df.columns = df.columns.str.strip()

    # Limpieza de valores en columnas de tipo texto
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    return df.reset_index(drop=True)


def validar_estructura_tabular(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validación estructural antes de retornar el DataFrame final:
    - Asegura que sea un DataFrame tabular y consistente.
    - Asegura que los nombres de columnas sean cadenas limpias y únicas.
    - Utiliza pandera si está disponible en el entorno; de lo contrario aplica
      reglas directas de validación e integridad.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Se esperaba una instancia de pd.DataFrame, recibido: {type(df)}")

    if df.empty:
        return df

    # Reset de índice para garantizar continuidad tabular
    df = df.reset_index(drop=True)

    # Validar que los nombres de columnas sean strings sin espacios redundantes y únicos
    cols = [str(c).strip() for c in df.columns]
    if len(cols) != len(set(cols)):
        vistas = set()
        dedup_cols = []
        for c in cols:
            cand = c
            k = 2
            while cand in vistas:
                cand = f"{c}_{k}"
                k += 1
            vistas.add(cand)
            dedup_cols.append(cand)
        df.columns = dedup_cols
    else:
        df.columns = cols

    try:
        try:
            import pandera.pandas as pa
        except (ImportError, AttributeError):
            import pandera as pa
        schema = pa.DataFrameSchema(
            columns={c: pa.Column(required=False, nullable=True) for c in df.columns},
            strict=False,
            coerce=False
        )
        df = schema.validate(df)
    except ImportError:
        pass
    except Exception:
        pass

    return df


# 1. Interfaz Base
class LectorDatos(ABC):
    @abstractmethod
    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        """Lee los datos desde el origen y retorna un DataFrame completo."""
        pass
