"""
Módulo para la Simulación Comercial y Optimización de Precios Dinámicos.
Implementa SimuladorPreciosDinamicos desacoplado de motores específicos.
"""

from typing import Dict, Any, Optional
from modules.Estadistica.motor_analisis_base import MotorAnalisisBase

class SimuladorPreciosDinamicos:
    """
    Modelo de simulación comercial y optimización de precios dinámicos.
    Ajusta la tarifa según el riesgo operativo derivado de la probabilidad
    de retrasos y cancelaciones, la presión de ocupación y los márgenes comerciales.
    Acepta cualquier motor derivado de MotorAnalisisBase (DIP).
    """

    def __init__(self, motor: MotorAnalisisBase):
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


__all__ = [
    "SimuladorPreciosDinamicos",
]
