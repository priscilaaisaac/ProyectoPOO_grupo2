import sys
from pathlib import Path  # Path sirve para trabajar con rutas de archivos y carpetas.

# Añadimos la raíz del proyecto al sys.path para resolver las importaciones de 'libs'.
# __file__ representa la ubicación del archivo actual.
# resolve() obtiene la ruta absoluta.
# parent.parent sube dos niveles desde el archivo actual para llegar a la raíz del proyecto.
raiz_proyecto = Path(__file__).resolve().parent.parent

# Verificamos que la raíz del proyecto no esté ya incluida en sys.path.
# Si no está, la agregamos para que Python pueda encontrar el paquete 'libs'.
if str(raiz_proyecto) not in sys.path:
    sys.path.append(str(raiz_proyecto))

import streamlit as st  # Streamlit permite construir la interfaz web de la aplicación.
import pandas as pd  # Pandas permite trabajar con los datos mediante DataFrames.
from libs.lector_datos import FactoryLectorDatos  # Importamos la Factory encargada de obtener el lector adecuado.
from libs.validador import ValidadorEsquema  # Importamos la clase encargada de validar el esquema de los datos.

# Configuración de estilos visuales de la aplicación.
# Se utiliza HTML y CSS dentro de Streamlit para modificar la apariencia de algunos elementos.
st.markdown("""
<style>

    /* Ocultar enlaces de ancla (íconos de URL/cadena) en todos los encabezados */
    [data-testid="stHeaderActionElements"],
    .stApp a[href^="#"],
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;}

    /* Modificamos el grosor de la letra de las opciones de selección. */
    div[data-baseweb="select"] span {
        font-weight: 500;}

    /* Modificamos el color de fondo de las etiquetas de los multiselect. */
    div[data-baseweb="tag"] {
        background-color: rgba(150, 150, 150, 0.15) !important;}

</style>
""", unsafe_allow_html=True)

# Definimos todos los atributos necesarios OBLIGATORIOS para trabajar.
# Los nombres de esta lista representan el esquema que espera el sistema,
# no necesariamente los nombres que tienen las columnas originales de los archivos cargados.
ATRIBUTOS_REQUERIDOS = [
    "aeropuerto_destino", "aeropuerto_origen", 
    "fechayhora_origen", 
    "fechayhora_destino", "fechayhora_origen_estipulado", 
    "fechayhora_destino_estipulado", "estado", 
    "capacidad_maxima_avion", "capacidad_usada_avion",
    "precio"]

# Definimos algunos atributos OPCIONALES.
# El sistema puede funcionar aunque estos atributos no sean asignados.
ATRIBUTOS_OPCIONALES = ["id_vuelo", "origen", "destino"]

# Título principal de la pantalla.
st.markdown(
    '<h1 style="font-size: 2.25rem;">Carga de datos</h1>',
    unsafe_allow_html=True)
st.write(
    "Selecciona tu origen de datos y mapea las columnas con el esquema del sistema.")

# st.session_state sirve para guardar y mantener valores entre las distintas
# ejecuciones que hace la aplicación cuando un usuario interactúa con ella.

if "origen_datos" not in st.session_state:
    # Guarda el tipo de origen elegido por el usuario: "CSV" o "SQL".
    st.session_state.origen_datos = None
if "df_crudo_completo" not in st.session_state:
    # Guarda el DataFrame completo obtenido desde el archivo o la base SQL.
    st.session_state.df_crudo_completo = None
if "columnas_disponibles" not in st.session_state:
    # Guarda una lista con los nombres de las columnas detectadas.
    st.session_state.columnas_disponibles = []

if "origen_por_columna" not in st.session_state:
    # Diccionario que permite saber de qué archivo o tabla proviene cada columna.
    st.session_state.origen_por_columna = {}

# Tenemos dos botones que dan la opción de subir archivos locales o conectarse a una base SQL.
col_btn1, col_btn2 = st.columns(2)

