"""
Suite de Pruebas Unitarias Exhaustivas para el Pipeline de Limpieza.
Cubre todas las estrategias de limpieza, casos normales, casos borde,
control de errores y orquestación con PipelineLimpieza.
"""

import pytest
import numpy as np
import pandas as pd

from modules.pipeline_limpieza import (
    OperacionLimpieza,
    ImputadorMedianaGlobal,
    ImputadorMediaGlobal,
    ImputadorMedianaPorGrupo,
    SaneadorUbicaciones,
    ImputadorCapacidadesPorFactorOcupacion,
    ImputadorEstadoInteligente,
    GeneradorIdVuelo,
    EliminadorFilasNulas,
    PipelineLimpieza,
)


# =====================================================================
# 1. OperacionLimpieza (Clase Abstracta)
# =====================================================================

class TestOperacionLimpiezaBase:
    """Verifica el contrato abstracto de OperacionLimpieza."""

    def test_no_se_puede_instanciar_directamente(self):
        with pytest.raises(TypeError):
            OperacionLimpieza()

    def test_subclase_concreta_funciona(self):
        class DummyOperacion(OperacionLimpieza):
            def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
                df_res = df.copy()
                df_res["dummy"] = 1
                return df_res

        dummy = DummyOperacion()
        df = pd.DataFrame({"a": [10, 20]})
        res = dummy.aplicar(df)
        assert "dummy" in res.columns
        assert list(res["dummy"]) == [1, 1]


# =====================================================================
# 2. ImputadorMedianaGlobal
# =====================================================================

class TestImputadorMedianaGlobal:
    """Pruebas unitarias para ImputadorMedianaGlobal."""

    def test_imputacion_normal_mediana(self):
        # Mediana de [10, 20, 30] es 20
        df = pd.DataFrame({"precio": [10.0, np.nan, 30.0, 20.0]})
        imputador = ImputadorMedianaGlobal(columna="precio")
        res = imputador.aplicar(df)
        assert res["precio"].iloc[1] == 20.0
        assert res["precio"].isna().sum() == 0

    def test_mediana_con_valores_pares(self):
        # Mediana de [10, 20, 30, 40] es 25.0
        df = pd.DataFrame({"precio": [10.0, 20.0, np.nan, 30.0, 40.0]})
        imputador = ImputadorMedianaGlobal(columna="precio")
        res = imputador.aplicar(df)
        assert res["precio"].iloc[2] == 25.0

    def test_columna_inexistente_no_falla(self):
        df = pd.DataFrame({"otra_col": [1, 2, 3]})
        imputador = ImputadorMedianaGlobal(columna="col_fantasma")
        res = imputador.aplicar(df)
        assert "col_fantasma" not in res.columns
        assert list(res["otra_col"]) == [1, 2, 3]

    def test_dataframe_vacio(self):
        df = pd.DataFrame(columns=["precio"])
        imputador = ImputadorMedianaGlobal(columna="precio")
        res = imputador.aplicar(df)
        assert res.empty
        assert "precio" in res.columns

    def test_control_error_valores_texto_en_columna_numerica(self):
        # Los textos inválidos se fuerzan a NaN con coerce y luego se imputa la mediana
        df = pd.DataFrame({"precio": ["10", "texto_invalido", "30", None]})
        imputador = ImputadorMedianaGlobal(columna="precio")
        res = imputador.aplicar(df)
        # Valores válidos: [10.0, 30.0] -> mediana = 20.0
        assert res["precio"].iloc[0] == 10.0
        assert res["precio"].iloc[1] == 20.0
        assert res["precio"].iloc[2] == 30.0
        assert res["precio"].iloc[3] == 20.0

    def test_todos_valores_nan(self):
        df = pd.DataFrame({"precio": [np.nan, None, np.nan]})
        imputador = ImputadorMedianaGlobal(columna="precio")
        res = imputador.aplicar(df)
        # Si todos son NaN, la mediana es NaN y el DataFrame no crashea
        assert res["precio"].isna().all()


