"""
Módulo para la lectura de archivos TXT.
Implementa la clase concreta LectorTXT delegando en LectorCSV.
"""

from typing import Dict
import pandas as pd
from modules.lector_base import LectorDatos
from modules.lector_csv import LectorCSV


class LectorTXT(LectorDatos):
    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def leer(self, origen, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        lector_csv = LectorCSV()
        df = lector_csv.leer(origen, nombre_tabla=nombre_tabla, **kwargs)
        self.origen_por_columna = lector_csv.origen_por_columna
        return df
