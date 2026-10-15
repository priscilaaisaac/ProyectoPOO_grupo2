"""
Módulo de Ingestión y Lectura de Datos.
Implementa clases concretas y una fábrica para la lectura robusta y saneada
de orígenes CSV, TXT, Excel y SQL.
"""

import csv
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Any
from sqlalchemy import create_engine


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


# 2. Clase Concreta para Archivos CSV y Similares
class LectorCSV(LectorDatos):
    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def leer(self, origen, nombre_tabla: str = None, modo_unificacion: str = "horizontal", **kwargs) -> pd.DataFrame:
        """
        Lee uno o varios archivos CSV aplicando las directivas:
        1. Detección de separador mediante csv.Sniffer(read(1024)) restringido a [',', ';', '\t', '|'].
        2. Limpieza de espacios: skipinitialspace=True en lectura, strip en columnas y en textos.
        3. Concatenación y mapeo seguro:
           - Por defecto 'horizontal' (axis=1) sumando columnas lado a lado con sufijos ante colisión.
           - Soporta 'vertical' (axis=0) alineando columnas y completando con NaN.
           - Preserva el 100% de las columnas en self.origen_por_columna.
        4. Validación estructural tabular previa al retorno.
        """
        archivos = list(origen) if isinstance(origen, (list, tuple)) else [origen]
        lista_dfs = []
        self.origen_por_columna = {}

        # Determinar modo de unificación ('horizontal' / axis=1 vs 'vertical' / axis=0)
        modo = kwargs.get('modo_unificacion', modo_unificacion)
        if kwargs.get('axis') in (0, '0', 'vertical', 'filas'):
            modo = 'vertical'
        elif kwargs.get('axis') in (1, '1', 'horizontal', 'columnas'):
            modo = 'horizontal'

        es_horizontal = modo not in (0, '0', 'vertical', 'filas')

        for archivo in archivos:
            nombre_archivo = getattr(archivo, 'name', str(archivo))
            nombre_lower = nombre_archivo.lower()

            # 1. Ramificación temprana por extensión (.xlsx, .xls, .xltx, .xltm, .xlsm vs .csv, .txt)
            es_excel = nombre_lower.endswith(('.xlsx', '.xls', '.xltx', '.xltm', '.xlsm'))

            if es_excel:
                # 2. Ruta segura para Excel: omitir csv.Sniffer por completo, .seek(0) y forzar engine='openpyxl'
                if hasattr(archivo, 'seek'):
                    try:
                        archivo.seek(0)
                    except Exception:
                        pass
                df = pd.read_excel(archivo, engine='openpyxl')
            else:
                # 3. Ruta para Texto (CSV/TXT): solo si el archivo no es Excel ejecutar csv.Sniffer
                sep_detectado = detectar_separador(archivo)
                sep_final = kwargs.get('sep', sep_detectado)

                # Lectura segura de espacios: si el separador es ' ', usar sep=r'\s+'
                # para evitar columnas vacías ante espacios contiguos
                if sep_final in (' ', r'\s+'):
                    sep_a_usar = r'\s+'
                else:
                    sep_a_usar = sep_final

                # Asegurar .seek(0) antes de pasarlo a pd.read_csv()
                if hasattr(archivo, 'seek'):
                    try:
                        archivo.seek(0)
                    except Exception:
                        pass

                # Forzar skipinitialspace=True y manejar codificaciones
                try:
                    df = pd.read_csv(archivo, sep=sep_a_usar, skipinitialspace=True)
                except UnicodeDecodeError:
                    if hasattr(archivo, 'seek'):
                        try:
                            archivo.seek(0)
                        except Exception:
                            pass
                    df = pd.read_csv(archivo, sep=sep_a_usar, encoding='latin-1', skipinitialspace=True)
                except Exception:
                    if hasattr(archivo, 'seek'):
                        try:
                            archivo.seek(0)
                        except Exception:
                            pass
                    df = pd.read_csv(archivo, sep=sep_a_usar, engine='python', on_bad_lines='skip', skipinitialspace=True)

            # 4. Consolidación inalterada: ambas ramas desembocan en saneamiento y lista_dfs
            df = sanear_dataframe_individual(df)
            lista_dfs.append((df, nombre_archivo))

        if not lista_dfs:
            return pd.DataFrame()

        # 3. Concatenación y Mapeo Seguro
        if es_horizontal:
            columnas_existentes = set()
            dfs_a_unir = []
            for df_indiv, nombre_arch in lista_dfs:
                nuevas_columnas = []
                for col in df_indiv.columns:
                    col_final = col
                    if col_final in columnas_existentes:
                        contador = 2
                        candidato = f"{col} ({contador})"
                        while candidato in columnas_existentes:
                            contador += 1
                            candidato = f"{col} ({contador})"
                        col_final = candidato

                    columnas_existentes.add(col_final)
                    nuevas_columnas.append(col_final)
                    self.origen_por_columna[col_final] = nombre_arch

                df_indiv.columns = nuevas_columnas
                dfs_a_unir.append(df_indiv)

            df_consolidado = pd.concat(dfs_a_unir, axis=1)
        else:
            dfs_a_unir = []
            for df_indiv, nombre_arch in lista_dfs:
                for col in df_indiv.columns:
                    if col not in self.origen_por_columna:
                        self.origen_por_columna[col] = nombre_arch
                dfs_a_unir.append(df_indiv)

            df_consolidado = pd.concat(dfs_a_unir, axis=0, ignore_index=True)

        # 4. Validación Estructural
        df_consolidado = validar_estructura_tabular(df_consolidado)
        df_consolidado.attrs['origen_por_columna'] = self.origen_por_columna
        return df_consolidado