# =====================================================================
# 3. ImputadorMediaGlobal
# =====================================================================

class TestImputadorMediaGlobal:
    """Pruebas unitarias para ImputadorMediaGlobal."""

    def test_imputacion_normal_media(self):
        # Media de [10, 20, 60] = 90 / 3 = 30.0
        df = pd.DataFrame({"precio": [10.0, np.nan, 20.0, 60.0]})
        imputador = ImputadorMediaGlobal(columna="precio")
        res = imputador.aplicar(df)
        assert res["precio"].iloc[1] == 30.0
        assert res["precio"].isna().sum() == 0

    def test_redondeo_dos_decimales(self):
        # Media de [10, 20, 25] = 55 / 3 = 18.3333... -> 18.33
        df = pd.DataFrame({"precio": [10.0, 20.0, 25.0, np.nan]})
        imputador = ImputadorMediaGlobal(columna="precio")
        res = imputador.aplicar(df)
        assert res["precio"].iloc[3] == 18.33

    def test_columna_inexistente(self):
        df = pd.DataFrame({"x": [1, 2]})
        imputador = ImputadorMediaGlobal(columna="no_existe")
        res = imputador.aplicar(df)
        assert "no_existe" not in res.columns
        assert len(res) == 2

    def test_dataframe_vacio(self):
        df = pd.DataFrame(columns=["precio"])
        imputador = ImputadorMediaGlobal(columna="precio")
        res = imputador.aplicar(df)
        assert res.empty

    def test_todos_nulos_retorna_cero(self):
        df = pd.DataFrame({"precio": [np.nan, None]})
        imputador = ImputadorMediaGlobal(columna="precio")
        res = imputador.aplicar(df)
        assert list(res["precio"]) == [0.0, 0.0]

    def test_control_error_cadenas_no_numericas(self):
        df = pd.DataFrame({"precio": ["100", "error_str", "200", np.nan]})
        imputador = ImputadorMediaGlobal(columna="precio")
        res = imputador.aplicar(df)
        # 100 y 200 promedian 150.0
        assert res["precio"].iloc[1] == 150.0
        assert res["precio"].iloc[3] == 150.0


# =====================================================================
# 4. ImputadorMedianaPorGrupo
# =====================================================================

class TestImputadorMedianaPorGrupo:
    """Pruebas unitarias para ImputadorMedianaPorGrupo."""

    def test_imputacion_por_grupo_origen_destino(self):
        df = pd.DataFrame({
            "origen": ["ARG", "ARG", "ARG", "USA", "USA"],
            "destino": ["ESP", "ESP", "ESP", "FRA", "FRA"],
            "precio": [100.0, 200.0, np.nan, 500.0, np.nan]
        })
        # Grupo (ARG, ESP): precios [100, 200] -> mediana = 150.0
        # Grupo (USA, FRA): precios [500] -> mediana = 500.0
        imputador = ImputadorMedianaPorGrupo(
            columna="precio", col_origen="origen", col_destino="destino"
        )
        res = imputador.aplicar(df)
        assert res["precio"].iloc[2] == 150.0
        assert res["precio"].iloc[4] == 500.0

    def test_fallback_mediana_global_si_grupo_es_todo_nan(self):
        df = pd.DataFrame({
            "origen": ["ARG", "ARG", "CHI", "CHI"],
            "destino": ["ESP", "ESP", "BRA", "BRA"],
            "precio": [100.0, 300.0, np.nan, np.nan]
        })
        # Mediana global de [100, 300] es 200.0
        imputador = ImputadorMedianaPorGrupo(
            columna="precio", col_origen="origen", col_destino="destino"
        )
        res = imputador.aplicar(df)
        assert res["precio"].iloc[2] == 200.0
        assert res["precio"].iloc[3] == 200.0

    def test_columna_objetivo_no_existe(self):
        df = pd.DataFrame({"origen": ["A"], "destino": ["B"]})
        imputador = ImputadorMedianaPorGrupo("precio", "origen", "destino")
        res = imputador.aplicar(df)
        assert "precio" not in res.columns

    def test_columnas_agrupacion_no_existen(self):
        # Si origen o destino no existen, cae directo a mediana global
        df = pd.DataFrame({"precio": [10.0, 30.0, np.nan]})
        imputador = ImputadorMedianaPorGrupo("precio", "col_orig_fantasma", "col_dest_fantasma")
        res = imputador.aplicar(df)
        assert res["precio"].iloc[2] == 20.0

    def test_dataframe_vacio(self):
        df = pd.DataFrame(columns=["origen", "destino", "precio"])
        imputador = ImputadorMedianaPorGrupo("precio", "origen", "destino")
        res = imputador.aplicar(df)
        assert res.empty


