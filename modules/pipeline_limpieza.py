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


class SaneadorUbicaciones(OperacionLimpieza):
    """
    Imputa automáticamente valores nulos o faltantes como 'Desconocido'
    en los atributos de ubicación: 'origen', 'destino', 'aeropuerto_origen' y 'aeropuerto_destino'.
    """

    def __init__(self, columnas_ubicaciones: list[str]):
        self.columnas = [c for c in columnas_ubicaciones if c]

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        for col in self.columnas:
            if col in df_resultado.columns:
                serie_str = df_resultado[col].astype(str).str.strip().str.lower()
                es_vacio = df_resultado[col].isna() | serie_str.isin(["", "nan", "none", "null", "n/a", "nat", "desconocido"])
                df_resultado.loc[es_vacio, col] = "Desconocido"
        return df_resultado


class ImputadorCapacidadesPorFactorOcupacion(OperacionLimpieza):
    """
    Tratamiento para 'capacidad_maxima_avion' y 'capacidad_usada_avion':
    - 'No modificar': Mantiene los nulos sin cambios.
    - 'Imputar por Factor de Ocupación': Imputa de forma acoplada basada en el factor medio del dataset.
    - 'Eliminar filas': Descarta cualquier fila que tenga al menos una capacidad faltante.
    """

    def __init__(
        self,
        col_maxima: str = "capacidad_maxima_avion",
        col_usada: str = "capacidad_usada_avion",
        metodo: str = "imputar",
        accion_ambas_nulas: str = "mantener",
        factor_default: float = 0.75
    ):
        self.col_maxima = col_maxima
        self.col_usada = col_usada
        self.metodo = metodo.lower()
        self.accion_ambas_nulas = accion_ambas_nulas.lower()
        self.factor_default = factor_default

    def calcular_factor_promedio(self, df: pd.DataFrame) -> float:
        """Calcula el factor medio de ocupación entre registros válidos (usada <= maxima y ambas > 0)."""
        if self.col_maxima not in df.columns or self.col_usada not in df.columns:
            return self.factor_default

        s_max = pd.to_numeric(df[self.col_maxima], errors="coerce")
        s_usada = pd.to_numeric(df[self.col_usada], errors="coerce")

        validos = (s_max > 0) & (s_usada >= 0) & (s_usada <= s_max)
        if validos.sum() > 0:
            factores = s_usada[validos] / s_max[validos]
            factor_promedio = float(factores.mean())
            if 0.0 < factor_promedio <= 1.0:
                return factor_promedio

        return self.factor_default

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        if self.col_maxima not in df_resultado.columns or self.col_usada not in df_resultado.columns:
            return df_resultado

        s_max = pd.to_numeric(df_resultado[self.col_maxima], errors="coerce")
        s_usada = pd.to_numeric(df_resultado[self.col_usada], errors="coerce")

        # Opción A: No modificar
        if "no modificar" in self.metodo:
            return df_resultado

        # Opción B: Eliminar filas si falta al menos una capacidad
        if "eliminar" in self.metodo:
            filas_validas = s_max.notna() & s_usada.notna()
            return df_resultado[filas_validas].reset_index(drop=True)

        # Opción C: Imputar por Factor de Ocupación
        if "descartar" in self.accion_ambas_nulas:
            ambas_nulas = s_max.isna() & s_usada.isna()
            df_resultado = df_resultado[~ambas_nulas].copy()
            s_max = pd.to_numeric(df_resultado[self.col_maxima], errors="coerce")
            s_usada = pd.to_numeric(df_resultado[self.col_usada], errors="coerce")

        factor = self.calcular_factor_promedio(df_resultado)

        # 1. Si falta la usada pero se tiene la máxima
        falta_usada = s_usada.isna() & s_max.notna() & (s_max > 0)
        s_usada.loc[falta_usada] = (s_max.loc[falta_usada] * factor).round()

        # 2. Si falta la máxima pero se tiene la usada
        falta_max = s_max.isna() & s_usada.notna() & (s_usada >= 0)
        imputadas_max = (s_usada.loc[falta_max] / factor).round()
        s_max.loc[falta_max] = imputadas_max.clip(lower=s_usada.loc[falta_max])

        # Asegurar coherencia: si alguna usada superara la maxima por redondeo, se ajusta
        inconsistentes = (s_usada > s_max) & s_max.notna() & s_usada.notna()
        s_usada.loc[inconsistentes] = s_max.loc[inconsistentes]

        # Convertir a entero si no quedan nulos
        if s_max.notna().all():
            s_max = s_max.astype(int)
        if s_usada.notna().all():
            s_usada = s_usada.astype(int)

        df_resultado[self.col_maxima] = s_max
        df_resultado[self.col_usada] = s_usada

        return df_resultado.reset_index(drop=True)


