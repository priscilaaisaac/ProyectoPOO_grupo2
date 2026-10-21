"""
Módulo para la lectura de archivos de texto delimitado (.csv, .txt).
Implementa la clase concreta LectorTextoDelimitado unificando la lectura
de formatos basados en delimitadores.
"""

import csv
from typing import Dict, List, Tuple, Optional
import pandas as pd
from modules.Lector.lector_base import LectorDatos, consolidar_dataframes_multiples

DELIMITADORES_VALIDOS = (',', ';', '\t', '|', ' ')


class LectorTextoDelimitado(LectorDatos):
    """
    Lector de datos para archivos de texto plano estructurado mediante delimitadores
    (valores separados por comas, puntos y comas, tabulaciones, barras o espacios).
    Soporta extensiones .csv y .txt mediante pd.read_csv y retorna DataFrames crudos.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = ('.csv', '.txt')
    DELIMITADORES_PERMITIDOS: Tuple[str, ...] = DELIMITADORES_VALIDOS

    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def detectar_separador(self, origen, default: str = ',') -> str:
        """
        Detecta el delimitador usando csv.Sniffer().sniff() de la librería estándar,
        leyendo los primeros 1024 bytes del archivo (.read(1024)).
        Restringe estrictamente los delimitadores válidos para evitar que símbolos
        internos (ej. guion) rompan columnas.
        Aplica .seek(0) inmediatamente después del sniff.
        """
        delimitadores = self.DELIMITADORES_PERMITIDOS
        delimiters_str = ''.join(delimitadores)
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
            if dialect.delimiter in delimitadores:
                return dialect.delimiter
        except Exception:
            pass

        # Respaldo si csv.Sniffer falla:
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if lines:
            for d in (',', ';', '\t', '|'):
                if d in delimitadores:
                    conteo_primera = lines[0].count(d)
                    if conteo_primera > 0 and all(l.count(d) == conteo_primera for l in lines[:5]):
                        return d

            if ' ' in delimitadores:
                num_tokens = [len(l.split()) for l in lines[:5]]
                if len(num_tokens) > 0 and num_tokens[0] >= 2 and len(set(num_tokens)) == 1:
                    return ' '

        return default

    def _leer(self, archivo, **kwargs) -> pd.DataFrame:
        sep_detectado = self.detectar_separador(archivo)
        sep_final = kwargs.get('sep', sep_detectado)
        nrows = kwargs.get('nrows', None)

        if sep_final in (' ', r'\s+'):
            sep_a_usar = r'\s+'
        else:
            sep_a_usar = sep_final

        if hasattr(archivo, 'seek'):
            try:
                archivo.seek(0)
            except Exception:
                pass

        try:
            df = pd.read_csv(archivo, sep=sep_a_usar, nrows=nrows, skipinitialspace=True)
        except UnicodeDecodeError:
            if hasattr(archivo, 'seek'):
                try:
                    archivo.seek(0)
                except Exception:
                    pass
            df = pd.read_csv(archivo, sep=sep_a_usar, nrows=nrows, encoding='latin-1', skipinitialspace=True)
        except Exception:
            if hasattr(archivo, 'seek'):
                try:
                    archivo.seek(0)
                except Exception:
                    pass
            df = pd.read_csv(archivo, sep=sep_a_usar, nrows=nrows, engine='python', on_bad_lines='skip', skipinitialspace=True)

        if hasattr(archivo, 'seek'):
            try:
                archivo.seek(0)
            except Exception:
                pass

        return df

    def obtener_cabeceras(self, archivo) -> List[str]:
        """Lee temporalmente los nombres de las columnas sin mover el puntero del archivo."""
        df_cab = self._leer(archivo, nrows=0)
        return [str(col).strip() for col in df_cab.columns]

    def leer_archivos(
        self,
        origen,
        nombre_tabla: str = None,
        modo_unificacion: str = "horizontal",
        columnas_id: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Lee uno o varios archivos delimitados (.csv, .txt) exclusivamente usando pd.read_csv.
        Si se provee `columnas_id`, alinea y une los registros mediante las claves ID seleccionadas.
        Devuelve el DataFrame crudo sin saneamiento ni validación interna.
        """
        archivos = list(origen) if isinstance(origen, (list, tuple)) else [origen]
        lista_dfs: List[Tuple[pd.DataFrame, str]] = []

        for archivo in archivos:
            nombre_archivo = getattr(archivo, 'name', str(archivo))
            df = self._leer(archivo, **kwargs)
            lista_dfs.append((df, nombre_archivo))

        df_consolidado, self.origen_por_columna = consolidar_dataframes_multiples(
            lista_dfs,
            modo_unificacion=modo_unificacion,
            columnas_id=columnas_id,
            **kwargs
        )
        return df_consolidado


def detectar_separador(origen, default: str = ',') -> str:
    """Función de conveniencia para detectar separador usando LectorTextoDelimitado."""
    return LectorTextoDelimitado().detectar_separador(origen, default=default)
