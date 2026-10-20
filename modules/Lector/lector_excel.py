"""
Módulo para la lectura de archivos Excel (.xlsx, .xls, etc.).
Implementa la clase concreta LectorExcel heredando directamente de LectorDatos.
"""

from typing import Dict, List, Tuple
import pandas as pd
from modules.Lector.lector_base import LectorDatos


class LectorExcel(LectorDatos):
    """
    Lector de datos para hojas de cálculo Excel.
    Hereda directamente de LectorDatos y utiliza openpyxl como motor de lectura.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = ('.xlsx', '.xls', '.xltx', '.xltm', '.xlsm')

    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def _leer(self, archivo, **kwargs) -> pd.DataFrame:
        if hasattr(archivo, 'seek'):
            try:
                archivo.seek(0)
            except Exception:
                pass
        sheet_name = kwargs.get('sheet_name', 0)
        return pd.read_excel(archivo, sheet_name=sheet_name, engine='openpyxl')

    def leer_archivos(self, origen, nombre_tabla: str = None, modo_unificacion: str = "horizontal", **kwargs) -> pd.DataFrame:
        """
        Lee uno o varios archivos Excel usando pd.read_excel(..., engine='openpyxl').
        Devuelve el DataFrame crudo sin saneamiento ni validación.
        """
        archivos = list(origen) if isinstance(origen, (list, tuple)) else [origen]
        lista_dfs: List[Tuple[pd.DataFrame, str]] = []
        self.origen_por_columna = {}

        modo = kwargs.get('modo_unificacion', modo_unificacion)
        if kwargs.get('axis') in (0, '0', 'vertical', 'filas'):
            modo = 'vertical'
        elif kwargs.get('axis') in (1, '1', 'horizontal', 'columnas'):
            modo = 'horizontal'

        es_horizontal = modo not in (0, '0', 'vertical', 'filas')

        for archivo in archivos:
            nombre_archivo = getattr(archivo, 'name', str(archivo))
            df = self._leer(archivo, **kwargs)
            lista_dfs.append((df, nombre_archivo))

        if not lista_dfs:
            return pd.DataFrame()

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

        df_consolidado.attrs['origen_por_columna'] = self.origen_por_columna
        return df_consolidado