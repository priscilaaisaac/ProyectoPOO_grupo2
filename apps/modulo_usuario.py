import streamlit as st
import os
import pandas as pd
from apps.modulo_validacion import ATRIBUTOS_REQUERIDOS, ATRIBUTOS_OPCIONALES, COLUMNAS_CANONICAS
from modules.calidad import EstandarizadorDatos
from modules.fabrica_vuelos import FabricaVuelos

def limpiar_estado_analisis():
    """
    Restablece a None o sus valores por defecto las variables de sesión responsables
    de mantener los datos cargados y el estado del análisis para evitar renderizados fantasma.
    """
    st.session_state.df_crudo = None
    st.session_state.df_crudo_completo = None
    st.session_state.df_estandarizado = None
    st.session_state.df_limpio = None
    st.session_state.contrato_validado = False
    st.session_state.archivos_procesados = False
    st.session_state.archivo_es_limpio = False
    st.session_state.modo_limpieza_directa = False
    st.session_state.mostrar_analisis = False
    st.session_state.nombre_archivo_actual = None
    st.session_state.lista_vuelos = []
    st.session_state.columnas_disponibles = []
    st.session_state.origen_por_columna = {}
    st.session_state.archivos_dfs = {}
    st.session_state.mapeo_columnas = {}
    st.session_state.pipeline_ejecutado_recientemente = False
    st.session_state.archivos_crudos_temporales = []
    st.session_state.archivos_subidos_previos = []
    st.session_state.variables_excluidas = []

def modulo_usuario(gestor_usr):
    st.sidebar.title("Módulo de Usuario")

    if st.session_state.usuario_activo is None:
        pestaña_login, pestaña_registro = st.sidebar.tabs(["Iniciar Sesión", "Registrarse"])

        with pestaña_login:
            usuario_in = st.text_input("Usuario:", key="login_usr")
            clave_in = st.text_input("Contraseña:", type="password", key="login_pass")
            if st.button("Ingresar", use_container_width=True):
                user = gestor_usr.autenticar(usuario_in, clave_in)
                if user:
                    st.session_state.usuario_activo = user
                    st.sidebar.success(f"Bienvenido/a, {user.username}")
                    st.rerun()
                else:
                    st.sidebar.error("Usuario o contraseña incorrectos.")

        with pestaña_registro:
            nuevo_usr = st.text_input("Nuevo Usuario:", key="reg_usr")
            nueva_clave = st.text_input("Nueva Contraseña:", type="password", key="reg_pass")
            if st.button("Crear Cuenta", use_container_width=True):
                try:
                    user = gestor_usr.registrar_usuario(nuevo_usr, nueva_clave)
                    st.session_state.usuario_activo = user
                    st.sidebar.success(f"Cuenta '{nuevo_usr}' creada exitosamente.")
                    st.rerun()
                except ValueError as e:
                    st.sidebar.error(str(e))
    else:
        usuario_actual = st.session_state.usuario_activo
        st.sidebar.markdown(f"**Usuario:** `{usuario_actual.username}`")

        if st.sidebar.button("Cerrar Sesión", use_container_width=True):
            st.session_state.usuario_activo = None
            st.session_state.mostrar_perfil = False
            st.rerun()

        st.sidebar.divider()
        
        if st.sidebar.button("📂 Ver mi Perfil y Archivos Guardados", use_container_width=True):
            st.session_state.mostrar_perfil = True
            st.session_state.mostrar_analisis = False
            st.rerun()

