try:
    import streamlit as st  # type: ignore[import-not-found]
except ModuleNotFoundError:
    class _StreamlitUnavailable:
        def __getattr__(self, name):
            raise ModuleNotFoundError("streamlit no está instalado. Instálalo con: pip install streamlit")

    st = _StreamlitUnavailable()

import pandas as pd
from modules.lector_datos import FactoryLectorDatos

def modulo_ingestion():
    st.markdown('<h1 style="font-size: 2.25rem;">Carga de datos</h1>', unsafe_allow_html=True)
    st.write("Selecciona tu origen de datos y mapea las columnas con el esquema del sistema.")

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

    if st.session_state.origen_datos == "CSV":
        st.subheader("Carga de archivo local")
        st.info("Puede subir uno o varios archivos (.csv, .txt, .xlsx, .xltx, .xltm). Los archivos se consolidarán automáticamente en un único DataFrame.")
        archivos_subidos = st.file_uploader("Selecciona uno o más archivos", type=["csv", "txt", "xlsx", "xltx", "xltm"], accept_multiple_files=True)

        if archivos_subidos:
            # 1. Evitar carga automática: requerir botón 'Continuar'
            nombres_actuales = [a.name for a in archivos_subidos]
            if st.session_state.get("archivos_subidos_previos") != nombres_actuales:
                st.session_state.archivos_procesados = False
                st.session_state.archivos_subidos_previos = nombres_actuales

            if st.button("Continuar", key="btn_continuar_csv", use_container_width=True):
                try:
                    lector = FactoryLectorDatos.obtener_lector_por_archivo(archivos_subidos)
                    df_consolidado = lector.leer(origen=archivos_subidos)

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
                            origen_map = {col: (archivos_subidos[0].name if archivos_subidos else "Consolidado") for col in columnas}

                        st.session_state.df_crudo_completo = df_consolidado
                        st.session_state.columnas_disponibles = columnas
                        st.session_state.origen_por_columna = origen_map
                        st.session_state.archivos_dfs = {"dataset_consolidado": df_consolidado}
                        st.session_state.archivos_crudos_temporales = archivos_subidos
                        st.session_state.archivos_procesados = True
                        st.success(f"Se cargaron y consolidaron {len(archivos_subidos)} archivo(s) exitosamente. Ya puede mapear los atributos abajo.")
                except Exception as e:
                    st.error(f"Error al procesar archivos: {e}")
                    st.session_state.archivos_procesados = False
                    st.session_state.df_crudo_completo = None
                    st.session_state.columnas_disponibles = []
                    st.session_state.origen_por_columna = {}
                    st.session_state.archivos_dfs = {}

            # Mostrar vista previa únicamente tras presionar 'Continuar'
            if st.session_state.get("archivos_procesados", False) and st.session_state.get("df_crudo_completo") is not None:
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

    elif st.session_state.origen_datos == "SQL":
        st.subheader("Conexión a Base de Datos")
        conexion_sql = st.text_input("Cadena de conexión (URI):")
        tabla_sql = st.text_input("Nombre de la tabla:")

        if conexion_sql and tabla_sql and st.button("Continuar"):
            try:
                lector = FactoryLectorDatos.obtener_lector("SQL")
                df_sql = lector.leer(origen=conexion_sql, nombre_tabla=tabla_sql)
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