# =====================================================================
# 5. SaneadorUbicaciones
# =====================================================================

class TestSaneadorUbicaciones:
    """Pruebas unitarias para SaneadorUbicaciones."""

    def test_saneamiento_valores_nulos_y_variantes(self):
        df = pd.DataFrame({
            "origen": ["Buenos Aires", "", "   ", "nan", None],
            "destino": ["Madrid", "NULL", "n/a", "desconocido", "Tokyo"]
        })
        saneador = SaneadorUbicaciones(["origen", "destino"])
        res = saneador.aplicar(df)

        assert res["origen"].iloc[0] == "Buenos Aires"
        assert res["origen"].iloc[1] == "Desconocido"
        assert res["origen"].iloc[2] == "Desconocido"
        assert res["origen"].iloc[3] == "Desconocido"
        assert res["origen"].iloc[4] == "Desconocido"

        assert res["destino"].iloc[0] == "Madrid"
        assert res["destino"].iloc[1] == "Desconocido"
        assert res["destino"].iloc[2] == "Desconocido"
        assert res["destino"].iloc[3] == "Desconocido"
        assert res["destino"].iloc[4] == "Tokyo"

    def test_columnas_inexistentes_se_ignoran(self):
        df = pd.DataFrame({"ciudad": ["Santiago"]})
        saneador = SaneadorUbicaciones(["col_fantasma", "ciudad"])
        res = saneador.aplicar(df)
        assert res["ciudad"].iloc[0] == "Santiago"
        assert "col_fantasma" not in res.columns

    def test_lista_vacia_de_columnas(self):
        df = pd.DataFrame({"a": [1, None]})
        saneador = SaneadorUbicaciones([])
        res = saneador.aplicar(df)
        assert len(res) == 2

    def test_dataframe_vacio(self):
        df = pd.DataFrame(columns=["origen", "destino"])
        saneador = SaneadorUbicaciones(["origen", "destino"])
        res = saneador.aplicar(df)
        assert res.empty


# =====================================================================
# 6. ImputadorCapacidadesPorFactorOcupacion
# =====================================================================

