import streamlit as st

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
            st.session_state.mostrar_perfil = False
            st.rerun()

    st.divider()

    # Accedemos directamente a la lista a través del diccionario 'data' de la clase SesionAnalisis
    comandos_lista = usuario_actual.sesion.data.get("historial_comandos", [])
    
    if comandos_lista:
        # Recorremos la lista al revés para mostrar lo más nuevo arriba
        for i in reversed(range(len(comandos_lista))):
            cmd = comandos_lista[i]
            
            # Como vimos en tu clase, cmd ya es un diccionario directo
            parametros = cmd.get('parametros', {})
            archivos = parametros.get('archivos', 'Archivo desconocido')
            numero_operacion = i + 1
            
            with st.expander(f"📁 {archivos}  |  (Operación #{numero_operacion})", expanded=True):
                col_info, col_eliminar = st.columns([0.8, 0.2])
                
                with col_info:
                    st.write(f"**Filas procesadas:** {parametros.get('total_filas', 'N/A')}")
                    
                    imputaciones = parametros.get('imputaciones', {})
                    if imputaciones:
                        st.markdown("**Limpieza aplicada:**")
                        for columna, procedimiento in imputaciones.items():
                            st.markdown(f"- **{columna}:** {procedimiento}")
                    else:
                        st.write("*No se aplicaron imputaciones numéricas.*")
                        
                with col_eliminar:
                    st.write("") # Espaciador para centrar verticalmente
                    # La clave incluye el índice 'i' original para no borrar el equivocado
                    if st.button("🗑️ Eliminar", key=f"del_{i}", use_container_width=True):
                        
                        # ¡La magia ocurre aquí! Borramos directamente del diccionario
                        usuario_actual.sesion.data["historial_comandos"].pop(i)
                        
                        # Guardamos en el JSON / Base de datos
                        gestor_usr.guardar_usuario(usuario_actual)
                        
                        st.success("Archivo eliminado exitosamente.")
                        st.rerun()
    else:
        st.info("Aún no tienes procedimientos en tu historial.")