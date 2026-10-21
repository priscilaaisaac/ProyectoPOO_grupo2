"""
Módulo para la lectura de archivos Excel (.xlsx, .xls, etc.).
Implementa la clase concreta LectorExcel heredando directamente de LectorDatos.
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
from modules.Lector.lector_base import LectorDatos, consolidar_dataframes_multiples


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
        nrows = kwargs.get('nrows', None)
        df = pd.read_excel(archivo, sheet_name=sheet_name, nrows=nrows, engine='openpyxl')
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
        Lee uno o varios archivos Excel usando pd.read_excel(..., engine='openpyxl').
        Si se provee `columnas_id`, alinea y une los registros mediante las claves ID seleccionadas.
        Devuelve el DataFrame crudo sin saneamiento ni validación.
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
