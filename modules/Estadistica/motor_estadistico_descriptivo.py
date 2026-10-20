"""
Módulo para el Motor Estadístico Descriptivo de Vuelos.
Implementa MotorEstadisticoDescriptivo heredando de MotorAnalisisBase.
"""

from typing import Dict, Any, Optional
import pandas as pd
from modules.Vuelos import Vuelo
from modules.Estadistica.motor_analisis_base import MotorAnalisisBase


class MotorEstadisticoDescriptivo(MotorAnalisisBase):
    """
    Motor estadístico descriptivo orientado a objetos.
    Calcula probabilidades marginales, condicionales y tablas de contingencia
    a partir del histórico de datos observados.
    """

    # ----------------------------------------------------------------------
    # Probabilidades Marginales Globales
    # ----------------------------------------------------------------------

    def calcular_conteos_marginales(self) -> Dict[str, int]:
        """Calcula el número absoluto de vuelos por cada estado canónico (excluyendo Desconocido)."""
        conteos = {"Atrasado": 0, "A tiempo": 0, "Exitoso": 0, "Cancelado": 0}
        for v in self.vuelos:
            est = v.normalizar_estado()
            if est in conteos:
                conteos[est] += 1
        return conteos

    def calcular_probabilidades_marginales(self) -> Dict[str, float]:
        """
        Retorna la probabilidad marginal global P(Estado = e) para cada estado canónico válido,
        con valores entre 0.0 y 1.0 sumando 1.0.
        """
        conteos = self.calcular_conteos_marginales()
        total_validos = sum(conteos.values())
        if total_validos == 0:
            return {k: 0.0 for k in conteos}
        return {k: v / total_validos for k, v in conteos.items()}

    # ----------------------------------------------------------------------
    # Probabilidades Condicionales Cruzadas (DataFrames para reportes y UI)
    # ----------------------------------------------------------------------

    def _generar_tabla_condicional(self, dimension_func, nombre_columna: str) -> pd.DataFrame:
        registros = []
        for v in self.vuelos:
            dim_val = dimension_func(v)
            if "desconocido" in str(dim_val).lower():
                continue
            registros.append({
                nombre_columna: dim_val,
                "estado": v.normalizar_estado(),
                "precio": v.precio,
                "factor_ocupacion": v.calcular_factor_ocupacion()
            })
        if not registros:
            return pd.DataFrame()
        df_temp = pd.DataFrame(registros)

        grupos = df_temp.groupby(nombre_columna)
        filas = []

        for dim_val, subdf in grupos:
            tot = len(subdf)
            conteos = subdf["estado"].value_counts().to_dict()
            p_atrasado = (conteos.get("Atrasado", 0) / tot) * 100.0
            p_atiempo = (conteos.get("A tiempo", 0) / tot) * 100.0
            p_exitoso = (conteos.get("Exitoso", 0) / tot) * 100.0
            p_cancelado = (conteos.get("Cancelado", 0) / tot) * 100.0
            precio_prom = subdf["precio"].mean()
            ocup_prom = subdf["factor_ocupacion"].mean()

            filas.append({
                nombre_columna: dim_val,
                "Total Vuelos": tot,
                "% Atrasado": round(p_atrasado, 2),
                "% A tiempo": round(p_atiempo, 2),
                "% Exitoso": round(p_exitoso, 2),
                "% Cancelado": round(p_cancelado, 2),
                "Precio Promedio ($)": round(precio_prom, 2),
                "Ocupación Media (%)": round(ocup_prom, 2)
            })

        df_res = pd.DataFrame(filas)
        if not df_res.empty:
            df_res = df_res.sort_values(by="Total Vuelos", ascending=False).reset_index(drop=True)
        return df_res

    def calcular_probabilidades_condicionales_franja(self) -> pd.DataFrame:
        """P(Estado | Franja Horaria de Salida)"""
        return self._generar_tabla_condicional(lambda v: v.obtener_franja_horaria(), "Franja Horaria")

    def calcular_probabilidades_condicionales_ruta(self) -> pd.DataFrame:
        """P(Estado | Ruta Origen -> Destino)"""
        return self._generar_tabla_condicional(lambda v: v.obtener_ruta(), "Ruta")

    def calcular_probabilidades_condicionales_ocupacion(self) -> pd.DataFrame:
        """P(Estado | Nivel de Ocupación)"""
        return self._generar_tabla_condicional(lambda v: v.obtener_categoria_ocupacion(), "Nivel de Ocupación")

    # ----------------------------------------------------------------------
    # Métricas de Segmento Concretas
    # ----------------------------------------------------------------------

    def calcular_metricas_segmento(
        self,
        ruta: Optional[str] = None,
        franja: Optional[str] = None,
        ocupacion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula probabilidades condicionales específicas y métricas comerciales
        para un segmento exacto definido por el usuario.
        """
        muestra = self.filtrar_vuelos(ruta, franja, ocupacion)
        n = len(muestra)
        if n == 0:
            return {
                "muestra_tamano": 0,
                "es_estimacion_global": True,
                "p_atrasado": 0.0,
                "p_cancelado": 0.0,
                "p_atiempo": 0.0,
                "p_exitoso": 0.0,
                "precio_promedio": 0.0,
                "ocupacion_promedio": 0.0,
                "capacidad_maxima_media": 0,
                "capacidad_usada_media": 0
            }

        conteos = {}
        suma_precio = 0.0
        suma_ocup = 0.0
        suma_cap_max = 0
        suma_cap_usada = 0

        for v in muestra:
            est = v.normalizar_estado()
            conteos[est] = conteos.get(est, 0) + 1
            suma_precio += v.precio
            suma_ocup += v.calcular_factor_ocupacion()
            suma_cap_max += v.capacidad_maxima_avion
            suma_cap_usada += v.capacidad_usada_avion

        return {
            "muestra_tamano": n,
            "es_estimacion_global": False,
            "p_atrasado": conteos.get("Atrasado", 0) / n,
            "p_cancelado": conteos.get("Cancelado", 0) / n,
            "p_atiempo": conteos.get("A tiempo", 0) / n,
            "p_exitoso": conteos.get("Exitoso", 0) / n,
            "precio_promedio": suma_precio / n,
            "ocupacion_promedio": suma_ocup / n,
            "capacidad_maxima_media": int(suma_cap_max / n),
            "capacidad_usada_media": int(suma_cap_usada / n)
        }


# Alias de retrocompatibilidad
MotorEstadisticoVuelos = MotorEstadisticoDescriptivo

__all__ = [
    "MotorEstadisticoDescriptivo",
    "MotorEstadisticoVuelos",
]
