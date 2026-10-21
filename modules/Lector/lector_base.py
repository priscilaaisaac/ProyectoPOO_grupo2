"""
Módulo Base para la Ingestión y Lectura de Datos.
Contiene la interfaz abstracta pura LectorDatos y la lógica unificada de consolidación multivariable.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Optional
import pandas as pd


class LectorDatos(ABC):
    """
    Clase abstracta pura para lectores de datos.
    Define el contrato base y extensiones soportadas para la lectura de cualquier formato.
    """
    EXTENSIONES_SOPORTADAS: Tuple[str, ...] = ()

    @abstractmethod
    def leer_archivos(self, origen, **kwargs) -> pd.DataFrame:
        """
        Lee datos desde un origen (ruta de archivo, buffer de memoria o lista de orígenes)
        y retorna un DataFrame con los datos crudos.
        """
        pass

    def leer(self, origen, **kwargs) -> pd.DataFrame:
        """
        Alias de conveniencia y compatibilidad para leer_archivos.
        """
        return self.leer_archivos(origen, **kwargs)

    def obtener_cabeceras(self, archivo) -> List[str]:
        """
        Lee temporalmente las cabeceras del archivo sin alterar el puntero de lectura.
        """
        if hasattr(self, '_leer'):
            df = self._leer(archivo, nrows=0)
        else:
            df = self.leer_archivos(archivo, nrows=0)
        if hasattr(archivo, 'seek'):
            try:
                archivo.seek(0)
            except Exception:
                pass
        return [str(col).strip() for col in df.columns]


def consolidar_dataframes_multiples(
    lista_dfs: List[Tuple[pd.DataFrame, str]],
    modo_unificacion: str = "horizontal",
    columnas_id: Optional[Dict[str, str]] = None,
    **kwargs
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Consolida una lista de tuplas (df, nombre_archivo).
    
    Si se proporciona `columnas_id` (o si modo_unificacion es por id),
    alinea y consolida horizontalmente los registros haciendo coincidir los IDs seleccionados
    mediante pd.merge con how='outer'. Si un ID existe en múltiples archivos pero en posiciones
    diferentes (desfasadas), se alinean primero por el ID. Los IDs no coincidentes se concatenan
    verticalmente rellenando las columnas con valores nulos (NaN).
    Las columnas repetidas reciben sufijos numéricos ' (2)', ' (3)', etc. para no perder datos.
    
    Si no se especifica `columnas_id`, mantiene el comportamiento tradicional (pd.concat).
    """
    if not lista_dfs:
        return pd.DataFrame(), {}

    if len(lista_dfs) == 1:
        df_indiv, nombre_arch = lista_dfs[0]
        origen_map = {str(col): nombre_arch for col in df_indiv.columns}
        df_res = df_indiv.copy()
        df_res.attrs['origen_por_columna'] = origen_map
        return df_res, origen_map

    # Caso con alineación por ID:
    if columnas_id is not None:
        cols_existentes = set()
        origen_por_columna: Dict[str, str] = {}

        df_base, nom_base = lista_dfs[0]
        df_acc = df_base.copy()

        # Determinar clave ID para el primer archivo:
        id_col_base = (
            columnas_id.get(nom_base)
            or columnas_id.get(0)
            or columnas_id.get("0")
            or next((c for c in df_acc.columns if "id" in str(c).lower()), df_acc.columns[0])
        )
        if id_col_base not in df_acc.columns:
            id_col_base = df_acc.columns[0]

        for c in df_acc.columns:
            cols_existentes.add(c)
            origen_por_columna[c] = nom_base

        for idx, (df_sig, nom_sig) in enumerate(lista_dfs[1:], start=1):
            id_col_sig = (
                columnas_id.get(nom_sig)
                or columnas_id.get(idx)
                or columnas_id.get(str(idx))
                or next((c for c in df_sig.columns if "id" in str(c).lower()), df_sig.columns[0])
            )
            if id_col_sig not in df_sig.columns:
                id_col_sig = df_sig.columns[0]

            df_sig_renom = df_sig.copy()
            renombrados = {}
            for c in df_sig_renom.columns:
                cand = c
                if cand in cols_existentes:
                    contador = 2
                    cand = f"{c} ({contador})"
                    while cand in cols_existentes:
                        contador += 1
                        cand = f"{c} ({contador})"
                renombrados[c] = cand
                cols_existentes.add(cand)
                origen_por_columna[cand] = nom_sig

            df_sig_renom = df_sig_renom.rename(columns=renombrados)
            id_col_sig_renom = renombrados[id_col_sig]

            # Crear clave de unión estandarizada como string limpio (preservando None para no colisionar NaNs)
            df_acc['__merge_key__'] = df_acc[id_col_base].apply(
                lambda v: str(v).strip() if pd.notna(v) and str(v).strip() != "" and str(v).strip().lower() != "nan" else None
            )
            df_sig_renom['__merge_key__'] = df_sig_renom[id_col_sig_renom].apply(
                lambda v: str(v).strip() if pd.notna(v) and str(v).strip() != "" and str(v).strip().lower() != "nan" else None
            )

            # pd.merge con how='outer' para alinear filas desfasadas y agregar filas únicas verticalmente
            df_acc = pd.merge(df_acc, df_sig_renom, on='__merge_key__', how='outer')

            # Rellenar en id_col_base los IDs de aquellas filas que solo existían en el nuevo archivo
            df_acc[id_col_base] = df_acc[id_col_base].combine_first(df_acc[id_col_sig_renom])
            df_acc.drop(columns=['__merge_key__'], inplace=True)

        df_acc.attrs['origen_por_columna'] = origen_por_columna
        return df_acc, origen_por_columna

    # Caso legacy (sin columnas_id especificadas):
    modo = kwargs.get('modo_unificacion', modo_unificacion)
    if kwargs.get('axis') in (0, '0', 'vertical', 'filas'):
        modo = 'vertical'
    elif kwargs.get('axis') in (1, '1', 'horizontal', 'columnas'):
        modo = 'horizontal'

    es_horizontal = modo not in (0, '0', 'vertical', 'filas')
    origen_por_columna = {}

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
                origen_por_columna[col_final] = nombre_arch

            df_indiv_copy = df_indiv.copy()
            df_indiv_copy.columns = nuevas_columnas
            dfs_a_unir.append(df_indiv_copy)

        df_consolidado = pd.concat(dfs_a_unir, axis=1)
    else:
        dfs_a_unir = []
        for df_indiv, nombre_arch in lista_dfs:
            for col in df_indiv.columns:
                if col not in origen_por_columna:
                    origen_por_columna[col] = nombre_arch
            dfs_a_unir.append(df_indiv)

        df_consolidado = pd.concat(dfs_a_unir, axis=0, ignore_index=True)

    df_consolidado.attrs['origen_por_columna'] = origen_por_columna
    return df_consolidado, origen_por_columna
