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
from modules.Generador_Archivo.generador_docx import GeneradorDOCX

__all__ = [
    "GeneradorArchivo",
    "GeneradorReportePDF",
    "GeneradorDOCX",
    "NumberedCanvas",
    "PALETA_COLORES",
]
