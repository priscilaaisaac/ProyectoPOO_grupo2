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


if __name__ == '__main__':
    unittest.main()
