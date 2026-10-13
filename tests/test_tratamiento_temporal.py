import unittest
import pandas as pd
from modules.pipeline_limpieza import (
    PipelineLimpieza, TratamientoFechas, EliminadorFilasNulas,
    SaneadorCategoricos, ImputadorMedianaGlobal
)
from modules.fabrica_vuelos import FabricaVuelos
from modules.Vuelos import Vuelo


class TestTratamientoFechas(unittest.TestCase):

    def setUp(self):
        """Crea un DataFrame de prueba con diversas anomalías en fechas."""
        self.df = pd.DataFrame({
            "id_vuelo": ["V1", "V2", "V3", "V4"],
            "aeropuerto_origen": ["EZE", "JFK", "MIA", "COR"],
            "aeropuerto_destino": ["MAD", "LHR", "EZE", "AEP"],
            "fechayhora_origen_estipulado": [
                "2026-10-01 08:00:00",
                None,  # Falta fecha estipulada
                "2026-10-01 12:00:00",
                "error_corrupto"  # Formato inválido
            ],
            "fechayhora_destino_estipulado": [
                "2026-10-01 16:00:00",
                "2026-10-01 18:00:00",
                None,  # Falta fecha estipulada
                "2026-10-01 14:00:00"
            ],
            "fechayhora_origen": [
                "2026-10-01 08:15:00",
                "2026-10-01 10:00:00",
                None,  # Vuelo sin despegue / cancelado
                "2026-10-01 12:05:00"
            ],
            "fechayhora_destino": [
                "2026-10-01 16:20:00",
                "2026-10-01 18:30:00",
                None,  # Vuelo sin aterrizaje / cancelado
                "2026-10-01 14:10:00"
            ],
            "estado": ["En vuelo", "Demorado", "Cancelado", "Finalizado"],
            "capacidad_maxima_avion": [200, 180, 150, 100],
            "capacidad_usada_avion": [180, 150, 100, 90],
            "precio": [500.0, 450.0, 300.0, 200.0],
            "origen": ["ARG", "USA", "USA", "ARG"],
            "destino": ["ESP", "GBR", "ARG", "ARG"]
        })

    def test_eliminar_fila_si_falta_estipulada(self):
        """Verifica que las filas sin fecha estipulada o con fecha corrupta se eliminen."""
        tratamiento_origen = TratamientoFechas("fechayhora_origen_estipulado", metodo="Eliminar fila si falta")
        tratamiento_destino = TratamientoFechas("fechayhora_destino_estipulado", metodo="Eliminar fila si falta")

        df_filtrado = tratamiento_origen.aplicar(self.df)
        # Se deben eliminar V2 (None) y V4 (error_corrupto)
        self.assertEqual(len(df_filtrado), 2)
        self.assertListEqual(list(df_filtrado["id_vuelo"]), ["V1", "V3"])

        df_filtrado_final = tratamiento_destino.aplicar(df_filtrado)
        # Se elimina V3 (None en destino estipulado)
        self.assertEqual(len(df_filtrado_final), 1)
        self.assertEqual(df_filtrado_final.iloc[0]["id_vuelo"], "V1")

    def test_fechas_reales_dejar_nulo(self):
        """Verifica que las fechas reales permitan 'Dejar nulo' para vuelos cancelados o no registrados."""
        tratamiento_origen_real = TratamientoFechas("fechayhora_origen", metodo="Dejar nulo")
        tratamiento_destino_real = TratamientoFechas("fechayhora_destino", metodo="Dejar nulo")

        df_res = tratamiento_origen_real.aplicar(self.df)
        df_res = tratamiento_destino_real.aplicar(df_res)

        # No se deben haber eliminado filas
        self.assertEqual(len(df_res), 4)

        # La fila V3 debe conservar nulos (NaT) en fechas reales
        fila_v3 = df_res[df_res["id_vuelo"] == "V3"].iloc[0]
        self.assertTrue(pd.isna(fila_v3["fechayhora_origen"]))
        self.assertTrue(pd.isna(fila_v3["fechayhora_destino"]))

    def test_fechas_reales_eliminar_fila_si_falta(self):
        """Verifica que si el usuario opta por eliminar filas faltantes en fechas reales, se descarten."""
        tratamiento = TratamientoFechas("fechayhora_origen", metodo="Eliminar fila si falta")
        df_res = tratamiento.aplicar(self.df)

        # Se debe haber descartado V3
        self.assertEqual(len(df_res), 3)
        self.assertNotIn("V3", list(df_res["id_vuelo"]))

    def test_pipeline_completo_e_instanciacion_vuelos(self):
        """
        Valida el flujo end-to-end:
        - Eliminar filas con fechas estipuladas faltantes.
        - Dejar nulo en fechas reales.
        - Instanciar objetos Vuelo con la FabricaVuelos.
        - Calcular métricas de retraso y duración en vuelos normales y vuelos cancelados (nulos).
        """
        pipeline = PipelineLimpieza()
        # Tratamiento temporal
        pipeline.agregar_paso(TratamientoFechas("fechayhora_origen_estipulado", metodo="Eliminar fila si falta"))
        pipeline.agregar_paso(TratamientoFechas("fechayhora_destino_estipulado", metodo="Eliminar fila si falta"))
        pipeline.agregar_paso(TratamientoFechas("fechayhora_origen", metodo="Dejar nulo"))
        pipeline.agregar_paso(TratamientoFechas("fechayhora_destino", metodo="Dejar nulo"))

        # Preparamos un DataFrame donde V1 es normal y V2 tiene fechas estipuladas válidas pero fechas reales nulas (cancelado)
        df_prueba = pd.DataFrame({
            "id_vuelo": ["V1", "V2", "V3_invalido"],
            "aeropuerto_origen": ["EZE", "JFK", "COR"],
            "aeropuerto_destino": ["MAD", "LHR", "AEP"],
            "fechayhora_origen_estipulado": ["2026-10-01 08:00:00", "2026-10-01 10:00:00", None],
            "fechayhora_destino_estipulado": ["2026-10-01 16:00:00", "2026-10-01 18:00:00", "2026-10-01 12:00:00"],
            "fechayhora_origen": ["2026-10-01 08:30:00", None, "2026-10-01 11:00:00"],
            "fechayhora_destino": ["2026-10-01 16:45:00", None, "2026-10-01 13:00:00"],
            "estado": ["En vuelo", "Cancelado", "Demorado"],
            "capacidad_maxima_avion": [200, 180, 150],
            "capacidad_usada_avion": [150, 0, 100],
            "precio": [500.0, 400.0, 300.0],
            "origen": ["ARG", "USA", "ARG"],
            "destino": ["ESP", "GBR", "ARG"]
        })

        df_limpio = pipeline.ejecutar(df_prueba)
        # V3_invalido se eliminó por faltar fechayhora_origen_estipulado
        self.assertEqual(len(df_limpio), 2)
        self.assertListEqual(list(df_limpio["id_vuelo"]), ["V1", "V2"])

        mapeo = {c: c for c in df_limpio.columns}
        vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, mapeo)
        self.assertEqual(len(vuelos), 2)

        vuelo_v1 = vuelos[0]
        vuelo_v2 = vuelos[1]

        # V1: Vuelo con fechas reales
        self.assertEqual(vuelo_v1.calcular_retraso_salida_minutos(), 30.0)
        self.assertEqual(vuelo_v1.calcular_retraso_llegada_minutos(), 45.0)
        self.assertTrue(vuelo_v1.es_retrasado(15.0))
        self.assertEqual(vuelo_v1.calcular_duracion_estipulada_minutos(), 480.0)
        self.assertEqual(vuelo_v1.calcular_duracion_real_minutos(), 495.0)

        # V2: Vuelo cancelado con fechas reales nulas
        self.assertIsNone(vuelo_v2.fechayhora_origen)
        self.assertIsNone(vuelo_v2.fechayhora_destino)
        self.assertEqual(vuelo_v2.calcular_retraso_salida_minutos(), 0.0)
        self.assertEqual(vuelo_v2.calcular_retraso_llegada_minutos(), 0.0)
        self.assertFalse(vuelo_v2.es_retrasado(15.0))
        self.assertEqual(vuelo_v2.calcular_duracion_estipulada_minutos(), 480.0)
        self.assertIsNone(vuelo_v2.calcular_duracion_real_minutos())


if __name__ == "__main__":
    unittest.main()
