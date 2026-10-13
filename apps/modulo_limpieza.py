import streamlit as st
from modules.calidad import ReporteCalidad, AnalizadorDuplicados
from modules.pipeline_limpieza import (
    PipelineLimpieza, SaneadorCategoricos, 
    ImputadorFactorOcupacion, AutogeneradorIds, EliminadorFilasNulas
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
    total_filas_actual = len(df_norm)

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Registros analizados", total_filas_actual)
    col_m2.metric("Registros duplicados totales", total_duplicados)
    st.dataframe(df_reporte, use_container_width=True)

    st.markdown('<h3 style="font-size: 1.4rem;">Tratamiento de Anomalías y Valores Nulos</h3>', unsafe_allow_html=True)
    
    # 1. Tratamiento para Capacidades (Factor de Ocupación)
    st.markdown("#### ✈️ Capacidades del Avión")
    st.info("**💡 Imputación basada en Factor de Ocupación:** Para evitar contradicciones lógicas (como que la capacidad usada sea mayor a la máxima), las capacidades faltantes se calculan de manera proporcional usando el factor de ocupación promedio del dataset.")
    
    # Cálculo previo del porcentaje de pérdida si deciden eliminar capacidades incompletas
    cols_cap = [mapeo.get("capacidad_maxima_avion"), mapeo.get("capacidad_usada_avion")]
    validas_cap = [c for c in cols_cap if c and c in df_norm.columns]
    nulos_cap = df_norm[validas_cap].isna().any(axis=1).sum() if validas_cap else 0
    pct_perdida_cap = round((nulos_cap / total_filas_actual) * 100, 2) if total_filas_actual > 0 else 0.0

    tratamiento_capacidad = st.selectbox(
        "Tratamiento para capacidades (Máxima y Usada):",
        options=[
            "No modificar", 
            "Imputar usando Factor de Ocupación Promedio", 
            f"Eliminar filas con capacidades incompletas (Pérdida: {pct_perdida_cap}% del dataset)"
        ],
        key="trat_capacidades"
    )

    # 2. Tratamiento para Fechas Estipuladas (Críticas)
    st.markdown("#### 📅 Fechas y Horas Estipuladas")
    cols_fechas_est = [
        mapeo.get('fechayhora_origen_estipulado'), 
        mapeo.get('fechayhora_destino_estipulado')
    ]
    validas_fechas_est = [c for c in cols_fechas_est if c and c in df_norm.columns]
    nulos_fechas_est = df_norm[validas_fechas_est].isna().any(axis=1).sum() if validas_fechas_est else 0
    pct_perdida_fechas = round((nulos_fechas_est / total_filas_actual) * 100, 2) if total_filas_actual > 0 else 0.0
    
    tratamiento_fechas_est = st.selectbox(
        "Tratamiento para fechas estipuladas faltantes (Críticas para retrasos):",
        options=[
            "Dejar nulo", 
            f"Eliminar filas si falta fecha estipulada (Pérdida: {pct_perdida_fechas}% del dataset)"
        ],
        key="trat_fechas_est"
    )

    # 3. Tratamiento para ID de Vuelo
    st.markdown("#### 🆔 Identificador de Vuelo")
    tratamiento_id = st.selectbox(
        "Tratamiento para 'id_vuelo' nulos:",
        options=[
            "Dejar tal cual está", 
            "Autogenerar ID automático (Ej. GEN-001, GEN-002...)"
        ],
        key="trat_id_vuelo"
    )

    if st.button("Ejecutar Pipeline de Limpieza"):
        pipeline = PipelineLimpieza()
        
        # Textos y categóricos estándar
        cols_texto = [mapeo[a] for a in ["aeropuerto_origen", "aeropuerto_destino", "estado"] if mapeo.get(a) and mapeo.get(a) != "(No asignar)"]
        if cols_texto:
            pipeline.agregar_paso(SaneadorCategoricos(cols_texto))

        # Capacidades
        if "Imputando" in tratamiento_capacidad or "Factor" in tratamiento_capacidad:
            if mapeo.get("capacidad_maxima_avion") and mapeo.get("capacidad_usada_avion"):
                pipeline.agregar_paso(ImputadorFactorOcupacion(mapeo["capacidad_maxima_avion"], mapeo["capacidad_usada_avion"]))
        elif "Eliminar filas con capacidades" in tratamiento_capacidad:
            if mapeo.get("capacidad_maxima_avion") and mapeo["capacidad_maxima_avion"] != "(No asignar)":
                pipeline.agregar_paso(EliminadorFilasNulas(mapeo["capacidad_maxima_avion"]))
            if mapeo.get("capacidad_usada_avion") and mapeo["capacidad_usada_avion"] != "(No asignar)":
                pipeline.agregar_paso(EliminadorFilasNulas(mapeo["capacidad_usada_avion"]))

        # Fechas estipuladas
        if "Eliminar filas si falta fecha estipulada" in tratamiento_fechas_est:
            if mapeo.get("fechayhora_origen_estipulado") and mapeo["fechayhora_origen_estipulado"] != "(No asignar)":
                pipeline.agregar_paso(EliminadorFilasNulas(mapeo["fechayhora_origen_estipulado"]))
            if mapeo.get("fechayhora_destino_estipulado") and mapeo["fechayhora_destino_estipulado"] != "(No asignar)":
                pipeline.agregar_paso(EliminadorFilasNulas(mapeo["fechayhora_destino_estipulado"]))

        # ID de vuelo
        if "Autogenerar" in tratamiento_id:
            if mapeo.get("id_vuelo") and mapeo["id_vuelo"] != "(No asignar)":
                pipeline.agregar_paso(AutogeneradorIds(mapeo["id_vuelo"]))

        df_limpio = pipeline.ejecutar(df_norm)
        st.session_state.df_limpio = df_limpio

        lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, st.session_state.mapeo_columnas)
        st.session_state.lista_vuelos = lista_vuelos
        st.success(f"¡Pipeline ejecutado! Se instanciaron con éxito {len(lista_vuelos)} objetos Vuelo.")

        if st.session_state.usuario_activo:
            usuario = st.session_state.usuario_activo
            
            nombre_base = st.session_state.get("nombre_archivo_actual", "dataset_vuelos.csv")
            if nombre_base.endswith(".csv"):
                nombre_base = nombre_base[:-4]
            nombre_limpio = f"{nombre_base}_limpio.csv"
            
            import os
            directorio_guardado = os.path.join("data", "archivos_guardados")
            os.makedirs(directorio_guardado, exist_ok=True)
            ruta_limpio = os.path.join(directorio_guardado, nombre_limpio)
            df_limpio.to_csv(ruta_limpio, index=False)
            
            resumen_tratamientos = {
                "capacidades": tratamiento_capacidad,
                "fechas_estipuladas": tratamiento_fechas_est,
                "id_vuelo": tratamiento_id
            }
            
            usuario.sesion.actualizar(origen=st.session_state.origen_datos, excluidas=st.session_state.get("variables_excluidas", []), mapeo=mapeo, imputacion=resumen_tratamientos)
            usuario.sesion.registrar_comando(
                accion="EjecucionPipelineLimpieza", 
                parametros={
                    "archivos": nombre_limpio, 
                    "total_filas": len(df_limpio), 
                    "tratamientos": resumen_tratamientos
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