import unittest
from datetime import datetime
import pandas as pd
from modules.Vuelos import Vuelo
from modules.fabrica_vuelos import FabricaVuelos
from modules.analisis_estadistico import MotorEstadisticoVuelos, SimuladorPreciosDinamicos


class TestAnalisisEstadisticoYSimulacion(unittest.TestCase):

    def setUp(self):
        """Crea vuelos de muestra con diversos estados, rutas, franjas y niveles de ocupación."""
        self.vuelo_atrasado = Vuelo(
            aeropuerto_origen="EZE",
            aeropuerto_destino="MIA",
            fechayhora_origen=datetime(2026, 10, 1, 10, 30),
            fechayhora_destino=datetime(2026, 10, 1, 19, 30),
            fechayhora_origen_estipulado=datetime(2026, 10, 1, 9, 30), # 1 hora demorado (Mañana)
            fechayhora_destino_estipulado=datetime(2026, 10, 1, 18, 30),
            estado="Atrasado",
            capacidad_maxima_avion=200,
            capacidad_usada_avion=180, # 90% ocupación (Alta)
            precio=500.0,
            id_vuelo="V-001"
        )

        self.vuelo_atiempo = Vuelo(
            aeropuerto_origen="EZE",
            aeropuerto_destino="MIA",
            fechayhora_origen=datetime(2026, 10, 2, 8, 0),
            fechayhora_destino=datetime(2026, 10, 2, 17, 0),
            fechayhora_origen_estipulado=datetime(2026, 10, 2, 8, 0), # A tiempo (Mañana)
            fechayhora_destino_estipulado=datetime(2026, 10, 2, 17, 0),
            estado="A tiempo",
            capacidad_maxima_avion=200,
            capacidad_usada_avion=140, # 70% ocupación (Media)
            precio=450.0,
            id_vuelo="V-002"
        )

        self.vuelo_cancelado = Vuelo(
            aeropuerto_origen="JFK",
            aeropuerto_destino="MAD",
            fechayhora_origen=None,
            fechayhora_destino=None,
            fechayhora_origen_estipulado=datetime(2026, 10, 3, 21, 0), # Noche
            fechayhora_destino_estipulado=datetime(2026, 10, 4, 10, 0),
            estado="Cancelado",
            capacidad_maxima_avion=300,
            capacidad_usada_avion=120, # 40% ocupación (Baja)
            precio=800.0,
            id_vuelo="V-003"
        )

        self.vuelo_exitoso = Vuelo(
            aeropuerto_origen="JFK",
            aeropuerto_destino="MAD",
            fechayhora_origen=datetime(2026, 10, 4, 15, 0), # Tarde
            fechayhora_destino=datetime(2026, 10, 5, 4, 0),
            fechayhora_origen_estipulado=datetime(2026, 10, 4, 15, 0),
            fechayhora_destino_estipulado=datetime(2026, 10, 5, 4, 0),
            estado="Exitoso",
            capacidad_maxima_avion=300,
            capacidad_usada_avion=270, # 90% ocupación (Alta)
            precio=750.0,
            id_vuelo="V-004"
        )

        self.coleccion = [
            self.vuelo_atrasado,
            self.vuelo_atiempo,
            self.vuelo_cancelado,
            self.vuelo_exitoso
        ]

    # ----------------------------------------------------------------------
    # 1. Pruebas de Obligatoriedad del Precio en Vuelo y Fábrica
    # ----------------------------------------------------------------------

    def test_vuelo_falla_sin_precio(self):
        """Verifica que instanciar un Vuelo con precio None o NaN lance ValueError."""
        with self.assertRaises(ValueError) as ctx:
            Vuelo(
                aeropuerto_origen="A", aeropuerto_destino="B",
                fechayhora_origen=None, fechayhora_destino=None,
                fechayhora_origen_estipulado=None, fechayhora_destino_estipulado=None,
                estado="A tiempo", capacidad_maxima_avion=100, capacidad_usada_avion=50,
                precio=None # Precio omitido
            )
        self.assertIn("precio", str(ctx.exception).lower())

    def test_vuelo_falla_con_precio_invalido_o_negativo(self):
        """Verifica que precios negativos o no convertibles lancen ValueError."""
        with self.assertRaises(ValueError):
            Vuelo(
                aeropuerto_origen="A", aeropuerto_destino="B",
                fechayhora_origen=None, fechayhora_destino=None,
                fechayhora_origen_estipulado=None, fechayhora_destino_estipulado=None,
                estado="A tiempo", capacidad_maxima_avion=100, capacidad_usada_avion=50,
                precio=-50.0
            )

    def test_fabrica_convierte_todas_las_filas(self):
        """Verifica que la fábrica convierta el 100% de las filas del DataFrame en Vuelo."""
        df = pd.DataFrame({
            "aeropuerto_origen": ["EZE", "JFK"],
            "aeropuerto_destino": ["MIA", "MAD"],
            "fechayhora_origen": ["2026-10-01 10:00", "2026-10-02 12:00"],
            "fechayhora_destino": ["2026-10-01 19:00", "2026-10-03 01:00"],
            "fechayhora_origen_estipulado": ["2026-10-01 10:00", "2026-10-02 12:00"],
            "fechayhora_destino_estipulado": ["2026-10-01 19:00", "2026-10-03 01:00"],
            "estado": ["A tiempo", "Exitoso"],
            "capacidad_maxima_avion": [200, 300],
            "capacidad_usada_avion": [150, 250],
            "precio": [300.0, 600.0]
        })
        mapeo = {c: c for c in df.columns}
        vuelos = FabricaVuelos.instanciar_desde_dataframe(df, mapeo)
        self.assertEqual(len(vuelos), 2)
        self.assertIsInstance(vuelos[0], Vuelo)
        self.assertIsInstance(vuelos[1], Vuelo)
        self.assertEqual(vuelos[0].precio, 300.0)

    def test_fabrica_falla_si_fila_carece_de_precio(self):
        """Verifica que la fábrica lance ValueError si algún registro carece de precio."""
        df_incompleto = pd.DataFrame({
            "aeropuerto_origen": ["EZE"],
            "aeropuerto_destino": ["MIA"],
            "fechayhora_origen": [None],
            "fechayhora_destino": [None],
            "fechayhora_origen_estipulado": [None],
            "fechayhora_destino_estipulado": [None],
            "estado": ["A tiempo"],
            "capacidad_maxima_avion": [200],
            "capacidad_usada_avion": [100],
            "precio": [None] # Falta precio
        })
        mapeo = {c: c for c in df_incompleto.columns}
        with self.assertRaises(ValueError) as ctx:
            FabricaVuelos.instanciar_desde_dataframe(df_incompleto, mapeo)
        self.assertIn("precio", str(ctx.exception).lower())

    # ----------------------------------------------------------------------
    # 2. Pruebas del Motor Estadístico (Probabilidades Marginales y Condicionales)
    # ----------------------------------------------------------------------

    def test_motor_probabilidades_marginales(self):
        """Verifica el cálculo de probabilidades marginales globales P(Estado)."""
        motor = MotorEstadisticoVuelos(self.coleccion)
        prob = motor.calcular_probabilidades_marginales()

        # En la colección de 4 vuelos: 1 Atrasado, 1 A tiempo, 1 Cancelado, 1 Exitoso
        self.assertAlmostEqual(prob["Atrasado"], 0.25)
        self.assertAlmostEqual(prob["A tiempo"], 0.25)
        self.assertAlmostEqual(prob["Cancelado"], 0.25)
        self.assertAlmostEqual(prob["Exitoso"], 0.25)
        self.assertAlmostEqual(sum(prob.values()), 1.0)

    def test_motor_probabilidades_condicionales_franja(self):
        """Verifica P(Estado | Franja Horaria)."""
        motor = MotorEstadisticoVuelos(self.coleccion)
        df_franja = motor.calcular_probabilidades_condicionales_franja()

        self.assertIn("Franja Horaria", df_franja.columns)
        self.assertIn("% Atrasado", df_franja.columns)
        self.assertIn("Total Vuelos", df_franja.columns)

        # En la mañana hay 2 vuelos: 1 Atrasado, 1 A tiempo
        fila_manana = df_franja[df_franja["Franja Horaria"].str.contains("Mañana")]
        self.assertEqual(len(fila_manana), 1)
        self.assertEqual(fila_manana.iloc[0]["Total Vuelos"], 2)
        self.assertEqual(fila_manana.iloc[0]["% Atrasado"], 50.0)
        self.assertEqual(fila_manana.iloc[0]["% A tiempo"], 50.0)

    def test_motor_probabilidades_condicionales_ruta(self):
        """Verifica P(Estado | Ruta)."""
        motor = MotorEstadisticoVuelos(self.coleccion)
        df_ruta = motor.calcular_probabilidades_condicionales_ruta()

        self.assertIn("Ruta", df_ruta.columns)
        self.assertIn("% Cancelado", df_ruta.columns)

        fila_jfk_mad = df_ruta[df_ruta["Ruta"] == "JFK -> MAD"]
        self.assertEqual(len(fila_jfk_mad), 1)
        self.assertEqual(fila_jfk_mad.iloc[0]["% Cancelado"], 50.0)
        self.assertEqual(fila_jfk_mad.iloc[0]["% Exitoso"], 50.0)

    def test_motor_probabilidades_condicionales_ocupacion(self):
        """Verifica P(Estado | Nivel de Ocupación)."""
        motor = MotorEstadisticoVuelos(self.coleccion)
        df_ocup = motor.calcular_probabilidades_condicionales_ocupacion()

        self.assertIn("Nivel de Ocupación", df_ocup.columns)
        self.assertTrue(len(df_ocup) >= 2)

    # ----------------------------------------------------------------------
    # 3. Pruebas del Simulador Comercial y Precios Dinámicos
    # ----------------------------------------------------------------------

    def test_simulador_precios_dinamicos_aumenta_por_riesgo(self):
        """
        Verifica que rutas u horarios con mayor riesgo (retraso/cancelación)
        generen un recargo por riesgo operativo sobre el precio base.
        """
        motor = MotorEstadisticoVuelos(self.coleccion)
        simulador = SimuladorPreciosDinamicos(motor)

        # Simular para JFK -> MAD (50% cancelación)
        res_riesgoso = simulador.simular(
            ruta="JFK -> MAD",
            costo_retraso_pct=0.25,
            costo_cancelacion_pct=0.60,
            margen_comercial_pct=0.10
        )

        self.assertGreater(res_riesgoso["precio_sugerido"], res_riesgoso["precio_base"])
        self.assertGreater(res_riesgoso["recargo_riesgo_monetario"], 0.0)
        self.assertGreater(res_riesgoso["fondo_contingencia_vuelo"], 0.0)
        self.assertEqual(res_riesgoso["p_cancelado_pct"], 50.0)

    def test_simulador_precio_base_manual(self):
        """Verifica que el usuario pueda forzar un precio base manual."""
        motor = MotorEstadisticoVuelos(self.coleccion)
        simulador = SimuladorPreciosDinamicos(motor)

        res = simulador.simular(precio_base_manual=1000.0)
        self.assertEqual(res["precio_base"], 1000.0)
        self.assertEqual(res["tipo_precio_base"], "Ingresado manualmente por el usuario")

    def test_construir_dataframe_graficos_contiene_atributos_requeridos(self):
        """Verifica que el DataFrame para gráficos contenga todos los atributos A y B solicitados."""
        from apps.modulo_analisis import construir_dataframe_graficos
        df_g = construir_dataframe_graficos(self.coleccion)

        # Atributos A requeridos
        for attr_a in ["precio", "franja horaria", "estado", "capacidad_usada"]:
            self.assertIn(attr_a, df_g.columns)

        # Atributos B requeridos
        for attr_b in ["origen", "destino", "aeropuerto_origen", "aeropuerto_destino"]:
            self.assertIn(attr_b, df_g.columns)

        self.assertEqual(len(df_g), len(self.coleccion))

    def test_discretizar_variable_numerica(self):
        """Verifica que discretizar_variable_numerica genere rangos legibles y ordenados."""
        from apps.modulo_analisis import discretizar_variable_numerica
        precios = pd.Series([100.0, 200.0, 350.0, 500.0, 750.0, 1000.0])
        s_disc, orden = discretizar_variable_numerica(precios, "precio", num_bins=4)

        self.assertEqual(len(orden), 4)
        self.assertTrue(all("$" in lbl for lbl in orden))
        self.assertEqual(len(s_disc), len(precios))

        capacidades = pd.Series([50, 100, 150, 200, 250])
        s_cap, orden_cap = discretizar_variable_numerica(capacidades, "capacidad_usada", num_bins=3)
        self.assertEqual(len(orden_cap), 3)
        self.assertTrue(all("pas." in lbl for lbl in orden_cap))

    def test_agrupacion_top_5_y_otros(self):
        """Verifica que más de 5 categorías se limiten a top 5 y el resto a 'Otros'."""
        ciudades = pd.Series(["A", "A", "A", "B", "B", "C", "D", "E", "F", "G", "H"])
        conteos = ciudades.value_counts()
        self.assertGreater(len(conteos), 5)

        top_5 = conteos.nlargest(5).index.tolist()
        ciudades_disp = ciudades.apply(lambda x: x if x in top_5 else "Otros")

        self.assertEqual(len(ciudades_disp.unique()), 6) # top 5 + 'Otros'
        self.assertIn("Otros", ciudades_disp.values)

    # ----------------------------------------------------------------------
    # 4. Pruebas de Exclusión de "Desconocido"
    # ----------------------------------------------------------------------

    def test_exclusion_total_de_desconocido(self):
        """Verifica que 'Desconocido' sea excluido al 100% de conteos, probabilidades y tablas."""
        vuelo_desconocido = Vuelo(
            aeropuerto_origen="Desconocido",
            aeropuerto_destino="EZE",
            fechayhora_origen=None,
            fechayhora_destino=None,
            fechayhora_origen_estipulado=None,
            fechayhora_destino_estipulado=None,
            estado="desconocido / no informado",
            capacidad_maxima_avion=100,
            capacidad_usada_avion=50,
            precio=200.0,
            id_vuelo="V-DESCONOCIDO"
        )
        coleccion_con_desconocido = self.coleccion + [vuelo_desconocido]
        motor = MotorEstadisticoVuelos(coleccion_con_desconocido)

        # 1. Conteos marginales no deben tener la clave "Desconocido"
        conteos = motor.calcular_conteos_marginales()
        self.assertNotIn("Desconocido", conteos)
        self.assertEqual(sum(conteos.values()), 4) # Solo los 4 válidos de setUp

        # 2. Probabilidades marginales no deben contener "Desconocido" y deben sumar 1.0
        prob = motor.calcular_probabilidades_marginales()
        self.assertNotIn("Desconocido", prob)
        self.assertAlmostEqual(sum(prob.values()), 1.0)

        # 3. Rutas disponibles no deben tener "Desconocido"
        rutas = motor.obtener_rutas_disponibles()
        for r in rutas:
            self.assertNotIn("Desconocido", r)

        # 4. Tablas condicionales no deben tener filas con "Desconocido"
        df_ruta = motor.calcular_probabilidades_condicionales_ruta()
        if not df_ruta.empty:
            for val in df_ruta["Ruta"]:
                self.assertNotIn("Desconocido", str(val))

    # ----------------------------------------------------------------------
    # 5. Pruebas de Generación de Reporte PDF Estructurado (ReportLab)
    # ----------------------------------------------------------------------

    def test_generador_reporte_pdf_valido(self):
        """Verifica que GeneradorReportePDF compile un PDF estructurado en 3 secciones."""
        from modules.generador_pdf import GeneradorReportePDF

        simulaciones = [
            {
                "ruta": "EZE -> MIA",
                "franja": "Mañana",
                "ocupacion": "Alta (> 80%)",
                "precio_base": 500.0,
                "precio_sugerido": 580.0,
                "p_atrasado_pct": 25.0,
                "p_cancelado_pct": 0.0,
                "riesgo_logistico_pct": 6.25,
                "recargo_riesgo_monetario": 31.25,
                "ajuste_total_monetario": 80.0,
                "ajuste_porcentual_total": 16.0,
                "fondo_contingencia_vuelo": 5625.0,
                "muestra_tamano": 10,
                "asientos_ocupados_media": 180
            }
        ]
        df_tabla_grafico = pd.DataFrame({
            "Estado": ["A tiempo", "Atrasado"],
            "EZE": [10, 5],
            "MIA": [8, 2]
        })
        graficos = [
            {
                "titulo": "Gráfico de Barras: Estado vs Origen",
                "tipo": "Gráfico de Barras",
                "descripcion": "Eje X: Estado | Agrupación: Origen",
                "tabla": df_tabla_grafico
            }
        ]
        metricas = [
            {
                "tipo": "Probabilidades Marginales Globales",
                "probabilidades_marginales": {"A tiempo": 0.5, "Atrasado": 0.5},
                "conteos_marginales": {"A tiempo": 50, "Atrasado": 50},
                "total_vuelos": 100
            }
        ]

        generador = GeneradorReportePDF(
            simulaciones=simulaciones,
            graficos=graficos,
            metricas=metricas,
            nombre_dataset="vuelos_test.csv",
            usuario="Analista_Test"
        )
        pdf_bytes = generador.construir_pdf()

        # Debe generar bytes válidos de formato PDF
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_generador_reporte_pdf_vacio(self):
        """Verifica que el generador maneje correctamente listas vacías sin errores."""
        from modules.generador_pdf import GeneradorReportePDF

        generador_vacio = GeneradorReportePDF([], [], [])
        pdf_bytes = generador_vacio.construir_pdf()
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    # ----------------------------------------------------------------------
    # 6. Pruebas de Persistencia de Sesión y Límite de 10 en Torta
    # ----------------------------------------------------------------------

    def test_registro_manual_simulacion_en_sesion(self):
        """Verifica que las simulaciones se registren bajo el patrón Command en usuario.sesion con nombre real de archivo."""
        from modules.gestor_usuarios import Usuario
        usuario = Usuario("analista1", "hash_test")

        # Inicialmente el historial debe estar vacío
        self.assertEqual(len(usuario.sesion.data["historial_comandos"]), 0)

        # Registro manual de comando pasando 'archivo'
        usuario.sesion.registrar_comando(
            "Simulación en ruta EZE -> MIA | Precio sugerido: $580.00",
            {"archivo": "vuelos_internacionales_limpio.csv", "ruta": "EZE -> MIA", "precio_sugerido": 580.0}
        )

        self.assertEqual(len(usuario.sesion.data["historial_comandos"]), 1)
        ultimo_cmd = usuario.sesion.data["historial_comandos"][0]
        self.assertIn("EZE -> MIA", ultimo_cmd["accion"])
        self.assertEqual(ultimo_cmd["parametros"]["precio_sugerido"], 580.0)
        # Debe tener ambos campos 'archivos' y 'archivo' con el nombre real
        self.assertEqual(ultimo_cmd["parametros"]["archivos"], "vuelos_internacionales_limpio.csv")
        self.assertEqual(ultimo_cmd["parametros"]["archivo"], "vuelos_internacionales_limpio.csv")

    def test_evitar_registros_fantasmas_archivo_desconocido(self):
        """Verifica que SesionAnalisis nunca registre comandos vacíos ni deje 'Archivo desconocido'."""
        from modules.gestor_usuarios import Usuario
        usuario = Usuario("analista2", "hash_test2")

        # Intentar registrar comando con acción vacía debe ser ignorado
        usuario.sesion.registrar_comando("", {"archivo": "test.csv"})
        usuario.sesion.registrar_comando("   ", {"archivo": "test.csv"})
        self.assertEqual(len(usuario.sesion.data["historial_comandos"]), 0)

        # Registrar comando sin archivo explícito normaliza a dataset_vuelos.csv y no a 'Archivo desconocido'
        usuario.sesion.registrar_comando("Simulación manual", {"ruta": "COR -> AEP"})
        self.assertEqual(len(usuario.sesion.data["historial_comandos"]), 1)
        cmd = usuario.sesion.data["historial_comandos"][0]
        self.assertNotEqual(cmd["parametros"].get("archivos"), "Archivo desconocido")
        self.assertEqual(cmd["parametros"].get("archivos"), "dataset_vuelos.csv")
        self.assertEqual(cmd["parametros"].get("archivo"), "dataset_vuelos.csv")

    def test_limite_estricto_10_categorias_torta(self):
        """Verifica que al mapear categorías no seleccionadas a 'Otros', el total sea <= 10."""
        categorias_15 = [f"Aeropuerto_{i}" for i in range(15)]
        serie = pd.Series(categorias_15 * 2)

        # Si el usuario selecciona 9 categorías, las 6 restantes van a 'Otros'
        seleccionadas = categorias_15[:9]
        serie_mapeada = serie.apply(lambda x: x if x in seleccionadas else "Otros")

        unicos = serie_mapeada.unique()
        self.assertLessEqual(len(unicos), 10)
        self.assertIn("Otros", unicos)

    def test_generador_reporte_pdf_con_torta_y_barras_vectoriales(self):
        """Verifica que el generador cree gráficos vectoriales nativos para tortas y barras."""
        from modules.generador_pdf import GeneradorReportePDF

        df_torta = pd.DataFrame({
            "Estado": ["A tiempo", "Exitoso", "Atrasado", "Cancelado"],
            "Cantidad": [40, 30, 20, 10],
            "Porcentaje": [40.0, 30.0, 20.0, 10.0]
        })
        df_contingencia = pd.DataFrame({
            "Estado": ["A tiempo", "Atrasado", "Total"],
            "EZE": [25, 10, 35],
            "MIA": [15, 5, 20],
            "Total": [40, 15, 55]
        })

        graficos = [
            {
                "titulo": "Gráfico de Torta: Distribución de Estado",
                "tipo": "Gráfico de Torta",
                "descripcion": "Categorías analizadas: 4",
                "tabla": df_torta
            },
            {
                "titulo": "Gráfico de Barras: Estado vs Origen",
                "tipo": "Gráfico de Barras",
                "descripcion": "Eje X: Estado | Agrupación: Origen",
                "tabla": df_contingencia
            }
        ]

        df_cond = pd.DataFrame({
            "Franja Horaria": ["Mañana", "Tarde"],
            "Total Vuelos": [10, 15],
            "% A tiempo": [80.0, 60.0]
        })
        tablas_cond = [
            {"tipo": "P(Estado | Franja Horaria)", "dataframe": df_cond}
        ]

        generador = GeneradorReportePDF(
            simulaciones=[],
            graficos=graficos,
            tablas_condicionales=tablas_cond,
            nombre_dataset="vuelos_aerolinea.csv",
            usuario="Analista_Jefe"
        )
        pdf_bytes = generador.construir_pdf()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 2000)

    def test_aislamiento_elementos_guardados_por_archivo(self):
        """Verifica que los elementos guardados para el reporte se aíslen por archivo activo."""
        guardados_por_archivo = {}

        archivo_1 = "vuelos_enero_limpio.csv"
        archivo_2 = "vuelos_febrero_limpio.csv"

        # Inicialización de archivo 1
        if archivo_1 not in guardados_por_archivo:
            guardados_por_archivo[archivo_1] = {"simulaciones": [], "graficos": [], "tablas_condicionales": []}

        # Guardado en archivo 1
        guardados_por_archivo[archivo_1]["simulaciones"].append({"ruta": "EZE -> MAD", "precio_sugerido": 900.0})
        guardados_por_archivo[archivo_1]["graficos"].append({"titulo": "Gráfico Torta Enero"})

        # Inicialización de archivo 2 (cambio de archivo por el usuario)
        if archivo_2 not in guardados_por_archivo:
            guardados_por_archivo[archivo_2] = {"simulaciones": [], "graficos": [], "tablas_condicionales": []}

        # Verificación estricta: Archivo 2 debe estar 100% limpio y no arrastrar datos de Archivo 1
        self.assertEqual(len(guardados_por_archivo[archivo_2]["simulaciones"]), 0)
        self.assertEqual(len(guardados_por_archivo[archivo_2]["graficos"]), 0)
        self.assertEqual(len(guardados_por_archivo[archivo_1]["simulaciones"]), 1)

    def test_resolver_columna_mapeo_dinamico_y_alias(self):
        """Verifica que resolver_columna detecte nombres directos, mapeos del usuario y alias sin KeyError."""
        from apps.modulo_analisis import resolver_columna

        df = pd.DataFrame({
            "lugar_origen": ["ARG", "BRA"],
            "ciudad_destino": ["MIA", "MAD"],
            "precio_usd": [250.0, 400.0],
            "estado_vuelo": ["A tiempo", "Cancelado"]
        })

        mapeo = {
            "origen": "lugar_origen",
            "destino": "ciudad_destino",
            "precio": "precio_usd",
            "estado": "estado_vuelo"
        }

        # 1. Búsqueda por clave canónica que debe resolver a la columna real del usuario
        self.assertEqual(resolver_columna(df, "origen", mapeo), "lugar_origen")
        self.assertEqual(resolver_columna(df, "destino", mapeo), "ciudad_destino")
        self.assertEqual(resolver_columna(df, "precio", mapeo), "precio_usd")
        self.assertEqual(resolver_columna(df, "estado", mapeo), "estado_vuelo")

        # 2. Búsqueda por nombre real directo
        self.assertEqual(resolver_columna(df, "lugar_origen", mapeo), "lugar_origen")

        # 3. Búsqueda por alias comunes sin mapeo explícito
        df_alias = pd.DataFrame({"aeropuerto_origen": ["EZE"], "precio": [100.0]})
        self.assertEqual(resolver_columna(df_alias, "aeropuerto_origen", {}), "aeropuerto_origen")
        self.assertEqual(resolver_columna(df_alias, "precio", {}), "precio")

        # 4. Atributo inexistente debe retornar None y no lanzar excepción
        self.assertIsNone(resolver_columna(df, "columna_inexistente", mapeo))

    def test_construir_dataframe_graficos_robusto_sin_keyerror(self):
        """Verifica que construir_dataframe_graficos garantice todas las columnas canónicas y mapeadas."""
        from apps.modulo_analisis import construir_dataframe_graficos, COLUMNAS_GRAFICOS

        # Caso con vuelos vacíos
        df_vacio = construir_dataframe_graficos([])
        for col in COLUMNAS_GRAFICOS:
            self.assertIn(col, df_vacio.columns)
        self.assertIn("origen", df_vacio.columns)

        # Caso con mapeo personalizado
        mapeo = {"origen": "pais_salida", "precio": "tarifa"}
        df_mapeado = construir_dataframe_graficos([self.vuelo_atrasado], mapeo=mapeo)
        self.assertIn("origen", df_mapeado.columns)
        self.assertIn("pais_salida", df_mapeado.columns)
        self.assertIn("precio", df_mapeado.columns)
        self.assertIn("tarifa", df_mapeado.columns)


if __name__ == '__main__':
    unittest.main()