def vista_perfil_pantalla_completa(gestor_usr):
    """Renderiza el historial y permite eliminar registros de operaciones pasadas."""
    usuario_actual = st.session_state.usuario_activo
    
    col_titulo, col_boton = st.columns([0.8, 0.2])
    with col_titulo:
        st.markdown('<h1 style="font-size: 2.25rem;">🗂️ Mis Archivos Guardados</h1>', unsafe_allow_html=True)
    with col_boton:
        st.write("") # Espaciador
        if st.button("⬅️ Volver", use_container_width=True):
            limpiar_estado_analisis()
            st.session_state.mostrar_perfil = False
            st.rerun()

    st.write("En esta sección podés visualizar tus archivos cargados (crudos) y los archivos que has creado (unificados)")
    st.divider()

    import os
    import pandas as pd
    directorio_guardado = os.path.join("data", "archivos_guardados")
    if not os.path.exists(directorio_guardado):
        st.info("Aún no hay archivos guardados físicos en esta sección.")
        archivos = []
    else:
        archivos = os.listdir(directorio_guardado)
        
    if archivos:
        crudos = [f for f in archivos if f.startswith("raw_")]
        creados = [f for f in archivos if not f.startswith("raw_")]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Archivos Cargados (Crudos)")
            if not crudos:
                st.write("No hay archivos cargados.")
            for f in crudos:
                ruta = os.path.join(directorio_guardado, f)
                c_btn, c_del = st.columns([0.82, 0.18])
                with c_btn:
                    if st.button(f"📥 {f}", key=f"btn_{f}", use_container_width=True):
                        try:
                            st.session_state.nombre_archivo_actual = f
                            df_cargado = pd.read_csv(ruta)
                            st.session_state.df_crudo = df_cargado
                            st.session_state.df_limpio = None
                            st.session_state.pipeline_ejecutado_recientemente = False
                            st.session_state.archivo_es_limpio = False
                            st.session_state.lista_vuelos = []
                            nuevo_mapeo = {}
                            for attr in ATRIBUTOS_REQUERIDOS + ATRIBUTOS_OPCIONALES:
                                if attr in df_cargado.columns:
                                    nuevo_mapeo[attr] = attr
                                else:
                                    nuevo_mapeo[attr] = "(No asignar)"
                            st.session_state.mapeo_columnas = nuevo_mapeo
                            st.session_state.contrato_validado = True
                            st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(df_cargado)
                            st.session_state.mostrar_perfil = False
                            st.session_state.modo_limpieza_directa = True
                            st.session_state.mostrar_analisis = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al cargar el archivo crudo: {e}")
                with c_del:
                    if st.button("🗑️", key=f"del_raw_{f}", help=f"Eliminar archivo {f}", use_container_width=True):
                        if os.path.exists(ruta):
                            os.remove(ruta)
                        st.success(f"Archivo crudo '{f}' eliminado.")
                        st.rerun()

        with col2:
            st.markdown("### Archivos Creados (Unificados y Limpios)")
            if not creados:
                st.write("No hay archivos unificados.")
            for f in creados:
                ruta = os.path.join(directorio_guardado, f)
                c_btn, c_del = st.columns([0.82, 0.18])
                with c_btn:
                    if st.button(f"📄 {f}", key=f"btn_{f}", use_container_width=True):
                        try:
                            st.session_state.nombre_archivo_actual = f
                            df_cargado = pd.read_csv(ruta)
                            if all(attr in df_cargado.columns for attr in ATRIBUTOS_REQUERIDOS):
                                for col_c in COLUMNAS_CANONICAS:
                                    if col_c not in df_cargado.columns:
                                        df_cargado[col_c] = None
                                df_cargado = df_cargado[COLUMNAS_CANONICAS].copy()

                            st.session_state.df_limpio = df_cargado
                            st.session_state.df_crudo = df_cargado

                            nuevo_mapeo = {}
                            for attr in ATRIBUTOS_REQUERIDOS + ATRIBUTOS_OPCIONALES:
                                if attr in df_cargado.columns:
                                    nuevo_mapeo[attr] = attr
                            for col in df_cargado.columns:
                                if col not in nuevo_mapeo:
                                    nuevo_mapeo[col] = col
                            st.session_state.mapeo_columnas = nuevo_mapeo
                            st.session_state.df_estandarizado = EstandarizadorDatos.normalizar(df_cargado)
                            st.session_state.contrato_validado = True

                            try:
                                # Pre-validación: asegurar que registros sin precio válido no pasen a la fábrica
                                df_para_vuelos = df_cargado.copy()
                                col_p = nuevo_mapeo.get("precio") or ("precio" if "precio" in df_para_vuelos.columns else None)
                                if col_p and col_p in df_para_vuelos.columns:
                                    s_p = pd.to_numeric(df_para_vuelos[col_p], errors="coerce")
                                    nulos_p = s_p.isna() | (s_p < 0)
                                    if nulos_p.any():
                                        df_para_vuelos = df_para_vuelos[~nulos_p].copy().reset_index(drop=True)
                                lista_vuelos = FabricaVuelos.instanciar_desde_dataframe(df_para_vuelos, nuevo_mapeo)
                                st.session_state.lista_vuelos = lista_vuelos
                            except Exception:
                                st.session_state.lista_vuelos = []

                            st.session_state.mostrar_perfil = False
                            st.session_state.modo_limpieza_directa = True
                            st.session_state.archivo_es_limpio = True
                            st.session_state.mostrar_analisis = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al cargar el archivo limpio para visualización: {e}")
                with c_del:
                    if st.button("🗑️", key=f"del_creado_{f}", help=f"Eliminar archivo {f}", use_container_width=True):
                        if os.path.exists(ruta):
                            os.remove(ruta)
                        st.success(f"Archivo limpio '{f}' eliminado.")
                        st.rerun()

    st.divider()
    st.markdown('<h2 style="font-size: 1.8rem;">Historial de Operaciones Realizadas</h2>', unsafe_allow_html=True)
    
    # Accedemos directamente a la lista a través del diccionario 'data' de la clase SesionAnalisis
    comandos_lista = usuario_actual.sesion.data.get("historial_comandos", [])
    
    if comandos_lista:
        # Recorremos la lista al revés para mostrar lo más nuevo arriba
        for i in reversed(range(len(comandos_lista))):
            cmd = comandos_lista[i]
            parametros = cmd.get('parametros', {})
            accion = cmd.get('accion', '')

            # Extraer y normalizar el nombre del archivo (soporta 'archivos' y 'archivo')
            archivo_hist = parametros.get('archivos') or parametros.get('archivo')
            if not archivo_hist or str(archivo_hist).strip() in ["", "None", "Archivo desconocido", "Dataset Activo"]:
                archivo_hist = "dataset_vuelos.csv"
            else:
                archivo_hist = str(archivo_hist).strip()

            numero_operacion = i + 1
            es_simulacion = "Simulación" in accion or parametros.get("tipo_operacion") == "SimulacionComercial" or "precio_sugerido" in parametros

            # Título descriptivo según el tipo de acción
            if es_simulacion:
                titulo_expander = f"🎯 Simulación: {archivo_hist}  |  (Operación #{numero_operacion})"
            else:
                titulo_expander = f"📁 Limpieza: {archivo_hist}  |  (Operación #{numero_operacion})"

            with st.expander(titulo_expander, expanded=True):
                col_info, col_acciones = st.columns([0.75, 0.25])
                
                with col_info:
                    st.markdown(f"**Archivo:** `{archivo_hist}` &nbsp;|&nbsp; **Fecha:** {cmd.get('timestamp', 'N/A')}")
                    if es_simulacion:
                        st.markdown(f"**Acción:** {accion}")
                        st.write(f"- **Ruta:** {parametros.get('ruta', 'N/A')}")
                        st.write(f"- **Precio Sugerido:** ${parametros.get('precio_sugerido', 0.0):,.2f}")
                        st.write(f"- **Riesgo Logístico:** {parametros.get('riesgo_logistico_pct', 0.0)}%")
                    else:
                        st.write(f"**Filas procesadas:** {parametros.get('total_filas', 'N/A')}")
                        imputaciones = parametros.get('imputaciones', {})
                        if imputaciones:
                            st.markdown("**Limpieza aplicada:**")
                            for columna, procedimiento in imputaciones.items():
                                st.markdown(f"- **{columna}:** {procedimiento}")
                        else:
                            st.write("*No se aplicaron imputaciones numéricas.*")
                        
                with col_acciones:
                    # Botón exclusivo para eliminar registro del historial (sin acceso a análisis desde el historial)
                    if st.button("🗑️ Eliminar Registro", key=f"del_{i}", use_container_width=True):
                        usuario_actual.sesion.data["historial_comandos"].pop(i)
                        gestor_usr.guardar_usuario(usuario_actual)
                        st.success("Operación eliminada del historial.")
                        st.rerun()
    else:
        st.info("Aún no tienes procedimientos en tu historial.")