import re
from abc import ABC, abstractmethod
import pandas as pd


class InspectorTipos:
    """Provee métodos estáticos de inspección y tolerancia sobre datos de pandas."""

    @staticmethod
    def es_patron_error_o_vacio(valor) -> bool:
        """Determina si un valor es nulo, vacío o representa un código de error admitido."""
        if pd.isna(valor):
            return True

        texto = str(valor).strip().lower()
        if texto in {"", "none", "null", "nan", "n/a", "na", "error"}:
            return True

        # Reconoce patrones como 'error_498', 'error123', 'err_01', etc.
        if re.match(r"^err(or)?([_\-\s]?\d+)?$", texto):
            return True

        return False

    @staticmethod
    def obtener_tipo_general(serie: pd.Series) -> str:
        """
        Clasifica una serie en su categoría semántica general:
        'texto', 'numerico', 'fecha' u 'otro'.
        """
        if pd.api.types.is_string_dtype(serie) or serie.dtype == object:
            return "texto"
        if pd.api.types.is_numeric_dtype(serie):
            return "numerico"
        if pd.api.types.is_datetime64_any_dtype(serie):
            return "fecha"
        return "otro"


class ReglaValidacion(ABC):
    """Interfaz abstracta para cualquier regla de contrato de esquema."""

    @abstractmethod
    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        pass


class ReglaCamposRequeridos(ReglaValidacion):
    """Comprueba asignaciones obligatorias y que no existan columnas completamente vacías."""

    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        # 1. Variables requeridas no asignadas
        faltantes = [attr for attr in requeridos if mapeo.get(attr) == "(No asignar)"]
        if faltantes:
            raise ValueError(f"Faltan asignar variables críticas: {', '.join(faltantes)}")

        # 2. Columnas obligatorias 100% vacías
        vacias = []
        for atributo in requeridos:
            col = mapeo[atributo]
            if col in df.columns:
                serie_limpia = df[col].dropna().astype(str).str.strip()
                if serie_limpia.empty or (serie_limpia == "").all():
                    vacias.append(atributo)
        if vacias:
            raise ValueError(f"Las siguientes columnas obligatorias están completamente vacías: {', '.join(vacias)}")


class ReglaCapacidadesYPrecio(ReglaValidacion):
    """Verifica integridad de capacidades de aeronave y consistencia de precios."""

    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        c_max = mapeo.get("capacidad_maxima_avion")
        c_usada = mapeo.get("capacidad_usada_avion")

        if c_max and c_max in df.columns:
            self._validar_enteros_tolerante(df[c_max], "capacidad_maxima_avion")
        if c_usada and c_usada in df.columns:
            self._validar_enteros_tolerante(df[c_usada], "capacidad_usada_avion")

        # Comparación fila por fila ignorando errores admitidos
        if c_max and c_usada and c_max in df.columns and c_usada in df.columns:
            s_max = pd.to_numeric(df[c_max], errors="coerce")
            s_usada = pd.to_numeric(df[c_usada], errors="coerce")
            if (s_usada > s_max).any():
                raise ValueError("Inconsistencia detectada: Hay registros donde la 'capacidad usada' es mayor a la 'capacidad máxima'.")

        c_precio = mapeo.get("precio")
        if not c_precio or c_precio == "(No asignar)":
            raise ValueError("El atributo 'precio' es obligatorio.")
        if c_precio in df.columns:
            self._validar_numerica_tolerante(df[c_precio], "precio")

    @staticmethod
    def _validar_enteros_tolerante(serie: pd.Series, nombre_campo: str):
        for valor in serie:
            if InspectorTipos.es_patron_error_o_vacio(valor):
                continue
            try:
                val_num = float(valor)
                if not val_num.is_integer():
                    raise ValueError
            except (ValueError, TypeError):
                raise ValueError(
                    f"El atributo '{nombre_campo}' contiene el valor inválido '{valor}'. "
                    f"Solo se admiten números enteros, valores vacíos o etiquetas de error (ej. 'error_498', 'ERROR')."
                )

    @staticmethod
    def _validar_numerica_tolerante(serie: pd.Series, nombre_campo: str):
        for valor in serie:
            if InspectorTipos.es_patron_error_o_vacio(valor):
                continue
            try:
                float(valor)
            except (ValueError, TypeError):
                raise ValueError(
                    f"El atributo '{nombre_campo}' contiene el valor inválido '{valor}'. "
                    f"Solo se admiten números, valores vacíos o etiquetas de error (ej. 'error_498', 'ERROR')."
                )
class ReglaParidadFormatos(ReglaValidacion):
    """Garantiza compatibilidad semántica entre campos pareados (origen / destino)."""

    def ejecutar(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        self._comparar_par(df, mapeo, "origen", "destino")
        self._comparar_par(df, mapeo, "aeropuerto_origen", "aeropuerto_destino")

    @staticmethod
    def _comparar_par(df: pd.DataFrame, mapeo: dict, campo_a: str, campo_b: str):
        col_a = mapeo.get(campo_a)
        col_b = mapeo.get(campo_b)
        if col_a and col_a != "(No asignar)" and col_b and col_b != "(No asignar)":
            if col_a in df.columns and col_b in df.columns:
                tipo_a = InspectorTipos.obtener_tipo_general(df[col_a])
                tipo_b = InspectorTipos.obtener_tipo_general(df[col_b])
                if tipo_a != tipo_b:
                    raise ValueError(
                        f"Los atributos '{campo_a}' ({tipo_a}) y '{campo_b}' ({tipo_b}) "
                        f"deben compartir el mismo tipo de dato general."
                    )
                
class ValidadorEsquema:
    """Orquestador que agrupa y ejecuta el conjunto de reglas de validación."""

    def __init__(self, df: pd.DataFrame, mapeo: dict, requeridos: list):
        self.df = df
        self.mapeo = mapeo
        self.requeridos = requeridos
        self.reglas: list[ReglaValidacion] = [
            ReglaCamposRequeridos(),
            ReglaCapacidadesYPrecio(),
            ReglaParidadFormatos(),
        ]

    def validar(self) -> str:
        """Ejecuta secuencialmente todas las reglas de contrato."""
        for regla in self.reglas:
            regla.ejecutar(self.df, self.mapeo, self.requeridos)

        return "Contrato validado exitosamente."