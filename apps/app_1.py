import sys
from pathlib import Path

raiz_proyecto = Path(__file__).resolve().parent.parent

if str(raiz_proyecto) not in sys.path:
    sys.path.append(str(raiz_proyecto))

import streamlit as st
import pandas as pd
from libs.lector_datos import FactoryLectorDatos
from libs.validador import ValidadorEsquema
from libs.calidad import EstandarizadorDatos, ReporteCalidad, AnalizadorDuplicados
from libs.pipeline_limpieza import (
    PipelineLimpieza, 
    SaneadorCategoricos, 
    ImputadorMedianaGlobal, 
    ImputadorMedianaPorGrupo
)
from libs.fabrica_vuelos import FabricaVuelos

st.markdown("""
<style>
    [data-testid="stHeaderActionElements"],
    .stApp a[href^="#"],
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;}

    div[data-baseweb="select"] span {
        font-weight: 500;}

    div[data-baseweb="tag"] {
        background-color: rgba(150, 150, 150, 0.15) !important;}
</style>
""", unsafe_allow_html=True)

ATRIBUTOS_REQUERIDOS = [
    "aeropuerto_destino", "aeropuerto_origen", 
    "fechayhora_origen", 
    "fechayhora_destino", "fechayhora_origen_estipulado", 
    "fechayhora_destino_estipulado", "estado", 
    "capacidad_maxima_avion", "capacidad_usada_avion",
    "precio", "origen", "destino"]

ATRIBUTOS_OPCIONALES = ["id_vuelo"]

st.markdown(
    '<h1 style="font-size: 2.25rem;">Carga de datos</h1>',
    unsafe_allow_html=True)

st.write(
    "Selecciona tu origen de datos y mapea las columnas con el esquema del sistema.")

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

    st.markdown(
        '<h3 style="font-size: 1.4rem;">Carga de archivos locales (múltiples permitidos)</h3>',
        unsafe_allow_html=True)

    st.info(
        "Si agrega más de un archivo, las columnas se identificarán por separado con su respectivo origen.")

    archivos_subidos = st.file_uploader(
        "Selecciona uno o más archivos",
        type=["csv", "txt", "xlsx", "xltx", "xltm"],
        accept_multiple_files=True)

    if archivos_subidos:
        archivos_validos = True
    
    for archivo in archivos_subidos:
        nombre_archivo = archivo.name.lower()
        
        # 1. Asignar el origen de datos según la extensión del archivo actual
        if nombre_archivo.endswith('.csv'):
            st.session_state.origen_datos = "CSV"
        elif nombre_archivo.endswith('.txt'):
            st.session_state.origen_datos = "TXT"
        elif nombre_archivo.endswith(('.xlsx', '.xltx', '.xltm')):
            st.session_state.origen_datos = "EXCEL"
            
        # 2. Validar que el archivo tenga contenido usando tu lógica original
        try:
            if st.session_state.origen_datos in ["CSV", "TXT"]:
                temp_df = pd.read_csv(
                    archivo,
                    sep=r'[,;\t-]',
                    engine='python',
                    nrows=5
                )
            elif st.session_state.origen_datos == "EXCEL":
                temp_df = pd.read_excel(
                    archivo,
                    nrows=5
                )

            if temp_df.empty or len(temp_df.columns) < 1:
                st.error(
                    f"El archivo '{archivo.name}' no cumple con la condición mínima "
                    "(requiere al menos 1 columna y encabezado)."
                )
                archivos_validos = False
                break
                
        except Exception as e:
            st.error(f"Error al intentar leer el archivo {archivo.name}: {e}")
            archivos_validos = False
            break

        if archivos_validos and st.button("Continuar"):

            try:
                lector = FactoryLectorDatos.obtener_lector("CSV")

                dfs_procesados = []
                columnas_separadas = []
                origen_map = {}

                for archivo in archivos_subidos:
                    archivo.seek(0)
                    df_comp = lector.leer(origen=archivo)

                    # Se renombra cada columna añadiendo el sufijo del archivo para mantenerlas independientes
                    nombres_renombrados = {}
                    for col in df_comp.columns:
                        col_id_unico = f"{col}__({archivo.name})"
                        nombres_renombrados[col] = col_id_unico
                        columnas_separadas.append(col_id_unico)
                        origen_map[col_id_unico] = {
                            "archivo": archivo.name,
                            "nombre_original": col
                        }

                    df_renombrado = df_comp.rename(columns=nombres_renombrados)
                    dfs_procesados.append(df_renombrado)

                # Se combinan los DataFrames manteniendo las columnas separadas
                st.session_state.df_crudo_completo = pd.concat(
                    dfs_procesados,
                    axis=0,
                    ignore_index=True)

                st.session_state.columnas_disponibles = columnas_separadas
                st.session_state.origen_por_columna = origen_map

                st.success(
                    f"Se consolidaron {len(dfs_procesados)} archivo(s) exitosamente.")

            except Exception as e:
                st.error(
                    f"Error al procesar y unificar los archivos: {e}")

