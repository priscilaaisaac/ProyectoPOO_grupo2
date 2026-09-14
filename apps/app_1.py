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

# Configuración de estilos: elimina enlaces ancla (URL) en títulos y atenúa textos secundarios
st.markdown("""
<style>
    /* Ocultar enlaces de ancla (íconos de URL/cadena) en todos los encabezados */
    [data-testid="stHeaderActionElements"],
    .stApp a[href^="#"],
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;
    }
    
    div[data-baseweb="select"] span {
        font-weight: 500;
    }
    div[data-baseweb="tag"] {
        background-color: rgba(150, 150, 150, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

ATRIBUTOS_REQUERIDOS = [
    "aeropuerto_destino", "aeropuerto_origen", 
    "fechayhora_origen", 
    "fechayhora_destino", "fechayhora_origen_estipulado", 
    "fechayhora_destino_estipulado", "estado", 
    "capacidad_maxima_avion", "capacidad_usada_avion",
    "precio"
]
ATRIBUTOS_OPCIONALES = ["id_vuelo", "origen", "destino"]

st.markdown('<h1 style="font-size: 2.25rem;">Carga de datos</h1>', unsafe_allow_html=True)
st.write("Selecciona tu origen de datos y mapea las columnas con el esquema del sistema.")

if "origen_datos" not in st.session_state:
    st.session_state.origen_datos = None
if "df_crudo_completo" not in st.session_state:
    st.session_state.df_crudo_completo = None
if "columnas_disponibles" not in st.session_state:
    st.session_state.columnas_disponibles = []
if "origen_por_columna" not in st.session_state:
    st.session_state.origen_por_columna = {}

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
    st.markdown('<h3 style="font-size: 1.4rem;">Carga de archivos locales (múltiples permitidos)</h3>', unsafe_allow_html=True)
    st.info("Si agrega mas de un archivo, verifique que no se repitan las columnas. En caso de repetirse, elegir una para el análisis y elegir una para excluirla.")
    
    archivos_subidos = st.file_uploader(
        "Selecciona uno o más archivos", 
        type=["csv", "txt", "xlsx", "xltx", "xltm"],
        accept_multiple_files=True
    )
    
    if archivos_subidos:
        archivos_validos = True
        for archivo in archivos_subidos:
            nombre_archivo = archivo.name.lower()
            try:
                if nombre_archivo.endswith(('.csv', '.txt')):
                    temp_df = pd.read_csv(archivo, sep=r'[,;\t\-]', engine='python', nrows=5)
                elif nombre_archivo.endswith(('.xlsx', '.xltx', '.xltm')):
                    temp_df = pd.read_excel(archivo, nrows=5)
                
                if temp_df.empty or len(temp_df.columns) < 1:
                    st.error(f"El archivo '{archivo.name}' no cumple con la condición mínima (requiere al menos 1 columna y encabezado).")
                    archivos_validos = False
                    break
            except Exception as e:
                st.error(f"Error al leer la estructura de '{archivo.name}': {e}")
                archivos_validos = False
                break

        if archivos_validos and st.button("Continuar"):
            try:
                lector = FactoryLectorDatos.obtener_lector("CSV")
                dfs_completos = []
                origen_map = {}
                for archivo in archivos_subidos:
                    archivo.seek(0)
                    df_comp = lector.leer(origen=archivo)
                    for col in df_comp.columns:
                        if col not in origen_map:
                            origen_map[col] = archivo.name
                        else:
                            origen_map[col] += f", {archivo.name}"
                    dfs_completos.append(df_comp)
                
                st.session_state.df_crudo_completo = pd.concat(dfs_completos, ignore_index=True)
                st.session_state.columnas_disponibles = st.session_state.df_crudo_completo.columns.tolist()
                st.session_state.origen_por_columna = origen_map
                st.success(f"Se consolidaron {len(dfs_completos)} archivo(s) exitosamente.")
            except Exception as e:
                st.error(f"Error al procesar y unificar los archivos: {e}")

elif st.session_state.origen_datos == "SQL":
    st.markdown('<h3 style="font-size: 1.4rem;">Conexión a Base de Datos</h3>', unsafe_allow_html=True)
    conexion_sql = st.text_input("Cadena de conexión (URI):")
    tabla_sql = st.text_input("Nombre de la tabla:")
    
    if conexion_sql and tabla_sql and st.button("Continuar"):
        try:
            lector = FactoryLectorDatos.obtener_lector("SQL")
            df_sql = lector.leer(origen=conexion_sql, nombre_tabla=tabla_sql)
            st.session_state.df_crudo_completo = df_sql
            st.session_state.columnas_disponibles = df_sql.columns.tolist()
            st.session_state.origen_por_columna = {c: f"Tabla: {tabla_sql}" for c in df_sql.columns}
            st.success("¡Conexión SQL y carga exitosa!")
        except Exception as e:
            st.error(f"Error al conectar o leer la tabla: {e}")

columnas_usuario = st.session_state.columnas_disponibles
if columnas_usuario:
    st.divider()
    
    def format_opcion_con_archivo(opcion):
        if opcion == "(No asignar)":
            return opcion
        archivo_orig = st.session_state.get("origen_por_columna", {}).get(opcion, "")
        if archivo_orig:
            return f"{opcion}   ·  〔 {archivo_orig} 〕"
        return opcion

    st.markdown('<h3 style="font-size: 1.4rem;">Seleccione variables a excluir</h3>', unsafe_allow_html=True)
    st.multiselect(
        "Variables a excluir:",
        options=columnas_usuario,
        format_func=format_opcion_con_archivo,
        key="variables_excluidas",
        placeholder="Seleccione las variables que desea descartar..."
    )

    st.markdown('<h3 style="font-size: 1.4rem;">Seleccione variables a analizar</h3>', unsafe_allow_html=True)
    mapeo_columnas = {}
    
    excluidas = st.session_state.get("variables_excluidas", [])
    columnas_disponibles_mapeo = [c for c in columnas_usuario if c not in excluidas]
    
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
            opciones_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':", 
                options=opciones_filtradas, 
                format_func=format_opcion_con_archivo, 
                key=key
            )
            
    with col2:
        st.markdown("**Variables Opcionales**")
        for atributo in ATRIBUTOS_OPCIONALES:
            key = f"opc_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")
            opciones_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':", 
                options=opciones_filtradas, 
                format_func=format_opcion_con_archivo, 
                key=key
            )

    if st.button("Validar Contrato y Continuar"):
        try:
            df_completo = st.session_state.df_crudo_completo.copy()
            if excluidas:
                df_completo = df_completo.drop(columns=[col for col in excluidas if col in df_completo.columns])

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