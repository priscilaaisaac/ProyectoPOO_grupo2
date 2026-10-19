"""
Módulo para la lectura de datos desde bases de datos SQL.
Implementa la clase concreta LectorSQL heredando de LectorDatos.
"""

from typing import Tuple
import pandas as pd
from sqlalchemy import create_engine
from modules.lector_base import LectorDatos


class LectorSQL(LectorDatos):
    """
    Lector de datos para fuentes relacionales SQL vía SQLAlchemy.
    Devuelve los datos crudos consultados de la tabla especificada.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = ('sql',)

    def leer(self, origen: str, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        """
        Lee datos de una tabla en la base de datos SQL indicada.
        Devuelve el DataFrame crudo sin saneamiento ni validación interna.
        """
        if not nombre_tabla:
            raise ValueError("Se requiere el nombre de la tabla para bases de datos SQL.")

        engine = create_engine(origen)
        query = f"SELECT * FROM {nombre_tabla}"
        df = pd.read_sql(query, con=engine)
        return df
