import streamlit as st
import pandas as pd
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

COLUMNAS_CANONICAS = [
    "id_vuelo",
    "aeropuerto_origen",
    "aeropuerto_destino",
    "origen",
    "destino",
    "fechayhora_origen",
    "fechayhora_destino",
    "fechayhora_origen_estipulado",
    "fechayhora_destino_estipulado",
    "estado",
    "capacidad_maxima_avion",
    "capacidad_usada_avion",
    "precio"
]

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
                        
            # Construir df_unificado conteniendo ÚNICAMENTE las 13 columnas canónicas limpias
            df_unificado = pd.DataFrame(index=df_completo.index)
            origen_map = st.session_state.get("origen_por_columna", {})
            for col_canon in COLUMNAS_CANONICAS:
                col_src = mapeo_columnas.get(col_canon)
                if col_src and col_src != "(No asignar)" and col_src in df_completo.columns:
                    serie = df_completo[col_src].copy()
                    # Coalescer si provienen de múltiples archivos consolidados verticalmente
                    info_src = origen_map.get(col_src)
                    if info_src and serie.isna().any():
                        orig_name = info_src.get("nombre_original")
                        for otra_col, info_otra in origen_map.items():
                            if otra_col != col_src and info_otra.get("nombre_original") == orig_name and otra_col in df_completo.columns:
                                serie = serie.combine_first(df_completo[otra_col])
                    df_unificado[col_canon] = serie.values
                else:
                    df_unificado[col_canon] = None

            # Garantizar orden canónico exacto
            df_unificado = df_unificado[COLUMNAS_CANONICAS].copy()

            ruta_unificado = os.path.join(directorio_guardado, f"{nombre_archivo_nuevo}.csv")
            df_unificado.to_csv(ruta_unificado, index=False)
            st.session_state.nombre_archivo_actual = f"{nombre_archivo_nuevo}.csv"

            st.session_state.df_crudo = df_unificado
            # El nuevo mapeo es 1:1 para todas las columnas canónicas
            nuevo_mapeo = {col: col for col in COLUMNAS_CANONICAS}
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