"""
Módulo para la lectura de archivos CSV y delimitados.
Implementa la clase concreta LectorCSV.
"""

from typing import Dict
import pandas as pd
from modules.lector_base import (
    LectorDatos,
    detectar_separador,
    sanear_dataframe_individual,
    validar_estructura_tabular
)


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