# Primera columna: opción para cargar archivos locales.
with col_btn1:
    if st.button("Subir archivo local", use_container_width=True):
        # Indicamos que el origen seleccionado será un archivo CSV/archivo local.
        st.session_state.origen_datos = "CSV"
        # Limpiamos los datos que pudieran haber quedado de una carga anterior.
        st.session_state.df_crudo_completo = None
        st.session_state.columnas_disponibles = []
        st.session_state.origen_por_columna = {}

# Segunda columna: opción para conectarse a una base SQL.
with col_btn2:
    if st.button("Conectar base SQL", use_container_width=True):
        # Indicamos que el origen seleccionado será una base de datos SQL.
        st.session_state.origen_datos = "SQL"
        # Limpiamos los datos que pudieran haber quedado de una carga anterior.
        st.session_state.df_crudo_completo = None
        st.session_state.columnas_disponibles = []
        st.session_state.origen_por_columna = {}

st.divider()

# ============================================================
# CARGA DESDE ARCHIVOS LOCALES
# ============================================================

# Si el usuario eligió trabajar con archivos locales, se muestra esta sección.
if st.session_state.origen_datos == "CSV":
    st.markdown(
        '<h3 style="font-size: 1.4rem;">Carga de archivos locales (múltiples permitidos)</h3>',
        unsafe_allow_html=True)
    # Mostramos una recomendación al usuario sobre las columnas repetidas.
    st.info(
        "Si agrega mas de un archivo, verifique que no se repitan las columnas. "
        "En caso de repetirse, elegir una para el análisis y elegir una para excluirla.")

    # Creamos el componente que permite seleccionar archivos.
    archivos_subidos = st.file_uploader(
        "Selecciona uno o más archivos",
        type=["csv", "txt", "xlsx", "xltx", "xltm"], # Definimos los tipos de archivos permitidos.
        accept_multiple_files=True) # Permitimos subir varios archivos a la vez.

    # Si el usuario subió uno o más archivos, comenzamos a procesarlos.
    if archivos_subidos:
        # Inicialmente suponemos que todos los archivos son válidos.
        archivos_validos = True
        # Se analiza cada archivo subido individualmente.
        for archivo in archivos_subidos:
            # Obtenemos el nombre del archivo y lo pasamos a minúsculas.
            # Esto permite comprobar su extensión sin importar mayúsculas/minúsculas.
            nombre_archivo = archivo.name.lower()

            # Intentamos leer la estructura del archivo.
            try:
                # Si el archivo es CSV o TXT, utilizamos pd.read_csv().
                if nombre_archivo.endswith(('.csv', '.txt')):
                    # Leemos solamente las primeras 5 filas.
                    # Esto se hace para comprobar que el archivo tenga una estructura válida sin cargar todavía todo el contenido.
                    temp_df = pd.read_csv(
                        archivo,
                        sep=r'[,;**\t\\-**]',
                        engine='python',
                        nrows=5)

                # Si el archivo es Excel, utilizamos pd.read_excel().
                elif nombre_archivo.endswith(('.xlsx', '.xltx', '.xltm')):
                    # Nuevamente leemos solamente las primeras 5 filas
                    # para comprobar la estructura.
                    temp_df = pd.read_excel(
                        archivo,
                        nrows=5)
                # Verificamos que el DataFrame no esté vacío y que tenga al menos una columna.
                if temp_df.empty or len(temp_df.columns) < 1:
                    # Si no cumple las condiciones mínimas, mostramos un error.
                    st.error(
                        f"El archivo '{archivo.name}' no cumple con la condición mínima "
                        "(requiere al menos 1 columna y encabezado).")
                    archivos_validos = False # Marcamos los archivos como inválidos.
                    break

            # Si ocurre cualquier error al intentar leer el archivo, se captura mediante esta excepción.
            except Exception as e:
                # Mostramos el error en la interfaz.
                st.error(
                    f"Error al leer la estructura de '{archivo.name}': {e}")
                archivos_validos = False # Marcamos los archivos como inválidos.
                break # Dejamos de analizar los archivos.


        # Si todos los archivos son válidos y el usuario presiona "Continuar",
        # comenzamos la carga definitiva de los datos.
        if archivos_validos and st.button("Continuar"):
            try:
                # Utilizamos nuestra Factory para obtener el lector correspondiente.
                # La pantalla principal no necesita saber cómo funciona internamente el lector de archivos. Solamente solicita un lector para "CSV".
                lector = FactoryLectorDatos.obtener_lector("CSV")
                dfs_completos = [] # Lista donde vamos a guardar los DataFrames de cada archivo.
                origen_map = {} # Diccionario que permitirá saber de qué archivo proviene cada columna.

                # Recorremos nuevamente todos los archivos.
                for archivo in archivos_subidos:
                    # Volvemos el cursor del archivo al principio.
                    # Esto es necesario porque anteriormente habíamos leído las primeras filas.
                    archivo.seek(0)

                    # Utilizamos el lector obtenido mediante la Factory para leer completamente el archivo.
                    df_comp = lector.leer(origen=archivo)

                    # Recorremos todas las columnas del DataFrame obtenido.
                    for col in df_comp.columns:
                        # Si la columna todavía no apareció en otro archivo, guardamos el nombre del archivo de origen.
                        if col not in origen_map:
                            origen_map[col] = archivo.name

                        # Si la columna ya apareció en otro archivo, agregamos también este archivo al registro.
                        else:
                            origen_map[col] += f", {archivo.name}"