elif st.session_state.origen_datos == "SQL":

    st.markdown(
        '<h3 style="font-size: 1.4rem;">Conexión a Base de Datos</h3>',
        unsafe_allow_html=True)

    conexion_sql = st.text_input(
        "Cadena de conexión (URI):")

    tabla_sql = st.text_input(
        "Nombre de la tabla:")

    if conexion_sql and tabla_sql and st.button("Continuar"):

        try:
            lector = FactoryLectorDatos.obtener_lector("SQL")

            df_sql = lector.leer(
                origen=conexion_sql,
                nombre_tabla=tabla_sql)

            columnas_separadas = []
            origen_map = {}
            nombres_renombrados = {}

            for col in df_sql.columns:
                col_id_unico = f"{col}__({tabla_sql})"
                nombres_renombrados[col] = col_id_unico
                columnas_separadas.append(col_id_unico)
                origen_map[col_id_unico] = {
                    "archivo": f"Tabla: {tabla_sql}",
                    "nombre_original": col
                }

            st.session_state.df_crudo_completo = df_sql.rename(columns=nombres_renombrados)
            st.session_state.columnas_disponibles = columnas_separadas
            st.session_state.origen_por_columna = origen_map

            st.success("¡Conexión SQL y carga exitosa!")

        except Exception as e:
            st.error(
                f"Error al conectar o leer la tabla: {e}")

columnas_usuario = st.session_state.columnas_disponibles

if columnas_usuario:

    st.divider()

    def format_opcion_con_archivo(opcion):
        if opcion == "(No asignar)":
            return opcion

        info = st.session_state.get("origen_por_columna", {}).get(opcion)
        if info:
            return f"{info['nombre_original']}   · 〔 {info['archivo']} 〕"

        return opcion

    st.markdown(
        '<h3 style="font-size: 1.4rem;">Seleccione variables a excluir</h3>',
        unsafe_allow_html=True)

    st.multiselect(
        "Variables a excluir:",
        options=columnas_usuario,
        format_func=format_opcion_con_archivo,
        key="variables_excluidas",
        placeholder="Seleccione las variables que desea descartar...")

    st.markdown(
        '<h3 style="font-size: 1.4rem;">Seleccione variables a analizar</h3>',
        unsafe_allow_html=True)

    mapeo_columnas = {}

    excluidas = st.session_state.get(
        "variables_excluidas",
        [])

    columnas_disponibles_mapeo = [
        c for c in columnas_usuario
        if c not in excluidas]

    seleccionados_global = []

    for prefijo, lista_atributos in [
        ("req_", ATRIBUTOS_REQUERIDOS),
        ("opc_", ATRIBUTOS_OPCIONALES)]:

        for attr in lista_atributos:
            key = f"{prefijo}{attr}"

            if key in st.session_state and st.session_state[key] != "(No asignar)":
                seleccionados_global.append(
                    st.session_state[key])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Variables Críticas (Obligatorias)**")

        for atributo in ATRIBUTOS_REQUERIDOS:
            key = f"req_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")

            opciones_filtradas = (
                ["(No asignar)"] +
                [
                    col
                    for col in columnas_disponibles_mapeo
                    if col not in seleccionados_global
                    or col == valor_actual])

            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':",
                options=opciones_filtradas,
                format_func=format_opcion_con_archivo,
                key=key)

    with col2:
        st.markdown("**Variables Opcionales**")

        for atributo in ATRIBUTOS_OPCIONALES:
            key = f"opc_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")

            opciones_filtradas = (
                ["(No asignar)"] +
                [
                    col
                    for col in columnas_disponibles_mapeo
                    if col not in seleccionados_global
                    or col == valor_actual])

            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':",
                options=opciones_filtradas,
                format_func=format_opcion_con_archivo,
                key=key)

    if st.button("Validar Contrato y Continuar"):
        try:
            df_completo = st.session_state.df_crudo_completo.copy()

            if excluidas:
                df_completo = df_completo.drop(
                    columns=[col for col in excluidas if col in df_completo.columns]
                )

            # Instanciamos el orquestador desacoplado
            validador = ValidadorEsquema(
                df=df_completo,
                mapeo=mapeo_columnas,
                requeridos=ATRIBUTOS_REQUERIDOS
            )

            # Ejecuta todas las reglas modulares
            resultado_validacion = validador.validar()

            st.session_state.df_crudo = df_completo
            st.session_state.mapeo_columnas = mapeo_columnas
            st.session_state.contrato_validado = True

            # Si ya importás EstandarizadorDatos para el reporte:
            st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(df_completo)

            st.success(resultado_validacion)

        except ValueError as ve:
            st.session_state.contrato_validado = False
            st.error(f"Error de Contrato: {ve}")

        except Exception as e:
            st.session_state.contrato_validado = False
            st.error(f"Error crítico al procesar los datos: {e}")

