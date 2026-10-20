"""
Módulo Base para la Ingestión y Lectura de Datos.
Contiene la interfaz abstracta pura LectorDatos.
"""

from abc import ABC, abstractmethod
from typing import Tuple
import pandas as pd


class LectorDatos(ABC):
    """
    Clase abstracta pura para lectores de datos.
    Define el contrato base y extensiones soportadas para la lectura de cualquier formato.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = ()

    @abstractmethod
    def leer_archivos(self, origen, **kwargs) -> pd.DataFrame:
        """
        Lee datos desde un origen (ruta de archivo, buffer de memoria o lista de orígenes)
        y retorna un DataFrame con los datos crudos.
        """
        pass