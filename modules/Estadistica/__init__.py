"""
Paquete Estadistica: motores de análisis estadístico descriptivo
y simulador de precios dinámicos bajo principios OCP y DIP.
"""

from modules.Estadistica.motor_analisis_base import MotorAnalisisBase
from modules.Estadistica.motor_estadistico_descriptivo import (
    MotorEstadisticoDescriptivo,
    MotorEstadisticoVuelos,
)
from modules.Estadistica.simulador_precios import SimuladorPreciosDinamicos

__all__ = [
    "MotorAnalisisBase",
    "MotorEstadisticoDescriptivo",
    "MotorEstadisticoVuelos",
    "SimuladorPreciosDinamicos",
]
