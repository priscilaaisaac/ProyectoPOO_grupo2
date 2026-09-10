import sys
from pathlib import Path

# Añadimos la raíz del proyecto al sys.path para resolver las importaciones de 'libs'
raiz_proyecto = Path(__file__).resolve().parent.parent
if str(raiz_proyecto) not in sys.path:
    sys.path.append(str(raiz_proyecto))

import streamlit as st
import pandas as pd
from libs.lector_datos import FactoryLectorDatos
from libs.validador import ValidadorEsquema

ATRIBUTOS_REQUERIDOS = [
    "id_vuelo", "aeropuerto_destino", "aeropuerto_origen", 
    "origen", "destino", "fechayhora_origen", 
    "fechayhora_destino", "fechayhora_origen_estipulado", 
    "fechayhora_destino_estipulado", "estado", 
    "capacidad_maxima_avion", "capacidad_usada_avion"
]
ATRIBUTOS_OPCIONALES = ["precio"]

st.title("Ingestión y Validación de Datos")
st.write("Selecciona tu origen de datos y mapea las columnas con el esquema del sistema.")

if "origen_datos" not in st.session_state:
    st.session_state.origen_datos = None

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("Subir archivo local", use_container_width=True):
        st.session_state.origen_datos = "CSV"
with col_btn2:
    if st.button("Conectar base SQL", use_container_width=True):
        st.session_state.origen_datos = "SQL"

st.divider()

columnas_usuario = []
df_preview = pd.DataFrame() 

if st.session_state.origen_datos == "CSV":
    st.subheader("Carga de archivo local")
    archivo_subido = st.file_uploader(
        "Selecciona tu base de datos", 
        type=["csv", "txt", "xlsx", "xltx", "xltm"]
    )
    
    if archivo_subido is not None:
        nombre_archivo = archivo_subido.name.lower()
        try:
            if nombre_archivo.endswith(('.csv', '.txt')):
                df_preview = pd.read_csv(archivo_subido, nrows=50)
            elif nombre_archivo.endswith(('.xlsx', '.xltx', '.xltm')):
                df_preview = pd.read_excel(archivo_subido, nrows=50)
            columnas_usuario = df_preview.columns.tolist()
        except Exception as e:
            st.error(f"Error al leer la estructura: {e}")

elif st.session_state.origen_datos == "SQL":
    st.subheader("Conexión a Base de Datos")
    conexion_sql = st.text_input("Cadena de conexión (URI):")
    tabla_sql = st.text_input("Nombre de la tabla:")
    
    if conexion_sql and tabla_sql:
        try:
            query = f"SELECT * FROM {tabla_sql} LIMIT 50"
            df_preview = pd.read_sql(query, con=conexion_sql)
            columnas_usuario = df_preview.columns.tolist()
            st.success("¡Conexión SQL exitosa!")
        except Exception as e:
            st.error(f"Error al conectar: {e}")

if columnas_usuario:
    st.subheader("Configuración del Contrato de Esquema")
    mapeo_columnas = {}
    
    seleccionados_global = []
    for prefijo, lista_atributos in [("req_", ATRIBUTOS_REQUERIDOS), ("opc_", ATRIBUTOS_OPCIONALES)]:
        for attr in lista_atributos:
            key = f"{prefijo}{attr}"
            if key in st.session_state and st.session_state[key] != "(No asignar)":
                seleccionados_global.append(st.session_state[key])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Variables Críticas (Obligatorias)**")
        for atributo in ATRIBUTOS_REQUERIDOS:
            key = f"req_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")
            opciones_filtradas = ["(No asignar)"] + [col for col in columnas_usuario if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(f"Asignar a '{atributo}':", options=opciones_filtradas, key=key)
            
    with col2:
        st.markdown("**Variables Opcionales**")
        for atributo in ATRIBUTOS_OPCIONALES:
            key = f"opc_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")
            opciones_filtradas = ["(No asignar)"] + [col for col in columnas_usuario if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(f"Asignar a '{atributo}':", options=opciones_filtradas, key=key)

    if st.button("Validar Contrato y Continuar"):
        try:
            lector = FactoryLectorDatos.obtener_lector(st.session_state.origen_datos)
            if st.session_state.origen_datos == "CSV":
                archivo_subido.seek(0)
                df_completo = lector.leer(origen=archivo_subido)
            else:
                df_completo = lector.leer(origen=conexion_sql, nombre_tabla=tabla_sql)

            validador = ValidadorEsquema(df_completo, mapeo_columnas, ATRIBUTOS_REQUERIDOS)
            resultado_validacion = validador.validar()

            st.session_state.df_crudo = df_completo
            st.session_state.mapeo_columnas = mapeo_columnas

            if "Advertencia" in resultado_validacion:
                st.warning(resultado_validacion)
            else:
                st.success(resultado_validacion)
                
        except ValueError as ve:
            st.error(f"Error de Contrato: {ve}")
        except Exception as e:
            st.error(f"Error crítico al procesar los datos: {e}")