class ImputadorEstadoInteligente(OperacionLimpieza):
    """
    Imputa de forma inteligente y algorítmica el atributo 'estado' evaluando
    las fechas y horas reales vs estipuladas según las reglas de negocio del sistema:
    1. Si no se posee ninguna fecha de ningún tipo -> 'Desconocido'.
    2. Si se tiene salida estipulada pero la real es nula -> 'Cancelado'.
    3. Si la salida estipulada es anterior a la real (> 10 min) -> 'Atrasado'.
    4. Si la llegada estipulada es anterior a la real (> 10 min) -> 'Atrasado'.
    5. Si las fechas estipuladas coinciden con las reales (margen <= 10 min) -> 'A tiempo'.
    6. Si no se tiene salida estipulada ni real, pero sí de llegada -> 'Exitoso'.
    7. Si se tienen únicamente fechas reales y ninguna estipulada -> 'Exitoso'.
    8. Si no se cuenta con ninguna fecha estipulada pero hay datos de operación -> 'Exitoso'.
    """

    def __init__(
        self,
        col_estado: str = "estado",
        col_s_est: str = "fechayhora_origen_estipulado",
        col_s_real: str = "fechayhora_origen",
        col_l_est: str = "fechayhora_destino_estipulado",
        col_l_real: str = "fechayhora_destino",
        forzar_recalculo: bool = False
    ):
        self.col_estado = col_estado
        self.col_s_est = col_s_est
        self.col_s_real = col_s_real
        self.col_l_est = col_l_est
        self.col_l_real = col_l_real
        self.forzar_recalculo = forzar_recalculo

    def deducir_estado_fila(self, fila: pd.Series) -> str:
        s_est = pd.to_datetime(fila.get(self.col_s_est), errors="coerce") if self.col_s_est in fila.index else pd.NaT
        s_real = pd.to_datetime(fila.get(self.col_s_real), errors="coerce") if self.col_s_real in fila.index else pd.NaT
        l_est = pd.to_datetime(fila.get(self.col_l_est), errors="coerce") if self.col_l_est in fila.index else pd.NaT
        l_real = pd.to_datetime(fila.get(self.col_l_real), errors="coerce") if self.col_l_real in fila.index else pd.NaT

        # Regla 8: Si no se posee ninguna fecha de ningún tipo
        if pd.isna(s_est) and pd.isna(s_real) and pd.isna(l_est) and pd.isna(l_real):
            return "Desconocido"

        # Regla 3: Si se tiene la salida estipulada pero la real es nula/inexistente
        if pd.notna(s_est) and pd.isna(s_real):
            return "Cancelado"

        # Reglas 1 y 2: Salida o llegada estipulada anterior a la real (> 10 min)
        if pd.notna(s_est) and pd.notna(s_real):
            diff_salida = (s_real - s_est).total_seconds() / 60.0
            if diff_salida > 10.0:
                return "Atrasado"

        if pd.notna(l_est) and pd.notna(l_real):
            diff_llegada = (l_real - l_est).total_seconds() / 60.0
            if diff_llegada > 10.0:
                return "Atrasado"

        # Regla 5: Si no se tiene la salida estipulada ni la real, pero sí se tienen las de llegada
        if pd.isna(s_est) and pd.isna(s_real) and (pd.notna(l_real) or pd.notna(l_est)):
            return "Exitoso"

        # Regla 6: Si se tienen únicamente las fechas reales y ninguna estipulada
        if pd.isna(s_est) and pd.isna(l_est) and (pd.notna(s_real) or pd.notna(l_real)):
            return "Exitoso"

        # Regla 7: Si no se cuenta con ninguna fecha estipulada pero hay datos de operación válidos
        if pd.isna(s_est) and pd.isna(l_est):
            return "Exitoso"

        # Regla 4: Fechas estipuladas coinciden con reales dentro de margen <= 10 min
        if (pd.notna(s_est) and pd.notna(s_real)) or (pd.notna(l_est) and pd.notna(l_real)):
            return "A tiempo"

        return "Exitoso"

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        if self.col_estado not in df_resultado.columns:
            df_resultado[self.col_estado] = None

        serie_estado = df_resultado[self.col_estado].astype(str).str.strip().str.lower()
        es_imputable = (
            df_resultado[self.col_estado].isna() | 
            serie_estado.isin(["", "nan", "none", "null", "n/a", "nat", "desconocido"])
        )

        for idx in df_resultado.index:
            if self.forzar_recalculo or es_imputable.loc[idx]:
                nuevo_estado = self.deducir_estado_fila(df_resultado.loc[idx])
                df_resultado.at[idx, self.col_estado] = nuevo_estado

        return df_resultado


