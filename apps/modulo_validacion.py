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

def _auto_detectar_columna(attr: str, columnas_disp: list) -> str:
    """Intenta sugerir automáticamente la columna más compatible."""
    if not columnas_disp:
        return "(No asignar)"
    col_map = {str(c).lower().strip(): c for c in columnas_disp}
    attr_l = attr.lower().strip()
    if attr_l in col_map:
        return col_map[attr_l]
    for c_l, orig in col_map.items():
        if attr_l in c_l or c_l in attr_l:
            return orig
    return "(No asignar)"


def formatear_opcion_con_archivo(opcion: str) -> str:
    """Devuelve 'nombre_de_la_columna (de: nombre_del_archivo.csv)' para las opciones del selectbox."""
    if opcion == "(No asignar)":
        return "(No asignar)"
    origenes = st.session_state.get("origen_por_columna", {})
    info = origenes.get(opcion)
    if info:
        nombre_arch = info if isinstance(info, str) else info.get("archivo", str(info))
        return f"{opcion} (de: {nombre_arch})"
    return str(opcion)


def modulo_validacion():
    # Condicional de escape rápido (early return): abortar si no hay un archivo activamente procesado en el flujo actual
    if not st.session_state.get("archivos_procesados", False) or st.session_state.get("df_crudo_completo") is None:
        return

    columnas_usuario = st.session_state.get("columnas_disponibles", [])
    if not columnas_usuario:
        return

    st.divider()
    st.markdown('<h3 style="font-size: 1.4rem;">Seleccione variables a analizar</h3>', unsafe_allow_html=True)
    mapeo_columnas = {}
    columnas_disponibles_mapeo = columnas_usuario

    # Detectar si cambiaron las columnas disponibles para resetear mapeos previos
    ultimas_cols = st.session_state.get("ultimas_cols_validacion", [])
    if set(ultimas_cols) != set(columnas_disponibles_mapeo):
        st.session_state.ultimas_cols_validacion = list(columnas_disponibles_mapeo)
        for prefijo, lista_atributos in [("req_", ATRIBUTOS_REQUERIDOS), ("opc_", ATRIBUTOS_OPCIONALES)]:
            for attr in lista_atributos:
                st.session_state.pop(f"{prefijo}{attr}", None)

    # 1. Identificar columnas ya seleccionadas válidas
    seleccionados_global = []
    for prefijo, lista_atributos in [("req_", ATRIBUTOS_REQUERIDOS), ("opc_", ATRIBUTOS_OPCIONALES)]:
        for attr in lista_atributos:
            key = f"{prefijo}{attr}"
            val = st.session_state.get(key)
            if val and val != "(No asignar)" and val in columnas_disponibles_mapeo:
                seleccionados_global.append(val)

    # 2. Autodetectar columnas para atributos aún no definidos en session_state
    for prefijo, lista_atributos in [("req_", ATRIBUTOS_REQUERIDOS), ("opc_", ATRIBUTOS_OPCIONALES)]:
        for attr in lista_atributos:
            key = f"{prefijo}{attr}"
            if key not in st.session_state or (st.session_state[key] != "(No asignar)" and st.session_state[key] not in columnas_disponibles_mapeo):
                disponibles_para_sug = [c for c in columnas_disponibles_mapeo if c not in seleccionados_global]
                sugerencia = _auto_detectar_columna(attr, disponibles_para_sug)
                st.session_state[key] = sugerencia
                if sugerencia != "(No asignar)":
                    seleccionados_global.append(sugerencia)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Variables Críticas (Obligatorias)**")
        for atributo in ATRIBUTOS_REQUERIDOS:
            key = f"req_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")
            opc_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            idx_def = opc_filtradas.index(valor_actual) if valor_actual in opc_filtradas else 0
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':",
                options=opc_filtradas,
                index=idx_def,
                format_func=formatear_opcion_con_archivo,
                key=key
            )

    with col2:
        st.markdown("**Variables Opcionales**")
        for atributo in ATRIBUTOS_OPCIONALES:
            key = f"opc_{atributo}"
            valor_actual = st.session_state.get(key, "(No asignar)")
            opc_filtradas = ["(No asignar)"] + [col for col in columnas_disponibles_mapeo if col not in seleccionados_global or col == valor_actual]
            idx_def = opc_filtradas.index(valor_actual) if valor_actual in opc_filtradas else 0
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':",
                options=opc_filtradas,
                index=idx_def,
                format_func=formatear_opcion_con_archivo,
                key=key
            )

    st.markdown('<h3 style="font-size: 1.4rem;">Guardar y Continuar</h3>', unsafe_allow_html=True)
    nombre_archivo_nuevo = st.text_input("Nombre para el nuevo archivo unificado (sin extensión):", "dataset_vuelos_unificado")

    if st.button("Validar Contrato y Continuar"):
        # REGLA: RESTRICCIÓN ABSOLUTA DE "(No asignar)" CON VALIDACIÓN INMEDIATA
        sin_asignar = [
            attr for attr in ATRIBUTOS_REQUERIDOS
            if not mapeo_columnas.get(attr) or mapeo_columnas.get(attr) == "(No asignar)"
        ]
        if sin_asignar:
            st.error(
                f"⚠️ **Asignación obligatoria incompleta:** "
                f"Ningún atributo obligatorio puede quedar como '(No asignar)'. "
                f"Debe asignar obligatoriamente: **{', '.join(sin_asignar)}**."
            )
            st.session_state.contrato_validado = False
            return

        try:
            df_completo = st.session_state.df_crudo_completo.copy()
            validador = ValidadorEsquema(df=df_completo, mapeo=mapeo_columnas, requeridos=ATRIBUTOS_REQUERIDOS)
            resultado_validacion = validador.validar()

            import os
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
                    info_src = origen_map.get(col_src)
                    if info_src and serie.isna().any():
                        orig_name = info_src if isinstance(info_src, str) else info_src.get("nombre_original")
                        for otra_col, info_otra in origen_map.items():
                            otra_name = info_otra if isinstance(info_otra, str) else info_otra.get("nombre_original")
                            if otra_col != col_src and otra_name == orig_name and otra_col in df_completo.columns:
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