import numpy as np
import pandas as pd

VALORES_VACIOS = ["", " ", "   ", "nan", "NaN", "null", "NULL", "None", "none", "N/A", "n/a", "-", "."]

class EstandarizadorDatos:
    """Se encarga exclusivamente de limpiar y unificar representaciones de valores nulos."""
    
    @staticmethod
    def normalizar(df: pd.DataFrame) -> pd.DataFrame:
        """Convierte cadenas vacías y representaciones de error en pd.NA / np.nan."""
        df_normalizado = df.copy()
        for col in df_normalizado.columns:
            if df_normalizado[col].dtype == object or pd.api.types.is_string_dtype(df_normalizado[col]):
                # Se eliminan los espacios en blanco a los extremos
                df_normalizado[col] = df_normalizado[col].astype(str).str.strip()
                # Se reemplazan los valores identificados como vacíos por np.nan
                df_normalizado[col] = df_normalizado[col].replace(VALORES_VACIOS, np.nan)
        return df_normalizado


class ReporteCalidad:
    """Se encarga exclusivamente de generar estadísticas tabulares sobre los valores faltantes."""
    
    def __init__(self, df_normalizado: pd.DataFrame, mapeo: dict):
        self.df = df_normalizado
        self.mapeo = mapeo

    def generar(self) -> pd.DataFrame:
        """Calcula el conteo y porcentaje de nulos únicamente para las variables mapeadas."""
        registros = []
        total_filas = len(self.df)

        for atributo_sistema, col_real in self.mapeo.items():
            if col_real == "(No asignar)" or col_real not in self.df.columns:
                continue

            conteo_nulos = int(self.df[col_real].isna().sum())
            porcentaje = (conteo_nulos / total_filas * 100) if total_filas > 0 else 0.0

            registros.append({
                "Atributo del Sistema": atributo_sistema,
                "Columna Real": col_real,
                "Tipo de Dato": str(self.df[col_real].dtype),
                "Cantidad Nulls": conteo_nulos,
                "Porcentaje (%)": round(porcentaje, 2)
            })

        return pd.DataFrame(registros)


class AnalizadorDuplicados:
    """Se encarga exclusivamente de identificar y contabilizar redundancias en los datos."""
    
    @staticmethod
    def contar(df_normalizado: pd.DataFrame) -> int:
        """Devuelve el total de filas idénticas duplicadas en el DataFrame."""
        return int(df_normalizado.duplicated().sum())