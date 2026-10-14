from typing import List, Dict, Any, Optional
import pandas as pd
from modules.Vuelos import Vuelo

class MotorEstadisticoVuelos:
    """
    Motor estadístico orientado a objetos que calcula probabilidades marginales,
    condicionales y métricas comerciales sobre una colección de objetos Vuelo.
    """

    def __init__(self, vuelos: List[Vuelo]):
        if not vuelos:
            raise ValueError("No se puede inicializar el motor estadístico con una colección vacía de vuelos.")
        self.vuelos = vuelos
        self.total_vuelos = len(vuelos)

    # ----------------------------------------------------------------------
    # Probabilidades Marginales Globales
    # ----------------------------------------------------------------------

    def calcular_conteos_marginales(self) -> Dict[str, int]:
        """Calcula el número absoluto de vuelos por cada estado canónico."""
        conteos = {"Atrasado": 0, "A tiempo": 0, "Exitoso": 0, "Cancelado": 0, "Desconocido": 0}
        for v in self.vuelos:
            est = v.normalizar_estado()
            conteos[est] = conteos.get(est, 0) + 1
        return conteos

    def calcular_probabilidades_marginales(self) -> Dict[str, float]:
        """
        Retorna la probabilidad marginal global P(Estado = e) para cada estado,
        con valores entre 0.0 y 1.0.
        """
        conteos = self.calcular_conteos_marginales()
        return {k: v / self.total_vuelos for k, v in conteos.items()}

    # ----------------------------------------------------------------------
    # Métodos Auxiliares de Extracción de Dimensiones
    # ----------------------------------------------------------------------

    def obtener_rutas_disponibles(self) -> List[str]:
        """Lista ordenada de rutas únicas presentes en la colección."""
        rutas = sorted(list(set(v.obtener_ruta() for v in self.vuelos)))
        return [r for r in rutas if r != "Desconocido -> Desconocido"]

    def obtener_franjas_disponibles(self) -> List[str]:
        """Lista de franjas horarias estándar."""
        return [
            "Madrugada (00:00 - 06:00)",
            "Mañana (06:00 - 12:00)",
            "Tarde (12:00 - 18:00)",
            "Noche (18:00 - 24:00)"
        ]

    def obtener_ocupaciones_disponibles(self) -> List[str]:
        """Lista de categorías de ocupación estándar."""
        return ["Baja (< 50%)", "Media (50% - 80%)", "Alta (> 80%)"]

    # ----------------------------------------------------------------------
    # Probabilidades Condicionales Cruzadas (DataFrames para reportes y UI)
    # ----------------------------------------------------------------------

    def _generar_tabla_condicional(self, dimension_func, nombre_columna: str) -> pd.DataFrame:
        registros = []
        for v in self.vuelos:
            registros.append({
                nombre_columna: dimension_func(v),
                "estado": v.normalizar_estado(),
                "precio": v.precio,
                "factor_ocupacion": v.calcular_factor_ocupacion()
            })
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
    # Filtrado y Consulta de Segmentos
    # ----------------------------------------------------------------------

    def filtrar_vuelos(
        self,
        ruta: Optional[str] = None,
        franja: Optional[str] = None,
        ocupacion: Optional[str] = None
    ) -> List[Vuelo]:
        """Filtra los objetos vuelo que coincidan con los criterios seleccionados."""
        resultado = self.vuelos
        if ruta and ruta != "Todas las rutas":
            resultado = [v for v in resultado if v.obtener_ruta() == ruta]
        if franja and franja != "Todas las franjas":
            resultado = [v for v in resultado if v.obtener_franja_horaria() == franja]
        if ocupacion and ocupacion != "Cualquier ocupación":
            resultado = [v for v in resultado if v.obtener_categoria_ocupacion() == ocupacion]
        return resultado

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
            # Si el cruce no tiene registros suficientes, se recurre a la probabilidad marginal
            marg = self.calcular_probabilidades_marginales()
            precio_global = sum(v.precio for v in self.vuelos) / self.total_vuelos
            ocup_global = sum(v.calcular_factor_ocupacion() for v in self.vuelos) / self.total_vuelos
            cap_media = int(sum(v.capacidad_maxima_avion for v in self.vuelos) / self.total_vuelos)
            usada_media = int(sum(v.capacidad_usada_avion for v in self.vuelos) / self.total_vuelos)
            return {
                "muestra_tamano": 0,
                "es_estimacion_global": True,
                "p_atrasado": marg.get("Atrasado", 0.0),
                "p_cancelado": marg.get("Cancelado", 0.0),
                "p_atiempo": marg.get("A tiempo", 0.0),
                "p_exitoso": marg.get("Exitoso", 0.0),
                "precio_promedio": precio_global,
                "ocupacion_promedio": ocup_global,
                "capacidad_maxima_media": cap_media,
                "capacidad_usada_media": usada_media
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


class SimuladorPreciosDinamicos:
    """
    Modelo de simulación comercial y optimización de precios dinámicos.
    Ajusta la tarifa según el riesgo operativo derivado de la probabilidad
    de retrasos y cancelaciones, la presión de ocupación y los márgenes comerciales.
    """

    def __init__(self, motor: MotorEstadisticoVuelos):
        self.motor = motor

    def simular(
        self,
        ruta: str = "Todas las rutas",
        franja: str = "Todas las franjas",
        ocupacion: str = "Cualquier ocupación",
        precio_base_manual: Optional[float] = None,
        costo_retraso_pct: float = 0.25,
        costo_cancelacion_pct: float = 0.60,
        margen_comercial_pct: float = 0.10
    ) -> Dict[str, Any]:
        """
        Ejecuta la simulación de precios dinámicos para los parámetros dados.
        
        Parámetros:
            - ruta: Ruta de interés o 'Todas las rutas'.
            - franja: Franja horaria de despegue o 'Todas las franjas'.
            - ocupacion: Rango de ocupación o 'Cualquier ocupación'.
            - precio_base_manual: Precio de referencia manual (si es None, usa el promedio histórico del segmento).
            - costo_retraso_pct: Factor de ineficiencia por retraso (ej. 0.25 = 25% de sobrecosto logístico).
            - costo_cancelacion_pct: Factor de ineficiencia por cancelación (ej. 0.60 = 60% por indemnizaciones/reubicación).
            - margen_comercial_pct: Margen de beneficio objetivo deseado (ej. 0.10 = 10%).
        """
        metricas = self.motor.calcular_metricas_segmento(ruta, franja, ocupacion)

        # Precio base a utilizar
        if precio_base_manual is not None and precio_base_manual > 0:
            precio_base = float(precio_base_manual)
            tipo_precio_base = "Ingresado manualmente por el usuario"
        else:
            precio_base = float(metricas["precio_promedio"])
            tipo_precio_base = "Promedio histórico del segmento"

        p_atraso = metricas["p_atrasado"]
        p_cancel = metricas["p_cancelado"]

        # 1. Cálculo de Riesgo Logístico y Operativo
        # P_riesgo = P(Atrasado) * Costo_Atraso + P(Cancelado) * Costo_Cancelacion
        riesgo_logistico = (p_atraso * costo_retraso_pct) + (p_cancel * costo_cancelacion_pct)
        factor_riesgo = 1.0 + riesgo_logistico
        recargo_riesgo_monetario = precio_base * riesgo_logistico

        # 2. Factor de Ajuste por Demanda y Ocupación
        # Si la ocupación promedio es alta, incrementa; si es baja, ofrece descuento promocional
        ocup_prom = metricas["ocupacion_promedio"]
        if ocup_prom >= 80.0:
            factor_demanda = 0.12  # +12% por alta presión de demanda
            etiqueta_demanda = "Alta demanda (+12%)"
        elif ocup_prom < 50.0:
            factor_demanda = -0.08 # -8% incentivo promocional para llenado de cabina
            etiqueta_demanda = "Baja demanda / Estimulación (-8%)"
        else:
            factor_demanda = 0.00  # Tarifa estándar neutra
            etiqueta_demanda = "Demanda moderada (Tarifa neutra)"

        # 3. Precio Sugerido Final
        precio_con_riesgo = precio_base * factor_riesgo
        precio_con_demanda = precio_con_riesgo * (1.0 + factor_demanda)
        precio_final_sugerido = precio_con_demanda * (1.0 + margen_comercial_pct)

        ajuste_total_monetario = precio_final_sugerido - precio_base
        ajuste_porcentual_total = ((precio_final_sugerido / precio_base) - 1.0) * 100.0 if precio_base > 0 else 0.0

        # 4. Proyecciones Financieras por Operación de Vuelo
        asientos_ocupados = max(1, metricas["capacidad_usada_media"])
        ingreso_base_vuelo = precio_base * asientos_ocupados
        ingreso_dinamico_vuelo = precio_final_sugerido * asientos_ocupados
        fondo_contingencia_vuelo = recargo_riesgo_monetario * asientos_ocupados

        return {
            "ruta": ruta,
            "franja": franja,
            "ocupacion": ocupacion,
            "muestra_tamano": metricas["muestra_tamano"],
            "es_estimacion_global": metricas["es_estimacion_global"],
            "p_atrasado_pct": round(p_atraso * 100.0, 2),
            "p_cancelado_pct": round(p_cancel * 100.0, 2),
            "p_atiempo_pct": round(metricas["p_atiempo"] * 100.0, 2),
            "p_exitoso_pct": round(metricas["p_exitoso"] * 100.0, 2),
            "precio_base": round(precio_base, 2),
            "tipo_precio_base": tipo_precio_base,
            "riesgo_logistico_pct": round(riesgo_logistico * 100.0, 2),
            "recargo_riesgo_monetario": round(recargo_riesgo_monetario, 2),
            "etiqueta_demanda": etiqueta_demanda,
            "margen_comercial_pct": round(margen_comercial_pct * 100.0, 2),
            "precio_sugerido": round(precio_final_sugerido, 2),
            "ajuste_total_monetario": round(ajuste_total_monetario, 2),
            "ajuste_porcentual_total": round(ajuste_porcentual_total, 2),
            "asientos_ocupados_media": asientos_ocupados,
            "ingreso_base_vuelo": round(ingreso_base_vuelo, 2),
            "ingreso_dinamico_vuelo": round(ingreso_dinamico_vuelo, 2),
            "fondo_contingencia_vuelo": round(fondo_contingencia_vuelo, 2),
        }
