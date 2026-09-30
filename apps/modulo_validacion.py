import streamlit as st
from libs.validador import ValidadorEsquema
from libs.calidad import EstandarizadorDatos

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

    st.markdown('<h3 style="font-size: 1.4rem;">Seleccione variables a excluir</h3>', unsafe_allow_html=True)
    st.multiselect("Variables a excluir:", options=columnas_usuario, format_func=format_opcion_con_archivo, key="variables_excluidas")

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
            opc_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(f"Asignar a '{atributo}':", options=opc_filtradas, format_func=format_opcion_con_archivo, key=key)

    with col2:
        st.markdown("**Variables Opcionales**")
        for atributo in ATRIBUTOS_OPCIONALES:
            key = f"opc_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")
            opc_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            mapeo_columnas[atributo] = st.selectbox(f"Asignar a '{atributo}':", options=opc_filtradas, format_func=format_opcion_con_archivo, key=key)

    if st.button("Validar Contrato y Continuar"):
        try:
            df_completo = st.session_state.df_crudo_completo.copy()
            if excluidas:
                df_completo = df_completo.drop(columns=[col for col in excluidas if col in df_completo.columns])

            validador = ValidadorEsquema(df=df_completo, mapeo=mapeo_columnas, requeridos=ATRIBUTOS_REQUERIDOS)
            resultado_validacion = validador.validar()

            st.session_state.df_crudo = df_completo
            st.session_state.mapeo_columnas = mapeo_columnas
            st.session_state.contrato_validado = True
            st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(df_completo)
            st.success(resultado_validacion)
        except ValueError as ve:
            st.session_state.contrato_validado = False
            st.error(f"Error de Contrato: {ve}")
        except Exception as e:
            st.session_state.contrato_validado = False
            st.error(f"Error crítico: {e}")