"""
Módulo Orquestador y Factory de Ingestión y Lectura de Datos.
Reexporta la clase abstracta LectorDatos, lectores concretos, funciones de utilidad
e implementa FactoryLectorDatos y LectorOrquestadorMultiArchivo.
"""

import csv
from typing import Dict, List, Tuple, Optional
import pandas as pd

from modules.Lector.lector_base import LectorDatos, consolidar_dataframes_multiples
from modules.Lector.lector_texto_delimitado import (
    LectorTextoDelimitado,
    DELIMITADORES_VALIDOS,
    detectar_separador,
)
from modules.Lector.lector_excel import LectorExcel
from modules.Lector.lector_sql import LectorSQL


def detectar_formato(origen) -> Tuple[str, bool]:
    """
    Detecta el separador y si el archivo tiene encabezado usando csv.Sniffer restringido
    a [',', ';', '\t', '|', ' '].
    Soporta rutas de archivo y streams/buffers de memoria (BytesIO, StringIO, UploadedFile).
    """
    sep = detectar_separador(origen)
    has_header = True
    chunk = ""

    if hasattr(origen, 'read'):
        if hasattr(origen, 'seek'):
            try:
                origen.seek(0)
            except Exception:
                pass
        raw = origen.read(1024)
        if isinstance(raw, bytes):
            try:
                chunk = raw.decode('utf-8')
            except UnicodeDecodeError:
                chunk = raw.decode('latin-1', errors='ignore')
        else:
            chunk = str(raw)

        if hasattr(origen, 'seek'):
            try:
                origen.seek(0)
            except Exception:
                pass
    else:
        try:
            with open(origen, 'r', encoding='utf-8') as f:
                chunk = f.read(1024)
        except (UnicodeDecodeError, Exception):
            try:
                with open(origen, 'r', encoding='latin-1', errors='ignore') as f:
                    chunk = f.read(1024)
            except Exception:
                chunk = ""

    if chunk and chunk.strip():
        try:
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(chunk)
        except Exception:
            has_header = True

    return sep, has_header


class LectorOrquestadorMultiArchivo(LectorDatos):
    """
    Orquestador polimórfico para leer colecciones de archivos con formatos mixtos
    (ej. combinación de .csv, .txt y .xlsx).
    Delega la lectura de cada archivo a su lector específico correspondiente
    y consolida los resultados alineando por ID si se proporcionan columnas_id,
    o mediante concatenación tradicional.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = (
        '.csv', '.txt', '.xlsx', '.xls', '.xltx', '.xltm', '.xlsm'
    )

    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def obtener_cabeceras(self, archivo) -> List[str]:
        """Delega la lectura preliminar de cabeceras al lector correspondiente del archivo."""
        lector_especifico = FactoryLectorDatos.obtener_lector_por_archivo(archivo)
        return lector_especifico.obtener_cabeceras(archivo)

    def leer_archivos(
        self,
        origen,
        nombre_tabla: str = None,
        modo_unificacion: str = "horizontal",
        columnas_id: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        archivos = list(origen) if isinstance(origen, (list, tuple)) else [origen]
        lista_dfs: List[Tuple[pd.DataFrame, str]] = []

        for archivo in archivos:
            lector_especifico = FactoryLectorDatos.obtener_lector_por_archivo(archivo)
            df_indiv = lector_especifico._leer(archivo, **kwargs) if hasattr(lector_especifico, '_leer') else lector_especifico.leer_archivos(archivo, **kwargs)
            nombre_archivo = getattr(archivo, 'name', str(archivo))
            lista_dfs.append((df_indiv, nombre_archivo))

        df_consolidado, self.origen_por_columna = consolidar_dataframes_multiples(
            lista_dfs,
            modo_unificacion=modo_unificacion,
            columnas_id=columnas_id,
            **kwargs
        )
        return df_consolidado


class FactoryLectorDatos:
    @staticmethod
    def obtener_lector(tipo_origen: str) -> LectorDatos:
        """
        Retorna la instancia adecuada según el tipo de origen.
        tipo_origen debe ser 'CSV', 'TXT', 'TEXTO_DELIMITADO', 'EXCEL' o 'SQL'.
        """
        tipo = str(tipo_origen).upper()
        if tipo in ("CSV", "TXT", "TEXTO_DELIMITADO"):
            return LectorTextoDelimitado()
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
                return LectorTextoDelimitado()

            tipos = []
            for item in nombre_archivo:
                n = getattr(item, 'name', str(item)).lower()
                if n.endswith(LectorExcel.EXTENSIONES_SOPORTADAS):
                    tipos.append('EXCEL')
                elif n.endswith(LectorTextoDelimitado.EXTENSIONES_SOPORTADAS):
                    tipos.append('CSV')
                else:
                    tipos.append('CSV')

            if len(set(tipos)) == 1:
                return FactoryLectorDatos.obtener_lector(tipos[0])

            return LectorOrquestadorMultiArchivo()

        nombre = getattr(nombre_archivo, 'name', str(nombre_archivo)).lower()
        if nombre.endswith(LectorTextoDelimitado.EXTENSIONES_SOPORTADAS):
            return LectorTextoDelimitado()
        elif nombre.endswith(LectorExcel.EXTENSIONES_SOPORTADAS):
            return LectorExcel()
        else:
            raise ValueError(f"Extensión de archivo no soportada: {nombre_archivo}")

    @staticmethod
    def obtener_cabeceras_archivo(archivo) -> List[str]:
        """Obtiene las cabeceras de un archivo delegando en su lector correspondiente."""
        lector = FactoryLectorDatos.obtener_lector_por_archivo(archivo)
        return lector.obtener_cabeceras(archivo)


LectorCSV = LectorTextoDelimitado
LectorTXT = LectorTextoDelimitado

__all__ = [
    "DELIMITADORES_VALIDOS",
    "detectar_separador",
    "detectar_formato",
    "LectorDatos",
    "LectorTextoDelimitado",
    "LectorCSV",
    "LectorTXT",
    "LectorExcel",
    "LectorSQL",
    "LectorOrquestadorMultiArchivo",
    "FactoryLectorDatos",
    "consolidar_dataframes_multiples",
]
