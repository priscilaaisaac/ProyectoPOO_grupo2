import sys
from pathlib import Path
import streamlit as st  # type: ignore[import-not-found]

# Configuración de rutas para importar las librerías
raiz_proyecto = Path(__file__).resolve().parent.parent
if str(raiz_proyecto) not in sys.path:
    sys.path.append(str(raiz_proyecto))

from modules.gestor_usuarios import GestorUsuarios

# Importaciones modulares locales
from apps.modulo_usuario import modulo_usuario, vista_perfil_pantalla_completa
from apps.modulo_ingestion import modulo_ingestion
from apps.modulo_validacion import modulo_validacion
from apps.modulo_limpieza import modulo_limpieza_y_dominio

def inicializar_estado():
    """Inicializa todas las variables de sesión globales necesarias."""
    claves_iniciales = {
        "usuario_activo": None, 
        "origen_datos": None,
        "df_crudo_completo": None, 
        "columnas_disponibles": [],
        "origen_por_columna": {}, 
        "contrato_validado": False,
        "mostrar_perfil": False,
        "modo_limpieza_directa": False
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
        /* Traducir límite de 200MB y tipos de archivo ocultando TODO el contenido original */
        [data-testid="stFileUploaderDropzoneInstructions"] > * {
            display: none !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] {
            font-size: 0px !important;
            color: transparent !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"]::after {
            content: "200MB por archivo • CSV, TXT, XLSX, XLTX, XLTM";
            font-size: 14px !important;
            color: rgba(250, 250, 250, 0.7) !important; 
            display: block !important;
            visibility: visible !important;
        }
    </style>
    """, unsafe_allow_html=True)

def main():
    """Ejecuta los módulos de la aplicación secuencialmente."""
    inicializar_estado()
    aplicar_estilos()
    
    gestor_usr = GestorUsuarios()
    
    # La barra lateral se renderiza siempre
    modulo_usuario(gestor_usr)
    
    # Lógica de navegación principal (Router)
    if st.session_state.get("mostrar_perfil", False) and st.session_state.usuario_activo:
        vista_perfil_pantalla_completa(gestor_usr)
    else:
        if st.session_state.get("modo_limpieza_directa", False):
            # Si venimos del perfil con un archivo cargado, vamos directo a limpiar
            modulo_limpieza_y_dominio(gestor_usr)
            if st.button("Volver al Inicio", use_container_width=True):
                st.session_state.modo_limpieza_directa = False
                st.session_state.df_crudo = None
                st.session_state.contrato_validado = False
                st.rerun()
        else:
            modulo_ingestion()
            modulo_validacion()
            modulo_limpieza_y_dominio(gestor_usr)

if __name__ == "__main__":
    main()