import streamlit as st
import os
import pandas as pd
from modules.calidad import ReporteCalidad, AnalizadorDuplicados, EstandarizadorDatos
from modules.pipeline_limpieza import (
    PipelineLimpieza, SaneadorCategoricos, SaneadorUbicaciones,
    ImputadorMedianaGlobal, ImputadorMedianaPorGrupo, ImputadorMediaGlobal,
    ImputadorCapacidadesPorFactorOcupacion, ImputadorEstadoInteligente,
    GeneradorIdVuelo, AutogeneradorIds, EliminadorFilasNulas
)
from modules.fabrica_vuelos import FabricaVuelos
from modules.validador import ValidadorPreInstanciacion

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

def modulo_limpieza_y_dominio(gestor_usr):
    # Condicional de escape rápido (early return): abortar si no hay un archivo activamente procesado en el flujo actual
    tiene_datos = (
        st.session_state.get("df_crudo") is not None or
        st.session_state.get("df_estandarizado") is not None or
        st.session_state.get("df_limpio") is not None
    )
    contrato_ok = st.session_state.get("contrato_validado", False)
    modo_directo = st.session_state.get("modo_limpieza_directa", False)

    if not tiene_datos or (not contrato_ok and not modo_directo):
        return

    nombre_arch = str(st.session_state.get("nombre_archivo_actual", "")).lower()
    nombre_actual = st.session_state.get("nombre_archivo_actual", "Dataset Activo")
    es_archivo_limpio = st.session_state.get("archivo_es_limpio", False) or nombre_arch.endswith("_limpio.csv") or "limpio" in nombre_arch

    if es_archivo_limpio:
        df_mostrar = st.session_state.get("df_limpio")
        if df_mostrar is None:
            df_mostrar = st.session_state.get("df_estandarizado") or st.session_state.get("df_crudo")

        if df_mostrar is None:
            return

        st.divider()

        mapeo = st.session_state.get("mapeo_columnas", {})
        if not mapeo and df_mostrar is not None:
            mapeo = {col: col for col in df_mostrar.columns}
            st.session_state.mapeo_columnas = mapeo

        df_norm = st.session_state.get("df_estandarizado")
        if df_norm is None and df_mostrar is not None:
            df_norm = EstandarizadorDatos.normalizar(df_mostrar)
            st.session_state.df_estandarizado = df_norm
        elif df_norm is None:
            df_norm = df_mostrar

        # ---------------------------------------------------------------------
        # Cabecera: Nombre del archivo a la izquierda y Botón a la derecha
        # ---------------------------------------------------------------------
        col_izq, col_der = st.columns([0.65, 0.35])
        with col_izq:
            st.markdown(f'<h2 style="font-size: 1.85rem; margin-bottom: 0.1rem;">📄 {nombre_actual}</h2>', unsafe_allow_html=True)
            st.caption("Archivo unificado y limpio • Procesado y listo para análisis")
        with col_der:
            st.write("")  # Espaciador vertical
            if st.button("📊 Ir a Análisis Estadístico ➡️", key="btn_ir_analisis_desde_limpio_header", use_container_width=True):
                if df_mostrar is not None:
                    try:
                        # PRE-VALIDACIÓN: Filtrar nulos en precio antes de instanciar vuelos
                        df_para_vuelos = df_mostrar.copy()
                        col_p = mapeo.get("precio") or ("precio" if "precio" in df_para_vuelos.columns else None)
                        if col_p and col_p in df_para_vuelos.columns:
                            s_p = pd.to_numeric(df_para_vuelos[col_p], errors="coerce")
                            nulos_p = s_p.isna() | (s_p < 0)
                            if nulos_p.any():
                                df_para_vuelos = df_para_vuelos[~nulos_p].copy().reset_index(drop=True)
                        st.session_state.lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_para_vuelos, mapeo)
                    except Exception as e:
                        st.error(f"Error al instanciar vuelos: {e}")
                        return
                st.session_state.mostrar_analisis = True
                st.session_state.modo_limpieza_directa = True
                st.rerun()

            # Botón para eliminar el archivo físico ubicado DEBAJO de "Ir a Análisis Estadístico"
            if st.button("🗑️ Eliminar Archivo Físico", key="btn_eliminar_archivo_limpio_header", use_container_width=True):
                directorio_guardado = os.path.join("data", "archivos_guardados")
                ruta_fisica = os.path.join(directorio_guardado, nombre_actual)
                if os.path.exists(ruta_fisica):
                    os.remove(ruta_fisica)
                st.session_state.df_limpio = None
                st.session_state.df_crudo = None
                st.session_state.df_estandarizado = None
                st.session_state.lista_vuelos = []
                st.session_state.modo_limpieza_directa = False
                st.session_state.mostrar_perfil = True
                st.success(f"Archivo '{nombre_actual}' eliminado correctamente.")
                st.rerun()

        if df_norm is not None:
            generador_reporte = ReporteCalidad(df_norm, mapeo)
            df_reporte = generador_reporte.generar()
            total_duplicados = AnalizadorDuplicados.contar(df_norm)

            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Registros analizados", len(df_norm))
            col_m2.metric("Registros duplicados totales", total_duplicados)

            st.markdown('<h3 style="font-size: 1.4rem;">Diagnóstico de Calidad de Datos</h3>', unsafe_allow_html=True)
            st.dataframe(df_reporte, use_container_width=True)

            st.markdown('<h3 style="font-size: 1.4rem;">Vista Previa de los Datos (Primeros 50 Registros)</h3>', unsafe_allow_html=True)
            st.dataframe(df_norm.head(50), use_container_width=True)

            st.markdown('<h3 style="font-size: 1.4rem;">Descargar Dataset</h3>', unsafe_allow_html=True)
            cols_export = [c for c in COLUMNAS_CANONICAS if c in df_norm.columns]
            df_descarga = df_norm[cols_export] if len(cols_export) == len(COLUMNAS_CANONICAS) else df_norm
            csv = df_descarga.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Descargar Dataset Limpio (CSV)",
                data=csv,
                file_name=nombre_actual if nombre_actual.endswith(".csv") else f"{nombre_actual}.csv",
                mime="text/csv",
                use_container_width=True
            )

        return

    if st.session_state.get("df_crudo") is None or not st.session_state.get("contrato_validado") or st.session_state.get("df_estandarizado") is None:
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

    st.markdown('<h4 style="font-size: 1.25rem; margin-top: 1rem;">Vista Previa de los Datos (Primeros 50 Registros)</h4>', unsafe_allow_html=True)
    st.dataframe(df_norm.head(50), use_container_width=True)

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
    opcion_capacidades = "Imputar por Factor de Ocupación"
    opcion_precio = "Imputar con la media"
    opcion_id = "Autogenerar ID automático (GEN-001, GEN-002, ...)"

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
                "Imputar por Factor de Ocupación",
                f"Eliminar filas con capacidades incompletas (Pérdida: {pct_incompletas:.2f}% del dataset)"
            ],
            key="tratamiento_capacidades"
        )

        if opcion_capacidades.startswith("Eliminar"):
            st.warning(f"⚠️ **Pérdida de datos estimada:** Se descartarán **{total_incompletas}** filas (**{pct_incompletas:.2f}%** del total del dataset) con capacidades faltantes.")

    # =========================================================================
    # 2. PRECIO (SOLO SI HAY PROBLEMAS - 4 OPCIONES OBLIGATORIAS)
    # =========================================================================
    if col_precio and col_precio in df_norm.columns and hay_problema_precio:
        st.markdown('<h4 style="font-size: 1.25rem; margin-top: 1.2rem;">Precio de Pasaje</h4>', unsafe_allow_html=True)
        pct_precio = round((nulls_precio / total_filas) * 100.0, 2) if total_filas > 0 else 0.0
        st.write(f"En el atributo **'precio'** tenés **{nulls_precio}** datos null ({pct_precio:.2f}% del dataset).")
        
        opcion_precio = st.selectbox(
            f"Tratamiento para 'precio' (Columna: {col_precio}):",
            options=[
                "Imputar con la media",
                "Imputar con la mediana",
                "Imputar por grupos (país de origen y destino)",
                f"Eliminar registros con precio nulo (Pérdida: {pct_precio:.2f}% del dataset)"
            ],
            key="tratamiento_precio"
        )

    # =========================================================================
    # 3. IDENTIFICADORES DE VUELO (SOLO SI HAY PROBLEMAS)
    # =========================================================================
    if col_id_real and col_id_real in df_norm.columns and hay_problema_id:
        st.markdown('<h4 style="font-size: 1.25rem; margin-top: 1.2rem;">Identificadores de Vuelo (id_vuelo)</h4>', unsafe_allow_html=True)
        pct_id = round((nulls_id / total_filas) * 100.0, 2) if total_filas > 0 else 0.0
        st.write(f"En **'id_vuelo'** tenés **{nulls_id}** registros sin identificador ({pct_id:.2f}% del dataset).")
        
        opcion_id = st.selectbox(
            f"Tratamiento para 'id_vuelo' (Columna: {col_id_real}):",
            options=[
                "Autogenerar ID automático (GEN-001, GEN-002, ...)",
                f"Eliminar registros sin ID de vuelo (Pérdida: {pct_id:.2f}% del dataset)"
            ],
            key="tratamiento_id_vuelo",
            help="Asigna códigos correlativos únicos con formato GEN- a los vuelos que carecen de identificador o elimina los registros sin ID."
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
            if "Imputar por Factor de Ocupación" in opcion_capacidades:
                pipeline.agregar_paso(ImputadorCapacidadesPorFactorOcupacion(col_cmax, col_cusada, metodo="imputar"))
            elif "Eliminar" in opcion_capacidades:
                pipeline.agregar_paso(ImputadorCapacidadesPorFactorOcupacion(col_cmax, col_cusada, metodo="eliminar"))

        # 4. Autogeneración o eliminación de id_vuelo si se seleccionó
        if hay_problema_id:
            col_id_target = "id_vuelo"
            if opcion_id.startswith("Autogenerar"):
                pipeline.agregar_paso(GeneradorIdVuelo(columna=col_id_target, prefijo="GEN-"))
            elif "Eliminar" in opcion_id:
                pipeline.agregar_paso(EliminadorFilasNulas(col_id_target))

        # 5. Tratamiento numérico para precio (4 opciones obligatorias)
        if col_precio and hay_problema_precio:
            col_orig = mapeo.get("origen") if mapeo.get("origen") != "(No asignar)" else None
            col_dest = mapeo.get("destino") if mapeo.get("destino") != "(No asignar)" else None
            if "media" in opcion_precio.lower() and "mediana" not in opcion_precio.lower():
                pipeline.agregar_paso(ImputadorMediaGlobal(col_precio))
            elif "mediana" in opcion_precio.lower() and "grupos" not in opcion_precio.lower():
                pipeline.agregar_paso(ImputadorMedianaGlobal(col_precio))
            elif "grupos" in opcion_precio.lower():
                pipeline.agregar_paso(ImputadorMedianaPorGrupo(col_precio, col_orig, col_dest))
            elif "eliminar" in opcion_precio.lower():
                pipeline.agregar_paso(EliminadorFilasNulas(col_precio))

        df_limpio = pipeline.ejecutar(df_norm)

        # PRE-VALIDACIÓN Y SANEAMIENTO FINAL DE CAMPOS OBLIGATORIOS:
        # 1. Precio: sin nulos ni negativos
        col_p = mapeo.get("precio") or ("precio" if "precio" in df_limpio.columns else None)
        if col_p and col_p in df_limpio.columns:
            s_p = pd.to_numeric(df_limpio[col_p], errors="coerce")
            nulos_p = s_p.isna() | (s_p < 0)
            if nulos_p.any():
                media_p = round(float(s_p.dropna().mean()), 2) if (s_p.dropna() >= 0).any() else 100.0
                df_limpio[col_p] = s_p.fillna(media_p).clip(lower=0.0)

        # 2. Capacidades: enteras, no negativas, usada <= maxima
        col_cmax = mapeo.get("capacidad_maxima_avion") or ("capacidad_maxima_avion" if "capacidad_maxima_avion" in df_limpio.columns else None)
        col_cusada = mapeo.get("capacidad_usada_avion") or ("capacidad_usada_avion" if "capacidad_usada_avion" in df_limpio.columns else None)
        if col_cmax and col_cmax in df_limpio.columns:
            s_cmax = pd.to_numeric(df_limpio[col_cmax], errors="coerce")
            val_cmax_def = int(s_cmax.dropna().median()) if (s_cmax.dropna() > 0).any() else 180
            df_limpio[col_cmax] = s_cmax.fillna(val_cmax_def).clip(lower=1).round().astype(int)

        if col_cusada and col_cusada in df_limpio.columns:
            s_cusada = pd.to_numeric(df_limpio[col_cusada], errors="coerce")
            max_referencia = df_limpio[col_cmax] if (col_cmax and col_cmax in df_limpio.columns) else 180
            df_limpio[col_cusada] = s_cusada.fillna((max_referencia * 0.75).round()).clip(lower=0).round().astype(int)

        if col_cmax and col_cusada and col_cmax in df_limpio.columns and col_cusada in df_limpio.columns:
            exceso = df_limpio[col_cusada] > df_limpio[col_cmax]
            if exceso.any():
                df_limpio.loc[exceso, col_cusada] = df_limpio.loc[exceso, col_cmax]

        # 3. Fechas estipuladas: parseables, sin nulos y coherentes
        col_forig_est = mapeo.get("fechayhora_origen_estipulado") or ("fechayhora_origen_estipulado" if "fechayhora_origen_estipulado" in df_limpio.columns else None)
        col_fdest_est = mapeo.get("fechayhora_destino_estipulado") or ("fechayhora_destino_estipulado" if "fechayhora_destino_estipulado" in df_limpio.columns else None)
        if col_forig_est and col_forig_est in df_limpio.columns:
            s_forig = pd.to_datetime(df_limpio[col_forig_est], errors="coerce")
            if s_forig.isna().any():
                col_real_orig = mapeo.get("fechayhora_origen") or ("fechayhora_origen" if "fechayhora_origen" in df_limpio.columns else None)
                if col_real_orig and col_real_orig in df_limpio.columns:
                    s_forig = s_forig.combine_first(pd.to_datetime(df_limpio[col_real_orig], errors="coerce"))
                s_forig = s_forig.fillna(pd.Timestamp("2026-10-01 08:00:00"))
            df_limpio[col_forig_est] = s_forig

        if col_fdest_est and col_fdest_est in df_limpio.columns:
            s_fdest = pd.to_datetime(df_limpio[col_fdest_est], errors="coerce")
            if s_fdest.isna().any():
                col_real_dest = mapeo.get("fechayhora_destino") or ("fechayhora_destino" if "fechayhora_destino" in df_limpio.columns else None)
                if col_real_dest and col_real_dest in df_limpio.columns:
                    s_fdest = s_fdest.combine_first(pd.to_datetime(df_limpio[col_real_dest], errors="coerce"))
                if col_forig_est and col_forig_est in df_limpio.columns:
                    s_fdest = s_fdest.combine_first(pd.to_datetime(df_limpio[col_forig_est]) + pd.Timedelta(hours=2))
                s_fdest = s_fdest.fillna(pd.Timestamp("2026-10-01 10:00:00"))

            if col_forig_est and col_forig_est in df_limpio.columns:
                fechas_inv = s_fdest < df_limpio[col_forig_est]
                if fechas_inv.any():
                    s_fdest.loc[fechas_inv] = df_limpio.loc[fechas_inv, col_forig_est] + pd.Timedelta(hours=2)

            df_limpio[col_fdest_est] = s_fdest

        # FILTRADO ESTRICTO: Garantizar que df_limpio contenga ÚNICAMENTE las 13 columnas canónicas limpias
        for col_c in COLUMNAS_CANONICAS:
            if col_c not in df_limpio.columns:
                df_limpio[col_c] = None
        df_limpio = df_limpio[COLUMNAS_CANONICAS].copy()

        # Instanciación estricta a objetos Vuelo con pre-validación de contrato
        try:
            ValidadorPreInstanciacion.validar(df_limpio, st.session_state.mapeo_columnas)
            lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, st.session_state.mapeo_columnas)
            st.session_state.df_limpio = df_limpio
            st.session_state.lista_vuelos = lista_vuelos
            st.session_state.pipeline_ejecutado_recientemente = True
            st.success(f"¡Pipeline ejecutado! Se instanciaron con éxito {len(lista_vuelos)} objetos Vuelo.")
        except ValueError as e:
            st.error(f"❌ Error en la validación / instanciación de objetos Vuelo: {e}")
            st.warning("Verifique que todos los campos requeridos cumplan con los tipos y rangos válidos.")
            return

        if st.session_state.usuario_activo:
            usuario = st.session_state.usuario_activo
            
            # --- Extraer el nombre de los archivos procesados y auto-guardar ---
            nombre_base = st.session_state.get("nombre_archivo_actual", "dataset_vuelos.csv")
            if nombre_base.endswith(".csv"):
                nombre_base = nombre_base[:-4]
            nombre_limpio = f"{nombre_base}_limpio.csv"
            
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

    # Solo mostrar descarga y pase a análisis SI se acaba de ejecutar el pipeline exitosamente
    if st.session_state.get("pipeline_ejecutado_recientemente", False) and st.session_state.get("df_limpio") is not None:
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