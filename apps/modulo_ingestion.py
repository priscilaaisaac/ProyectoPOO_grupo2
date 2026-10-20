try:
    import streamlit as st  # type: ignore[import-not-found]
except ModuleNotFoundError:
    class _StreamlitUnavailable:
        def __getattr__(self, name):
            raise ModuleNotFoundError("streamlit no está instalado. Instálalo con: pip install streamlit")

    st = _StreamlitUnavailable()

import pandas as pd
from modules.Lector.lector import FactoryLectorDatos
from modules.calidad import EstandarizadorDatos
from modules.validador import ValidadorEsquema

def modulo_ingestion():
    st.markdown('<h1 style="font-size: 2.25rem;">Carga de datos</h1>', unsafe_allow_html=True)
    st.write("Selecciona tu origen de datos y mapea las columnas con el esquema del sistema.")

    # Botones para seleccionar el origen de datos
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Subir archivo local", use_container_width=True):
            st.session_state.origen_datos = "CSV"
            st.session_state.df_crudo_completo = None
            st.session_state.columnas_disponibles = []
            st.session_state.origen_por_columna = {}
            st.session_state.archivos_dfs = {}
            st.session_state.archivos_procesados = False
    with col_btn2:
        if st.button("Conectar base SQL", use_container_width=True):
            st.session_state.origen_datos = "SQL"
            st.session_state.df_crudo_completo = None
            st.session_state.columnas_disponibles = []
            st.session_state.origen_por_columna = {}
            st.session_state.archivos_dfs = {}
            st.session_state.archivos_procesados = False

    st.divider()
    
    # CSV COMO ORIGEN DE LOS DATOS
    if st.session_state.origen_datos == "CSV":
        st.subheader("Carga de archivo local")
        st.info("Puede subir uno o varios archivos (.csv, .txt, .xlsx, .xltx, .xltm). Los archivos se consolidarán automáticamente en un único DataFrame.")
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

            if st.button("Continuar", key="btn_continuar_csv", use_container_width=True):
                try:
                    lector = FactoryLectorDatos.obtener_lector_por_archivo(archivos_activos)
                    df_crudo = lector.leer_archivos(origen=archivos_activos)
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
                        origen_map = getattr(lector, 'origen_por_columna', {}) or df_consolidado.attrs.get('origen_por_columna', {})
                        if not origen_map:
                            origen_map = {col: (archivos_activos[0].name if archivos_activos else "Consolidado") for col in columnas}

                        st.session_state.df_crudo_completo = df_consolidado
                        st.session_state.columnas_disponibles = columnas
                        st.session_state.origen_por_columna = origen_map
                        st.session_state.archivos_dfs = {"dataset_consolidado": df_consolidado}
                        st.session_state.archivos_crudos_temporales = archivos_activos
                        st.session_state.archivos_procesados = True
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
                # 5. Botón 'X' para descartar/eliminar un archivo específico de los ya procesados
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
                            lector = FactoryLectorDatos.obtener_lector_por_archivo(archivos_restantes)
                            df_crudo_nuevo = lector.leer_archivos(origen=archivos_restantes)
                            df_saneado_nuevo = EstandarizadorDatos.sanear_dataframe_individual(df_crudo_nuevo)
                            df_nuevo = ValidadorEsquema.validar_estructura_tabular(df_saneado_nuevo)
                            cols_nuevas = list(df_nuevo.columns)
                            origen_nuevo = getattr(lector, 'origen_por_columna', {}) or df_nuevo.attrs.get('origen_por_columna', {})

                            st.session_state.df_crudo_completo = df_nuevo
                            st.session_state.columnas_disponibles = cols_nuevas
                            st.session_state.origen_por_columna = origen_nuevo
                            st.session_state.archivos_dfs = {"dataset_consolidado": df_nuevo}
                            st.session_state.archivos_crudos_temporales = archivos_restantes
                            st.session_state.archivos_subidos_previos = [a.name for a in archivos_restantes]
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

    # SQL COMO ORIGEN DE LOS DATOS
    elif st.session_state.origen_datos == "SQL":
        st.subheader("Conexión a Base de Datos")
        conexion_sql = st.text_input("Cadena de conexión (URI):")
        tabla_sql = st.text_input("Nombre de la tabla:")

        if conexion_sql and tabla_sql and st.button("Continuar"):
            try:
                lector = FactoryLectorDatos.obtener_lector("SQL")
                df_sql_crudo = lector.leer_archivos(origen=conexion_sql, nombre_tabla=tabla_sql)
                df_sql_saneado = EstandarizadorDatos.sanear_dataframe_individual(df_sql_crudo)
                df_sql = ValidadorEsquema.validar_estructura_tabular(df_sql_saneado)
                columnas_separadas, origen_map, nombres_renombrados = [], {}, {}

                for col in df_sql.columns:
                    col_id_unico = f"{col}__({tabla_sql})"
                    nombres_renombrados[col] = col_id_unico
                    columnas_separadas.append(col_id_unico)
                    origen_map[col_id_unico] = f"Tabla: {tabla_sql}"

                st.session_state.archivos_dfs = {f"Tabla_{tabla_sql}": df_sql}
                st.session_state.df_crudo_completo = df_sql.rename(columns=nombres_renombrados)
                st.session_state.columnas_disponibles = columnas_separadas
                st.session_state.origen_por_columna = origen_map
                st.session_state.archivos_procesados = True
                st.success("¡Conexión SQL exitosa!")
            except Exception as e:
                st.error(f"Error SQL: {e}")