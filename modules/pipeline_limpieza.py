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

class ImputadorFactorOcupacion(OperacionLimpieza):
    """Imputa capacidades faltantes basándose en el factor de ocupación promedio."""

    def __init__(self, col_maxima: str, col_usada: str):
        self.col_maxima = col_maxima
        self.col_usada = col_usada

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_res = df.copy()
        if self.col_maxima not in df_res.columns or self.col_usada not in df_res.columns:
            return df_res

        s_max = pd.to_numeric(df_res[self.col_maxima], errors="coerce")
        s_usada = pd.to_numeric(df_res[self.col_usada], errors="coerce")

        # Calcular factor de ocupación promedio válido (usada / máxima)
        mask_validos = (s_max > 0) & s_max.notna() & s_usada.notna()
        if mask_validos.any():
            factores = s_usada[mask_validos] / s_max[mask_validos]
            factor_promedio = factores.mean()
        else:
            factor_promedio = 0.75  # Fallback por defecto si no hay datos de referencia

        # Si falta capacidad usada pero hay máxima: Máxima * Factor Promedio
        mask_falta_usada = s_usada.isna() & s_max.notna() & (s_max > 0)
        df_res.loc[mask_falta_usada, self.col_usada] = (s_max[mask_falta_usada] * factor_promedio).round()

        # Si falta capacidad máxima pero hay usada: Usada / Factor Promedio
        mask_falta_max = s_max.isna() & s_usada.notna() & (factor_promedio > 0)
        df_res.loc[mask_falta_max, self.col_maxima] = (s_usada[mask_falta_max] / factor_promedio).round()

        return df_res


class AutogeneradorIds(OperacionLimpieza):
    """Asigna un ID secuencial (ej. GEN-001) a los registros que tengan id_vuelo nulo."""

    def __init__(self, col_id: str, prefijo: str = "GEN"):
        self.col_id = col_id
        self.prefijo = prefijo

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_res = df.copy()
        if self.col_id not in df_res.columns:
            return df_res

        contador = 1
        for idx, val in df_res[self.col_id].items():
            if pd.isna(val) or str(val).strip() == "" or str(val).lower() in ["nan", "none", "null"]:
                df_res.at[idx, self.col_id] = f"{self.prefijo}-{contador:03d}"
                contador += 1
        return df_res


class EliminadorFilasNulas(OperacionLimpieza):
    """Elimina filas donde una columna crítica tenga valores nulos."""

    def __init__(self, columna: str):
        self.columna = columna

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_res = df.copy()
        if self.columna in df_res.columns:
            df_res = df_res.dropna(subset=[self.columna])
        return df_res

