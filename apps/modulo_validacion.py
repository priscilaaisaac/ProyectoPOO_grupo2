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
    if not columnas_disp: # comprueba si la lista está vacia
        return "(No asignar)"
    col_map = {str(c).lower().strip(): c for c in columnas_disp} # diccionario normalizado (se convierten a minúsculas y se quitan los espacios)
    attr_l = attr.lower().strip() # aplica las mismas transformaciones al atributo que se busca
    if attr_l in col_map:
        return col_map[attr_l]
    for c_l, orig in col_map.items():
        if attr_l in c_l or c_l in attr_l:
            return orig
    return "(No asignar)"

# Para saber de qué archivo provienen las columnas de los selectbox
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

    archivos_dfs = st.session_state.get("archivos_dfs", {})
    if not archivos_dfs:
        if st.session_state.get("df_crudo_completo") is not None:
            archivos_dfs = {"dataset_cargado": st.session_state.df_crudo_completo}
        else:
            return

    st.divider()
    st.markdown('<h3 style="font-size: 1.4rem;">Seleccione variables a analizar</h3>', unsafe_allow_html=True)

    es_multifile = len(archivos_dfs) > 1
    if es_multifile:
        st.info(
            f"Se cargaron **{len(archivos_dfs)} archivos**. Configure a continuación la asignación de columnas para cada uno. "
            "Esto permite consolidar archivos aunque tengan encabezados de columnas con nombres distintos (ej. 'aero_orig' vs 'aeropuerto_salida')."
        )

    mapeos_por_archivo = {} # Se inicializa vacío porque almacenará las correspondencias entre los atributos que espera el sistema y las columnas originales seleccionadas por el usuario.

    if es_multifile:
        tabs = st.tabs([f"📄 {nombre}" for nombre in archivos_dfs.keys()])
        for i, (nombre_archivo, df_archivo) in enumerate(archivos_dfs.items()):
            with tabs[i]:
                st.markdown(f"**Asignación de columnas para `{nombre_archivo}`:**")
                mapeo_f = {}
                col1, col2 = st.columns(2)
                cols_archivo = list(df_archivo.columns)

                with col1:
                    st.markdown("**Variables Críticas (Obligatorias)**")
                    for atributo in ATRIBUTOS_REQUERIDOS:
                        key = f"map_{nombre_archivo}_req_{atributo}"
                        sugerencia = _auto_detectar_columna(atributo, cols_archivo)
                        idx_def = cols_archivo.index(sugerencia) + 1 if sugerencia in cols_archivo else 0
                        opc = ["(No asignar)"] + cols_archivo
                        mapeo_f[atributo] = st.selectbox(
                            f"Asignar a '{atributo}':",
                            options=opc,
                            index=idx_def,
                            format_func=formatear_opcion_con_archivo,
                            key=key
                        )

                with col2:
                    st.markdown("**Variables Opcionales**")
                    for atributo in ATRIBUTOS_OPCIONALES:
                        key = f"map_{nombre_archivo}_opc_{atributo}"
                        sugerencia = _auto_detectar_columna(atributo, cols_archivo)
                        idx_def = cols_archivo.index(sugerencia) + 1 if sugerencia in cols_archivo else 0
                        opc = ["(No asignar)"] + cols_archivo
                        mapeo_f[atributo] = st.selectbox(
                            f"Asignar a '{atributo}':",
                            options=opc,
                            index=idx_def,
                            format_func=formatear_opcion_con_archivo,
                            key=key
                        )

                mapeos_por_archivo[nombre_archivo] = mapeo_f
    else:
        nombre_unico = list(archivos_dfs.keys())[0]
        df_unico = archivos_dfs[nombre_unico]
        cols_archivo = list(df_unico.columns)
        mapeo_f = {}

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Variables Críticas (Obligatorias)**")
            for atributo in ATRIBUTOS_REQUERIDOS:
                key = f"single_req_{atributo}"
                sugerencia = _auto_detectar_columna(atributo, cols_archivo)
                idx_def = cols_archivo.index(sugerencia) + 1 if sugerencia in cols_archivo else 0
                opc = ["(No asignar)"] + cols_archivo
                mapeo_f[atributo] = st.selectbox(
                    f"Asignar a '{atributo}':",
                    options=opc,
                    index=idx_def,
                    format_func=formatear_opcion_con_archivo,
                    key=key
                )

        with col2:
            st.markdown("**Variables Opcionales**")
            for atributo in ATRIBUTOS_OPCIONALES:
                key = f"single_opc_{atributo}"
                sugerencia = _auto_detectar_columna(atributo, cols_archivo)
                idx_def = cols_archivo.index(sugerencia) + 1 if sugerencia in cols_archivo else 0
                opc = ["(No asignar)"] + cols_archivo
                mapeo_f[atributo] = st.selectbox(
                    f"Asignar a '{atributo}':",
                    options=opc,
                    index=idx_def,
                    format_func=formatear_opcion_con_archivo,
                    key=key
                )

        mapeos_por_archivo[nombre_unico] = mapeo_f

    st.markdown('<h3 style="font-size: 1.4rem;">Guardar y Continuar</h3>', unsafe_allow_html=True)
    # Nombre para el nuevo archivo
    nombre_archivo_nuevo = st.text_input("Nombre para el nuevo archivo unificado:", "dataset_vuelos_unificado")

    if st.button("Validar Contrato y Continuar"):
        # REGLA 1: RESTRICCIÓN ABSOLUTA DE "(No asignar)" CON VALIDACIÓN INMEDIATA
        incompletos = {}
        for nombre_f, map_f in mapeos_por_archivo.items():
            sin_asig = [
                attr for attr in ATRIBUTOS_REQUERIDOS
                if not map_f.get(attr) or map_f.get(attr) == "(No asignar)"
            ]
            if sin_asig:
                incompletos[nombre_f] = sin_asig

        if incompletos:
            for n_f, s_asig in incompletos.items():
                st.error(
                    f"⚠️ **Asignación obligatoria incompleta en '{n_f}':** "
                    f"Ningún atributo obligatorio puede quedar como '(No asignar)'. "
                    f"Debe asignar obligatoriamente: **{', '.join(s_asig)}**."
                )
            st.session_state.contrato_validado = False
            return

        try:
            import os
            # Validar contrato en cada archivo
            for nombre_f, df_f in archivos_dfs.items():
                map_f = mapeos_por_archivo[nombre_f]
                validador = ValidadorEsquema(df=df_f, mapeo=map_f, requeridos=ATRIBUTOS_REQUERIDOS)
                validador.validar()

            directorio_guardado = os.path.join("data", "archivos_guardados")
            os.makedirs(directorio_guardado, exist_ok=True)

            # Guardar archivos crudos originales
            if "archivos_crudos_temporales" in st.session_state:
                for archivo in st.session_state.archivos_crudos_temporales:
                    ruta_crudo = os.path.join(directorio_guardado, f"raw_{archivo.name}")
                    with open(ruta_crudo, "wb") as f:
                        f.write(archivo.getvalue())

            # Construir dataset unificado con exactamente las 13 columnas canónicas limpias
            dfs_canonicos = []
            for nombre_f, df_f in archivos_dfs.items():
                map_f = mapeos_por_archivo[nombre_f]
                df_canon = pd.DataFrame(index=df_f.index)
                for col_c in COLUMNAS_CANONICAS:
                    col_src = map_f.get(col_c)
                    if col_src and col_src != "(No asignar)" and col_src in df_f.columns:
                        df_canon[col_c] = df_f[col_src].values
                    else:
                        df_canon[col_c] = None
                dfs_canonicos.append(df_canon[COLUMNAS_CANONICAS])

            df_unificado = pd.concat(dfs_canonicos, axis=0, ignore_index=True)
            df_unificado = df_unificado[COLUMNAS_CANONICAS].copy()

            ruta_unificado = os.path.join(directorio_guardado, f"{nombre_archivo_nuevo}.csv")
            df_unificado.to_csv(ruta_unificado, index=False)
            st.session_state.nombre_archivo_actual = f"{nombre_archivo_nuevo}.csv"

            st.session_state.df_crudo = df_unificado
            nuevo_mapeo = {col: col for col in COLUMNAS_CANONICAS}
            st.session_state.mapeo_columnas = nuevo_mapeo
            st.session_state.contrato_validado = True
            st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(df_unificado)

            st.success(
                f"✅ ¡Contrato validado exitosamente! Se unificaron {len(dfs_canonicos)} archivo(s) "
                f"bajo las 13 columnas canónicas limpias. Guardado en '{nombre_archivo_nuevo}.csv'."
            )
        except ValueError as ve:
            st.session_state.contrato_validado = False
            st.error(f"Error de Contrato: {ve}")
        except Exception as e:
            st.session_state.contrato_validado = False
            st.error(f"Error crítico al validar contrato: {e}")