class TestImputadorCapacidadesPorFactorOcupacion:
    """Pruebas unitarias para ImputadorCapacidadesPorFactorOcupacion."""

    def test_calcular_factor_promedio_valido(self):
        # Fila 1: 150 / 200 = 0.75
        # Fila 2: 50 / 100 = 0.50
        # Promedio = 0.625
        df = pd.DataFrame({
            "capacidad_maxima_avion": [200, 100],
            "capacidad_usada_avion": [150, 50]
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion()
        factor = imputador.calcular_factor_promedio(df)
        assert pytest.approx(factor, 0.001) == 0.625

    def test_calcular_factor_promedio_sin_validos_usa_default(self):
        # Datos inválidos: usadas > maximas o ceros
        df = pd.DataFrame({
            "capacidad_maxima_avion": [0, -10, 50],
            "capacidad_usada_avion": [10, 20, 100]  # 100 > 50 inválido
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion(factor_default=0.80)
        assert imputador.calcular_factor_promedio(df) == 0.80

    def test_calcular_factor_columna_faltante_usa_default(self):
        df = pd.DataFrame({"otra": [1, 2]})
        imputador = ImputadorCapacidadesPorFactorOcupacion(factor_default=0.70)
        assert imputador.calcular_factor_promedio(df) == 0.70

    def test_metodo_no_modificar(self):
        df = pd.DataFrame({
            "capacidad_maxima_avion": [200, np.nan],
            "capacidad_usada_avion": [np.nan, 100]
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion(metodo="no modificar")
        res = imputador.aplicar(df)
        assert res["capacidad_maxima_avion"].isna().sum() == 1
        assert res["capacidad_usada_avion"].isna().sum() == 1

    def test_metodo_eliminar_filas_nulas(self):
        df = pd.DataFrame({
            "capacidad_maxima_avion": [200, np.nan, 150],
            "capacidad_usada_avion": [150, 100, np.nan]
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion(metodo="eliminar")
        res = imputador.aplicar(df)
        assert len(res) == 1
        assert res["capacidad_maxima_avion"].iloc[0] == 200
        assert res["capacidad_usada_avion"].iloc[0] == 150

    def test_metodo_imputar_bidireccional(self):
        # Fila 0: válida (200, 100) -> factor = 0.5
        # Fila 1: falta usada -> usada = 200 * 0.5 = 100
        # Fila 2: falta máxima -> máxima = 80 / 0.5 = 160
        df = pd.DataFrame({
            "capacidad_maxima_avion": [200.0, 200.0, np.nan],
            "capacidad_usada_avion": [100.0, np.nan, 80.0]
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion(metodo="imputar")
        res = imputador.aplicar(df)
        assert res["capacidad_usada_avion"].iloc[1] == 100
        assert res["capacidad_maxima_avion"].iloc[2] == 160

    def test_ajuste_usada_no_supere_maxima(self):
        # Caso extremo donde el factor de ocupación default (ej. 1.0)
        # o redondeo pudiera generar usada > maxima
        df = pd.DataFrame({
            "capacidad_maxima_avion": [100.0, 50.0],
            "capacidad_usada_avion": [100.0, 75.0]  # 75 > 50
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion(metodo="imputar")
        res = imputador.aplicar(df)
        # Debe ajustar la usada a la máxima
        assert res["capacidad_usada_avion"].iloc[1] <= res["capacidad_maxima_avion"].iloc[1]

    def test_descartar_ambas_nulas(self):
        df = pd.DataFrame({
            "capacidad_maxima_avion": [200.0, np.nan, 100.0],
            "capacidad_usada_avion": [150.0, np.nan, 80.0]
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion(
            metodo="imputar", accion_ambas_nulas="descartar"
        )
        res = imputador.aplicar(df)
        assert len(res) == 2
        assert not res["capacidad_maxima_avion"].isna().any()

    def test_mantener_ambas_nulas(self):
        df = pd.DataFrame({
            "capacidad_maxima_avion": [200.0, np.nan],
            "capacidad_usada_avion": [150.0, np.nan]
        })
        imputador = ImputadorCapacidadesPorFactorOcupacion(
            metodo="imputar", accion_ambas_nulas="mantener"
        )
        res = imputador.aplicar(df)
        assert len(res) == 2
        assert pd.isna(res["capacidad_maxima_avion"].iloc[1])

    def test_columnas_faltantes_retorna_dataframe(self):
        df = pd.DataFrame({"otra_cosa": [1, 2]})
        imputador = ImputadorCapacidadesPorFactorOcupacion()
        res = imputador.aplicar(df)
        assert list(res.columns) == ["otra_cosa"]


# =====================================================================
# 7. ImputadorEstadoInteligente
# =====================================================================

class TestImputadorEstadoInteligente:
    """Pruebas unitarias para ImputadorEstadoInteligente y sus 8 reglas."""

    def test_regla_8_sin_ninguna_fecha_es_desconocido(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": None,
            "fechayhora_origen": None,
            "fechayhora_destino_estipulado": None,
            "fechayhora_destino": None,
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "Desconocido"

    def test_regla_3_salida_estipulada_sin_real_es_cancelado(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": "2026-10-21 10:00:00",
            "fechayhora_origen": None,
            "fechayhora_destino_estipulado": "2026-10-21 12:00:00",
            "fechayhora_destino": None,
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "Cancelado"

    def test_regla_1_salida_retrasada_mas_de_10_minutos(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": "2026-10-21 10:00:00",
            "fechayhora_origen": "2026-10-21 10:15:00",  # +15 min
            "fechayhora_destino_estipulado": "2026-10-21 12:00:00",
            "fechayhora_destino": "2026-10-21 12:15:00",
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "Atrasado"

    def test_regla_2_llegada_retrasada_mas_de_10_minutos(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": "2026-10-21 10:00:00",
            "fechayhora_origen": "2026-10-21 10:05:00",  # salida a tiempo
            "fechayhora_destino_estipulado": "2026-10-21 12:00:00",
            "fechayhora_destino": "2026-10-21 12:20:00",  # llegada retrasada +20 min
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "Atrasado"

    def test_regla_4_a_tiempo_dentro_del_margen(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": "2026-10-21 10:00:00",
            "fechayhora_origen": "2026-10-21 10:05:00",  # 5 min <= 10 min
            "fechayhora_destino_estipulado": "2026-10-21 12:00:00",
            "fechayhora_destino": "2026-10-21 12:08:00",  # 8 min <= 10 min
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "A tiempo"

    def test_regla_5_solo_fechas_llegada_es_exitoso(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": None,
            "fechayhora_origen": None,
            "fechayhora_destino_estipulado": "2026-10-21 12:00:00",
            "fechayhora_destino": "2026-10-21 12:00:00",
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "Exitoso"

    def test_regla_6_solo_fechas_reales_es_exitoso(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": None,
            "fechayhora_origen": "2026-10-21 10:00:00",
            "fechayhora_destino_estipulado": None,
            "fechayhora_destino": "2026-10-21 12:00:00",
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "Exitoso"

    def test_deducir_estado_llegada_estipulada_y_despegue_real_sin_par_cruzado(self):
        fila = pd.Series({
            "fechayhora_origen_estipulado": None,
            "fechayhora_origen": "2026-10-21 10:00:00",
            "fechayhora_destino_estipulado": "2026-10-21 12:00:00",
            "fechayhora_destino": None,
        })
        imputador = ImputadorEstadoInteligente()
        assert imputador.deducir_estado_fila(fila) == "Exitoso"

    def test_aplicar_preserva_estados_existentes_si_no_fuerza(self):
        df = pd.DataFrame({
            "estado": ["Cancelado", None],
            "fechayhora_origen_estipulado": ["2026-10-21 10:00:00", "2026-10-21 10:00:00"],
            "fechayhora_origen": ["2026-10-21 10:00:00", "2026-10-21 10:00:00"],
            "fechayhora_destino_estipulado": ["2026-10-21 12:00:00", "2026-10-21 12:00:00"],
            "fechayhora_destino": ["2026-10-21 12:00:00", "2026-10-21 12:00:00"],
        })
        imputador = ImputadorEstadoInteligente(forzar_recalculo=False)
        res = imputador.aplicar(df)
        # La fila 0 ya tenía 'Cancelado' y no debe sobreescribirse
        assert res["estado"].iloc[0] == "Cancelado"
        # La fila 1 era None y debe deducirse como 'A tiempo'
        assert res["estado"].iloc[1] == "A tiempo"

    def test_aplicar_con_forzar_recalculo(self):
        df = pd.DataFrame({
            "estado": ["Cancelado"],
            "fechayhora_origen_estipulado": ["2026-10-21 10:00:00"],
            "fechayhora_origen": ["2026-10-21 10:00:00"],
            "fechayhora_destino_estipulado": ["2026-10-21 12:00:00"],
            "fechayhora_destino": ["2026-10-21 12:00:00"],
        })
        imputador = ImputadorEstadoInteligente(forzar_recalculo=True)
        res = imputador.aplicar(df)
        assert res["estado"].iloc[0] == "A tiempo"

    def test_columna_estado_creada_si_no_existe(self):
        df = pd.DataFrame({
            "fechayhora_origen_estipulado": ["2026-10-21 10:00:00"],
            "fechayhora_origen": ["2026-10-21 10:00:00"],
        })
        imputador = ImputadorEstadoInteligente()
        res = imputador.aplicar(df)
        assert "estado" in res.columns
        assert res["estado"].iloc[0] is not None


# =====================================================================
# 8. GeneradorIdVuelo
# =====================================================================

class TestGeneradorIdVuelo:
    """Pruebas unitarias para GeneradorIdVuelo."""

    def test_autogeneracion_secuencial_desde_uno(self):
        df = pd.DataFrame({"id_vuelo": [None, np.nan, ""]})
        generador = GeneradorIdVuelo(prefijo="GEN-", relleno=3)
        res = generador.aplicar(df)
        assert list(res["id_vuelo"]) == ["GEN-001", "GEN-002", "GEN-003"]

    def test_columna_alternativa_fallback_a_id_vuelo(self):
        df = pd.DataFrame({"id_vuelo": [None, "EXISTENTE"]})
        generador = GeneradorIdVuelo(columna="col_inexistente")
        res = generador.aplicar(df)
        assert res["id_vuelo"].iloc[0] == "GEN-001"
        assert res["id_vuelo"].iloc[1] == "EXISTENTE"

    def test_preserva_ids_existentes_y_continua_secuencia(self):
        df = pd.DataFrame({"id_vuelo": ["FL-999", "GEN-004", None, "IB-101", np.nan]})
        generador = GeneradorIdVuelo(prefijo="GEN-", relleno=3)
        res = generador.aplicar(df)
        assert res["id_vuelo"].iloc[0] == "FL-999"
        assert res["id_vuelo"].iloc[1] == "GEN-004"
        assert res["id_vuelo"].iloc[2] == "GEN-005"
        assert res["id_vuelo"].iloc[3] == "IB-101"
        assert res["id_vuelo"].iloc[4] == "GEN-006"

    def test_columna_creada_si_no_existe(self):
        df = pd.DataFrame({"origen": ["JFK"]})
        generador = GeneradorIdVuelo(columna="codigo_vuelo", prefijo="V-", relleno=2)
        res = generador.aplicar(df)
        assert "codigo_vuelo" in res.columns
        assert res["codigo_vuelo"].iloc[0] == "V-01"

    def test_dataframe_sin_nulos_no_cambia(self):
        df = pd.DataFrame({"id_vuelo": ["A1", "A2"]})
        generador = GeneradorIdVuelo()
        res = generador.aplicar(df)
        assert list(res["id_vuelo"]) == ["A1", "A2"]

    def test_dataframe_vacio(self):
        df = pd.DataFrame(columns=["id_vuelo"])
        generador = GeneradorIdVuelo()
        res = generador.aplicar(df)
        assert res.empty


# =====================================================================
# 9. EliminadorFilasNulas
# =====================================================================

class TestEliminadorFilasNulas:
    """Pruebas unitarias para EliminadorFilasNulas."""

    def test_eliminar_nulos_columna_numerica(self):
        # Debe descartar nulos y valores negativos
        df = pd.DataFrame({"precio": [100.0, np.nan, -50.0, 200.0, "texto_invalido"]})
        eliminador = EliminadorFilasNulas(columna="precio")
        res = eliminador.aplicar(df)
        assert len(res) == 2
        assert list(res["precio"]) == [100.0, 200.0]

    def test_eliminar_nulos_columna_fecha(self):
        df = pd.DataFrame({"fechayhora_origen": [
            "2026-10-21 10:00:00",
            None,
            "fecha_completamente_invalida",
            "2026-10-22 15:30:00"
        ]})
        eliminador = EliminadorFilasNulas(columna="fechayhora_origen")
        res = eliminador.aplicar(df)
        assert len(res) == 2
        assert list(res["fechayhora_origen"]) == ["2026-10-21 10:00:00", "2026-10-22 15:30:00"]

    def test_eliminar_nulos_columna_texto(self):
        df = pd.DataFrame({"aeropuerto": ["EZE", "", "   ", "nan", "JFK", None]})
        eliminador = EliminadorFilasNulas(columna="aeropuerto")
        res = eliminador.aplicar(df)
        assert list(res["aeropuerto"]) == ["EZE", "JFK"]

    def test_columna_inexistente_no_rompe(self):
        df = pd.DataFrame({"a": [1, None]})
        eliminador = EliminadorFilasNulas(columna="fantasma")
        res = eliminador.aplicar(df)
        assert len(res) == 2

    def test_dataframe_vacio(self):
        df = pd.DataFrame(columns=["precio"])
        eliminador = EliminadorFilasNulas(columna="precio")
        res = eliminador.aplicar(df)
        assert res.empty


# =====================================================================
# 10. PipelineLimpieza (Orquestador)
# =====================================================================

class TestPipelineLimpieza:
    """Pruebas de integración del orquestador PipelineLimpieza."""

    def test_ejecucion_secuencial_completa(self):
        df = pd.DataFrame({
            "id_vuelo": [None, "FL-2"],
            "origen": ["", "Buenos Aires"],
            "destino": ["Madrid", "Miami"],
            "precio": [100.0, np.nan],
            "capacidad_maxima_avion": [200.0, 200.0],
            "capacidad_usada_avion": [150.0, np.nan],
            "estado": [None, "A tiempo"]
        })

        pipeline = (
            PipelineLimpieza()
            .agregar_paso(GeneradorIdVuelo(columna="id_vuelo", prefijo="AUTO-"))
            .agregar_paso(SaneadorUbicaciones(["origen", "destino"]))
            .agregar_paso(ImputadorMedianaGlobal(columna="precio"))
            .agregar_paso(ImputadorCapacidadesPorFactorOcupacion(metodo="imputar"))
        )

        res = pipeline.ejecutar(df)

        # 1. ID generado
        assert res["id_vuelo"].iloc[0] == "AUTO-001"
        assert res["id_vuelo"].iloc[1] == "FL-2"

        # 2. Origen saneado
        assert res["origen"].iloc[0] == "Desconocido"
        assert res["origen"].iloc[1] == "Buenos Aires"

        # 3. Precio imputado
        assert res["precio"].iloc[1] == 100.0

        # 4. Capacidad usada imputada (factor 150/200 = 0.75 -> 200 * 0.75 = 150)
        assert res["capacidad_usada_avion"].iloc[1] == 150

    def test_pipeline_sin_pasos_retorna_copia_identica(self):
        df = pd.DataFrame({"a": [1, 2]})
        pipeline = PipelineLimpieza()
        res = pipeline.ejecutar(df)
        assert res.equals(df)
        assert res is not df  # Debe ser copia

    def test_pipeline_dataframe_vacio(self):
        df = pd.DataFrame(columns=["id_vuelo", "precio"])
        pipeline = (
            PipelineLimpieza()
            .agregar_paso(GeneradorIdVuelo())
            .agregar_paso(ImputadorMedianaGlobal("precio"))
        )
        res = pipeline.ejecutar(df)
        assert res.empty
