"""
Módulo Base para Motores de Análisis de Vuelos.
Define la clase abstracta pura MotorAnalisisBase.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from modules.Vuelos import Vuelo


class MotorAnalisisBase(ABC):
    """
    Clase abstracta base para motores de análisis de vuelos.
    Define el contrato obligatorio para el cálculo de métricas de segmento y
    centraliza la colección de vuelos junto con los métodos comunes de segmentación y filtrado.
    """

    def __init__(self, vuelos: List[Vuelo]):
        if not vuelos:
            raise ValueError("No se puede inicializar el motor estadístico con una colección vacía de vuelos.")
        self.vuelos = vuelos
        self.total_vuelos = len(vuelos)

    def obtener_rutas_disponibles(self) -> List[str]:
        """Lista ordenada de rutas únicas presentes en la colección (excluyendo cualquier ruta con 'Desconocido')."""
        rutas = sorted(list(set(v.obtener_ruta() for v in self.vuelos)))
        return [r for r in rutas if "desconocido" not in r.lower()]

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


# La clase padre motor_analisis_base sabe cómo organizar y filtrar los datos de los vuelos,
# pero obliga a sus hijos a especializarse en qué motor matemático aplicar para analizarlos
# (el método abstracto calcular_metricas_segmento).

    @abstractmethod
    def calcular_metricas_segmento(
        self,
        ruta: Optional[str] = None,
        franja: Optional[str] = None,
        ocupacion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula probabilidades condicionales específicas y métricas comerciales
        para un segmento exacto definido por el usuario.
        Contrato obligatorio para cualquier motor de análisis.
        """
        pass