class LectorTXT(LectorDatos):
    def __init__(self):
        self.origen_por_columna = {}

    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        lector_csv = LectorCSV()
        df = lector_csv.leer(origen, nombre_tabla=nombre_tabla, **kwargs)
        self.origen_por_columna = lector_csv.origen_por_columna
        return df


class LectorExcel(LectorDatos):
    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def leer(self, origen, nombre_tabla: str = None, modo_unificacion: str = "horizontal", **kwargs) -> pd.DataFrame:
        lector_csv = LectorCSV()
        df = lector_csv.leer(origen, nombre_tabla=nombre_tabla, modo_unificacion=modo_unificacion, **kwargs)
        self.origen_por_columna = lector_csv.origen_por_columna
        return df


# 3. Clase Concreta para Bases de Datos SQL
class LectorSQL(LectorDatos):
    def leer(self, origen: str, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        if not nombre_tabla:
            raise ValueError("Se requiere el nombre de la tabla para bases de datos SQL.")

        engine = create_engine(origen)
        query = f"SELECT * FROM {nombre_tabla}"
        df = pd.read_sql(query, con=engine)
        df = sanear_dataframe_individual(df)
        return validar_estructura_tabular(df)


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
    def obtener_lector_por_archivo(nombre_archivo) -> LectorDatos:
        """Determina y retorna la instancia de LectorDatos adecuada según la extensión del archivo."""
        if isinstance(nombre_archivo, (list, tuple)):
            if not nombre_archivo:
                return LectorCSV()
            # Al procesar múltiples archivos (posiblemente mixtos .csv, .txt, .xlsx),
            # LectorCSV posee la ramificación temprana por extensión y consolidación horizontal unificada.
            return LectorCSV()

        nombre = getattr(nombre_archivo, 'name', str(nombre_archivo)).lower()
        if nombre.endswith('.csv'):
            return LectorCSV()
        elif nombre.endswith('.txt'):
            return LectorTXT()
        elif nombre.endswith(('.xlsx', '.xls', '.xltx', '.xltm', '.xlsm')):
            return LectorExcel()
        else:
            raise ValueError(f"Extensión de archivo no soportada: {nombre_archivo}")