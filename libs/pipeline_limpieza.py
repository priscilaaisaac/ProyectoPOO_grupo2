from abc import ABC, abstractmethod
import pandas as pd


class OperacionLimpieza(ABC):
    """Interfaz abstracta (Estrategia) para cualquier transformación de limpieza."""

    @abstractmethod
    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        pass


class SaneadorCategoricos(OperacionLimpieza):
    """Asigna 'Desconocido' a columnas de texto con valores nulos."""

    def __init__(self, columnas_categoricas: list[str]):
        self.columnas = columnas_categoricas

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        for col in self.columnas:
            if col in df_resultado.columns:
                df_resultado[col] = df_resultado[col].fillna("Desconocido")
        return df_resultado


class ImputadorMedianaGlobal(OperacionLimpieza):
    """Imputa nulos de una columna numérica con la mediana de toda la columna."""

    def __init__(self, columna: str):
        self.columna = columna

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        if self.columna in df_resultado.columns:
            valores_num = pd.to_numeric(df_resultado[self.columna], errors="coerce")
            mediana = valores_num.median()
            df_resultado[self.columna] = valores_num.fillna(mediana)
        return df_resultado


class ImputadorMedianaPorGrupo(OperacionLimpieza):
    """Imputa nulos usando la mediana agrupada por país de origen y país de destino."""

    def __init__(self, columna: str, col_origen: str, col_destino: str):
        self.columna = columna
        self.col_origen = col_origen
        self.col_destino = col_destino

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        if self.columna not in df_resultado.columns:
            return df_resultado

        df_resultado[self.columna] = pd.to_numeric(df_resultado[self.columna], errors="coerce")

        if (self.col_origen and self.col_destino and 
                self.col_origen in df_resultado.columns and 
                self.col_destino in df_resultado.columns):
            mediana_grupo = df_resultado.groupby([self.col_origen, self.col_destino])[self.columna].transform("median")
            df_resultado[self.columna] = df_resultado[self.columna].fillna(mediana_grupo)

        # Resguardo si algún grupo carecía de valores numéricos
        mediana_global = df_resultado[self.columna].median()
        df_resultado[self.columna] = df_resultado[self.columna].fillna(mediana_global)
        return df_resultado


class PipelineLimpieza:
    """Orquestador que apila operaciones secuencialmente y las ejecuta."""

    def __init__(self):
        self.pasos: list[OperacionLimpieza] = []

    def agregar_paso(self, operacion: OperacionLimpieza) -> "PipelineLimpieza":
        self.pasos.append(operacion)
        return self

    def ejecutar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_transformado = df.copy()
        for paso in self.pasos:
            df_transformado = paso.aplicar(df_transformado)
        return df_transformado