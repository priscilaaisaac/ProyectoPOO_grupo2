import unittest
from datetime import datetime
from typing import Dict, Any, Optional

from modules.Vuelos import Vuelo
from modules.Estadistica.motor_analisis_base import MotorAnalisisBase
from modules.Estadistica.motor_estadistico_descriptivo import (
    MotorEstadisticoDescriptivo,
    MotorEstadisticoVuelos
)
from modules.Estadistica.simulador_precios import SimuladorPreciosDinamicos


class MockMotorPredictivo(MotorAnalisisBase):
    """Motor de prueba que simula un futuro motor predictivo / ML para validar OCP y DIP."""

    def calcular_metricas_segmento(
        self,
        ruta: Optional[str] = None,
        franja: Optional[str] = None,
        ocupacion: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "muestra_tamano": 50,
            "es_estimacion_global": False,
            "p_atrasado": 0.10,
            "p_cancelado": 0.05,
            "p_atiempo": 0.85,
            "p_exitoso": 0.85,
            "precio_promedio": 300.0,
            "ocupacion_promedio": 75.0,
            "capacidad_maxima_media": 180,
            "capacidad_usada_media": 135
        }


class TestAnalisisEstadistico(unittest.TestCase):

    def setUp(self):
        now = datetime(2026, 10, 20, 10, 0, 0)
        self.vuelos = [
            Vuelo(
                aeropuerto_origen="EZE",
                aeropuerto_destino="MIA",
                fechayhora_origen=now,
                fechayhora_destino=now,
                fechayhora_origen_estipulado=now,
                fechayhora_destino_estipulado=now,
                estado="A tiempo",
                capacidad_maxima_avion=200,
                capacidad_usada_avion=160,
                precio=500.0
            ),
            Vuelo(
                aeropuerto_origen="EZE",
                aeropuerto_destino="MIA",
                fechayhora_origen=now,
                fechayhora_destino=now,
                fechayhora_origen_estipulado=now,
                fechayhora_destino_estipulado=now,
                estado="Atrasado",
                capacidad_maxima_avion=200,
                capacidad_usada_avion=180,
                precio=600.0
            ),
            Vuelo(
                aeropuerto_origen="JFK",
                aeropuerto_destino="ORY",
                fechayhora_origen=now,
                fechayhora_destino=now,
                fechayhora_origen_estipulado=now,
                fechayhora_destino_estipulado=now,
                estado="Cancelado",
                capacidad_maxima_avion=150,
                capacidad_usada_avion=60,
                precio=400.0
            )
        ]

    def test_validacion_coleccion_vacia(self):
        with self.assertRaises(ValueError):
            MotorEstadisticoDescriptivo([])

    def test_motor_base_es_abstracto(self):
        with self.assertRaises(TypeError):
            MotorAnalisisBase(self.vuelos)

    def test_jerarquia_y_alias_retrocompatibilidad(self):
        self.assertTrue(issubclass(MotorEstadisticoDescriptivo, MotorAnalisisBase))
        self.assertIs(MotorEstadisticoVuelos, MotorEstadisticoDescriptivo)

    def test_metodos_comunes_heredados(self):
        motor = MotorEstadisticoDescriptivo(self.vuelos)
        self.assertEqual(motor.total_vuelos, 3)
        rutas = motor.obtener_rutas_disponibles()
        self.assertIn("EZE -> MIA", rutas)
        self.assertIn("JFK -> ORY", rutas)

        filtrados = motor.filtrar_vuelos(ruta="EZE -> MIA")
        self.assertEqual(len(filtrados), 2)

    def test_calculo_metricas_segmento_descriptivo(self):
        motor = MotorEstadisticoDescriptivo(self.vuelos)
        metricas = motor.calcular_metricas_segmento(ruta="EZE -> MIA")
        self.assertEqual(metricas["muestra_tamano"], 2)
        self.assertEqual(metricas["p_atrasado"], 0.5)
        self.assertEqual(metricas["p_atiempo"], 0.5)
        self.assertEqual(metricas["precio_promedio"], 550.0)

    def test_simulador_polimorfico_dip(self):
        # 1. Probar simulador con MotorEstadisticoDescriptivo
        motor_desc = MotorEstadisticoDescriptivo(self.vuelos)
        sim_desc = SimuladorPreciosDinamicos(motor_desc)
        res_desc = sim_desc.simular(ruta="EZE -> MIA")
        self.assertIn("precio_sugerido", res_desc)
        self.assertGreater(res_desc["precio_sugerido"], 0)

        # 2. Probar simulador con un nuevo motor polimórfico (OCP / DIP)
        motor_pred = MockMotorPredictivo(self.vuelos)
        sim_pred = SimuladorPreciosDinamicos(motor_pred)
        res_pred = sim_pred.simular()
        self.assertEqual(res_pred["precio_base"], 300.0)
        self.assertIn("precio_sugerido", res_pred)


if __name__ == "__main__":
    unittest.main()
