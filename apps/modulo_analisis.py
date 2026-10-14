import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from typing import List, Dict, Any, Optional
from modules.Vuelos import Vuelo
from modules.fabrica_vuelos import FabricaVuelos
from modules.analisis_estadistico import MotorEstadisticoVuelos, SimuladorPreciosDinamicos
from modules.generador_pdf import GeneradorReportePDF


COLUMNAS_GRAFICOS = [
    "precio", "franja horaria", "estado", "capacidad_usada",
    "origen", "destino", "aeropuerto_origen", "aeropuerto_destino"
]


def resolver_columna(
    df: pd.DataFrame,
    atributo: str,
    mapeo: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Resuelve dinámicamente el nombre real de una columna en el DataFrame a partir de un
    atributo solicitado (canónico o personalizado), utilizando el mapeo activo del usuario,
    inspección directa o alias canónicos del dominio.
    """
    if df is None or not atributo:
        return None

    # 1. Coincidencia directa exacta
    if atributo in df.columns:
        return atributo

    # 2. Consultar mapeo activo del usuario (canónico -> columna real configurada)
    if mapeo:
        col_mapeada = mapeo.get(atributo)
        if col_mapeada and col_mapeada != "(No asignar)" and col_mapeada in df.columns:
            return col_mapeada

        # Búsqueda inversa: si el atributo proporcionado es el nombre real y buscamos la clave canónica
        for canon, real in mapeo.items():
            if real == atributo and canon in df.columns:
                return canon

    # 3. Coincidencia insensible a mayúsculas/minúsculas y espacios
    attr_lower = str(atributo).lower().strip()
    for col in df.columns:
        if str(col).lower().strip() == attr_lower:
            return col

    # 4. Alias y equivalencias estándar del modelo de dominio
    alias_dict = {
        "precio": ["precio", "precio_usd", "valor", "tarifa", "price"],
        "capacidad_usada": ["capacidad_usada", "capacidad_usada_avion", "capacidad_uso", "pasajeros", "ocupacion"],
        "capacidad_maxima": ["capacidad_maxima", "capacidad_maxima_avion", "capacidad_max", "capacidad"],
        "origen": ["origen", "lugar_origen", "pais_origen", "ciudad_origen", "aeropuerto_origen", "aero_orig"],
        "destino": ["destino", "lugar_destino", "pais_destino", "ciudad_destino", "aeropuerto_destino", "aero_dest"],
        "aeropuerto_origen": ["aeropuerto_origen", "aero_orig", "origen_aeropuerto", "origen"],
        "aeropuerto_destino": ["aeropuerto_destino", "aero_dest", "destino_aeropuerto", "destino"],
        "estado": ["estado", "estado_vuelo", "status", "flight_status"],
        "franja horaria": ["franja horaria", "franja", "franja_horaria", "horario"],
        "id_vuelo": ["id_vuelo", "codigo_vuelo", "vuelo", "flight_id", "id"]
    }

    if attr_lower in alias_dict:
        for alias in alias_dict[attr_lower]:
            if alias in df.columns:
                return alias
            if mapeo:
                col_m = mapeo.get(alias)
                if col_m and col_m in df.columns:
                    return col_m

    return None


def construir_dataframe_graficos(
    vuelos: List[Vuelo],
    df_fuente: Optional[pd.DataFrame] = None,
    mapeo: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Extrae las variables clave de la colección de vuelos en un DataFrame optimizado para gráficos.
    Garantiza que todas las columnas canónicas y las mapeadas existan en el resultado para prevenir KeyError.
    """
    datos = []
    if vuelos:
        for v in vuelos:
            est = v.normalizar_estado() if hasattr(v, "normalizar_estado") else str(getattr(v, "estado", "Desconocido"))
            orig = str(getattr(v, "origen", "") or "").strip()
            dest = str(getattr(v, "destino", "") or "").strip()
            ap_orig = str(getattr(v, "aeropuerto_origen", "") or "").strip()
            ap_dest = str(getattr(v, "aeropuerto_destino", "") or "").strip()

            val_orig = orig if (orig and orig != "Desconocido") else (ap_orig if (ap_orig and ap_orig != "Desconocido") else "Desconocido")
            val_dest = dest if (dest and dest != "Desconocido") else (ap_dest if (ap_dest and ap_dest != "Desconocido") else "Desconocido")
            val_ap_orig = ap_orig if (ap_orig and ap_orig != "Desconocido") else (orig if (orig and orig != "Desconocido") else "Desconocido")
            val_ap_dest = ap_dest if (ap_dest and ap_dest != "Desconocido") else (dest if (dest and dest != "Desconocido") else "Desconocido")

            franja = v.obtener_franja_horaria() if hasattr(v, "obtener_franja_horaria") else "Sin horario"

            datos.append({
                "precio": float(v.precio) if getattr(v, "precio", None) is not None else 0.0,
                "franja horaria": franja if franja and "Sin horario" not in franja else "Desconocido",
                "estado": est,
                "capacidad_usada": int(getattr(v, "capacidad_usada_avion", 0) or 0),
                "origen": val_orig,
                "destino": val_dest,
                "aeropuerto_origen": val_ap_orig,
                "aeropuerto_destino": val_ap_dest
            })

    if not datos and df_fuente is not None and not df_fuente.empty:
        # Fallback desde el DataFrame fuente si no hay lista_vuelos instanciados
        df_res = pd.DataFrame(index=df_fuente.index)
        for col_can in COLUMNAS_GRAFICOS:
            c_real = resolver_columna(df_fuente, col_can, mapeo)
            if c_real and c_real in df_fuente.columns:
                df_res[col_can] = df_fuente[c_real].values
            else:
                df_res[col_can] = 0.0 if col_can in ["precio", "capacidad_usada"] else "Desconocido"
    elif datos:
        df_res = pd.DataFrame(datos)
    else:
        df_res = pd.DataFrame(columns=COLUMNAS_GRAFICOS)

    # Asegurar presencia de todas las columnas canónicas
    for c in COLUMNAS_GRAFICOS:
        if c not in df_res.columns:
            df_res[c] = 0.0 if c in ["precio", "capacidad_usada"] else "Desconocido"

    # Si hay mapeo activo con nombres personalizados, crear columnas espejo para máxima compatibilidad
    if mapeo:
        for can_col, real_col in mapeo.items():
            if real_col and real_col != "(No asignar)" and real_col not in df_res.columns:
                col_origen = can_col if can_col in df_res.columns else resolver_columna(df_res, can_col, mapeo)
                if col_origen and col_origen in df_res.columns:
                    df_res[real_col] = df_res[col_origen]

    return df_res


def discretizar_variable_numerica(
    serie: pd.Series,
    nombre_col: str,
    num_bins: int = 5
) -> tuple[pd.Series, List[str]]:
    """
    Transforma una variable numérica continua en rangos discretos categóricos legibles y ordenados.
    Para 'precio': '$100 a $250'.
    Para 'capacidad_usada': '0 a 50 pas.'.
    """
    s_num = pd.to_numeric(serie, errors="coerce").fillna(0)
    v_min = float(s_num.min())
    v_max = float(s_num.max())

    if v_min == v_max or s_num.nunique() <= 1:
        etiqueta_unica = f"${int(round(v_min)):,}" if nombre_col == "precio" else f"{int(round(v_min))} pas."
        return pd.Series([etiqueta_unica] * len(serie), index=serie.index), [etiqueta_unica]

    cortes, bins_bordes = pd.cut(
        s_num,
        bins=num_bins,
        retbins=True,
        right=True,
        include_lowest=True
    )

    etiquetas_raw = []
    for i in range(len(bins_bordes) - 1):
        ini = int(round(bins_bordes[i]))
        fin = int(round(bins_bordes[i + 1]))
        if nombre_col == "precio":
            etiquetas_raw.append(f"${ini:,} a ${fin:,}")
        else:
            etiquetas_raw.append(f"{ini} a {fin} pas.")

    etiquetas_ordenadas: List[str] = []
    vistos = set()
    for lbl in etiquetas_raw:
        candidato = lbl
        sufijo = 2
        while candidato in vistos:
            candidato = f"{lbl} ({sufijo})"
            sufijo += 1
        vistos.add(candidato)
        etiquetas_ordenadas.append(candidato)

    serie_discreta = pd.cut(
        s_num,
        bins=bins_bordes,
        labels=etiquetas_ordenadas,
        include_lowest=True,
        right=True
    ).astype(str)

    return serie_discreta, etiquetas_ordenadas


def vista_analisis_estadistico(gestor_usr=None):
    """
    Vista principal de la sección de Análisis Estadístico y Simulación Comercial.
    Organizada mediante acordeones desplegables (st.expander) con títulos idénticos en formato,
    prioridad visual superior para la simulación, aislamiento estricto de elementos por archivo y
    exportación PDF consolidada con gráficos y tablas.
    """
    # ----------------------------------------------------------------------
    # Identificación y Aislamiento Estricto por Archivo Activo
    # ----------------------------------------------------------------------
    nombre_arch = st.session_state.get("nombre_archivo_actual", "Dataset Activo")

    if "guardados_por_archivo" not in st.session_state:
        st.session_state.guardados_por_archivo = {}

    if nombre_arch not in st.session_state.guardados_por_archivo:
        st.session_state.guardados_por_archivo[nombre_arch] = {
            "simulaciones": [],
            "graficos": [],
            "tablas_condicionales": []
        }

    # Contenedor de elementos guardados exclusivo para el dataset activo
    elementos_guardados = st.session_state.guardados_por_archivo[nombre_arch]

    # ----------------------------------------------------------------------
    # Estilos CSS Unificados para los Acordeones Desplegables
    # ----------------------------------------------------------------------
    st.markdown("""
    <style>
        div[data-testid="stExpander"] details summary p {
            font-size: 1.35rem !important;
            font-weight: 700 !important;
            color: #1E88E5 !important;
            margin: 0 !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid rgba(150, 150, 150, 0.3) !important;
            border-radius: 10px !important;
            margin-bottom: 1.2rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # ----------------------------------------------------------------------
    # Cabecera y Botón Obligatorio de Volver
    # ----------------------------------------------------------------------
    col_titulo, col_volver = st.columns([0.8, 0.2])
    with col_titulo:
        st.markdown('<h1 style="font-size: 2.2rem; margin-bottom: 0.2rem;">📈 Análisis Estadístico y Simulación Comercial</h1>', unsafe_allow_html=True)
        st.caption(f"Explorando datos de vuelos y modelo estocástico de precios dinámicos · Archivo activo: **{nombre_arch}**")
    with col_volver:
        st.write("")  # Espaciador vertical
        if st.button("⬅️ Volver", key="btn_volver_analisis", use_container_width=True):
            st.session_state.mostrar_analisis = False
            st.rerun()

    st.divider()

    # ----------------------------------------------------------------------
    # Verificación de Colección de Objetos Vuelo
    # ----------------------------------------------------------------------
    lista_vuelos: List[Vuelo] = st.session_state.get("lista_vuelos", [])

    if not lista_vuelos:
        df_limpio = st.session_state.get("df_limpio")
        if df_limpio is not None and not df_limpio.empty:
            try:
                mapeo = st.session_state.get("mapeo_columnas", {})
                df_para_vuelos = df_limpio.copy()
                col_p = mapeo.get("precio") or ("precio" if "precio" in df_para_vuelos.columns else None)
                if col_p and col_p in df_para_vuelos.columns:
                    s_p = pd.to_numeric(df_para_vuelos[col_p], errors="coerce")
                    nulos_p = s_p.isna() | (s_p < 0)
                    if nulos_p.any():
                        df_para_vuelos = df_para_vuelos[~nulos_p].copy().reset_index(drop=True)
                lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_para_vuelos, mapeo)
                st.session_state.lista_vuelos = lista_vuelos
            except Exception as e:
                st.error(f"Error al instanciar objetos Vuelo desde el DataFrame limpio: {e}")
                st.warning("Verifique que todos los registros cuenten con un valor de 'precio' obligatorio.")
                return

    if not lista_vuelos:
        st.warning("⚠️ No hay vuelos limpios cargados actualmente en memoria.")
        st.info("Seleccione un archivo limpio desde 'Mis Archivos Guardados' en su perfil para iniciar el análisis.")
        if st.button("Ir al Inicio / Ingestión", use_container_width=True):
            st.session_state.mostrar_analisis = False
            st.session_state.modo_limpieza_directa = False
            st.session_state.df_crudo = None
            st.session_state.contrato_validado = False
            st.rerun()
        return

    # Inicialización del motor estadístico y del simulador
    try:
        motor = MotorEstadisticoVuelos(lista_vuelos)
        simulador = SimuladorPreciosDinamicos(motor)
        df_fuente = st.session_state.get("df_limpio")
        mapeo_activo = st.session_state.get("mapeo_columnas", {})
        df_graficos = construir_dataframe_graficos(lista_vuelos, df_fuente=df_fuente, mapeo=mapeo_activo)
    except Exception as e:
        st.error(f"Error al inicializar el motor estadístico: {e}")
        return

    # ======================================================================
    # SECCIÓN 1 (Prioridad Visual Superior):
    # 🎯 Módulo de Simulación Comercial y Precios Dinámicos
    # ======================================================================
    with st.expander("🎯 Módulo de Simulación Comercial y Precios Dinámicos", expanded=True):
        st.write(
            "Ajuste y simule precios dinámicos basados en el **riesgo operativo logístico** (probabilidades de retraso y cancelación), "
            "la presión de ocupación y los costos de contingencia calculados a partir de los vuelos reales."
        )

        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        rutas_disp = ["Todas las rutas"] + motor.obtener_rutas_disponibles()
        franjas_disp = ["Todas las franjas"] + motor.obtener_franjas_disponibles()
        ocupaciones_disp = ["Cualquier ocupación"] + motor.obtener_ocupaciones_disponibles()

        with col_ctrl1:
            sel_ruta = st.selectbox("🗺️ Seleccionar Ruta (Origen -> Destino):", options=rutas_disp, index=0)
        with col_ctrl2:
            sel_franja = st.selectbox("⏰ Seleccionar Franja Horaria:", options=franjas_disp, index=0)
        with col_ctrl3:
            sel_ocupacion = st.selectbox("👥 Nivel de Ocupación de Aeronave:", options=ocupaciones_disp, index=0)

        # Parámetros avanzados de la simulación
        with st.expander("⚙️ Parámetros Avanzados de Costos y Margen Comercial", expanded=False):
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)
            with col_p1:
                costo_retraso = st.slider("Sobrecosto por Retraso (%):", min_value=5, max_value=60, value=25, step=5) / 100.0
            with col_p2:
                costo_cancelacion = st.slider("Sobrecosto por Cancelación (%):", min_value=10, max_value=100, value=60, step=5) / 100.0
            with col_p3:
                margen_comercial = st.slider("Margen Objetivo (%):", min_value=0, max_value=40, value=10, step=1) / 100.0
            with col_p4:
                usar_precio_manual = st.checkbox("Ingresar precio base manual", value=False)
                precio_manual = None
                if usar_precio_manual:
                    precio_manual = st.number_input("Precio Base Manual ($):", min_value=1.0, value=250.0, step=10.0)

        # Ejecución del modelo de simulación
        resultado_sim = simulador.simular(
            ruta=sel_ruta,
            franja=sel_franja,
            ocupacion=sel_ocupacion,
            precio_base_manual=precio_manual,
            costo_retraso_pct=costo_retraso,
            costo_cancelacion_pct=costo_cancelacion,
            margen_comercial_pct=margen_comercial
        )

        # Métricas de salida en tarjetas visuales de alto impacto
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        with col_m1:
            st.metric("Precio Base", f"${resultado_sim['precio_base']:,.2f}", help=resultado_sim['tipo_precio_base'])
        with col_m2:
            st.metric("P(Atraso)", f"{resultado_sim['p_atrasado_pct']}%", help="Probabilidad condicionada de retraso")
        with col_m3:
            st.metric("P(Cancelación)", f"{resultado_sim['p_cancelado_pct']}%", help="Probabilidad condicionada de cancelación")
        with col_m4:
            st.metric("Riesgo Logístico", f"{resultado_sim['riesgo_logistico_pct']}%", delta=f"+${resultado_sim['recargo_riesgo_monetario']:,.2f}")
        with col_m5:
            st.metric(
                "✨ Precio Dinámico Sugerido",
                f"${resultado_sim['precio_sugerido']:,.2f}",
                delta=f"+{resultado_sim['ajuste_porcentual_total']}% (${resultado_sim['ajuste_total_monetario']:,.2f})"
            )

        # Diagnóstico Comercial con formato de moneda limpio y seguro contra KaTeX
        st.info(
            f"💡 **Diagnóstico Comercial:** Para el segmento seleccionado "
            f"(Muestra: {resultado_sim['muestra_tamano']} vuelos), "
            f"el modelo detecta un riesgo operativo del **{resultado_sim['riesgo_logistico_pct']}%** "
            f"(P(Atraso)={resultado_sim['p_atrasado_pct']}%, P(Cancelación)={resultado_sim['p_cancelado_pct']}%). "
            f"El precio dinámico sugerido de **\\${resultado_sim['precio_sugerido']:,.2f}** incluye un recargo de "
            f"cobertura de **\\${resultado_sim['recargo_riesgo_monetario']:,.2f}** por pasaje, generando un fondo de contingencia "
            f"estimado de **\\${resultado_sim['fondo_contingencia_vuelo']:,.2f}** por vuelo para absorber ineficiencias logísticas "
            f"e indemnizaciones."
        )

        # ------------------------------------------------------------------
        # Botón Explícito de Guardado de Simulación (Patrón Command)
        # ------------------------------------------------------------------
        col_btn_sim, col_espacio_sim = st.columns([0.35, 0.65])
        with col_btn_sim:
            if st.button("💾 Guardar Simulación", key="btn_guardar_simulacion", use_container_width=True):
                # Obtener el nombre real y limpio del archivo activo
                nombre_real = st.session_state.get("nombre_archivo_actual")
                if not nombre_real or str(nombre_real).strip() in ["", "None", "Dataset Activo", "Archivo desconocido"]:
                    nombre_real = "dataset_vuelos.csv"
                else:
                    nombre_real = str(nombre_real).strip()

                # 1. Registro en la sesión persistente del usuario (si está autenticado)
                usr = st.session_state.get("usuario_activo")
                desc_sim = f"Simulación en ruta {resultado_sim['ruta']} | Precio sugerido: ${resultado_sim['precio_sugerido']:,.2f}"
                if usr and gestor_usr:
                    usr.sesion.registrar_comando(
                        accion=desc_sim,
                        parametros={
                            "tipo_operacion": "SimulacionComercial",
                            "archivos": nombre_real,
                            "archivo": nombre_real,
                            "ruta": resultado_sim["ruta"],
                            "franja": resultado_sim["franja"],
                            "ocupacion": resultado_sim["ocupacion"],
                            "precio_base": resultado_sim["precio_base"],
                            "precio_sugerido": resultado_sim["precio_sugerido"],
                            "riesgo_logistico_pct": resultado_sim["riesgo_logistico_pct"],
                            "fondo_contingencia_vuelo": resultado_sim["fondo_contingencia_vuelo"]
                        }
                    )
                    gestor_usr.guardar_usuario(usr)

                # 2. Registro en la lista aislada de este archivo para exportación PDF
                elementos_guardados["simulaciones"].append(resultado_sim.copy())

                # Mensaje de confirmación estructurado con punto y aparte
                st.success(
                    f"✅ Simulación en ruta **{resultado_sim['ruta']}** | Precio sugerido: **\\${resultado_sim['precio_sugerido']:,.2f}**.\n\n"
                    f"Guardada exitosamente en el historial y en el informe PDF."
                )

    # ======================================================================
    # SECCIÓN 2:
    # 📊 Probabilidades Condicionales Cruzadas (Incluye Gráficos Interactivos)
    # ======================================================================
    with st.expander("📊 Probabilidades Condicionales Cruzadas", expanded=False):
        st.write("Análisis cruzado del comportamiento operativo y tarifas por variables clave:")

        # ------------------------------------------------------------------
        # Bloque de Gráficos Interactivos
        # ------------------------------------------------------------------
        st.markdown('<h3 style="font-size: 1.3rem; color: #1E88E5; margin-top: 0.5rem; margin-bottom: 0.5rem;">📊 Visualización Gráfica Interactiva</h3>', unsafe_allow_html=True)
        st.write("Seleccione el tipo de gráfico y configure las variables a cruzar para analizar patrones y correlaciones:")

        tipo_grafico = st.radio(
            "Seleccionar tipo de gráfico:",
            options=["Gráfico de Barras", "Gráfico de Torta"],
            horizontal=True,
            key="radio_tipo_grafico_analisis"
        )

        if tipo_grafico == "Gráfico de Barras":
            c_sel_a, c_sel_b = st.columns(2)
            with c_sel_a:
                attr_a = st.selectbox(
                    "Atributo A (Eje X / Principal):",
                    options=["precio", "franja horaria", "estado", "capacidad_usada"],
                    index=2,  # 'estado' por defecto
                    key="sel_attr_a_barras"
                )
            with c_sel_b:
                attr_b = st.selectbox(
                    "Atributo B (Comparación / Agrupación):",
                    options=["origen", "destino", "aeropuerto_origen", "aeropuerto_destino"],
                    index=0,  # 'origen' por defecto
                    key="sel_attr_b_barras"
                )

            # Preparación de datos para gráfico de barras
            df_plot = df_graficos.copy()

            mapeo_activo = st.session_state.get("mapeo_columnas", {})

            # Resolver dinámicamente nombres reales de columna en df_plot usando mapeo y alias
            col_a_real = resolver_columna(df_plot, attr_a, mapeo_activo) or attr_a
            col_b_real = resolver_columna(df_plot, attr_b, mapeo_activo) or attr_b

            # Garantizar que las columnas existan en df_plot para prevenir cualquier KeyError
            if col_a_real not in df_plot.columns:
                df_plot[col_a_real] = 0.0 if attr_a in ["precio", "capacidad_usada"] else "Desconocido"
            if col_b_real not in df_plot.columns:
                df_plot[col_b_real] = "Desconocido"

            titulo_a = attr_a.replace('_', ' ').capitalize()
            titulo_b = attr_b.replace('_', ' ').capitalize()

            # 1. Transformación de Atributo A: variables numéricas en rangos discretos legibles
            if attr_a in ["precio", "capacidad_usada"] or col_a_real in ["precio", "capacidad_usada"]:
                serie_discreta, orden_a = discretizar_variable_numerica(df_plot[col_a_real], attr_a, num_bins=5)
                df_plot[f"{attr_a}_display"] = serie_discreta
                col_a_plot = f"{attr_a}_display"
            else:
                col_a_plot = f"{attr_a}_display"
                df_plot[col_a_plot] = df_plot[col_a_real]
                if attr_a == "estado" or col_a_real == "estado":
                    orden_a = ["A tiempo", "Exitoso", "Atrasado", "Cancelado"]
                elif attr_a == "franja horaria" or col_a_real == "franja horaria":
                    orden_a = [
                        "Madrugada (00:00 - 06:00)",
                        "Mañana (06:00 - 12:00)",
                        "Tarde (12:00 - 18:00)",
                        "Noche (18:00 - 24:00)"
                    ]
                else:
                    orden_a = df_plot[col_a_real].value_counts().index.tolist()

            # 2. Limitación de categorías de Atributo B: Top 5 + "Otros"
            serie_b = df_plot[col_b_real]
            conteos_b = serie_b[serie_b != "Desconocido"].value_counts() if (serie_b != "Desconocido").any() else serie_b.value_counts()
            if len(conteos_b) > 5:
                top_5 = conteos_b.nlargest(5).index.tolist()
                df_plot[f"{attr_b}_display"] = serie_b.apply(lambda x: x if x in top_5 else "Otros")
                orden_b = top_5 + ["Otros"]
            else:
                df_plot[f"{attr_b}_display"] = serie_b
                orden_b = conteos_b.index.tolist() if not conteos_b.empty else ["Sin datos"]

            # 3. Pre-agregación para conteos exactos y renderizado de barras agrupadas lado a lado (Side-by-Side)
            df_barras = df_plot.groupby([col_a_plot, f"{attr_b}_display"]).size().reset_index(name="Cantidad de Vuelos")

            # Orientación horizontal de etiquetas del eje X con labelAngle=0
            chart_barras = alt.Chart(df_barras).mark_bar().encode(
                x=alt.X(
                    f"{col_a_plot}:N",
                    title=titulo_a,
                    sort=orden_a,
                    axis=alt.Axis(labelAngle=0, labelLimit=250)
                ),
                y=alt.Y("Cantidad de Vuelos:Q", title="Cantidad de Vuelos", stack=None),
                color=alt.Color(
                    f"{attr_b}_display:N",
                    title=f"{titulo_b} (Top 5 + Otros)",
                    scale=alt.Scale(scheme='tableau10'),
                    sort=orden_b
                ),
                xOffset=alt.XOffset(f"{attr_b}_display:N", sort=orden_b),
                tooltip=[
                    alt.Tooltip(f"{col_a_plot}:N", title=titulo_a),
                    alt.Tooltip(f"{attr_b}_display:N", title=titulo_b),
                    alt.Tooltip("Cantidad de Vuelos:Q", title="Cantidad de Vuelos")
                ]
            ).properties(height=430)

            st.altair_chart(chart_barras, use_container_width=True)

            tabla_contingencia = pd.crosstab(
                df_plot[col_a_plot],
                df_plot[f"{attr_b}_display"],
                margins=True,
                margins_name="Total"
            )

            with st.expander(f"📋 Ver tabla de contingencia: {titulo_a} vs {titulo_b}", expanded=True):
                st.dataframe(tabla_contingencia, use_container_width=True)

            # Botón de guardado para Gráfico de Barras
            col_btn_gb, col_esp_gb = st.columns([0.35, 0.65])
            with col_btn_gb:
                if st.button("💾 Guardar Gráfico de Barras y Tabla", key="btn_guardar_grafico_barras", use_container_width=True):
                    elementos_guardados["graficos"].append({
                        "titulo": f"Gráfico de Barras: {titulo_a} vs {titulo_b}",
                        "tipo": "Gráfico de Barras",
                        "descripcion": f"Eje X: {titulo_a} | Agrupación: {titulo_b} (Top 5 + Otros)",
                        "tabla": tabla_contingencia.reset_index()
                    })
                    st.success(f"✅ Gráfico de barras ({titulo_a} vs {titulo_b}) y tabla de contingencia guardados para el reporte PDF.")

        else:
            # --------------------------------------------------------------
            # Gráfico de Torta con límite estricto de 10 atributos,
            # multiselect interactivo, agrupación en 'Otros' y tabla adjunta
            # --------------------------------------------------------------
            attr_torta = st.selectbox(
                "Seleccionar atributo a visualizar en el Gráfico de Torta:",
                options=["estado", "franja horaria", "origen", "destino", "aeropuerto_origen", "aeropuerto_destino"],
                index=0,
                key="sel_attr_torta_pie"
            )

            col_torta_nombre = attr_torta.replace('_', ' ').capitalize()
            mapeo_activo = st.session_state.get("mapeo_columnas", {})
            col_torta_real = resolver_columna(df_graficos, attr_torta, mapeo_activo) or attr_torta
            if col_torta_real in df_graficos.columns:
                s_torta = df_graficos[col_torta_real].dropna()
            else:
                s_torta = pd.Series(["Desconocido"] * len(df_graficos), index=df_graficos.index)

            if (s_torta != "Desconocido").any():
                s_torta = s_torta[s_torta != "Desconocido"]

            conteos_cat = s_torta.value_counts()
            categorias_disponibles = conteos_cat.index.tolist()
            if not categorias_disponibles:
                categorias_disponibles = ["Sin datos"]
                s_torta = pd.Series(["Sin datos"], index=[0])

            # Límite estricto de 10 atributos a la vez
            max_sel = 9 if len(categorias_disponibles) > 10 else min(10, len(categorias_disponibles))
            default_sel = categorias_disponibles[:max_sel]

            cat_seleccionadas = st.multiselect(
                f"Seleccionar categorías de {col_torta_nombre} a graficar (máximo 10):",
                options=categorias_disponibles,
                default=default_sel,
                max_selections=10,
                key=f"mselect_torta_{attr_torta}"
            )

            if not cat_seleccionadas:
                cat_seleccionadas = default_sel

            # Clasificación automática en "Otros" para categorías no seleccionadas
            s_torta_mapeada = s_torta.apply(lambda x: x if x in cat_seleccionadas else "Otros")
            df_torta_final = s_torta_mapeada.value_counts().reset_index()
            df_torta_final.columns = [col_torta_nombre, "Cantidad"]
            df_torta_final["Porcentaje"] = (df_torta_final["Cantidad"] / df_torta_final["Cantidad"].sum()) * 100.0

            # Si 'Otros' está presente, ubicarlo al final de la tabla y leyenda
            if "Otros" in df_torta_final[col_torta_nombre].values:
                fila_otros = df_torta_final[df_torta_final[col_torta_nombre] == "Otros"]
                df_torta_final = pd.concat([
                    df_torta_final[df_torta_final[col_torta_nombre] != "Otros"],
                    fila_otros
                ]).reset_index(drop=True)

            c_torta_ctrl, c_torta_plot = st.columns([0.45, 0.55])
            with c_torta_ctrl:
                st.write(f"**Tabla Detallada de Porcentajes ({col_torta_nombre}):**")
                st.dataframe(
                    df_torta_final.style.format({"Porcentaje": "{:.2f}%", "Cantidad": "{:,}"}),
                    use_container_width=True
                )

            with c_torta_plot:
                chart_pie = alt.Chart(df_torta_final).mark_arc(innerRadius=45).encode(
                    theta=alt.Theta(field="Cantidad", type="quantitative"),
                    color=alt.Color(
                        field=col_torta_nombre,
                        type="nominal",
                        title=col_torta_nombre,
                        scale=alt.Scale(scheme='tableau10'),
                        sort=df_torta_final[col_torta_nombre].tolist()
                    ),
                    tooltip=[
                        alt.Tooltip(f"{col_torta_nombre}:N", title="Categoría"),
                        alt.Tooltip("Cantidad:Q", title="Vuelos", format=","),
                        alt.Tooltip("Porcentaje:Q", title="% del Total", format=".2f")
                    ]
                ).properties(height=380)
                st.altair_chart(chart_pie, use_container_width=True)

            # Botón de guardado para Gráfico de Torta
            col_btn_gt, col_esp_gt = st.columns([0.35, 0.65])
            with col_btn_gt:
                if st.button("💾 Guardar Gráfico de Torta y Tabla", key="btn_guardar_grafico_torta", use_container_width=True):
                    elementos_guardados["graficos"].append({
                        "titulo": f"Gráfico de Torta: Distribución de {col_torta_nombre}",
                        "tipo": "Gráfico de Torta",
                        "descripcion": f"Categorías visualizadas: {len(df_torta_final)} (máx. 10 + Otros)",
                        "tabla": df_torta_final
                    })
                    st.success(f"✅ Gráfico de torta de {col_torta_nombre} y tabla adjunta guardados para el reporte PDF.")

        st.divider()

        # ------------------------------------------------------------------
        # Tablas Detalladas de Probabilidades Condicionales
        # ------------------------------------------------------------------
        st.markdown('<h3 style="font-size: 1.3rem; color: #1E88E5; margin-bottom: 0.5rem;">📋 Tablas de Probabilidades Condicionales</h3>', unsafe_allow_html=True)
        tab_franja, tab_ruta, tab_ocupacion = st.tabs([
            "⏰ Franja Horaria de Salida",
            "🗺️ Rutas (Origen -> Destino)",
            "👥 Nivel de Ocupación de Aeronave"
        ])

        with tab_franja:
            st.markdown("#### P(Estado | Franja Horaria)")
            df_franja = motor.calcular_probabilidades_condicionales_franja()
            if not df_franja.empty:
                st.dataframe(df_franja, use_container_width=True)
            else:
                st.info("No hay información temporal suficiente para clasificar por franja horaria.")

        with tab_ruta:
            st.markdown("#### P(Estado | Ruta)")
            df_ruta = motor.calcular_probabilidades_condicionales_ruta()
            if not df_ruta.empty:
                st.dataframe(df_ruta, use_container_width=True)
            else:
                st.info("No hay información de rutas disponible.")

        with tab_ocupacion:
            st.markdown("#### P(Estado | Nivel de Ocupación)")
            df_ocup = motor.calcular_probabilidades_condicionales_ocupacion()
            if not df_ocup.empty:
                st.dataframe(df_ocup, use_container_width=True)
            else:
                st.info("No hay información de ocupación disponible.")

        # Botón interno de guardado de tablas condicionales
        col_btn_tc, col_esp_tc = st.columns([0.35, 0.65])
        with col_btn_tc:
            if st.button("💾 Guardar Tablas Condicionales", key="btn_guardar_tablas_cond", use_container_width=True):
                if not df_franja.empty:
                    elementos_guardados["tablas_condicionales"].append({
                        "tipo": "Tabla Condicional: P(Estado | Franja Horaria)",
                        "dataframe": df_franja
                    })
                if not df_ruta.empty:
                    elementos_guardados["tablas_condicionales"].append({
                        "tipo": "Tabla Condicional: P(Estado | Ruta)",
                        "dataframe": df_ruta
                    })
                if not df_ocup.empty:
                    elementos_guardados["tablas_condicionales"].append({
                        "tipo": "Tabla Condicional: P(Estado | Nivel de Ocupación)",
                        "dataframe": df_ocup
                    })
                st.success("✅ Tablas de probabilidades condicionales guardadas para el reporte PDF.")

    # ======================================================================
    # EXPORTACIÓN GLOBAL DE RESULTADOS A PDF ESTRUCTURADO (Fuera de Acordeones)
    # ======================================================================
    st.divider()
    st.markdown('<h2 style="font-size: 1.6rem; color: #0D47A1; margin-bottom: 0.3rem;">📄 Exportación de Informe Ejecutivo (PDF)</h2>', unsafe_allow_html=True)
    st.write(
        f"Genere un reporte ejecutivo consolidado en formato PDF basado **únicamente en los elementos guardados manualmente** "
        f"para el dataset **'{nombre_arch}'**. El informe respeta la estructura formal en 3 secciones independientes:"
    )

    n_sims = len(elementos_guardados["simulaciones"])
    n_grafs = len(elementos_guardados["graficos"])
    n_tabs = len(elementos_guardados["tablas_condicionales"])
    total_guardados = n_sims + n_grafs + n_tabs

    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        st.metric("Simulaciones Comerciales", f"{n_sims} guardadas")
    with col_stat2:
        st.metric("Gráficos y Visualizaciones", f"{n_grafs} guardados")
    with col_stat3:
        st.metric("Tablas Condicionales", f"{n_tabs} guardadas")
    with col_stat4:
        st.metric("Total Elementos a Exportar", f"{total_guardados} elementos")

    if total_guardados == 0:
        st.info(
            f"ℹ️ Aún no ha guardado ningún elemento para el reporte del archivo **'{nombre_arch}'**. "
            "Utilice los botones **'💾 Guardar...'** presentes en cada sección para seleccionar "
            "las simulaciones comerciales, gráficos y tablas condicionales que desea incluir en el PDF final."
        )
    else:
        col_down1, col_down2 = st.columns([0.4, 0.6])
        with col_down1:
            usr_actual = st.session_state.get("usuario_activo")
            nombre_usr = usr_actual.username if usr_actual else "Analista Comercial"

            generador_pdf = GeneradorReportePDF(
                simulaciones=elementos_guardados["simulaciones"],
                graficos=elementos_guardados["graficos"],
                tablas_condicionales=elementos_guardados["tablas_condicionales"],
                nombre_dataset=nombre_arch,
                usuario=nombre_usr
            )

            try:
                archivo_pdf = generador_pdf.construir_pdf()
                nombre_descarga = f"Reporte_Analisis_{nombre_arch}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                st.download_button(
                    label="📥 Exportar Resultados (PDF)",
                    data=archivo_pdf,
                    file_name=nombre_descarga,
                    mime="application/pdf",
                    use_container_width=True,
                    key="btn_descargar_pdf_global"
                )
            except Exception as e:
                st.error(f"Error al compilar el informe PDF: {e}")

        with col_down2:
            if st.button("🗑️ Limpiar Elementos Guardados de este Archivo", key="btn_limpiar_elementos_pdf"):
                st.session_state.guardados_por_archivo[nombre_arch] = {
                    "simulaciones": [],
                    "graficos": [],
                    "tablas_condicionales": []
                }
                st.rerun()
