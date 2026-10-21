"""
Paquete Lector: módulos y clases para la lectura e ingestión de datos
desde diversos orígenes (CSV, TXT, Excel y colecciones multiformato).
"""

from modules.Lector.lector_base import LectorDatos
from modules.Lector.lector_texto_delimitado import (
    LectorTextoDelimitado,
    detectar_separador,
    DELIMITADORES_VALIDOS,
)
from modules.Lector.lector_excel import LectorExcel
from modules.Lector.lector import (
    LectorCSV,
    LectorTXT,
    LectorOrquestadorMultiArchivo,
    FactoryLectorDatos,
    detectar_formato,
)

__all__ = [
    "LectorDatos",
    "LectorTextoDelimitado",
    "LectorCSV",
    "LectorTXT",
    "detectar_separador",
    "DELIMITADORES_VALIDOS",
    "LectorExcel",
    "LectorOrquestadorMultiArchivo",
    "FactoryLectorDatos",
    "detectar_formato",
]
