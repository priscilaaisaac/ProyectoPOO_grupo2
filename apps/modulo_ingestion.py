try:
    import streamlit as st  # type: ignore[import-not-found]
except ModuleNotFoundError:
    class _StreamlitUnavailable:
        def __getattr__(self, name):
            raise ModuleNotFoundError("streamlit no está instalado. Instálalo con: pip install streamlit")

    st = _StreamlitUnavailable()

from typing import List, Tuple, Dict, Optional
import pandas as pd
from modules.Lector.lector import FactoryLectorDatos
from modules.calidad import EstandarizadorDatos
from modules.validador import ValidadorEsquema


def consolidar_cruce_con_ocurrencia(
    lista_dfs: List[Tuple[pd.DataFrame, str]],
    columnas_id: Dict[str, str]
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Consolida una lista de tuplas (df, nombre_archivo) mediante pd.merge(how='outer')
    utilizando una clave compuesta [ID, '_ocurrencia'] para prevenir productos cartesianos.

    Pasos aplicados:
    1. Creación de clave temporal: df['_ocurrencia'] = df.groupby(columna_id_seleccionada).cumcount()
    2. Cruce seguro (Merge): pd.merge(how='outer', left_on=[id_izq, '_ocurrencia'], right_on=[id_der, '_ocurrencia'])
    3. Limpieza de variables temporales: df_final.drop(columns=['_ocurrencia'], inplace=True, errors='ignore')
    4. Conservar registros únicos rellenando el resto con nulos.
    """
    if not lista_dfs:
        return pd.DataFrame(), {}

    if len(lista_dfs) == 1:
        df_indiv, nombre_arch = lista_dfs[0]
        origen_map = {str(col): nombre_arch for col in df_indiv.columns}
        df_res = df_indiv.copy()
        df_res.attrs['origen_por_columna'] = origen_map
        return df_res, origen_map

    cols_existentes = set()
    origen_por_columna: Dict[str, str] = {}

    df_base, nom_base = lista_dfs[0]
    df_acc = df_base.copy()

    id_izq = (
        columnas_id.get(nom_base)
        or next((c for c in df_acc.columns if "id" in str(c).lower()), df_acc.columns[0])
    )
    if id_izq not in df_acc.columns:
        id_izq = df_acc.columns[0]

    for c in df_acc.columns:
        cols_existentes.add(c)
        origen_por_columna[c] = nom_base

    # Creación de clave temporal: orden secuencial de aparición de IDs duplicados
    df_acc['_ocurrencia'] = df_acc.groupby(id_izq).cumcount()

    for idx, (df_sig, nom_sig) in enumerate(lista_dfs[1:], start=1):
        id_der = (
            columnas_id.get(nom_sig)
            or next((c for c in df_sig.columns if "id" in str(c).lower()), df_sig.columns[0])
        )
        if id_der not in df_sig.columns:
            id_der = df_sig.columns[0]

        df_sig_renom = df_sig.copy()
        renombrados = {}
        for c in df_sig_renom.columns:
            if c == '_ocurrencia':
                continue
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
        id_der_renom = renombrados[id_der]

        # Creación de clave temporal en el DataFrame secundario
        df_sig_renom['_ocurrencia'] = df_sig_renom.groupby(id_der_renom).cumcount()

        # Compatibilidad de tipos en clave de unión
        if df_acc[id_izq].dtype != df_sig_renom[id_der_renom].dtype:
            df_acc[id_izq] = df_acc[id_izq].astype(str)
            df_sig_renom[id_der_renom] = df_sig_renom[id_der_renom].astype(str)

        # Cruce seguro (Merge): clave compuesta [ID, '_ocurrencia'] con how='outer'
        df_acc = pd.merge(
            df_acc,
            df_sig_renom,
            left_on=[id_izq, '_ocurrencia'],
            right_on=[id_der_renom, '_ocurrencia'],
            how='outer'
        )

        # Rellenar en id_izq los IDs de aquellas filas que solo existían en el nuevo archivo
        df_acc[id_izq] = df_acc[id_izq].combine_first(df_acc[id_der_renom])

    # Limpieza de variables temporales
    df_acc.drop(columns=['_ocurrencia'], inplace=True, errors='ignore')
    df_acc.attrs['origen_por_columna'] = origen_por_columna
    return df_acc, origen_por_columna


def modulo_ingestion():
    st.markdown('<h1 style="font-size: 2.25rem;">Carga de datos</h1>', unsafe_allow_html=True)
    st.write("Sube tus archivos locales y mapea las columnas con el esquema del sistema.")
    st.info("Puede subir uno o varios archivos (.csv, .txt, .xlsx, .xltx, .xltm). Los archivos se consolidarán automáticamente en un único DataFrame.")
    st.session_state.origen_datos = "CSV"

    st.markdown("""
    <style>
        [data-testid="stFileUploadDropzone"] small,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzoneInstructions"],
        div[data-testid="stFileUploaderDropzoneInstructions"],
        section[data-testid="stFileUploadDropzone"] small,
        section[data-testid="stFileUploaderDropzone"] small {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    archivos_subidos = st.file_uploader("Selecciona uno o más archivos", type=["csv", "txt", "xlsx", "xltx", "xltm"], accept_multiple_files=True)

    if "archivos_descartados" not in st.session_state:
        st.session_state.archivos_descartados = set()

    nombres_uploader = [a.name for a in (archivos_subidos or [])]
    st.session_state.archivos_descartados = {
        n for n in st.session_state.archivos_descartados if n in nombres_uploader
    }

    archivos_activos = [
        a for a in (archivos_subidos or [])
        if a.name not in st.session_state.archivos_descartados
    ]

    if archivos_activos:
        # 1. Evitar carga automática: requerir botón 'Continuar'
        nombres_actuales = [a.name for a in archivos_activos]
        if st.session_state.get("archivos_subidos_previos") != nombres_actuales:
            st.session_state.archivos_procesados = False
            st.session_state.archivos_subidos_previos = nombres_actuales

        columnas_id_seleccionadas = {}
        # Selección de IDs en la Interfaz (Pre-Continuar)
        if len(archivos_activos) >= 2:
            st.markdown("##### Selección de Claves de Unión (IDs)")
            st.info("Seleccione la columna ID para cada archivo para alinear y consolidar los registros correspondientes:")
            for arch in archivos_activos:
                nombre_arch = getattr(arch, "name", str(arch))
                try:
                    lector_arch = FactoryLectorDatos.obtener_lector_por_archivo(arch)
                    cabeceras_arch = lector_arch.obtener_cabeceras(arch)
                except Exception:
                    cabeceras_arch = []

                if not cabeceras_arch:
                    cabeceras_arch = ["(Sin columnas)"]

                # Sugerir columna ID si coincide con 'id', 'id_vuelo', etc.
                idx_defecto = 0
                for i_c, c_nom in enumerate(cabeceras_arch):
                    c_low = str(c_nom).lower()
                    if c_low == "id" or "id_vuelo" in c_low or "codigo" in c_low or "id" in c_low:
                        idx_defecto = i_c
                        break

                col_id_elegida = st.selectbox(
                    f"Seleccione la columna ID para el archivo {nombre_arch}",
                    options=cabeceras_arch,
                    index=idx_defecto,
                    key=f"id_col_{nombre_arch}"
                )
                columnas_id_seleccionadas[nombre_arch] = col_id_elegida

        # Consolidación por Alineación de IDs con clave temporal secuencial al presionar 'Continuar'
        if st.button("Continuar", key="btn_continuar_csv", use_container_width=True):
            try:
                if len(archivos_activos) >= 2:
                    lista_dfs = []
                    for arch in archivos_activos:
                        lector_arch = FactoryLectorDatos.obtener_lector_por_archivo(arch)
                        df_i = lector_arch._leer(arch) if hasattr(lector_arch, '_leer') else lector_arch.leer_archivos(arch)
                        lista_dfs.append((df_i, getattr(arch, 'name', str(arch))))
                    df_crudo, origen_map = consolidar_cruce_con_ocurrencia(lista_dfs, columnas_id_seleccionadas)
                else:
                    lector = FactoryLectorDatos.obtener_lector_por_archivo(archivos_activos[0])
                    df_crudo = lector.leer_archivos(archivos_activos[0])
                    origen_map = {col: archivos_activos[0].name for col in df_crudo.columns}

                df_saneado = EstandarizadorDatos.sanear_dataframe_individual(df_crudo)
                df_consolidado = ValidadorEsquema.validar_estructura_tabular(df_saneado)

                if df_consolidado.empty or len(df_consolidado.columns) < 1:
                    st.error("Los archivos subidos están vacíos o no contienen columnas válidas.")
                    st.session_state.archivos_procesados = False
                    st.session_state.df_crudo_completo = None
                    st.session_state.columnas_disponibles = []
                    st.session_state.origen_por_columna = {}
                    st.session_state.archivos_dfs = {}
                else:
                    columnas = list(df_consolidado.columns)
                    if not origen_map:
                        origen_map = {col: (archivos_activos[0].name if archivos_activos else "Consolidado") for col in columnas}

                    st.session_state.df_crudo_completo = df_consolidado
                    st.session_state.columnas_disponibles = columnas
                    st.session_state.origen_por_columna = origen_map
                    st.session_state.archivos_dfs = {"dataset_consolidado": df_consolidado}
                    st.session_state.archivos_crudos_temporales = archivos_activos
                    st.session_state.archivos_procesados = True
                    st.session_state.columnas_id_seleccionadas = columnas_id_seleccionadas
                    st.success(f"Se cargaron y consolidaron {len(archivos_activos)} archivo(s) exitosamente. Ya puede mapear los atributos abajo.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al procesar archivos: {e}")
                st.session_state.archivos_procesados = False
                st.session_state.df_crudo_completo = None
                st.session_state.columnas_disponibles = []
                st.session_state.origen_por_columna = {}
                st.session_state.archivos_dfs = {}

        # Mostrar vista previa y lista de archivos procesados únicamente tras presionar 'Continuar'
        if st.session_state.get("archivos_procesados", False) and st.session_state.get("df_crudo_completo") is not None:
            st.markdown("##### Archivos incorporados al dataset:")
            arch_a_quitar = None
            for arch in list(st.session_state.get("archivos_crudos_temporales", [])):
                n_arch = getattr(arch, 'name', str(arch))
                cols_arch = [c for c, orig in st.session_state.get("origen_por_columna", {}).items() if orig == n_arch]
                c_info, c_btn = st.columns([6, 1])
                with c_info:
                    st.markdown(f"📄 **`{n_arch}`** &nbsp; <small style='color: #666;'>({len(cols_arch)} columnas)</small>", unsafe_allow_html=True)
                with c_btn:
                    if st.button("❌", key=f"btn_del_{n_arch}", help=f"Descartar {n_arch} del dataset"):
                        arch_a_quitar = n_arch

            if arch_a_quitar:
                st.session_state.archivos_descartados.add(arch_a_quitar)
                archivos_restantes = [
                    a for a in st.session_state.archivos_crudos_temporales
                    if getattr(a, 'name', str(a)) != arch_a_quitar
                ]

                if archivos_restantes:
                    try:
                        cols_id_rest = {
                            getattr(a, 'name', str(a)): st.session_state.get(f"id_col_{getattr(a, 'name', str(a))}")
                            for a in archivos_restantes
                        } if len(archivos_restantes) >= 2 else {}

                        if len(archivos_restantes) >= 2:
                            lista_dfs_rest = []
                            for arch in archivos_restantes:
                                lector_arch = FactoryLectorDatos.obtener_lector_por_archivo(arch)
                                df_i = lector_arch._leer(arch) if hasattr(lector_arch, '_leer') else lector_arch.leer_archivos(arch)
                                lista_dfs_rest.append((df_i, getattr(arch, 'name', str(arch))))
                            df_crudo_nuevo, origen_nuevo = consolidar_cruce_con_ocurrencia(lista_dfs_rest, cols_id_rest)
                        else:
                            lector = FactoryLectorDatos.obtener_lector_por_archivo(archivos_restantes[0])
                            df_crudo_nuevo = lector.leer_archivos(archivos_restantes[0])
                            origen_nuevo = {col: archivos_restantes[0].name for col in df_crudo_nuevo.columns}

                        df_saneado_nuevo = EstandarizadorDatos.sanear_dataframe_individual(df_crudo_nuevo)
                        df_nuevo = ValidadorEsquema.validar_estructura_tabular(df_saneado_nuevo)
                        cols_nuevas = list(df_nuevo.columns)

                        st.session_state.df_crudo_completo = df_nuevo
                        st.session_state.columnas_disponibles = cols_nuevas
                        st.session_state.origen_por_columna = origen_nuevo
                        st.session_state.archivos_dfs = {"dataset_consolidado": df_nuevo}
                        st.session_state.archivos_crudos_temporales = archivos_restantes
                        st.session_state.archivos_subidos_previos = [a.name for a in archivos_restantes]
                        st.session_state.columnas_id_seleccionadas = cols_id_rest
                        st.session_state.archivos_procesados = True

                        # Limpiar llaves de mapeo de columnas eliminadas
                        for k in list(st.session_state.keys()):
                            if k.startswith(("single_req_", "single_opc_", "map_")):
                                if st.session_state[k] not in cols_nuevas:
                                    del st.session_state[k]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al reconstruir dataset tras descartar archivo: {e}")
                else:
                    st.session_state.archivos_procesados = False
                    st.session_state.df_crudo_completo = None
                    st.session_state.columnas_disponibles = []
                    st.session_state.origen_por_columna = {}
                    st.session_state.archivos_dfs = {}
                    st.session_state.archivos_crudos_temporales = []
                    st.session_state.archivos_subidos_previos = []
                    st.session_state.columnas_id_seleccionadas = {}
                    for k in list(st.session_state.keys()):
                        if k.startswith(("single_req_", "single_opc_", "map_")):
                            del st.session_state[k]
                    st.rerun()

            st.markdown("**Vista previa de los datos consolidados:**")
            st.dataframe(st.session_state.df_crudo_completo.head(10), use_container_width=True)
    else:
        # Limpiar el estado si se eliminan todos los archivos
        st.session_state.archivos_procesados = False
        st.session_state.archivos_subidos_previos = []
        st.session_state.df_crudo_completo = None
        st.session_state.columnas_disponibles = []
        st.session_state.origen_por_columna = {}
        st.session_state.archivos_crudos_temporales = []
        st.session_state.archivos_dfs = {}
        st.session_state.columnas_id_seleccionadas = {}