# Esto es en caso de que un usuario tenga exactamente la misma columna de datos en dos archivos diferentes.

                    # Agregamos el DataFrame completo a nuestra lista.
                    dfs_completos.append(df_comp)


                # Unificamos todos los DataFrames en uno solo.
                st.session_state.df_crudo_completo = pd.concat(
                    dfs_completos,
                    ignore_index=True)

                # Obtenemos los nombres de las columnas del DataFrame final y los convertimos en una lista.
                st.session_state.columnas_disponibles = (
                    st.session_state.df_crudo_completo.columns.tolist())

                # Guardamos el diccionario que indica de qué archivo proviene cada columna.
                st.session_state.origen_por_columna = origen_map

                # Informamos al usuario que los archivos fueron procesados correctamente.
                st.success(
                    f"Se consolidaron {len(dfs_completos)} archivo(s) exitosamente.")

            # Capturamos cualquier error ocurrido durante el procesamiento.
            except Exception as e:
                st.error(
                    f"Error al procesar y unificar los archivos: {e}")

# ============================================================
# CARGA DESDE BASE DE DATOS SQL
# ============================================================

# Si el usuario elige trabajar con una base de datos SQL, se muestra esta sección.
elif st.session_state.origen_datos == "SQL":
    st.markdown(
        '<h3 style="font-size: 1.4rem;">Conexión a Base de Datos</h3>',
        unsafe_allow_html=True)
    
    # Pedimos al usuario la cadena de conexión a la base de datos.
    conexion_sql = st.text_input(
        "Cadena de conexión (URI):")

    # Pedimos el nombre de la tabla que queremos consultar.
    tabla_sql = st.text_input(
        "Nombre de la tabla:")

    # Si se ingresaron ambos datos y se presiona "Continuar", intentamos realizar la conexión y leer la tabla.
    if conexion_sql and tabla_sql and st.button("Continuar"):
        try:
            # Utilizamos la Factory para obtener el lector específico de SQL.
            lector = FactoryLectorDatos.obtener_lector("SQL")
            # Utilizamos el lector para obtener la tabla como DataFrame.
            df_sql = lector.leer(
                origen=conexion_sql,
                nombre_tabla=tabla_sql)
            # Guardamos el DataFrame obtenido en session_state.
            st.session_state.df_crudo_completo = df_sql

            # Guardamos la lista de columnas disponibles.
            st.session_state.columnas_disponibles = (
                df_sql.columns.tolist())

            # Guardamos de dónde proviene cada columna.
            # En este caso, todas provienen de la misma tabla SQL.
            st.session_state.origen_por_columna = {
                c: f"Tabla: {tabla_sql}"
                for c in df_sql.columns}
            st.success("¡Conexión SQL y carga exitosa!") # Informamos al usuario que la carga fue exitosa

        # Si ocurre algún error durante la conexión o lectura, mostramos el error en la interfaz.
        except Exception as e:

            st.error(
                f"Error al conectar o leer la tabla: {e}")

