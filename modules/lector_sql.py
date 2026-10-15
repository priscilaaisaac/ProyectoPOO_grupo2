"""
Módulo para la lectura de datos desde bases de datos SQL.
Implementa la clase concreta LectorSQL.
"""

import pandas as pd
from sqlalchemy import create_engine
from modules.lector_base import (
    LectorDatos,
    sanear_dataframe_individual,
    validar_estructura_tabular
)


class LectorSQL(LectorDatos):
    def leer(self, origen: str, nombre_tabla: str = None, **kwargs) -> pd.DataFrame:
        if not nombre_tabla:
            raise ValueError("Se requiere el nombre de la tabla para bases de datos SQL.")

        engine = create_engine(origen)
        query = f"SELECT * FROM {nombre_tabla}"
        df = pd.read_sql(query, con=engine)
        df = sanear_dataframe_individual(df)
        return validar_estructura_tabular(df)
