import streamlit as st
from modules.calidad import ReporteCalidad, AnalizadorDuplicados
from modules.pipeline_limpieza import (
    PipelineLimpieza, SaneadorCategoricos, SaneadorUbicaciones,
    ImputadorMedianaGlobal, ImputadorMedianaPorGrupo,
    ImputadorCapacidadesPorFactorOcupacion, ImputadorEstadoInteligente,
    GeneradorIdVuelo
)
from modules.fabrica_vuelos import FabricaVuelos

def modulo_limpieza_y_dominio(gestor_usr):
    if st.session_state.get("df_crudo") is None or not st.session_state.get("contrato_validado"):
        return

    st.divider()
    st.markdown('<h2 style="font-size: 1.8rem;">Reporte de Diagnóstico de Calidad</h2>', unsafe_allow_html=True)

    df_norm = st.session_state.df_estandarizado
    mapeo = st.session_state.mapeo_columnas

    generador_reporte = ReporteCalidad(df_norm, mapeo)
    df_reporte = generador_reporte.generar()
    total_duplicados = AnalizadorDuplicados.contar(df_norm)

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Registros analizados", len(df_norm))
    col_m2.metric("Registros duplicados totales", total_duplicados)
    st.dataframe(df_reporte, use_container_width=True)

    st.markdown('<h3 style="font-size: 1.4rem;">Tratamiento de Anomalías y Valores Nulos</h3>', unsafe_allow_html=True)

    total_filas = len(df_norm)

    # =========================================================================
    # DETECCIÓN DE ANOMALÍAS PARA RENDERIZADO CONDICIONAL (REQ-01)
    # =========================================================================
    # Capacidades
    col_cmax = mapeo.get("capacidad_maxima_avion") if mapeo.get("capacidad_maxima_avion") != "(No asignar)" else None
    col_cusada = mapeo.get("capacidad_usada_avion") if mapeo.get("capacidad_usada_avion") != "(No asignar)" else None
    nulls_cmax = int(df_norm[col_cmax].isna().sum()) if col_cmax and col_cmax in df_norm.columns else 0
    nulls_cusada = int(df_norm[col_cusada].isna().sum()) if col_cusada and col_cusada in df_norm.columns else 0
    hay_problema_capacidades = (nulls_cmax > 0) or (nulls_cusada > 0)

    # Precio
    col_precio = mapeo.get("precio") if mapeo.get("precio") != "(No asignar)" else None
    nulls_precio = int(df_norm[col_precio].isna().sum()) if col_precio and col_precio in df_norm.columns else 0
    hay_problema_precio = (nulls_precio > 0)

    # ID de Vuelo
    col_id_asignada = mapeo.get("id_vuelo")
    col_id_real = col_id_asignada if (col_id_asignada and col_id_asignada != "(No asignar)") else ("id_vuelo" if "id_vuelo" in df_norm.columns else None)
    nulls_id = 0
    if col_id_real and col_id_real in df_norm.columns:
        serie_id = df_norm[col_id_real].astype(str).str.strip().str.lower()
        nulls_id = int((df_norm[col_id_real].isna() | serie_id.isin(["", "nan", "none", "null", "n/a", "nat"])).sum())
    hay_problema_id = (nulls_id > 0)

    # Variables de selección
    opcion_capacidades = "No modificar"
    opcion_precio = "No modificar (mantener nulos)"
    opcion_id = "No autogenerar (mantener valores originales / nulos)"

    # =========================================================================
    # 1. CAPACIDADES (SOLO SI HAY PROBLEMAS - REQ 01 Y 02)
    # =========================================================================
    if (col_cmax or col_cusada) and hay_problema_capacidades:
        st.markdown('<h4 style="font-size: 1.25rem; margin-top: 1rem;">Capacidades de Aeronaves</h4>', unsafe_allow_html=True)
        imputador_temp = ImputadorCapacidadesPorFactorOcupacion(col_cmax or "", col_cusada or "")
        factor_detectado = imputador_temp.calcular_factor_promedio(df_norm)

        filas_incompletas = (df_norm[col_cmax].isna() | df_norm[col_cusada].isna()) if (col_cmax and col_cusada) else (df_norm[col_cmax].isna() if col_cmax else df_norm[col_cusada].isna())
        total_incompletas = int(filas_incompletas.sum())
        pct_incompletas = round((total_incompletas / total_filas) * 100.0, 2) if total_filas > 0 else 0.0

        st.info(
            f"Se detectaron valores faltantes en capacidades (Factor de ocupación promedio detectado: **{factor_detectado * 100:.1f}%**). "
            f"Registros incompletos: **{total_incompletas}** ({pct_incompletas:.2f}% del dataset)."
        )

        opcion_capacidades = st.selectbox(
            "Tratamiento para capacidades:",
            options=[
                "No modificar",
                "Imputar por Factor de Ocupación",
                "Eliminar filas"
            ],
            key="tratamiento_capacidades"
        )

        if opcion_capacidades == "Eliminar filas":
            st.warning(f"⚠️ **Pérdida de datos estimada:** Se descartarán **{total_incompletas}** filas (**{pct_incompletas:.2f}%** del total del dataset) con capacidades faltantes.")

    # =========================================================================
    # 2. PRECIO (SOLO SI HAY PROBLEMAS - REQ 01)
    # =========================================================================
    if col_precio and col_precio in df_norm.columns and hay_problema_precio:
        st.markdown('<h4 style="font-size: 1.25rem; margin-top: 1.2rem;">Precio de Pasaje</h4>', unsafe_allow_html=True)
        pct_precio = round((nulls_precio / total_filas) * 100.0, 2) if total_filas > 0 else 0.0
        st.write(f"En el atributo **'precio'** tenés **{nulls_precio}** datos null ({pct_precio:.2f}% del dataset).")
        
        opcion_precio = st.selectbox(
            f"Tratamiento para 'precio' (Columna: {col_precio}):",
            options=[
                "No modificar (mantener nulos)", 
                "Imputar con la mediana global", 
                "Imputar con la mediana por grupos (país de origen y país de llegada)"
            ],
            key="tratamiento_precio"
        )

    # =========================================================================
    # 3. IDENTIFICADORES DE VUELO (SOLO SI HAY PROBLEMAS - REQ 01)
    # =========================================================================
    if col_id_real and col_id_real in df_norm.columns and hay_problema_id:
        st.markdown('<h4 style="font-size: 1.25rem; margin-top: 1.2rem;">Identificadores de Vuelo (id_vuelo)</h4>', unsafe_allow_html=True)
        pct_id = round((nulls_id / total_filas) * 100.0, 2) if total_filas > 0 else 0.0
        st.write(f"En **'id_vuelo'** tenés **{nulls_id}** registros sin identificador ({pct_id:.2f}% del dataset).")
        
        opcion_id = st.selectbox(
            f"Tratamiento para 'id_vuelo' (Columna: {col_id_real}):",
            options=[
                "Autogenerar ID automático (GEN-001, GEN-002, ...)",
                "No autogenerar (mantener valores originales / nulos)"
            ],
            key="tratamiento_id_vuelo",
            help="Asigna códigos correlativos únicos con formato GEN- a los vuelos que carecen de identificador."
        )

    # Mensaje si no se detectó ningún problema en los atributos configurables
    if not hay_problema_capacidades and not hay_problema_precio and not hay_problema_id:
        st.success("✅ **Datos Íntegros:** No se detectaron valores nulos ni anomalías pendientes de configuración en capacidades, precio ni identificadores.")

    # =========================================================================
    # EJECUCIÓN DEL PIPELINE (RESPONSIVE USE_CONTAINER_WIDTH - REQ 04)
    # =========================================================================
    if st.button("Ejecutar Pipeline de Limpieza", use_container_width=True):
        pipeline = PipelineLimpieza()

        # 1. Imputación estándar para ubicaciones (REQ-06)
        cols_ubicaciones = [
            mapeo[a] for a in ["origen", "destino", "aeropuerto_origen", "aeropuerto_destino"] 
            if mapeo.get(a) and mapeo.get(a) != "(No asignar)"
        ]
        if cols_ubicaciones:
            pipeline.agregar_paso(SaneadorUbicaciones(cols_ubicaciones))

        # 2. Imputación inteligente automática para el atributo 'estado' (REQ-05)
        col_estado = mapeo.get("estado") if mapeo.get("estado") != "(No asignar)" else None
        if col_estado and col_estado in df_norm.columns:
            pipeline.agregar_paso(ImputadorEstadoInteligente(
                col_estado=col_estado,
                col_s_est=mapeo.get("fechayhora_origen_estipulado"),
                col_s_real=mapeo.get("fechayhora_origen"),
                col_l_est=mapeo.get("fechayhora_destino_estipulado"),
                col_l_real=mapeo.get("fechayhora_destino"),
                forzar_recalculo=False
            ))

        # 3. Tratamiento de capacidades según opción elegida (REQ-02)
        if col_cmax and col_cusada and hay_problema_capacidades:
            if opcion_capacidades == "Imputar por Factor de Ocupación":
                pipeline.agregar_paso(ImputadorCapacidadesPorFactorOcupacion(col_cmax, col_cusada, metodo="imputar"))
            elif opcion_capacidades == "Eliminar filas":
                pipeline.agregar_paso(ImputadorCapacidadesPorFactorOcupacion(col_cmax, col_cusada, metodo="eliminar"))

        # 4. Autogeneración de id_vuelo si se seleccionó
        if hay_problema_id and opcion_id.startswith("Autogenerar"):
            col_id_target = col_id_real or "id_vuelo"
            pipeline.agregar_paso(GeneradorIdVuelo(col_id_target, prefijo="GEN-"))

        # 5. Imputaciones numéricas para precio
        if col_precio and hay_problema_precio:
            col_orig = mapeo.get("origen") if mapeo.get("origen") != "(No asignar)" else None
            col_dest = mapeo.get("destino") if mapeo.get("destino") != "(No asignar)" else None
            if opcion_precio == "Imputar con la mediana global":
                pipeline.agregar_paso(ImputadorMedianaGlobal(col_precio))
            elif opcion_precio == "Imputar con la mediana por grupos (país de origen y país de llegada)":
                pipeline.agregar_paso(ImputadorMedianaPorGrupo(col_precio, col_orig, col_dest))

        df_limpio = pipeline.ejecutar(df_norm)

        # Instanciación estricta a objetos Vuelo (REQ: precio obligatorio)
        try:
            lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, st.session_state.mapeo_columnas)
            st.session_state.df_limpio = df_limpio
            st.session_state.lista_vuelos = lista_vuelos
            st.success(f"¡Pipeline ejecutado! Se instanciaron con éxito {len(lista_vuelos)} objetos Vuelo.")
        except ValueError as e:
            st.error(f"❌ Error en la instanciación de objetos Vuelo: {e}")
            st.warning("El atributo 'precio' es estrictamente obligatorio para todos los vuelos. Asegúrese de imputar los precios faltantes antes de continuar.")
            return

        if st.session_state.usuario_activo:
            usuario = st.session_state.usuario_activo
            
            # --- Extraer el nombre de los archivos procesados y auto-guardar ---
            nombre_base = st.session_state.get("nombre_archivo_actual", "dataset_vuelos.csv")
            if nombre_base.endswith(".csv"):
                nombre_base = nombre_base[:-4]
            nombre_limpio = f"{nombre_base}_limpio.csv"
            
            import os
            directorio_guardado = os.path.join("data", "archivos_guardados")
            os.makedirs(directorio_guardado, exist_ok=True)
            ruta_limpio = os.path.join(directorio_guardado, nombre_limpio)
            df_limpio.to_csv(ruta_limpio, index=False)
            
            configuracion_total = {
                "ubicaciones": "Imputación automática a 'Desconocido'",
                "estado": "Imputación algorítmica inteligente",
            }
            if hay_problema_capacidades:
                configuracion_total["capacidades"] = opcion_capacidades
            if hay_problema_precio:
                configuracion_total["precio"] = opcion_precio
            if hay_problema_id:
                configuracion_total["id_vuelo"] = opcion_id

            usuario.sesion.actualizar(
                origen=st.session_state.origen_datos, 
                excluidas=st.session_state.get("variables_excluidas", []), 
                mapeo=mapeo, 
                imputacion=configuracion_total
            )
            usuario.sesion.registrar_comando(
                accion="EjecucionPipelineLimpieza", 
                parametros={
                    "archivos": nombre_limpio,
                    "total_filas": len(df_limpio), 
                    "imputaciones": configuracion_total
                }
            )
            gestor_usr.guardar_usuario(usuario)
            st.sidebar.success("Sesión y cambios guardados en su perfil.")

    if st.session_state.get("df_limpio") is not None:
        st.markdown('<h3 style="font-size: 1.4rem;">Descargar Resultados</h3>', unsafe_allow_html=True)
        csv = st.session_state.df_limpio.to_csv(index=False).encode('utf-8')
        
        nombre_base = st.session_state.get("nombre_archivo_actual", "dataset_vuelos.csv")
        if nombre_base.endswith(".csv"):
            nombre_base = nombre_base[:-4]
        nombre_limpio_descarga = f"{nombre_base}_limpio.csv"

        st.download_button(
            label="⬇️ Descargar Dataset Limpio (CSV)",
            data=csv,
            file_name=nombre_limpio_descarga,
            mime="text/csv",
            use_container_width=True
        )

        if st.session_state.get("lista_vuelos"):
            st.write("")
            if st.button("📊 Pasar al Módulo de Análisis Estadístico y Simulación Comercial ➡️", key="btn_ir_analisis_limpieza", use_container_width=True):
                st.session_state.mostrar_analisis = True
                st.rerun()