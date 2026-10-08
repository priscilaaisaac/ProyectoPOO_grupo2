import streamlit as st
from modules.validador import ValidadorEsquema
from modules.calidad import EstandarizadorDatos

ATRIBUTOS_REQUERIDOS = [
    "aeropuerto_destino", "aeropuerto_origen", "fechayhora_origen", 
    "fechayhora_destino", "fechayhora_origen_estipulado", 
    "fechayhora_destino_estipulado", "estado", 
    "capacidad_maxima_avion", "capacidad_usada_avion",
    "precio", "origen", "destino"
]

ATRIBUTOS_OPCIONALES = ["id_vuelo"]

def modulo_validacion():
    columnas_usuario = st.session_state.columnas_disponibles
    if not columnas_usuario:
        return

    st.divider()

    def format_opcion_con_archivo(opcion):
        if opcion == "(No asignar)": return opcion
        info = st.session_state.get("origen_por_columna", {}).get(opcion)
        return f"{info['nombre_original']}   · 〔 {info['archivo']} 〕" if info else opcion

    st.markdown('<h3 style="font-size: 1.4rem;">Seleccione variables a analizar</h3>', unsafe_allow_html=True)
    mapeo_columnas = {}
    excluidas = []
    columnas_disponibles_mapeo = columnas_usuario
    
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
            opc_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(f"Asignar a '{atributo}':", options=opc_filtradas, format_func=format_opcion_con_archivo, key=key)

    with col2:
        st.markdown("**Variables Opcionales**")
        for atributo in ATRIBUTOS_OPCIONALES:
            key = f"opc_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")
            opc_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(f"Asignar a '{atributo}':", options=opc_filtradas, format_func=format_opcion_con_archivo, key=key)

    st.markdown('<h3 style="font-size: 1.4rem;">Guardar y Continuar</h3>', unsafe_allow_html=True)
    nombre_archivo_nuevo = st.text_input("Nombre para el nuevo archivo unificado (sin extensión):", "dataset_vuelos_unificado")

    if st.button("Validar Contrato y Continuar"):
        try:
            df_completo = st.session_state.df_crudo_completo.copy()
            if excluidas:
                df_completo = df_completo.drop(columns=[col for col in excluidas if col in df_completo.columns])

            validador = ValidadorEsquema(df=df_completo, mapeo=mapeo_columnas, requeridos=ATRIBUTOS_REQUERIDOS)
            resultado_validacion = validador.validar()
            
            import os
            import json
            directorio_guardado = os.path.join("data", "archivos_guardados")
            os.makedirs(directorio_guardado, exist_ok=True)
            
            # Guardar archivos crudos originales
            if "archivos_crudos_temporales" in st.session_state:
                for archivo in st.session_state.archivos_crudos_temporales:
                    ruta_crudo = os.path.join(directorio_guardado, f"raw_{archivo.name}")
                    with open(ruta_crudo, "wb") as f:
                        f.write(archivo.getvalue())
                        
            # Renombrar las columnas al mapeo canónico
            mapeo_inverso = {v: k for k, v in mapeo_columnas.items() if v != "(No asignar)"}
            df_unificado = df_completo.rename(columns=mapeo_inverso)
            
            # Limpiar columnas que no fueron mapeadas y no nos interesan?
            # El usuario dijo "a partir de las columnas de los archivos que se deseó cargar"
            # Dejaremos todas las que no fueron excluidas.
            
            ruta_unificado = os.path.join(directorio_guardado, f"{nombre_archivo_nuevo}.csv")
            df_unificado.to_csv(ruta_unificado, index=False)
            st.session_state.nombre_archivo_actual = f"{nombre_archivo_nuevo}.csv"

            st.session_state.df_crudo = df_unificado
            # El nuevo mapeo es 1:1 para las columnas canónicas
            nuevo_mapeo = {k: k for k in mapeo_columnas.keys() if mapeo_columnas[k] != "(No asignar)"}
            st.session_state.mapeo_columnas = nuevo_mapeo
            st.session_state.contrato_validado = True
            st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(df_unificado)
            
            st.success(f"{resultado_validacion} Archivos guardados exitosamente. Puedes verlos en la sección 'Ver mi Perfil y Archivos Guardados'.")
        except ValueError as ve:
            st.session_state.contrato_validado = False
            st.error(f"Error de Contrato: {ve}")
        except Exception as e:
            st.session_state.contrato_validado = False
            st.error(f"Error crítico: {e}")