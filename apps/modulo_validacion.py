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


def _renderizar_selectboxes_mapeo(nombre_archivo: str, df_archivo: pd.DataFrame, prefix: str) -> dict:
    """
    Renderiza los selectbox de mapeo aplicando exclusión mutua estricta:
    1. Detección de columnas ocupadas: Lee st.session_state para identificar qué columnas físicas ya han sido seleccionadas en los otros selectbox.
    2. Filtrado dinámico: Para cada atributo del contrato, la lista contiene ['(No asignar)'] + [columna_actual (si hay)] + [columnas libres].
    3. Conserva el formato visual mediante format_func=formatear_opcion_con_archivo sobre valores internos reales.
    """
    cols_archivo = list(df_archivo.columns)
    atributos_info = (
        [(attr, f"{prefix}req_{attr}", True) for attr in ATRIBUTOS_REQUERIDOS] +
        [(attr, f"{prefix}opc_{attr}", False) for attr in ATRIBUTOS_OPCIONALES]
    )

    # 0. Inicialización de sugerencias iniciales en st.session_state si es la primera vez que se renderizan
    #    o si el valor guardado previamente ya no pertenece a las columnas del archivo actual.
    columnas_asignadas_inicio = set()
    for attr, key, _ in atributos_info:
        val = st.session_state.get(key)
        if val and val != "(No asignar)" and val in cols_archivo:
            columnas_asignadas_inicio.add(val)

    for attr, key, _ in atributos_info:
        val = st.session_state.get(key)
        if key not in st.session_state or (val != "(No asignar)" and val not in cols_archivo):
            cols_candidatas = [c for c in cols_archivo if c not in columnas_asignadas_inicio]
            sug = _auto_detectar_columna(attr, cols_candidatas)
            if sug != "(No asignar)" and sug in cols_candidatas:
                st.session_state[key] = sug
                columnas_asignadas_inicio.add(sug)
            else:
                st.session_state[key] = "(No asignar)"

    # 1. Detección de columnas ocupadas en st.session_state:
    columnas_ocupadas = set()
    for attr, key, _ in atributos_info:
        val = st.session_state.get(key)
        if val and val != "(No asignar)" and val in cols_archivo:
            columnas_ocupadas.add(val)

    # 2. Filtrado dinámico y renderizado:
    mapeo_f = {}
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Variables Críticas (Obligatorias)**")
        for attr in ATRIBUTOS_REQUERIDOS:
            key = f"{prefix}req_{attr}"
            val_actual = st.session_state.get(key)
            col_seleccionada = val_actual if val_actual and val_actual != "(No asignar)" and val_actual in cols_archivo else None

            # Columnas ocupadas por OTROS selectbox
            ocupadas_otros = columnas_ocupadas - ({col_seleccionada} if col_seleccionada else set())
            columnas_libres = [c for c in cols_archivo if c not in ocupadas_otros and c != col_seleccionada]

            # Opciones dinámicas: ['(No asignar)'] + [col_seleccionada (si la hay)] + [columnas libres]
            if col_seleccionada:
                opciones = ["(No asignar)", col_seleccionada] + columnas_libres
                idx_actual = 1
            else:
                opciones = ["(No asignar)"] + columnas_libres
                idx_actual = 0

            opciones = list(dict.fromkeys(opciones))

            mapeo_f[attr] = st.selectbox(
                f"Asignar a '{attr}':",
                options=opciones,
                index=idx_actual,
                format_func=formatear_opcion_con_archivo,
                key=key
            )

    with col2:
        st.markdown("**Variables Opcionales**")
        for attr in ATRIBUTOS_OPCIONALES:
            key = f"{prefix}opc_{attr}"
            val_actual = st.session_state.get(key)
            col_seleccionada = val_actual if val_actual and val_actual != "(No asignar)" and val_actual in cols_archivo else None

            ocupadas_otros = columnas_ocupadas - ({col_seleccionada} if col_seleccionada else set())
            columnas_libres = [c for c in cols_archivo if c not in ocupadas_otros and c != col_seleccionada]

            if col_seleccionada:
                opciones = ["(No asignar)", col_seleccionada] + columnas_libres
                idx_actual = 1
            else:
                opciones = ["(No asignar)"] + columnas_libres
                idx_actual = 0

            opciones = list(dict.fromkeys(opciones))

            mapeo_f[attr] = st.selectbox(
                f"Asignar a '{attr}':",
                options=opciones,
                index=idx_actual,
                format_func=formatear_opcion_con_archivo,
                key=key
            )

    return mapeo_f


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

    mapeos_por_archivo = {}

    if es_multifile:
        tabs = st.tabs([f"📄 {nombre}" for nombre in archivos_dfs.keys()])
        for i, (nombre_archivo, df_archivo) in enumerate(archivos_dfs.items()):
            with tabs[i]:
                st.markdown(f"**Asignación de columnas para `{nombre_archivo}`:**")
                mapeos_por_archivo[nombre_archivo] = _renderizar_selectboxes_mapeo(
                    nombre_archivo=nombre_archivo,
                    df_archivo=df_archivo,
                    prefix=f"map_{nombre_archivo}_"
                )
    else:
        nombre_unico = list(archivos_dfs.keys())[0]
        df_unico = archivos_dfs[nombre_unico]
        mapeos_por_archivo[nombre_unico] = _renderizar_selectboxes_mapeo(
            nombre_archivo=nombre_unico,
            df_archivo=df_unico,
            prefix="single_"
        )

    archivos_crudos = st.session_state.get("archivos_crudos_temporales", [])
    total_archivos = len(archivos_crudos) if archivos_crudos else len(archivos_dfs)

    if total_archivos >= 2:
        st.markdown('<h3 style="font-size: 1.4rem;">Guardar Archivo Unificado y Continuar</h3>', unsafe_allow_html=True)
        nombre_archivo_nuevo = st.text_input("Nombre para el nuevo archivo unificado:", "dataset_unificado")
    else:
        st.markdown('<h3 style="font-size: 1.4rem;">Continuar a Limpieza</h3>', unsafe_allow_html=True)
        nombre_archivo_nuevo = ""

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

            usuario_activo = st.session_state.get("usuario_activo")
            username = usuario_activo.username if usuario_activo else "general"
            from modules.gestor_usuarios import GestorUsuarios
            directorio_guardado = GestorUsuarios.obtener_directorio_archivos(username)

            # Guardar archivos crudos originales
            if archivos_crudos:
                for archivo in archivos_crudos:
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

            # --- PASO INTERMEDIO: Filtro de Calidad Pos-Validación (Directiva 3) ---
            # Calcula el porcentaje de atributos faltantes de cada fila.
            # Elimina automáticamente los registros que tengan 50% o más de sus columnas en estado nulo/NaN.
            df_unificado, registros_eliminados = EstandarizadorDatos.filtrar_por_umbral_nulos(
                df_unificado, umbral_pct=0.50
            )

            if df_unificado.empty:
                st.error("⚠️ Todos los registros fueron eliminados porque tenían 50% o más de columnas nulas. No es posible continuar.")
                st.session_state.contrato_validado = False
                return

            if registros_eliminados > 0:
                st.info(
                    f"ℹ️ **Filtro de calidad pos-validación aplicado:** Se eliminaron {registros_eliminados} registro(s) "
                    f"que presentaban 50% o más de atributos faltantes/nulos. "
                    f"Continuando con {len(df_unificado)} registro(s) hacia el pipeline de limpieza."
                )

            if total_archivos >= 2:
                # Regla: Si se procesan 2 o más archivos, se guarda como archivo 'Unificado' ANTES de la limpieza
                nombre_guardar = nombre_archivo_nuevo.strip() if nombre_archivo_nuevo.strip() else "dataset_unificado"
                if not nombre_guardar.endswith(".csv"):
                    nombre_guardar = f"{nombre_guardar}.csv"
                ruta_unificado = os.path.join(directorio_guardado, nombre_guardar)
                df_unificado.to_csv(ruta_unificado, index=False)
                st.session_state.nombre_archivo_actual = nombre_guardar
                mensaje_exito = (
                    f"✅ ¡Contrato validado exitosamente! Se unificaron {total_archivos} archivo(s) "
                    f"y se guardó '{nombre_guardar}' en Archivos Unificados."
                )
            else:
                # Regla: Si se procesa un solo archivo, NO debe existir ni registrarse un archivo 'Unificado'.
                # Pasa directamente a limpieza.
                if archivos_crudos:
                    nombre_orig = archivos_crudos[0].name
                else:
                    nombre_orig = list(archivos_dfs.keys())[0] if archivos_dfs else "dataset_vuelos.csv"

                if nombre_orig.endswith((".xlsx", ".xltx", ".xltm", ".txt")):
                    nombre_orig = os.path.splitext(nombre_orig)[0] + ".csv"

                st.session_state.nombre_archivo_actual = nombre_orig
                mensaje_exito = (
                    f"✅ ¡Contrato validado exitosamente para '{nombre_orig}'! "
                    f"Avanzando directamente al pipeline de limpieza."
                )

            st.session_state.df_crudo = df_unificado
            nuevo_mapeo = {col: col for col in COLUMNAS_CANONICAS}
            st.session_state.mapeo_columnas = nuevo_mapeo
            st.session_state.contrato_validado = True
            st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(df_unificado)

            st.success(mensaje_exito)
        except ValueError as ve:
            st.session_state.contrato_validado = False
            st.error(f"Error de Contrato: {ve}")
        except Exception as e:
            st.session_state.contrato_validado = False
            st.error(f"Error crítico al validar contrato: {e}")
