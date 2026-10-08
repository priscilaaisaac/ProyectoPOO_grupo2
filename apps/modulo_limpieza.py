import streamlit as st
from modules.calidad import ReporteCalidad, AnalizadorDuplicados
from modules.pipeline_limpieza import (
    PipelineLimpieza, SaneadorCategoricos, 
    ImputadorMedianaGlobal, ImputadorMedianaPorGrupo
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
    st.info("**💡 ¿Qué significa imputar con la mediana?**\n\nLa **mediana** es el valor central exacto de tus datos cuando los ordenás de menor a mayor. A diferencia del promedio clásico, la mediana **no se distorsiona por valores extremos (outliers)**.")

    columnas_numericas = ["capacidad_maxima_avion", "capacidad_usada_avion"]
    if mapeo.get("precio") and mapeo.get("precio") != "(No asignar)":
        columnas_numericas.append("precio")

    configuracion_imputacion = {}
    for attr in columnas_numericas:
        col_real = mapeo[attr]
        info_attr = df_reporte[df_reporte["Atributo del Sistema"] == attr]
        nulls = int(info_attr["Cantidad Nulls"].values[0]) if not info_attr.empty else 0
        st.write(f"En el atributo **'{attr}'** tenés **{nulls}** datos null.")
        
        configuracion_imputacion[attr] = st.selectbox(
            f"Tratamiento para '{attr}' (Columna: {col_real}):",
            options=["No modificar (mantener nulos)", "Imputar con la mediana global", "Imputar con la mediana por grupos (país de origen y país de llegada)"],
            key=f"tratamiento_{attr}"
        )

    if st.button("Ejecutar Pipeline de Limpieza"):
        pipeline = PipelineLimpieza()
        cols_texto = [mapeo[a] for a in ["aeropuerto_origen", "aeropuerto_destino", "estado"] if mapeo.get(a) and mapeo.get(a) != "(No asignar)"]
        if cols_texto:
            pipeline.agregar_paso(SaneadorCategoricos(cols_texto))

        col_orig = mapeo.get("origen") if mapeo.get("origen") != "(No asignar)" else None
        col_dest = mapeo.get("destino") if mapeo.get("destino") != "(No asignar)" else None

        for attr, metodo in configuracion_imputacion.items():
            col_fisica = mapeo[attr]
            if metodo == "Imputar con la mediana global":
                pipeline.agregar_paso(ImputadorMedianaGlobal(col_fisica))
            elif metodo == "Imputar con la mediana por grupos (país de origen y país de llegada)":
                pipeline.agregar_paso(ImputadorMedianaPorGrupo(col_fisica, col_orig, col_dest))

        df_limpio = pipeline.ejecutar(df_norm)
        st.session_state.df_limpio = df_limpio

        lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, st.session_state.mapeo_columnas)
        st.session_state.lista_vuelos = lista_vuelos
        st.success(f"¡Pipeline ejecutado! Se instanciaron con éxito {len(lista_vuelos)} objetos Vuelo.")

        if st.session_state.usuario_activo:
            usuario = st.session_state.usuario_activo
            
            # --- NUEVA LÓGICA: Extraer el nombre de los archivos procesados y auto-guardar ---
            nombre_base = st.session_state.get("nombre_archivo_actual", "dataset_vuelos.csv")
            if nombre_base.endswith(".csv"):
                nombre_base = nombre_base[:-4]
            nombre_limpio = f"{nombre_base}_limpio.csv"
            
            import os
            directorio_guardado = os.path.join("data", "archivos_guardados")
            os.makedirs(directorio_guardado, exist_ok=True)
            ruta_limpio = os.path.join(directorio_guardado, nombre_limpio)
            df_limpio.to_csv(ruta_limpio, index=False)
            
            usuario.sesion.actualizar(origen=st.session_state.origen_datos, excluidas=st.session_state.get("variables_excluidas", []), mapeo=mapeo, imputacion=configuracion_imputacion)
            usuario.sesion.registrar_comando(
                accion="EjecucionPipelineLimpieza", 
                parametros={
                    "archivos": nombre_limpio, # Guardamos el nombre real + _limpio en el historial
                    "total_filas": len(df_limpio), 
                    "imputaciones": configuracion_imputacion
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