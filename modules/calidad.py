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

    @staticmethod
    def sanear_dataframe_individual(df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica limpieza estricta de espacios en blanco sobre cabeceras y contenido:
        1. df.columns = df.columns.str.strip() para eliminar espacios invisibles en nombres.
        2. .apply(strip) a todas las columnas de texto (object/string) preservando valores nulos.
        """
        if df is None or df.empty:
            return df

        df = df.copy()
        # Limpieza absoluta de cabeceras
        df.columns = [str(col).strip() for col in df.columns]
        if hasattr(df.columns, 'str'):
            df.columns = df.columns.str.strip()

        # Limpieza de valores en columnas de tipo texto
        for col in df.columns:
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

        return df.reset_index(drop=True)

    sanear_espacios = sanear_dataframe_individual


def sanear_dataframe_individual(df: pd.DataFrame) -> pd.DataFrame:
    """Función de compatibilidad a nivel de módulo para saneamiento de espacios."""
    return EstandarizadorDatos.sanear_dataframe_individual(df)


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
                "Porcentaje (%)": round(porcentaje, 2),
                "Pérdida si se descarta": f"{round(porcentaje, 2)}% ({conteo_nulos} filas)"
            })

        return pd.DataFrame(registros)

    def calcular_impacto_descarte(self, col_real: str) -> tuple[int, float]:
        """Calcula la cantidad de filas nulas y el porcentaje exacto de pérdida si se descarta."""
        total = len(self.df)
        if total == 0 or col_real not in self.df.columns:
            return 0, 0.0
        nulos = int(self.df[col_real].isna().sum())
        porcentaje = (nulos / total) * 100.0
        return nulos, round(porcentaje, 2)

    def calcular_impacto_ambas_nulas(self, col1: str, col2: str) -> tuple[int, float]:
        """Calcula la cantidad y porcentaje de filas donde ambas columnas son simultáneamente nulas."""
        total = len(self.df)
        if total == 0 or col1 not in self.df.columns or col2 not in self.df.columns:
            return 0, 0.0
        nulos = int((self.df[col1].isna() & self.df[col2].isna()).sum())
        porcentaje = (nulos / total) * 100.0
        return nulos, round(porcentaje, 2)


class AnalizadorDuplicados:
    """Se encarga exclusivamente de identificar y contabilizar redundancias en los datos."""
    
    @staticmethod
    def contar(df_normalizado: pd.DataFrame) -> int:
        """Devuelve el total de filas idénticas duplicadas en el DataFrame."""
        return int(df_normalizado.duplicated().sum())