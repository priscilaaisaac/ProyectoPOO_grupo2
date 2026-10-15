"""
Módulo para la lectura de archivos Excel (.xlsx, .xls, etc.).
Implementa la clase concreta LectorExcel delegando en LectorCSV.
"""

from typing import Dict
import pandas as pd
from modules.lector_base import LectorDatos
from modules.lector_csv import LectorCSV


class LectorExcel(LectorDatos):
    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def leer(self, origen, nombre_tabla: str = None, modo_unificacion: str = "horizontal", **kwargs) -> pd.DataFrame:
        lector_csv = LectorCSV()
        df = lector_csv.leer(origen, nombre_tabla=nombre_tabla, modo_unificacion=modo_unificacion, **kwargs)
        self.origen_por_columna = lector_csv.origen_por_columna
        return df