# ----------------------------------------------------
# ANALISIS DE CALIDAD Y PIPELINE DE LIMPIEZA
# ----------------------------------------------------

# Se ejecuta tras validar el contrato satisfactoriamente
if st.session_state.get("df_crudo") is not None and "mapeo_columnas" in st.session_state:
    st.divider()
    st.markdown('<h2 style="font-size: 1.8rem;">Reporte de Diagnóstico de Calidad</h2>', unsafe_allow_html=True)

    # 1. Estandarización de representaciones de error y vacíos a nulos mediante EstandarizadorDatos
    if "df_estandarizado" not in st.session_state:
        st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(st.session_state.df_crudo)

    df_norm = st.session_state.df_estandarizado
    mapeo = st.session_state.mapeo_columnas

    # 2. Generación del reporte tabular mediante ReporteCalidad
    generador_reporte = ReporteCalidad(df_norm, mapeo)
    df_reporte = generador_reporte.generar()

    # 3. Cálculo de filas duplicadas mediante AnalizadorDuplicados
    total_duplicados = AnalizadorDuplicados.contar(df_norm)

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Registros analizados", len(df_norm))
    col_m2.metric("Registros duplicados totales", total_duplicados)

    st.dataframe(df_reporte, use_container_width=True)

    st.markdown('<h3 style="font-size: 1.4rem;">Tratamiento de Anomalías y Valores Nulos</h3>', unsafe_allow_html=True)
    
    # Identificación de atributos numéricos según el contrato
    columnas_numericas = ["capacidad_maxima_avion", "capacidad_usada_avion"]
    if mapeo.get("precio") and mapeo.get("precio") != "(No asignar)":
        columnas_numericas.append("precio")

    configuracion_imputacion = {}

    # Opciones de tratamiento con advertencia explícita de nulos
    for attr in columnas_numericas:
        col_real = mapeo[attr]
        info_attr = df_reporte[df_reporte["Atributo del Sistema"] == attr]
        nulls = int(info_attr["Cantidad Nulls"].values[0]) if not info_attr.empty else 0

        st.write(f"En el atributo **'{attr}'** tenés **{nulls}** datos null.")

        opcion = st.selectbox(
            f"Tratamiento para '{attr}' (Columna: {col_real}):",
            options=[
                "Dejar tal cual está",
                "Imputar con la mediana global",
                "Imputar con la mediana por grupos (país de origen y país de llegada)"
            ],
            key=f"tratamiento_{attr}"
        )
        configuracion_imputacion[attr] = opcion

    if st.button("Ejecutar Pipeline de Limpieza"):
        # Instanciación del orquestador PipelineLimpieza
        pipeline = PipelineLimpieza()

        # 1. Estrategia fija: reemplazo de valores faltantes en texto por 'Desconocido'
        cols_texto = [
            mapeo[a]
            for a in ["aeropuerto_origen", "aeropuerto_destino", "estado"]
            if mapeo.get(a) and mapeo.get(a) != "(No asignar)"
        ]
        if cols_texto:
            pipeline.agregar_paso(SaneadorCategoricos(cols_texto))

        # 2. Configuración de estrategias numéricas según la selección del analista
        col_pais_orig = mapeo.get("origen") if mapeo.get("origen") != "(No asignar)" else None
        col_pais_dest = mapeo.get("destino") if mapeo.get("destino") != "(No asignar)" else None

        for attr, metodo in configuracion_imputacion.items():
            col_fisica = mapeo[attr]
            if metodo == "Imputar con la mediana global":
                pipeline.agregar_paso(ImputadorMedianaGlobal(col_fisica))
            elif metodo == "Imputar con la mediana por grupos (país de origen y país de llegada)":
                pipeline.agregar_paso(ImputadorMedianaPorGrupo(col_fisica, col_pais_orig, col_pais_dest))

        # Ejecución secuencial de los pasos apilados
        df_limpio = pipeline.ejecutar(df_norm)
        st.session_state.df_limpio = df_limpio
        st.success("¡Pipeline ejecutado exitosamente! Base de datos saneada y lista para instanciar objetos Vuelo.")

        # Dentro del bloque "if st.button('Ejecutar Pipeline de Limpieza'):"
        df_limpio = pipeline.ejecutar(df_norm)
        st.session_state.df_limpio = df_limpio

# Instanciación de objetos de dominio en memoria
        lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, st.session_state.mapeo_columnas)
        st.session_state.lista_vuelos = lista_vuelos

        st.success(f"¡Pipeline ejecutado! Se instanciaron con éxito {len(lista_vuelos)} objetos Vuelo en memoria.")