"""
Módulo de Manual de Funcionamiento y Reglas Lógicas del Sistema.
Renderiza una vista estructurada y cronológica que documenta las políticas
de ingesta, calidad, limpieza, deducción operativa y simulación comercial.
"""

import streamlit as st


def vista_manual_funcionamiento():
    """
    Renderiza en pantalla completa la guía y documentación interactiva
    con las reglas de negocio y algoritmos del sistema ordenados cronológicamente.
    """
    col_titulo, col_boton = st.columns([0.8, 0.2])
    with col_titulo:
        st.markdown('<h1 style="font-size: 2.25rem;">📖 Manual de Funcionamiento</h1>', unsafe_allow_html=True)
        st.caption("Guía cronológica del flujo de trabajo, reglas lógicas y políticas de negocio de la aplicación.")
    with col_boton:
        st.write("")
        if st.button("⬅️ Volver", use_container_width=True, key="btn_volver_manual_top"):
            st.session_state.mostrar_manual = False
            st.rerun()

    st.markdown("""
    Bienvenido al **Manual de Funcionamiento del Sistema de Gestión y Análisis de Vuelos**.  
    A continuación se detallan las reglas y algoritmos que rigen el procesamiento de los datos,
    siguiendo estrictamente el orden en que se ejecutan durante el flujo de uso de la plataforma.
    """)
    st.divider()

    # -------------------------------------------------------------------------
    # 1. Ingesta y Consolidación de Datos
    # -------------------------------------------------------------------------
    st.markdown("### 1. Ingesta y Consolidación de Datos")
    st.info("""
    **Requisito Estricto de Columnas Coincidentes:**  
    A la hora de cargar **2 o más archivos simultáneamente**, es un requisito indispensable que los nombres
    de las columnas coincidan exactamente entre los archivos para garantizar un correcto acoplamiento de la información.
    """)

    with st.expander("ℹ️ Detalle de la lógica de acoplamiento y consolidación relacional", expanded=True):
        st.markdown(r"""
        - **Selección de Clave ID:** Antes de unificar los datos, la interfaz permite seleccionar la columna que actúa como identificador (`ID`) en cada archivo.
        - **Alineación por Ocurrencias (`_ocurrencia`):** El sistema asigna internamente una clave temporal secuencial (`df.groupby(ID).cumcount()`). Esto permite alinear los registros idénticos sin multiplicar filas por producto cartesiano ($n \times m$).
        - **Unión Externa (*Outer Join*):** Si un ID existe en varios archivos pero en filas desfasadas, el motor los hace coincidir horizontalmente en un único registro consolidado.
        - **Registros No Coincidentes:** Aquellos IDs que solo figuren en un archivo se concatenan verticalmente, rellenando con valores nulos (`NaN`) las columnas de los archivos donde no estaban presentes.
        - **Protección de Colisiones:** Columnas con el mismo nombre en diferentes archivos reciben sufijos numéricos automáticos (`columna (2)`, `columna (3)`) para preservar toda la información sin sobreescrituras.
        """)

    st.write("")

    # -------------------------------------------------------------------------
    # 2. Filtros de Calidad (Pre-Limpieza)
    # -------------------------------------------------------------------------
    st.markdown("### 2. Filtros de Calidad (Pre-Limpieza)")
    st.warning("""
    **Regla de Poda por Umbral de Nulos:**  
    Cualquier registro que contenga un **50% o más de sus atributos en estado desconocido o nulo** 
    es eliminado automáticamente del sistema antes de enviarlo al pipeline de limpieza final.
    """)

    with st.expander("ℹ️ Detalle del filtro de calidad pos-validación", expanded=True):
        st.markdown(r"""
        - **Momento de Ejecución:** Se ejecuta inmediatamente después de que el usuario confirma el mapeo oprimiendo *"Validar contrato y continuar"*.
        - **Normalización Previa:** Primero se estandarizan todas las variantes de vacío (`""`, `" "`, `"nan"`, `"null"`, `"none"`, `"N/A"`, `"-"`, `"."`) a valores ausentes (`NaN`).
        - **Cálculo de Porcentaje:** Para cada fila individual, se calcula:
          $$\text{Porcentaje de Faltantes} = \frac{\text{Cantidad de Columnas Nulas en la Fila}}{\text{Total de Columnas del Dataset}}$$
        - **Criterio de Exclusión:** Si $\text{Porcentaje de Faltantes} \ge 0.50$ (50%), el registro se descarta por carecer de masa crítica suficiente para el análisis estadístico o imputación fiable.
        """)

    st.write("")

    # -------------------------------------------------------------------------
    # 3. Tratamiento de Valores Categóricos
    # -------------------------------------------------------------------------
    st.markdown("### 3. Tratamiento de Valores Categóricos")
    st.markdown("""
    **Asignación de Valor Canónico:**  
    Internamente, a todos los campos de texto o categóricos que ingresen vacíos, en blanco o con etiquetas
    de error se les asigna por defecto el valor **`'Desconocido'`**.
    """)

    with st.expander("ℹ️ Detalle de saneamiento categórico y ubicaciones", expanded=False):
        st.markdown("""
        - **Columnas Afectadas:** Aeropuertos (`aeropuerto_origen`, `aeropuerto_destino`), ciudades (`origen`, `destino`) y textos descriptivos.
        - **Limpieza de Espacios:** Se eliminan espacios en blanco sobrantes en extremos (`strip()`) y se sustituyen cadenas vacías o pseudo-nulas por `'Desconocido'`.
        - **Filtrado en Reportes:** Al generar rutas para análisis (`Origen -> Destino`), cualquier ruta que contenga la palabra `'Desconocido'` es excluida automáticamente de los selectores comerciales para no distorsionar las métricas de rutas operativas reales.
        """)

    st.write("")

    # -------------------------------------------------------------------------
    # 4. Deducción de Estados de Vuelo
    # -------------------------------------------------------------------------
    st.markdown("### 4. Deducción de Estados de Vuelo")
    st.markdown("""
    **Algoritmo de Deducción Inteligente:**  
    Los estados de los vuelos faltantes se calculan y registran automáticamente ejecutando un algoritmo
    que evalúa las **fechas y horas reales de operación frente a las estipuladas**.
    """)

    with st.expander("ℹ️ Detalle de las 8 reglas del Imputador de Estado Inteligente", expanded=True):
        st.markdown(r"""
        El motor evalúa las diferencias temporales $\Delta t$ entre las horas reales y estipuladas con una tolerancia estándar de **10 minutos**:

        | Estado Deducido | Condición Operativa |
        | :--- | :--- |
        | **Atrasado** | Si el despegue real supera en **más de 10 minutos** la hora estipulada, o si el aterrizaje real excede en más de 10 minutos la hora estipulada de llegada. |
        | **A tiempo** | Si la salida y llegada reales coinciden con las estipuladas dentro del margen de tolerancia admisible (diferencia $\le 10$ minutos). |
        | **Cancelado** | Si el vuelo contaba con fecha y hora de despegue estipulada, pero no registra ninguna fecha real de operación (ni salida ni llegada). |
        | **Exitoso** | Si el vuelo cuenta con fechas reales de operación pero no se disponía de programación estipulada de partida/llegada. |
        | **Desconocido** | Si el registro carece por completo de fechas estipuladas y reales. |
        """)

    st.write("")

    # -------------------------------------------------------------------------
    # 5. Cálculo de Capacidades (Factor de Ocupación)
    # -------------------------------------------------------------------------
    st.markdown("### 5. Cálculo de Capacidades (Factor de Ocupación)")
    st.markdown("""
    **Imputación Proporcional de Aeronaves:**  
    El sistema calcula el **factor de ocupación promedio** observado en el histórico para rellenar
    de forma bidireccional los datos faltantes en la capacidad de los aviones.
    """)

    with st.expander("ℹ️ Detalle matemático del Factor de Ocupación", expanded=True):
        st.markdown(r"""
        1. **Fórmula del Factor Individual:**  
           Para cada vuelo que posea ambos datos válidos:
           $$\text{Factor de Ocupación} = \frac{\text{Capacidad Usada (pasajeros)}}{\text{Capacidad Máxima (asientos)}}$$
        2. **Cálculo del Factor Promedio:**  
           Se promedian todos los factores válidos de la flota. Si no existiera ningún registro completo, se utiliza un factor estándar por defecto de **$0.75$ ($75\%$)**.
        3. **Imputación Bidireccional:**  
           - **Si falta la Capacidad Usada:** $\text{Capacidad Usada} = \text{round}(\text{Capacidad Máxima} \times \text{Factor Promedio})$.
           - **Si falta la Capacidad Máxima:** $\text{Capacidad Máxima} = \text{round}\left(\frac{\text{Capacidad Usada}}{\text{Factor Promedio}}\right)$.
        4. **Restricción de Consistencia Física:**  
           La capacidad usada imputada **nunca puede ser mayor a la capacidad máxima** de la aeronave ($\text{usada} \le \text{máxima}$). Si por redondeo esto ocurriera, se ajusta automáticamente al valor de la capacidad máxima.
        """)

    st.write("")

    # -------------------------------------------------------------------------
    # 6. Ajustes de Demanda en el Simulador de Precios
    # -------------------------------------------------------------------------
    st.markdown("### 6. Ajustes de Demanda en el Simulador de Precios")
    st.markdown("""
    **Políticas Comerciales de Presión de Ocupación:**  
    El motor de simulación de tarifas dinámicas evalúa el nivel de ocupación promedio del segmento analizado
    y aplica estrictamente las siguientes reglas de negocio:
    """)

    st.markdown(r"""
    - 📈 **Recargo del +12%:** Se aplica si la ocupación del segmento **supera el 80%** ($\ge 80\%$), debido a la alta demanda y escasez de asientos disponibles.
    - 📉 **Descuento del -8%:** Se aplica si la ocupación **cae por debajo del 50%** ($< 50\%$), funcionando como un incentivo comercial y descuento promocional para estimular el llenado de la cabina.
    - ⚖️ **Tarifa Neutra (0%):** Se mantiene **sin alterar el precio base** si la ocupación se sitúa **entre el 50% y el 80%** ($50\% \le \text{Ocupación} < 80\%$), considerándose un nivel de demanda moderado y equilibrado.
    """)

    with st.expander("ℹ️ Fórmula completa del Precio Dinámico Sugerido", expanded=False):
        st.markdown(r"""
        El precio sugerido final integra riesgo logístico, presión de demanda y margen comercial:
        
        $$\text{Precio Final} = \text{Precio Base} \times (1 + \text{Riesgo Logístico}) \times (1 + \text{Factor Demanda}) \times (1 + \text{Margen Comercial})$$

        - **Riesgo Logístico:** $P(\text{Atrasado}) \times \text{Costo Retraso} + P(\text{Cancelado}) \times \text{Costo Cancelación}$.
        - **Factor Demanda:** $+0.12$ (alta), $-0.08$ (baja) o $0.00$ (moderada).
        - **Margen Comercial:** Margen de beneficio objetivo configurado por el analista (por defecto $+10\%$).
        """)

    st.divider()

    # Botón inferior para volver
    col_izq, col_der = st.columns([0.8, 0.2])
    with col_der:
        if st.button("⬅️ Volver al Inicio", use_container_width=True, key="btn_volver_manual_bottom"):
            st.session_state.mostrar_manual = False
            st.rerun()
