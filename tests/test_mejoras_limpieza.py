import unittest
import pandas as pd
import numpy as np

from modules.pipeline_limpieza import (
    PipelineLimpieza,
    ImputadorCapacidadesPorFactorOcupacion,
    GeneradorIdVuelo,
    AutogeneradorIds,
    SaneadorUbicaciones,
    ImputadorEstadoInteligente,
    ImputadorMediaGlobal,
    EliminadorFilasNulas
)
from modules.calidad import ReporteCalidad


class TestMejorasLimpieza(unittest.TestCase):

    def setUp(self):
        """Prepara dataframes con casos borde para probar capacidades, autogeneración e impacto."""
        # Dataset para probar capacidades
        # V1: 200 max, 160 usada -> factor = 0.8
        # V2: 100 max, 80 usada  -> factor = 0.8
        # Factor promedio = 0.8 (80%)
        # V3: 150 max, NaN usada -> debería imputarse usada = round(150 * 0.8) = 120
        # V4: NaN max, 80 usada  -> debería imputarse max = round(80 / 0.8) = 100
        # V5: NaN max, NaN usada -> ambas nulas
        self.df_capacidades = pd.DataFrame({
            "id_vuelo": ["V1", "V2", "V3", "V4", "V5"],
            "cap_max": [200.0, 100.0, 150.0, np.nan, np.nan],
            "cap_usada": [160.0, 80.0, np.nan, 80.0, np.nan]
        })

        # Dataset para probar autogeneración de ID
        self.df_ids = pd.DataFrame({
            "id_vuelo": ["EXISTENTE-99", None, "", "   ", "EXISTENTE-100", np.nan],
            "dato": [1, 2, 3, 4, 5, 6]
        })

    def test_imputacion_capacidades_factor_ocupacion_mantener_ambas(self):
        """Verifica la imputación correcta basada en factor de ocupación manteniendo ambas nulas."""
        imputador = ImputadorCapacidadesPorFactorOcupacion(
            col_maxima="cap_max",
            col_usada="cap_usada",
            metodo="imputar",
            accion_ambas_nulas="mantener"
        )
        factor = imputador.calcular_factor_promedio(self.df_capacidades)
        self.assertAlmostEqual(factor, 0.8, places=2)

        df_res = imputador.aplicar(self.df_capacidades)

        # Se deben mantener las 5 filas
        self.assertEqual(len(df_res), 5)

        # Fila V3: faltaba usada -> 150 * 0.8 = 120
        v3 = df_res[df_res["id_vuelo"] == "V3"].iloc[0]
        self.assertEqual(v3["cap_usada"], 120)
        self.assertEqual(v3["cap_max"], 150)

        # Fila V4: faltaba max -> 80 / 0.8 = 100
        v4 = df_res[df_res["id_vuelo"] == "V4"].iloc[0]
        self.assertEqual(v4["cap_max"], 100)
        self.assertEqual(v4["cap_usada"], 80)

        # Fila V5: ambas nulas se mantienen
        v5 = df_res[df_res["id_vuelo"] == "V5"].iloc[0]
        self.assertTrue(pd.isna(v5["cap_max"]))
        self.assertTrue(pd.isna(v5["cap_usada"]))

        # Verificar que la capacidad usada nunca supere a la máxima
        validos = df_res["cap_max"].notna() & df_res["cap_usada"].notna()
        self.assertTrue((df_res.loc[validos, "cap_usada"] <= df_res.loc[validos, "cap_max"]).all())

    def test_capacidades_opcion_eliminar_filas(self):
        """Verifica que 'eliminar filas' descarte cualquier registro con capacidad faltante."""
        imputador = ImputadorCapacidadesPorFactorOcupacion(
            col_maxima="cap_max",
            col_usada="cap_usada",
            metodo="eliminar"
        )
        df_res = imputador.aplicar(self.df_capacidades)

        # Solo V1 y V2 tienen ambas capacidades completas
        self.assertEqual(len(df_res), 2)
        self.assertListEqual(list(df_res["id_vuelo"]), ["V1", "V2"])

    def test_capacidades_opcion_no_modificar(self):
        """Verifica que 'no modificar' conserve los datos exactamente como están."""
        imputador = ImputadorCapacidadesPorFactorOcupacion(
            col_maxima="cap_max",
            col_usada="cap_usada",
            metodo="no modificar"
        )
        df_res = imputador.aplicar(self.df_capacidades)
        self.assertEqual(len(df_res), 5)
        self.assertTrue(pd.isna(df_res.loc[2, "cap_usada"]))

    def test_autogeneracion_id_vuelo(self):
        """Verifica la asignación correlativa secuencial de ID (GEN-001, GEN-002, ...) preservando existentes."""
        generador = GeneradorIdVuelo(columna="id_vuelo", prefijo="GEN-", relleno=3)
        df_res = generador.aplicar(self.df_ids)

        self.assertFalse(df_res["id_vuelo"].isna().any())
        self.assertFalse((df_res["id_vuelo"].str.strip() == "").any())

        self.assertEqual(df_res.iloc[0]["id_vuelo"], "EXISTENTE-99")
        self.assertEqual(df_res.iloc[4]["id_vuelo"], "EXISTENTE-100")

        self.assertEqual(df_res.iloc[1]["id_vuelo"], "GEN-001")
        self.assertEqual(df_res.iloc[2]["id_vuelo"], "GEN-002")
        self.assertEqual(df_res.iloc[3]["id_vuelo"], "GEN-003")
        self.assertEqual(df_res.iloc[5]["id_vuelo"], "GEN-004")

    def test_saneador_ubicaciones(self):
        """Verifica que origen, destino y aeropuertos nulos se imputen como 'Desconocido'."""
        df_loc = pd.DataFrame({
            "origen": ["ARG", None, ""],
            "destino": [None, "USA", "ESP"],
            "aeropuerto_origen": ["EZE", "JFK", None],
            "aeropuerto_destino": ["MIA", None, "MAD"]
        })
        saneador = SaneadorUbicaciones(["origen", "destino", "aeropuerto_origen", "aeropuerto_destino"])
        res = saneador.aplicar(df_loc)

        for col in ["origen", "destino", "aeropuerto_origen", "aeropuerto_destino"]:
            self.assertFalse(res[col].isna().any())
            self.assertFalse((res[col].str.strip() == "").any())
        
        self.assertEqual(res.loc[1, "origen"], "Desconocido")
        self.assertEqual(res.loc[2, "origen"], "Desconocido")
        self.assertEqual(res.loc[0, "destino"], "Desconocido")
        self.assertEqual(res.loc[2, "aeropuerto_origen"], "Desconocido")
        self.assertEqual(res.loc[1, "aeropuerto_destino"], "Desconocido")

    def test_imputador_estado_inteligente_reglas(self):
        """Verifica las 8 reglas exhaustivas de imputación para el atributo 'estado'."""
        df_estados = pd.DataFrame({
            "id": ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"],
            "estado": [None] * 8,
            "s_est": [
                "2026-10-01 10:30:00",  # R1: salida retrasada 30 min (> 10) -> Atrasado
                "2026-10-01 10:30:00",  # R2: llegada retrasada 20 min (> 10) -> Atrasado
                "2026-10-01 10:30:00",  # R3: salida estipulada pero real nula -> Cancelado
                "2026-10-01 10:30:00",  # R4: coinciden dentro de 5 min (<= 10) -> A tiempo
                None,                   # R5: sin salida, pero sí de llegada -> Exitoso
                None,                   # R6: únicamente reales -> Exitoso
                None,                   # R7: sin estipuladas pero con datos -> Exitoso
                None                    # R8: ninguna fecha de ningún tipo -> Desconocido
            ],
            "s_real": [
                "2026-10-01 11:00:00",  # R1: 30 min tarde
                "2026-10-01 10:30:00",  # R2: salida en hora
                None,                   # R3: cancelado
                "2026-10-01 10:35:00",  # R4: 5 min margen
                None,                   # R5
                "2026-10-01 10:30:00",  # R6
                "2026-10-01 10:30:00",  # R7
                None                    # R8
            ],
            "l_est": [
                "2026-10-01 12:00:00",  # R1
                "2026-10-01 12:00:00",  # R2: 20 min tarde
                "2026-10-01 12:00:00",  # R3
                "2026-10-01 12:00:00",  # R4: a tiempo
                "2026-10-01 12:00:00",  # R5
                None,                   # R6
                None,                   # R7
                None                    # R8
            ],
            "l_real": [
                "2026-10-01 12:30:00",  # R1
                "2026-10-01 12:20:00",  # R2
                None,                   # R3
                "2026-10-01 12:02:00",  # R4: a tiempo
                "2026-10-01 12:00:00",  # R5
                "2026-10-01 12:00:00",  # R6
                "2026-10-01 12:00:00",  # R7
                None                    # R8
            ]
        })

        imputador_est = ImputadorEstadoInteligente(
            col_estado="estado",
            col_s_est="s_est",
            col_s_real="s_real",
            col_l_est="l_est",
            col_l_real="l_real"
        )
        res = imputador_est.aplicar(df_estados)

        self.assertEqual(res.loc[0, "estado"], "Atrasado")     # R1: salida demorada 30 min
        self.assertEqual(res.loc[1, "estado"], "Atrasado")     # R2: llegada demorada 20 min
        self.assertEqual(res.loc[2, "estado"], "Cancelado")    # R3: s_est existe pero s_real es nula
        self.assertEqual(res.loc[3, "estado"], "A tiempo")     # R4: dentro de 10 min
        self.assertEqual(res.loc[4, "estado"], "Exitoso")      # R5: solo llegada
        self.assertEqual(res.loc[5, "estado"], "Exitoso")      # R6: únicamente reales
        self.assertEqual(res.loc[6, "estado"], "Exitoso")      # R7: sin estipuladas pero con datos
        self.assertEqual(res.loc[7, "estado"], "Desconocido")  # R8: sin fechas

    def test_reporte_calidad_impacto_perdida(self):
        """Verifica los cálculos dinámicos de pérdida de filas y la columna en el reporte."""
        mapeo = {
            "capacidad_maxima_avion": "cap_max",
            "capacidad_usada_avion": "cap_usada"
        }
        reporte = ReporteCalidad(self.df_capacidades, mapeo)
        df_rep = reporte.generar()

        self.assertIn("Pérdida si se descarta", df_rep.columns)

        nulos_max, pct_max = reporte.calcular_impacto_descarte("cap_max")
        self.assertEqual(nulos_max, 2)
        self.assertEqual(pct_max, 40.0)

        nulos_ambas, pct_ambas = reporte.calcular_impacto_ambas_nulas("cap_max", "cap_usada")
        self.assertEqual(nulos_ambas, 1)
        self.assertEqual(pct_ambas, 20.0)


    def test_imputador_media_global(self):
        """Verifica que ImputadorMediaGlobal calcule e impute la media aritmética."""
        df = pd.DataFrame({"precio": [100.0, 200.0, np.nan, 300.0]})
        imputador = ImputadorMediaGlobal("precio")
        res = imputador.aplicar(df)
        # Media de 100, 200, 300 es 200.0
        self.assertEqual(res.loc[2, "precio"], 200.0)
        self.assertFalse(res["precio"].isna().any())

    def test_eliminador_filas_nulas_precio(self):
        """Verifica que EliminadorFilasNulas descarte registros sin precio numérico válido."""
        df = pd.DataFrame({"precio": [100.0, np.nan, -10.0, 250.0, None]})
        eliminador = EliminadorFilasNulas("precio")
        res = eliminador.aplicar(df)
        self.assertEqual(len(res), 2)
        self.assertListEqual(list(res["precio"]), [100.0, 250.0])

    def test_autogenerador_ids_alias_and_preservation(self):
        """Verifica que AutogeneradorIds respete IDs válidos, no cree columnas duplicadas y sea secuencial."""
        df = pd.DataFrame({
            "id_vuelo": ["AR-100", None, "GEN-002", "", "   ", "IB-500", np.nan],
            "otro_dato": [1, 2, 3, 4, 5, 6, 7]
        })
        generador = AutogeneradorIds(columna="id_vuelo", prefijo="GEN-", relleno=3)
        res = generador.aplicar(df)

        # Mismo número de columnas (sin columnas duplicadas)
        self.assertListEqual(list(res.columns), ["id_vuelo", "otro_dato"])

        # Preserva IDs existentes
        self.assertEqual(res.loc[0, "id_vuelo"], "AR-100")
        self.assertEqual(res.loc[2, "id_vuelo"], "GEN-002")
        self.assertEqual(res.loc[5, "id_vuelo"], "IB-500")

        # Continúa secuencialmente después del máximo existente (GEN-002 -> GEN-003, GEN-004...)
        self.assertEqual(res.loc[1, "id_vuelo"], "GEN-003")
        self.assertEqual(res.loc[3, "id_vuelo"], "GEN-004")
        self.assertEqual(res.loc[4, "id_vuelo"], "GEN-005")
        self.assertEqual(res.loc[6, "id_vuelo"], "GEN-006")

    def test_estricto_13_columnas_canonicas(self):
        """Verifica que el dataset procesado contenga exactamente las 13 columnas canónicas limpias."""
        from apps.modulo_validacion import COLUMNAS_CANONICAS
        self.assertEqual(len(COLUMNAS_CANONICAS), 13)
        
        # Simular un DataFrame con columnas sucias/residuales de múltiples archivos
        df_sucio = pd.DataFrame({
            "id_vuelo": ["V1"],
            "aeropuerto_origen": ["EZE"],
            "aeropuerto_destino": ["COR"],
            "origen": ["Argentina"],
            "destino": ["Argentina"],
            "fechayhora_origen": ["2026-10-01 10:00"],
            "fechayhora_destino": ["2026-10-01 11:30"],
            "fechayhora_origen_estipulado": ["2026-10-01 10:00"],
            "fechayhora_destino_estipulado": ["2026-10-01 11:30"],
            "estado": ["a tiempo"],
            "capacidad_maxima_avion": [180],
            "capacidad_usada_avion": [150],
            "precio": [200.0],
            "codigo_vuelo__(archivo_viejo.xlsx)": ["RESIDUO_1"],
            "fecha_extra__(otro_archivo.csv)": ["RESIDUO_2"],
            "columna_no_seleccionada": [np.nan]
        })
        self.assertEqual(len(df_sucio.columns), 16)

        # Aplicar el filtrado estricto
        for col_c in COLUMNAS_CANONICAS:
            if col_c not in df_sucio.columns:
                df_sucio[col_c] = None
        df_limpio = df_sucio[COLUMNAS_CANONICAS].copy()

        self.assertEqual(len(df_limpio.columns), 13)
        self.assertListEqual(list(df_limpio.columns), COLUMNAS_CANONICAS)
        self.assertNotIn("codigo_vuelo__(archivo_viejo.xlsx)", df_limpio.columns)
        self.assertNotIn("fecha_extra__(otro_archivo.csv)", df_limpio.columns)
        self.assertNotIn("columna_no_seleccionada", df_limpio.columns)


if __name__ == "__main__":
    unittest.main()