class GeneradorIdVuelo(OperacionLimpieza):
    """
    Autogenera identificadores secuenciales únicos para registros con 'id_vuelo' nulo o vacío.
    Formato: prefijo + número secuencial con ceros a la izquierda (ej. GEN-001, GEN-002, ...).
    """

    def __init__(self, columna: str = "id_vuelo", prefijo: str = "GEN-", relleno: int = 3):
        self.columna = columna
        self.prefijo = prefijo
        self.relleno = relleno

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        if self.columna not in df_resultado.columns:
            df_resultado[self.columna] = None

        serie_str = df_resultado[self.columna].astype(str).str.strip().str.lower()
        es_nulo = df_resultado[self.columna].isna() | serie_str.isin(["", "nan", "none", "null", "n/a", "nat"])

        cant_nulos = int(es_nulo.sum())
        if cant_nulos > 0:
            contador = 1
            nuevos_ids = []
            for nulo in es_nulo:
                if nulo:
                    nuevos_ids.append(f"{self.prefijo}{str(contador).zfill(self.relleno)}")
                    contador += 1
                else:
                    nuevos_ids.append(None)

            df_resultado.loc[es_nulo, self.columna] = [nid for nid in nuevos_ids if nid is not None]

        return df_resultado


class TratamientoFechas(OperacionLimpieza):
    """
    Estrategia de limpieza para campos temporales (fechas y horas).
    - 'Eliminar fila si falta': Descarta registros donde la fecha sea nula o inválida
      (crítico para fechas estipuladas necesarias en el análisis de retrasos).
    - 'Dejar nulo': Mantiene valores nulos o normaliza valores erróneos a NaT
      (para representar vuelos sin registro efectivo o cancelados en fechas reales).
    """

    def __init__(self, columna: str, metodo: str = "Eliminar fila si falta"):
        self.columna = columna
        self.metodo = metodo

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        if self.columna not in df_resultado.columns:
            return df_resultado

        fechas_dt = pd.to_datetime(df_resultado[self.columna], errors="coerce")

        if self.metodo == "Eliminar fila si falta":
            mask_valida = df_resultado[self.columna].notna() & fechas_dt.notna()
            df_resultado = df_resultado[mask_valida].copy()
            df_resultado[self.columna] = fechas_dt[mask_valida]
            return df_resultado.reset_index(drop=True)
        elif self.metodo in ("Dejar nulo", "No modificar (mantener nulos)"):
            df_resultado[self.columna] = fechas_dt
            return df_resultado

        return df_resultado


class EliminadorFilasNulas(OperacionLimpieza):
    """Elimina filas que contengan valores nulos o inválidos en la columna especificada."""

    def __init__(self, columna: str):
        self.columna = columna

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        df_resultado = df.copy()
        if self.columna in df_resultado.columns:
            fechas_dt = pd.to_datetime(df_resultado[self.columna], errors="coerce")
            mask_valida = df_resultado[self.columna].notna() & fechas_dt.notna()
            df_resultado = df_resultado[mask_valida].reset_index(drop=True)
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