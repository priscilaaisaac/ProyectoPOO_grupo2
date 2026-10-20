"""
Módulo Orquestador y Factory de Ingestión y Lectura de Datos.
Reexporta la clase abstracta LectorDatos, lectores concretos, funciones de utilidad
(con sus nuevas ubicaciones canónicas en modules/calidad.py y modules/validador.py),
e implementa FactoryLectorDatos y LectorOrquestadorMultiArchivo.
"""

import csv
from typing import Dict, List, Tuple
import pandas as pd

from modules.lector_base import LectorDatos
from modules.lector_texto_delimitado import (
    LectorTextoDelimitado,
    DELIMITADORES_VALIDOS,
    detectar_separador,
)
from modules.lector_excel import LectorExcel
from modules.lector_sql import LectorSQL


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
    y consolida los resultados horizontal o verticalmente.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = (
        '.csv', '.txt', '.xlsx', '.xls', '.xltx', '.xltm', '.xlsm'
    )

    def __init__(self):
        self.origen_por_columna: Dict[str, str] = {}

    def leer_archivos(self, origen, nombre_tabla: str = None, modo_unificacion: str = "horizontal", **kwargs) -> pd.DataFrame:
        archivos = list(origen) if isinstance(origen, (list, tuple)) else [origen]
        lista_dfs: List[Tuple[pd.DataFrame, str]] = []
        self.origen_por_columna = {}

        modo = kwargs.get('modo_unificacion', modo_unificacion)
        if kwargs.get('axis') in (0, '0', 'vertical', 'filas'):
            modo = 'vertical'
        elif kwargs.get('axis') in (1, '1', 'horizontal', 'columnas'):
            modo = 'horizontal'

        es_horizontal = modo not in (0, '0', 'vertical', 'filas')

        for archivo in archivos:
            lector_especifico = FactoryLectorDatos.obtener_lector_por_archivo(archivo)
            df_indiv = lector_especifico.leer_archivos(archivo, **kwargs)
            nombre_archivo = getattr(archivo, 'name', str(archivo))
            lista_dfs.append((df_indiv, nombre_archivo))

        if not lista_dfs:
            return pd.DataFrame()

        if es_horizontal:
            columnas_existentes = set()
            dfs_a_unir = []
            for df_indiv, nombre_arch in lista_dfs:
                nuevas_columnas = []
                for col in df_indiv.columns:
                    col_final = col
                    if col_final in columnas_existentes:
                        contador = 2
                        candidato = f"{col} ({contador})"
                        while candidato in columnas_existentes:
                            contador += 1
                            candidato = f"{col} ({contador})"
                        col_final = candidato

                    columnas_existentes.add(col_final)
                    nuevas_columnas.append(col_final)
                    self.origen_por_columna[col_final] = nombre_arch

                df_indiv.columns = nuevas_columnas
                dfs_a_unir.append(df_indiv)

            df_consolidado = pd.concat(dfs_a_unir, axis=1)
        else:
            dfs_a_unir = []
            for df_indiv, nombre_arch in lista_dfs:
                for col in df_indiv.columns:
                    if col not in self.origen_por_columna:
                        self.origen_por_columna[col] = nombre_arch
                dfs_a_unir.append(df_indiv)

            df_consolidado = pd.concat(dfs_a_unir, axis=0, ignore_index=True)

        df_consolidado.attrs['origen_por_columna'] = self.origen_por_columna
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
]