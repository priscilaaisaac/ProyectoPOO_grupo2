"""
Paquete Generador_Archivo: módulos para la generación de reportes ejecutivos
utilizando clases abstractas bajo OCP.
"""

from modules.Generador_Archivo.generador_archivo_base import GeneradorArchivo
from modules.Generador_Archivo.generador_pdf import (
    GeneradorReportePDF,
    NumberedCanvas,
    PALETA_COLORES,
)

__all__ = [
    "GeneradorArchivo",
    "GeneradorReportePDF",
    "NumberedCanvas",
    "PALETA_COLORES",
]
