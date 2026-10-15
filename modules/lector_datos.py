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
    def __init__(self):
        self.origen_por_columna = {}

    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        """
        Lee uno o varios archivos CSV aplicando el flujo:
        1. Iteración aislada (Backend): Procesa cada archivo de forma individual en un bucle.
        2. Detección dinámica por archivo: Lee la 1ra línea y cuenta [',', ';', '\t', '|'].
        3. Aplica .seek(0) inmediatamente tras leer la primera línea y antes de pd.read_csv().
        4. Lectura individual: pd.read_csv(archivo, sep=separador_detectado) en lista temporal.
        5. Diferenciación de columnas duplicadas y acumulación progresiva de metadatos de origen.
        6. Unificación horizontal: pd.concat(lista_dfs, axis=1).
        """
        archivos = list(origen) if isinstance(origen, (list, tuple)) else [origen]
        lista_dfs = []
        self.origen_por_columna = {}
        columnas_existentes = set()
        separadores_posibles = [',', ';', '\t', '|']

        for archivo in archivos:
            nombre_archivo = getattr(archivo, 'name', str(archivo))
            nombre_lower = nombre_archivo.lower()

            if nombre_lower.endswith(('.xlsx', '.xltx', '.xltm')):
                if hasattr(archivo, 'seek'):
                    archivo.seek(0)
                df = pd.read_excel(archivo)
            else:
                # 1. Asegurar posición inicial antes de leer primera línea
                if hasattr(archivo, 'seek'):
                    archivo.seek(0)

                # Leer la primera línea como texto
                primera_linea = ""
                if hasattr(archivo, 'readline'):
                    raw = archivo.readline()
                    if isinstance(raw, bytes):
                        try:
                            primera_linea = raw.decode('utf-8')
                        except UnicodeDecodeError:
                            primera_linea = raw.decode('latin-1', errors='ignore')
                    else:
                        primera_linea = str(raw)
                else:
                    try:
                        with open(archivo, 'r', encoding='utf-8') as f:
                            primera_linea = f.readline()
                    except UnicodeDecodeError:
                        with open(archivo, 'r', encoding='latin-1', errors='ignore') as f:
                            primera_linea = f.readline()

                # REQUISITO CRÍTICO: .seek(0) inmediatamente después de leer la primera línea
                if hasattr(archivo, 'seek'):
                    archivo.seek(0)

                conteos = {sep: primera_linea.count(sep) for sep in separadores_posibles}
                separador_detectado = max(conteos, key=conteos.get)
                if conteos[separador_detectado] == 0:
                    separador_detectado = ','

                sep_final = kwargs.get('sep', separador_detectado)

                # Asegurar .seek(0) antes de pasarlo a pd.read_csv()
                if hasattr(archivo, 'seek'):
                    archivo.seek(0)

                try:
                    df = pd.read_csv(archivo, sep=sep_final, skipinitialspace=True)
                except UnicodeDecodeError:
                    if hasattr(archivo, 'seek'):
                        archivo.seek(0)
                    df = pd.read_csv(archivo, sep=sep_final, encoding='latin-1', skipinitialspace=True)
                except Exception:
                    if hasattr(archivo, 'seek'):
                        archivo.seek(0)
                    df = pd.read_csv(archivo, sep=sep_final, engine='python', on_bad_lines='skip')

            # Normalizar nombres de columnas eliminando espacios y retornos
            df.columns = [str(col).strip() for col in df.columns]
            df = df.reset_index(drop=True)

            # Acumular progresivamente el origen y diferenciar duplicados
            nuevas_columnas = []
            for col in df.columns:
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
                self.origen_por_columna[col_final] = nombre_archivo

            df.columns = nuevas_columnas
            lista_dfs.append(df)

        # Concatenación horizontal global
        if not lista_dfs:
            return pd.DataFrame()

        df_consolidado = pd.concat(lista_dfs, axis=1)
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
        self.origen_por_columna = {}

    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        archivos = list(origen) if isinstance(origen, (list, tuple)) else [origen]
        lista_dfs = []
        self.origen_por_columna = {}
        columnas_existentes = set()
        for archivo in archivos:
            nombre_archivo = getattr(archivo, 'name', str(archivo))
            if hasattr(archivo, 'seek'):
                archivo.seek(0)
            df = pd.read_excel(archivo)
            df.columns = [str(col).strip() for col in df.columns]
            df = df.reset_index(drop=True)
            nuevas_columnas = []
            for col in df.columns:
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
                self.origen_por_columna[col_final] = nombre_archivo
            df.columns = nuevas_columnas
            lista_dfs.append(df)

        if not lista_dfs:
            return pd.DataFrame()

        df_consolidado = pd.concat(lista_dfs, axis=1)
        df_consolidado.attrs['origen_por_columna'] = self.origen_por_columna
        return df_consolidado


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
    def obtener_lector_por_archivo(nombre_archivo) -> LectorDatos:
        """Determina y retorna la instancia de LectorDatos adecuada según la extensión del archivo."""
        if isinstance(nombre_archivo, (list, tuple)):
            if not nombre_archivo:
                return LectorCSV()
            primer = getattr(nombre_archivo[0], 'name', str(nombre_archivo[0]))
            return FactoryLectorDatos.obtener_lector_por_archivo(primer)

        nombre = getattr(nombre_archivo, 'name', str(nombre_archivo)).lower()
        if nombre.endswith('.csv'):
            return LectorCSV()
        elif nombre.endswith('.txt'):
            return LectorTXT()
        elif nombre.endswith(('.xlsx', '.xltx', '.xltm')):
            return LectorExcel()
        else:
            raise ValueError(f"Extensión de archivo no soportada: {nombre_archivo}")