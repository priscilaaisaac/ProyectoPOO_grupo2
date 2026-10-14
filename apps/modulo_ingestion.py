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
    with col_btn2:
        if st.button("Conectar base SQL", use_container_width=True):
            st.session_state.origen_datos = "SQL"
            st.session_state.df_crudo_completo = None
            st.session_state.columnas_disponibles = []
            st.session_state.origen_por_columna = {}
            st.session_state.archivos_dfs = {}

    st.divider()

    if st.session_state.origen_datos == "CSV":
        st.subheader("Carga de archivo local")
        st.info("Puede subir uno o varios archivos simultáneamente (.csv, .txt, .xlsx, .xltx, .xltm). Cada archivo se leerá de forma independiente.")
        archivos_subidos = st.file_uploader("Selecciona uno o más archivos", type=["csv", "txt", "xlsx", "xltx", "xltm"], accept_multiple_files=True)

        if archivos_subidos:
            archivos_validos = True
            archivos_dfs = {}
            dfs_procesados, columnas_separadas, origen_map = [], [], {}

            for archivo in archivos_subidos:
                try:
                    archivo.seek(0)
                    lector = FactoryLectorDatos.obtener_lector_por_archivo(archivo.name)
                    df_comp = lector.leer(origen=archivo)

                    if df_comp.empty or len(df_comp.columns) < 1:
                        st.error(f"El archivo '{archivo.name}' está vacío o no contiene columnas válidas.")
                        archivos_validos = False
                        break

                    archivos_dfs[archivo.name] = df_comp

                    nombres_renombrados = {}
                    for col in df_comp.columns:
                        col_id_unico = f"{col}__({archivo.name})" if len(archivos_subidos) > 1 else str(col)
                        nombres_renombrados[col] = col_id_unico
                        columnas_separadas.append(col_id_unico)
                        origen_map[col_id_unico] = {"archivo": archivo.name, "nombre_original": str(col)}

                    dfs_procesados.append(df_comp.rename(columns=nombres_renombrados))

                except Exception as e:
                    st.error(f"Error al procesar el archivo '{archivo.name}': {e}")
                    archivos_validos = False
                    break

            if archivos_validos and dfs_procesados:
                try:
                    st.session_state.archivos_dfs = archivos_dfs
                    st.session_state.df_crudo_completo = pd.concat(dfs_procesados, axis=0, ignore_index=True)
                    st.session_state.columnas_disponibles = columnas_separadas
                    st.session_state.origen_por_columna = origen_map
                    st.session_state.archivos_crudos_temporales = archivos_subidos
                    st.success(f"Se cargaron {len(dfs_procesados)} archivo(s) exitosamente. Ya puede mapear los atributos abajo.")
                except Exception as e:
                    st.error(f"Error al consolidar archivos: {e}")
        else:
            # Limpiar el estado si se eliminan todos los archivos
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
                    origen_map[col_id_unico] = {"archivo": f"Tabla: {tabla_sql}", "nombre_original": col}

                st.session_state.archivos_dfs = {f"Tabla_{tabla_sql}": df_sql}
                st.session_state.df_crudo_completo = df_sql.rename(columns=nombres_renombrados)
                st.session_state.columnas_disponibles = columnas_separadas
                st.session_state.origen_por_columna = origen_map
                st.success("¡Conexión SQL exitosa!")
            except Exception as e:
                st.error(f"Error SQL: {e}")