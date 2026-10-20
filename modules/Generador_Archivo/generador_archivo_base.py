"""
Módulo Base para Generadores de Archivos y Reportes.
Define la clase abstracta pura GeneradorArchivo bajo el Principio Abierto/Cerrado (OCP).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional


class GeneradorArchivo(ABC):
    """
    Clase abstracta base para la generación de reportes y exportación de archivos.
    Centraliza el almacenamiento y estructura de los datos del reporte,
    desacoplándolo de la responsabilidad de renderizado del formato físico.
    """

    TITULO_OFICIAL = "Análisis Histórico de Vuelos para la Toma de Decisiones"

    def __init__(
        self,
        simulaciones: Optional[List[Dict[str, Any]]] = None,
        graficos: Optional[List[Dict[str, Any]]] = None,
        tablas_condicionales: Optional[List[Dict[str, Any]]] = None,
        nombre_dataset: str = "Dataset Activo",
        usuario: Optional[str] = None,
        metricas: Optional[List[Dict[str, Any]]] = None
    ):
        self.simulaciones = simulaciones or []
        self.graficos = graficos or []
        self.tablas_condicionales = tablas_condicionales or metricas or []
        self.nombre_dataset = nombre_dataset
        self.usuario = usuario or "Analista de Operaciones"
        self.fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    @abstractmethod
    def generar_archivo(self) -> bytes:
        """Compila y retorna el archivo generado en formato de bytes crudos."""
        pass
