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
            st.rerun()

        st.sidebar.divider()
        
        if st.sidebar.button("📂 Ver mi Perfil y Archivos Guardados", use_container_width=True):
            st.session_state.mostrar_perfil = not st.session_state.get("mostrar_perfil", False)

        if st.session_state.get("mostrar_perfil", False):
            with st.sidebar.container(border=True):
                st.markdown("### 🗂️ Procedimientos Aplicados")
                datos_sesion = usuario_actual.sesion.to_dict()
                
                if datos_sesion.get("ultima_actualizacion"):
                    st.caption(f"Última actualización: {datos_sesion['ultima_actualizacion']}")
                    comandos = datos_sesion.get("historial_comandos", [])
                    
                    if comandos:
                        for i, cmd in enumerate(comandos):
                            st.markdown(f"**Operación #{i+1}**")
                            parametros = cmd.get('parametros', {})
                            st.write(f"Filas procesadas: {parametros.get('total_filas', 'N/A')}")
                            
                            if 'imputaciones' in parametros and parametros['imputaciones']:
                                st.markdown("**Limpieza aplicada:**")
                                for columna, procedimiento in parametros['imputaciones'].items():
                                    st.markdown(f"- **{columna}:** {procedimiento}")
                            else:
                                st.write("*No se aplicaron imputaciones numéricas.*")
                            st.divider()
                    else:
                        st.write("Aún no tienes procedimientos en tu historial.")
                else:
                    st.info("No tienes un historial registrado en esta cuenta.")