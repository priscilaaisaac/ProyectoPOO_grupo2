import sys
from pathlib import Path
import streamlit as st  # type: ignore[import-not-found]

# Configuración de rutas para importar las librerías
raiz_proyecto = Path(__file__).resolve().parent.parent
ruta_libs = raiz_proyecto / "libs"
for ruta in (raiz_proyecto, ruta_libs):
    if str(ruta) not in sys.path:
        sys.path.append(str(ruta))

from modules.gestor_usuarios import GestorUsuarios

# Importaciones modulares locales
from apps.modulo_usuario import modulo_usuario, vista_perfil_pantalla_completa, limpiar_estado_analisis
from apps.modulo_ingestion import modulo_ingestion
from apps.modulo_validacion import modulo_validacion
from apps.modulo_limpieza import modulo_limpieza_y_dominio
from apps.modulo_analisis import vista_analisis_estadistico
from apps.modulo_manual import vista_manual_funcionamiento

def inicializar_estado():
    """Inicializa todas las variables de sesión globales necesarias."""
    claves_iniciales = {
        "usuario_activo": None, 
        "origen_datos": "CSV",
        "df_crudo": None,
        "df_crudo_completo": None, 
        "columnas_disponibles": [],
        "origen_por_columna": {}, 
        "contrato_validado": False,
        "mostrar_perfil": False,
        "modo_limpieza_directa": False,
        "mostrar_analisis": False,
        "lista_vuelos": [],
        "df_limpio": None,
        "df_estandarizado": None,
        "archivos_procesados": False,
        "nombre_archivo_actual": None,
        "archivo_es_limpio": False,
        "mostrar_manual": False
    }
    for clave, valor in claves_iniciales.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor

def aplicar_estilos():
    """Oculta elementos predeterminados de Streamlit y aplica CSS."""
    st.markdown("""
    <style>
        [data-testid="stHeaderActionElements"], .stApp a[href^="#"],
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; }
        div[data-baseweb="select"] span { font-weight: 500; }
        div[data-baseweb="tag"] { background-color: rgba(150, 150, 150, 0.15) !important; }
        
        /* Ocultar por completo el texto secundario (límite de peso y extensiones) en el file uploader */
        [data-testid="stFileUploadDropzone"] small,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzoneInstructions"],
        div[data-testid="stFileUploaderDropzoneInstructions"],
        section[data-testid="stFileUploadDropzone"] small,
        section[data-testid="stFileUploaderDropzone"] small {
            display: none !important;
        }
        
        /* Contenedor principal adaptable y fluido al ancho total */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

def main():
    """Ejecuta los módulos de la aplicación secuencialmente."""
    try:
        st.set_page_config(page_title="Sistema de Gestión de Vuelos", layout="wide")
    except Exception:
        pass
    inicializar_estado()
    aplicar_estilos()
    
    gestor_usr = GestorUsuarios()
    
    # La barra lateral se renderiza siempre
    modulo_usuario(gestor_usr)
    
    # Lógica de navegación principal (Router)
    if st.session_state.get("mostrar_manual", False):
        vista_manual_funcionamiento()
    elif st.session_state.get("mostrar_analisis", False):
        vista_analisis_estadistico(gestor_usr)
    elif st.session_state.get("mostrar_perfil", False) and st.session_state.usuario_activo:
        vista_perfil_pantalla_completa(gestor_usr)
    else:
        if st.session_state.get("modo_limpieza_directa", False):
            # Si venimos del perfil con un archivo cargado, vamos directo a limpiar
            modulo_limpieza_y_dominio(gestor_usr)
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                if st.button("⬅️ Volver a Mis Archivos Guardados", key="btn_volver_archivos_guardados", use_container_width=True):
                    st.session_state.modo_limpieza_directa = False
                    st.session_state.mostrar_perfil = True
                    st.rerun()
            with col_v2:
                if st.button("🏠 Volver al Inicio", key="btn_volver_inicio_directo", use_container_width=True):
                    limpiar_estado_analisis()
                    st.rerun()
        else:
            modulo_ingestion()
            modulo_validacion()
            modulo_limpieza_y_dominio(gestor_usr)

if __name__ == "__main__":
    main()