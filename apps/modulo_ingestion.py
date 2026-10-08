import streamlit as st
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
    with col_btn2:
        if st.button("Conectar base SQL", use_container_width=True):
            st.session_state.origen_datos = "SQL"
            st.session_state.df_crudo_completo = None
            st.session_state.columnas_disponibles = []
            st.session_state.origen_por_columna = {}

    st.divider()

    if st.session_state.origen_datos == "CSV":
        st.markdown('<h3 style="font-size: 1.4rem;">Carga de archivos locales</h3>', unsafe_allow_html=True)
        st.info("Si agrega más de un archivo, las columnas se identificarán por separado con su respectivo origen.")
        archivos_subidos = st.file_uploader("Selecciona uno o más archivos", type=["csv", "txt", "xlsx", "xltx", "xltm"], accept_multiple_files=True)

        if archivos_subidos:
            archivos_validos = True
            for archivo in archivos_subidos:
                nombre_archivo = archivo.name.lower()
                tipo_archivo = "CSV" if nombre_archivo.endswith('.csv') else "TXT" if nombre_archivo.endswith('.txt') else "EXCEL" if nombre_archivo.endswith(('.xlsx', '.xltx', '.xltm')) else None
                    
                try:
                    if tipo_archivo in ["CSV", "TXT"]:
                        from modules.lector_datos import detectar_separador
                        sep_det = detectar_separador(archivo)
                        temp_df = pd.read_csv(archivo, sep=sep_det, engine='python', nrows=5)
                    else:
                        temp_df = pd.read_excel(archivo, nrows=5)
                        
                    if temp_df.empty or len(temp_df.columns) < 1:
                        st.error(f"El archivo '{archivo.name}' no cumple con la condición mínima.")
                        archivos_validos = False
                        break
                except Exception as e:
                    st.error(f"Error al intentar leer el archivo {archivo.name}: {e}")
                    archivos_validos = False
                    break

            if archivos_validos and st.button("Continuar"):
                try:
                    dfs_procesados, columnas_separadas, origen_map = [], [], {}
                    for archivo in archivos_subidos:
                        archivo.seek(0)
                        nombre_archivo = archivo.name.lower()
                        tipo = "CSV" if nombre_archivo.endswith('.csv') else "TXT" if nombre_archivo.endswith('.txt') else "EXCEL"
                        lector = FactoryLectorDatos.obtener_lector(tipo)
                        df_comp = lector.leer(origen=archivo)

                        nombres_renombrados = {}
                        for col in df_comp.columns:
                            col_id_unico = f"{col}__({archivo.name})"
                            nombres_renombrados[col] = col_id_unico
                            columnas_separadas.append(col_id_unico)
                            origen_map[col_id_unico] = {"archivo": archivo.name, "nombre_original": col}

                        dfs_procesados.append(df_comp.rename(columns=nombres_renombrados))

                    st.session_state.df_crudo_completo = pd.concat(dfs_procesados, axis=0, ignore_index=True)
                    st.session_state.columnas_disponibles = columnas_separadas
                    st.session_state.origen_por_columna = origen_map
                    st.success(f"Se consolidaron {len(dfs_procesados)} archivo(s) exitosamente.")
                except Exception as e:
                    st.error(f"Error al procesar: {e}")

    elif st.session_state.origen_datos == "SQL":
        st.markdown('<h3 style="font-size: 1.4rem;">Conexión a Base de Datos</h3>', unsafe_allow_html=True)
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

                st.session_state.df_crudo_completo = df_sql.rename(columns=nombres_renombrados)
                st.session_state.columnas_disponibles = columnas_separadas
                st.session_state.origen_por_columna = origen_map
                st.success("¡Conexión SQL exitosa!")
            except Exception as e:
                st.error(f"Error SQL: {e}")