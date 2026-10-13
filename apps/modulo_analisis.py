import streamlit as st
import pandas as pd
from typing import List
from modules.Vuelos import Vuelo
from modules.fabrica_vuelos import FabricaVuelos
from modules.analisis_estadistico import MotorEstadisticoVuelos, SimuladorPreciosDinamicos


def vista_analisis_estadistico(gestor_usr=None):
    """
    Vista principal de la sección de Análisis Estadístico y Simulación Comercial.
    Cumple con la prioridad visual: la simulación comercial y precios dinámicos
    aparece en primer lugar en la parte superior de la pantalla.
    """
    # ----------------------------------------------------------------------
    # Cabecera y Botón Obligatorio de Volver
    # ----------------------------------------------------------------------
    col_titulo, col_volver = st.columns([0.8, 0.2])
    with col_titulo:
        st.markdown('<h1 style="font-size: 2.2rem; margin-bottom: 0.2rem;">📈 Análisis Estadístico y Simulación Comercial</h1>', unsafe_allow_html=True)
        nombre_arch = st.session_state.get("nombre_archivo_actual", "Dataset Activo")
        st.caption(f"Explorando datos de vuelos y modelo estocástico de precios dinámicos · Archivo: **{nombre_arch}**")
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
        # Intento de instanciación automática si existe df_limpio
        df_limpio = st.session_state.get("df_limpio")
        if df_limpio is not None and not df_limpio.empty:
            try:
                mapeo = st.session_state.get("mapeo_columnas", {})
                lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, mapeo)
                st.session_state.lista_vuelos = lista_vuelos
            except Exception as e:
                st.error(f"Error al instanciar objetos Vuelo desde el DataFrame limpio: {e}")
                st.warning("Verifique que todos los registros cuenten con un valor de 'precio' obligatorio.")
                return

    if not lista_vuelos:
        st.warning("⚠️ No hay vuelos limpios cargados actualmente en memoria.")
        st.info("Puede seleccionar un archivo limpio desde su perfil en 'Mis Archivos Guardados' o procesar un archivo desde el inicio.")
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
    except Exception as e:
        st.error(f"Error al inicializar el motor estadístico: {e}")
        return

    # ----------------------------------------------------------------------
    # 1. PRIORIDAD VISUAL: Módulo de Simulación Comercial y Precios Dinámicos
    # (Lo primero que aparece en la parte superior)
    # ----------------------------------------------------------------------
    st.markdown('<h2 style="font-size: 1.6rem; color: #1E88E5;">🎯 Módulo de Simulación Comercial y Precios Dinámicos</h2>', unsafe_allow_html=True)
    st.write(
        "Ajuste y simule precios dinámicos basados en el **riesgo operativo logístico** (probabilidades de retraso y cancelación), "
        "la presión de ocupación y los costos de contingencia calculados a partir de los vuelos reales."
    )

    with st.container():
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

        # Ejecución de la simulación
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

        # Resumen explicativo de la estrategia comercial
        st.info(
            f"💡 **Diagnóstico Comercial:** Para el segmento seleccionado "
            f"(Muestra: {resultado_sim['muestra_tamano']} vuelos), "
            f"el modelo detecta un riesgo operativo del **{resultado_sim['riesgo_logistico_pct']}%** "
            f"(P(Atraso)={resultado_sim['p_atrasado_pct']}%, P(Cancelación)={resultado_sim['p_cancelado_pct']}%). "
            f"El precio dinámico sugerido de **${resultado_sim['precio_sugerido']:,.2f}** incluye un recargo de "
            f"cobertura de **${resultado_sim['recargo_riesgo_monetario']:,.2f}** por pasaje, generando un fondo de contingencia "
            f"estimado de **${resultado_sim['fondo_contingencia_vuelo']:,.2f}** por vuelo para absorber ineficiencias logísticas "
            f"e indemnizaciones."
        )

    st.divider()

    # ----------------------------------------------------------------------
    # 2. Probabilidades Marginales Globales del Dataset
    # ----------------------------------------------------------------------
    st.markdown('<h2 style="font-size: 1.5rem;">🌐 Probabilidades Marginales Globales</h2>', unsafe_allow_html=True)
    st.write(f"Distribución no condicionada de estados en la flota total (**{motor.total_vuelos:,} vuelos analizados**):")

    prob_marg = motor.calcular_probabilidades_marginales()
    conteos_marg = motor.calcular_conteos_marginales()

    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    with col_g1:
        st.metric("P(A tiempo)", f"{prob_marg.get('A tiempo', 0.0) * 100:.2f}%", f"{conteos_marg.get('A tiempo', 0):,} vuelos")
    with col_g2:
        st.metric("P(Exitoso)", f"{prob_marg.get('Exitoso', 0.0) * 100:.2f}%", f"{conteos_marg.get('Exitoso', 0):,} vuelos")
    with col_g3:
        st.metric("P(Atrasado)", f"{prob_marg.get('Atrasado', 0.0) * 100:.2f}%", f"{conteos_marg.get('Atrasado', 0):,} vuelos", delta_color="inverse")
    with col_g4:
        st.metric("P(Cancelado)", f"{prob_marg.get('Cancelado', 0.0) * 100:.2f}%", f"{conteos_marg.get('Cancelado', 0):,} vuelos", delta_color="inverse")

    # Gráfico de barras de distribución marginal
    df_chart_marg = pd.DataFrame({
        "Estado": ["A tiempo", "Exitoso", "Atrasado", "Cancelado", "Desconocido"],
        "Probabilidad (%)": [
            round(prob_marg.get("A tiempo", 0.0) * 100, 2),
            round(prob_marg.get("Exitoso", 0.0) * 100, 2),
            round(prob_marg.get("Atrasado", 0.0) * 100, 2),
            round(prob_marg.get("Cancelado", 0.0) * 100, 2),
            round(prob_marg.get("Desconocido", 0.0) * 100, 2),
        ]
    }).set_index("Estado")
    st.bar_chart(df_chart_marg, use_container_width=True)

    st.divider()

    # ----------------------------------------------------------------------
    # 3. Probabilidades Condicionales Cruzadas
    # ----------------------------------------------------------------------
    st.markdown('<h2 style="font-size: 1.5rem;">📊 Probabilidades Condicionales Cruzadas</h2>', unsafe_allow_html=True)
    st.write("Análisis cruzado del comportamiento operativo y tarifas por variables clave:")

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
