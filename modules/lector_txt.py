"""
Módulo para la lectura de archivos TXT delimitados.
Implementa la clase concreta LectorTXT heredando directamente de LectorCSV.
"""

from typing import Tuple
from modules.lector_csv import LectorCSV


class LectorTXT(LectorCSV):
    """
    Lector especializado para archivos de texto plano (.txt).
    Hereda directamente de LectorCSV y prioriza delimitadores tabulados y barras.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = ('.txt',)
    # Prioridad específica de delimitadores para archivos de texto
    DELIMITADORES_PERMITIDOS: Tuple[str, ...] = ('\t', '|', ';', ',', ' ')

    def detectar_separador(self, origen, default: str = '\t') -> str:
        """Prioriza separadores tabulares como '\\t' o '|' para archivos TXT."""
        return super().detectar_separador(origen, default=default)