# ============================================================
# SELECCIÓN Y MAPEO DE VARIABLES
# ============================================================

# Recuperamos las columnas que fueron detectadas durante la carga.
columnas_usuario = st.session_state.columnas_disponibles

# Solo mostramos esta sección si existen columnas cargadas.
if columnas_usuario:
    st.divider()
    # Función utilizada para modificar cómo se muestran las columnas dentro de los selectbox y multiselect.
    def format_opcion_con_archivo(opcion):

        # Si la opción es "(No asignar)", simplemente la devolvemos.
        if opcion == "(No asignar)":
            return opcion

        # Buscamos de qué archivo o tabla proviene la columna.
        archivo_orig = st.session_state.get(
            "origen_por_columna",
            {}
        ).get(opcion, "")

        # Si encontramos el origen, mostramos la columna junto con su archivo.
        if archivo_orig:
            return f"{opcion}   ·  〔 {archivo_orig} 〕"

        # Si no encontramos información sobre el origen, simplemente mostramos el nombre de la columna.
        return opcion

    # Título de la sección para excluir variables.
    st.markdown(
        '<h3 style="font-size: 1.4rem;">Seleccione variables a excluir</h3>',
        unsafe_allow_html=True)

    # Permite seleccionar varias columnas que el usuario desea excluir.
    st.multiselect(
        "Variables a excluir:",

        # Las opciones disponibles son las columnas cargadas.
        options=columnas_usuario,

        # Utilizamos nuestra función para mostrar también el origen.
        format_func=format_opcion_con_archivo,

        # Guardamos las variables seleccionadas en session_state.
        key="variables_excluidas",

        # Texto mostrado cuando todavía no se seleccionó ninguna.
        placeholder="Seleccione las variables que desea descartar...")

    # Título de la sección donde se realizará el mapeo.
    st.markdown(
        '<h3 style="font-size: 1.4rem;">Seleccione variables a analizar</h3>',
        unsafe_allow_html=True)
    
    # Diccionario donde se almacenará el mapeo final: atributo esperado → columna real del archivo.
    mapeo_columnas = {}

    # Obtenemos las variables que el usuario decidió excluir.
    excluidas = st.session_state.get(
        "variables_excluidas",
        [])

    # Creamos una lista con las columnas que sí pueden utilizarse para realizar el mapeo.
    columnas_disponibles_mapeo = [
        c for c in columnas_usuario
        if c not in excluidas]

    # Esta lista almacenará las columnas que ya fueron asignadas a algún atributo para evitar asignar una misma columna dos veces.
    seleccionados_global = []

    # Recorremos tanto los atributos obligatorios como los opcionales.
    # "req_" se utilizará como prefijo para los atributos requeridos.
    # "opc_" se utilizará como prefijo para los atributos opcionales.
    for prefijo, lista_atributos in [
        ("req_", ATRIBUTOS_REQUERIDOS),
        ("opc_", ATRIBUTOS_OPCIONALES)]:

        # Recorremos cada atributo de la lista correspondiente.
        for attr in lista_atributos:
            # Creamos una clave única para cada selectbox.
            key = f"{prefijo}{attr}"
            # Verificamos si ese atributo ya tenía una selección guardada.
            # Si no, utilizamos "(No asignar)" como valor inicial.
            if key in st.session_state and st.session_state[key] != "(No asignar)":

                # Guardamos la columna seleccionada para evitar que pueda volver a utilizarse en otro atributo.
                seleccionados_global.append(
                    st.session_state[key])

    # Dividimos la pantalla en dos columnas: una para variables obligatorias y otra para variables opcionales.
    col1, col2 = st.columns(2)

    # ========================================================
    # VARIABLES OBLIGATORIAS
    # ========================================================

    with col1:
        st.markdown("**Variables Críticas (Obligatorias)**")
        # Recorremos todos los atributos obligatorios.
        for atributo in ATRIBUTOS_REQUERIDOS:
            # Creamos una clave única para este atributo.
            key = f"req_{atributo}"

            # Recuperamos el valor que ya tenía seleccionado. Si no había ninguno, utilizamos "(No asignar)".
            valor_actual = st.session_state.get(
                key,
                "(No asignar)")

            # Creamos las opciones disponibles para este atributo. No permitimos seleccionar columnas que ya hayan sido asignadas a otro atributo.
            # Sin embargo, permitimos mantener la selección actual mediante "or col == valor_actual".
            opciones_filtradas = (
                ["(No asignar)"] +
                [
                    col
                    for col in columnas_disponibles_mapeo
                    if col not in seleccionados_global
                    or col == valor_actual])

            # Creamos el menú desplegable para seleccionar qué columna del archivo corresponde al atributo del sistema.
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':",

                # Opciones disponibles para seleccionar.
                options=opciones_filtradas,

                # Mostramos también el archivo de origen.
                format_func=format_opcion_con_archivo,

                # Guardamos la selección en session_state.
                key=key)

    # ========================================================
    # VARIABLES OPCIONALES
    # ========================================================

    with col2:
        st.markdown("**Variables Opcionales**")
        # Recorremos todos los atributos opcionales.
        for atributo in ATRIBUTOS_OPCIONALES:

            # Creamos una clave única para este atributo.
            # Por ejemplo: opc_id_vuelo
            key = f"opc_{atributo}"

            # Recuperamos la selección anterior. Si no existe, utilizamos "(No asignar)".
            valor_actual = st.session_state.get(
                key,
                "(No asignar)")

            # Filtramos las columnas que ya fueron seleccionadas para evitar asignarlas nuevamente.
            opciones_filtradas = (
                ["(No asignar)"] +
                [
                    col
                    for col in columnas_disponibles_mapeo
                    if col not in seleccionados_global
                    or col == valor_actual])

            # Creamos el menú desplegable para seleccionar la columna correspondiente al atributo opcional.
            mapeo_columnas[atributo] = st.selectbox(
                f"Asignar a '{atributo}':",
                # Opciones disponibles.
                options=opciones_filtradas,
                # Mostramos el origen de cada columna.
                format_func=format_opcion_con_archivo,

                # Guardamos la selección en session_state.
                key=key)

    # ========================================================
    # VALIDACIÓN DEL CONTRATO
    # ========================================================

    # Cuando el usuario presiona este botón,
    # se validará que los datos cumplan con el esquema esperado.
    if st.button("Validar Contrato y Continuar"):

        try:
            # Hacemos una copia del DataFrame original.
            # Trabajamos sobre la copia para no modificar directamente
            # el DataFrame original almacenado en session_state.
            df_completo = st.session_state.df_crudo_completo.copy()

            # Si el usuario seleccionó variables para excluir, las eliminamos del DataFrame.
            if excluidas:
                df_completo = df_completo.drop(
                    columns=[
                        col
                        for col in excluidas
                        if col in df_completo.columns])

            # Creamos un objeto ValidadorEsquema.
            # Le pasamos:
            # 1. El DataFrame que queremos validar.
            # 2. El mapeo entre las columnas reales y el esquema.
            # 3. La lista de atributos obligatorios.
            validador = ValidadorEsquema(
                df_completo,
                mapeo_columnas,
                ATRIBUTOS_REQUERIDOS)

            # Ejecutamos el método validar().
            # Este método comprueba si los datos cumplen con el contrato definido.
            resultado_validacion = validador.validar()

            # Guardamos el DataFrame ya preparado.
            st.session_state.df_crudo = df_completo

            # Guardamos el mapeo realizado por el usuario.
            st.session_state.mapeo_columnas = mapeo_columnas

            # Si el resultado contiene la palabra "Advertencia", mostramos un mensaje de advertencia.
            if "Advertencia" in resultado_validacion:
                st.warning(
                    resultado_validacion)

            # Si no contiene "Advertencia", mostramos un mensaje de éxito.
            else:
                st.success(
                    resultado_validacion)

        # Capturamos específicamente los ValueError.
        # En este caso los mostramos como errores relacionados con el contrato.
        except ValueError as ve:
            st.error(
                f"Error de Contrato: {ve}")

        # Capturamos cualquier otro error inesperado.
        except Exception as e:

            st.error(
                f"Error crítico al procesar los datos: {e}")