import streamlit as st
import pandas as pd

# Atributos internos obligatorios del sistema
ATRIBUTOS_REQUERIDOS = [
    "id_vuelo", "aeropuerto_llegada", "aeropuerto_salida", 
    "pais_salida", "pais_llegada", "fechayhora_salida", 
    "fechayhora_llegada", "fechayhora_salida_estipulado", 
    "fechayhora_llegada_estipulado", "estado", 
    "capacidad_maxima_avion", "capacidad_usada_avion"
]

# El precio lo marcamos como opcional para mostrar la "degradación elegante"
ATRIBUTOS_OPCIONALES = ["precio"]

st.title("Ingestión y Validación de Datos")
st.write("Sube tu archivo de vuelos y mapea las columnas con el esquema del sistema.")

# Paso 1: Carga del archivo
archivo_subido = st.file_uploader("Cargar base de datos (CSV)", type=["csv"])

if archivo_subido is not None:
    # Leemos temporalmente las columnas para armar la interfaz
    df_preview = pd.read_csv(archivo_subido, nrows=0)
    columnas_usuario = df_preview.columns.tolist()
    columnas_opciones = ["(No asignar)"] + columnas_usuario

    st.subheader("Configuración del Contrato de Esquema")
    
    # Diccionario para guardar cómo el usuario mapeó las columnas
    mapeo_columnas = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Variables Críticas (Obligatorias)**")
        for atributo in ATRIBUTOS_REQUERIDOS:
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':", 
                options=columnas_opciones,
                key=f"req_{atributo}"
            )
            
    with col2:
        st.markdown("**Variables Opcionales**")
        for atributo in ATRIBUTOS_OPCIONALES:
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':", 
                options=columnas_opciones,
                key=f"opc_{atributo}"
            )

    # Paso 2: Validación del contrato
    if st.button("Validar Contrato y Continuar"):
        faltantes_criticos = [
            attr for attr in ATRIBUTOS_REQUERIDOS 
            if mapeo_columnas[attr] == "(No asignar)"
        ]
        
        if len(faltantes_criticos) > 0:
            st.error(f"Error de Contrato: Faltan asignar variables críticas: {', '.join(faltantes_criticos)}")
            st.stop() # Aborta la ejecución
            
        elif mapeo_columnas["precio"] == "(No asignar)":
            st.warning("Advertencia de degradación: No se asignó la variable 'precio'. Los módulos financieros estarán deshabilitados.")
            st.success("Contrato validado con degradación. Procediendo al Reporte de Calidad...")
            # Aquí llamaremos al backend para continuar
        else:
            st.success("Contrato validado exitosamente. Procediendo al Reporte de Calidad...")
            # Aquí llamaremos al backend para continuar