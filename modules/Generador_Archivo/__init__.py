"""
Paquete Generador_Archivo: módulos para la generación de reportes ejecutivos en PDF
utilizando ReportLab.
"""

from modules.Generador_Archivo.generador_pdf import (
    GeneradorReportePDF,
    NumberedCanvas,
    PALETA_COLORES,
)

__all__ = [
    "GeneradorReportePDF",
    "NumberedCanvas",
    "PALETA_COLORES",
]
