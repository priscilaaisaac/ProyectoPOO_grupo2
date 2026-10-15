"""
Módulo Orquestador y Factory de Ingestión y Lectura de Datos.
Reexporta la clase abstracta LectorDatos, funciones auxiliares y lectores concretos,
e implementa FactoryLectorDatos para la instanciación polimórfica.
"""

from modules.lector_base import (
    DELIMITADORES_VALIDOS,
    detectar_separador,
    detectar_formato,
    sanear_dataframe_individual,
    validar_estructura_tabular,
    LectorDatos
)
from modules.lector_csv import LectorCSV
from modules.lector_txt import LectorTXT
from modules.lector_excel import LectorExcel
from modules.lector_sql import LectorSQL


class FactoryLectorDatos:
    @staticmethod
    def obtener_lector(tipo_origen: str) -> LectorDatos:
        """
        Retorna la instancia adecuada según el tipo de origen.
        tipo_origen debe ser 'CSV', 'TXT', 'EXCEL' o 'SQL'.
        """
        tipo = str(tipo_origen).upper()
        if tipo == "CSV":
            return LectorCSV()
        elif tipo == "TXT":
            return LectorTXT()
        elif tipo == "EXCEL":
            return LectorExcel()
        elif tipo == "SQL":
            return LectorSQL()
        else:
            raise ValueError(f"Tipo de origen desconocido: {tipo_origen}")

    @staticmethod
    def obtener_lector_por_archivo(nombre_archivo) -> LectorDatos:
        """Determina y retorna la instancia de LectorDatos adecuada según la extensión del archivo."""
        if isinstance(nombre_archivo, (list, tuple)):
            if not nombre_archivo:
                return LectorCSV()
            # Al procesar múltiples archivos (posiblemente mixtos .csv, .txt, .xlsx),
            # LectorCSV posee la ramificación temprana por extensión y consolidación horizontal unificada.
            return LectorCSV()

        nombre = getattr(nombre_archivo, 'name', str(nombre_archivo)).lower()
        if nombre.endswith('.csv'):
            return LectorCSV()
        elif nombre.endswith('.txt'):
            return LectorTXT()
        elif nombre.endswith(('.xlsx', '.xls', '.xltx', '.xltm', '.xlsm')):
            return LectorExcel()
        else:
            raise ValueError(f"Extensión de archivo no soportada: {nombre_archivo}")


__all__ = [
    "DELIMITADORES_VALIDOS",
    "detectar_separador",
    "detectar_formato",
    "sanear_dataframe_individual",
    "validar_estructura_tabular",
    "LectorDatos",
    "LectorCSV",
    "LectorTXT",
    "LectorExcel",
    "LectorSQL",
    "FactoryLectorDatos",
]