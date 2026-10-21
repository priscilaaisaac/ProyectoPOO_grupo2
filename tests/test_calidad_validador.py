"""
Suite exhaustiva de pruebas unitarias para los módulos de Auditoría de Calidad,
Validación de Esquema y Contratos, y Fábrica de Objetos Vuelo
(modules.calidad, modules.validador, modules.fabrica_vuelos).

Cumple estrictamente con:
- Aislamiento absoluto (100% en memoria mediante DataFrames y estructuras sintéticas).
- Exclusión total de UI y dependencias de Streamlit.
- Cobertura integral (>= 70%, buscando >= 95%):
  - EstandarizadorDatos (normalización de nulos, saneamiento de espacios, filtro de umbral >= 50% de nulos).
  - ReporteCalidad y AnalizadorDuplicados.
  - InspectorTipos (patrones de error regex, tipos generales).
  - Reglas de validación: ReglaCamposRequeridos, ReglaCapacidadesYPrecio, ReglaParidadFormatos, ReglaCronologiaFechas.
  - ValidadorEsquema y validar_estructura_tabular (deduplicación de columnas, pandera/fallback).
  - ValidadorPreInstanciacion (contrato estricto antes de instanciación).
  - FabricaVuelos (instanciación desde DataFrames saneados y control de consistencia).
"""

from datetime import datetime
import numpy as np
import pandas as pd
import pytest

from modules.calidad import (
    EstandarizadorDatos,
    ReporteCalidad,
    AnalizadorDuplicados,
    sanear_dataframe_individual,
    filtrar_por_umbral_nulos,
    VALORES_VACIOS,
)
from modules.validador import (
    InspectorTipos,
    ReglaCamposRequeridos,
    ReglaCapacidadesYPrecio,
    ReglaParidadFormatos,
    ReglaCronologiaFechas,
    ValidadorEsquema,
    validar_estructura_tabular,
    ValidadorPreInstanciacion,
)
from modules.fabrica_vuelos import FabricaVuelos
from modules.Vuelos import Vuelo


# =====================================================================
# 1. Pruebas para EstandarizadorDatos y Funciones de Calidad
# =====================================================================

class TestEstandarizadorDatos:
    """Pruebas para normalización de valores nulos, saneamiento y filtro de umbral."""

    def test_normalizar_reemplaza_todas_las_variantes_de_vacios_por_nan(self):
        datos = {
            "texto": ["valido", "", " ", "   ", "nan", "NaN", "null", "NULL", "None", "none", "N/A", "n/a", "-", "."],
            "numero": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        }
        df = pd.DataFrame(datos)
        df_norm = EstandarizadorDatos.normalizar(df)

        # El primer valor es válido, los restantes 13 deben ser NaN
        assert df_norm["texto"].iloc[0] == "valido"
        assert df_norm["texto"].iloc[1:].isna().all()
        # La columna numérica no debe verse alterada
        assert list(df_norm["numero"]) == list(range(1, 15))

    def test_sanear_dataframe_individual_cabeceras_y_valores(self):
        df = pd.DataFrame({
            "  col_con_espacios  ": ["  valor1  ", "valor2 ", " valor3"],
            "col_numerica": [10, 20, 30]
        })
        df_limpio = EstandarizadorDatos.sanear_dataframe_individual(df)

        assert list(df_limpio.columns) == ["col_con_espacios", "col_numerica"]
        assert list(df_limpio["col_con_espacios"]) == ["valor1", "valor2", "valor3"]
        assert list(df_limpio["col_numerica"]) == [10, 20, 30]

    def test_sanear_dataframe_individual_casos_borde_none_y_vacio(self):
        assert EstandarizadorDatos.sanear_dataframe_individual(None) is None
        df_vacio = pd.DataFrame()
        assert EstandarizadorDatos.sanear_dataframe_individual(df_vacio).empty
        # Alias sanear_espacios
        assert EstandarizadorDatos.sanear_espacios(df_vacio).empty
        # Función a nivel de módulo
        assert sanear_dataframe_individual(df_vacio).empty

    def test_filtrar_por_umbral_nulos_50_porciento(self):
        """
        Elimina automáticamente los registros que tengan 50% o más de nulos:
        - Fila 0: 0 nulos de 4 (0%) -> se conserva
        - Fila 1: 1 nulo de 4 (25%) -> se conserva
        - Fila 2: 2 nulos de 4 (50%) -> SE ELIMINA (umbral >= 50%)
        - Fila 3: 3 nulos de 4 (75%) -> SE ELIMINA
        - Fila 4: 4 nulos de 4 (100%) -> SE ELIMINA
        """
        df = pd.DataFrame({
            "c1": ["A", "B", "C", "D", np.nan],
            "c2": ["1", "2", np.nan, np.nan, "null"],
            "c3": ["X", "Y", "Z", "-", ""],
            "c4": [10, np.nan, np.nan, np.nan, None]
        })

        df_filtrado, eliminados = EstandarizadorDatos.filtrar_por_umbral_nulos(df, umbral_pct=0.50)

        assert eliminados == 3
        assert len(df_filtrado) == 2
        assert list(df_filtrado["c1"]) == ["A", "B"]

    def test_filtrar_por_umbral_nulos_dataframe_vacio_o_none(self):
        df_res, elim = EstandarizadorDatos.filtrar_por_umbral_nulos(None)
        assert df_res is None
        assert elim == 0

        df_vacio = pd.DataFrame()
        df_res_vacio, elim_vacio = filtrar_por_umbral_nulos(df_vacio)
        assert df_res_vacio.empty
        assert elim_vacio == 0


# =====================================================================
# 2. Pruebas para ReporteCalidad y AnalizadorDuplicados
# =====================================================================

class TestReporteCalidadYDuplicados:
    """Pruebas de generación de métricas de calidad de datos y análisis de duplicados."""

    def test_reporte_calidad_generar_normal(self):
        df = pd.DataFrame({
            "id": ["1", "2", "3", "4"],
            "precio": [100.0, np.nan, 200.0, np.nan],
            "origen": ["EZE", "COR", np.nan, "BRC"],
            "col_extra": [1, 2, 3, 4]
        })
        mapeo = {
            "id_vuelo": "id",
            "precio": "precio",
            "origen": "origen",
            "destino": "(No asignar)",
            "aerolinea": "col_inexistente"
        }

        reporte = ReporteCalidad(df, mapeo)
        df_reporte = reporte.generar()

        # Debe generar reporte sólo para las 3 variables presentes y asignadas
        assert len(df_reporte) == 3
        assert "Atributo del Sistema" in df_reporte.columns
        assert "Cantidad Nulls" in df_reporte.columns
        assert "Porcentaje (%)" in df_reporte.columns

        fila_precio = df_reporte[df_reporte["Atributo del Sistema"] == "precio"].iloc[0]
        assert fila_precio["Cantidad Nulls"] == 2
        assert fila_precio["Porcentaje (%)"] == 50.0

    def test_reporte_calidad_dataframe_vacio(self):
        df_vacio = pd.DataFrame(columns=["id", "precio"])
        mapeo = {"id_vuelo": "id", "precio": "precio"}
        reporte = ReporteCalidad(df_vacio, mapeo)
        df_reporte = reporte.generar()
        assert len(df_reporte) == 2
        assert df_reporte["Porcentaje (%)"].iloc[0] == 0.0

    def test_calcular_impacto_descarte(self):
        df = pd.DataFrame({"colA": [1, np.nan, 3, np.nan]})
        reporte = ReporteCalidad(df, {})
        nulos, pct = reporte.calcular_impacto_descarte("colA")
        assert nulos == 2
        assert pct == 50.0

        # Columna inexistente
        nulos_err, pct_err = reporte.calcular_impacto_descarte("col_inexistente")
        assert nulos_err == 0
        assert pct_err == 0.0

    def test_calcular_impacto_ambas_nulas(self):
        df = pd.DataFrame({
            "c_max": [200, np.nan, np.nan, 150],
            "c_usada": [150, 100, np.nan, np.nan]
        })
        # Fila 2 tiene ambas nulas (1 de 4 = 25%)
        reporte = ReporteCalidad(df, {})
        nulos, pct = reporte.calcular_impacto_ambas_nulas("c_max", "c_usada")
        assert nulos == 1
        assert pct == 25.0

        # Columna ausente
        nulos_inv, pct_inv = reporte.calcular_impacto_ambas_nulas("c_max", "fantasma")
        assert nulos_inv == 0
        assert pct_inv == 0.0

    def test_analizador_duplicados_contar(self):
        df = pd.DataFrame({
            "a": [1, 2, 1, 3, 1],
            "b": ["x", "y", "x", "z", "x"]
        })
        # (1, 'x') aparece 3 veces -> 2 filas duplicadas
        duplicados = AnalizadorDuplicados.contar(df)
        assert duplicados == 2


# =====================================================================
# 3. Pruebas para InspectorTipos
# =====================================================================

class TestInspectorTipos:
    """Pruebas para clasificación semántica y reconocimiento de patrones de error."""

    def test_es_patron_error_o_vacio_valores_nulos_y_texto(self):
        assert InspectorTipos.es_patron_error_o_vacio(None) is True
        assert InspectorTipos.es_patron_error_o_vacio(np.nan) is True
        assert InspectorTipos.es_patron_error_o_vacio(pd.NA) is True
        assert InspectorTipos.es_patron_error_o_vacio("") is True
        assert InspectorTipos.es_patron_error_o_vacio("   ") is True
        assert InspectorTipos.es_patron_error_o_vacio("none") is True
        assert InspectorTipos.es_patron_error_o_vacio("NULL") is True
        assert InspectorTipos.es_patron_error_o_vacio("nan") is True
        assert InspectorTipos.es_patron_error_o_vacio("N/A") is True
        assert InspectorTipos.es_patron_error_o_vacio("error") is True

    def test_es_patron_error_o_vacio_codigos_regex_admitidos(self):
        assert InspectorTipos.es_patron_error_o_vacio("error_498") is True
        assert InspectorTipos.es_patron_error_o_vacio("error123") is True
        assert InspectorTipos.es_patron_error_o_vacio("err_01") is True
        assert InspectorTipos.es_patron_error_o_vacio("err-50") is True
        assert InspectorTipos.es_patron_error_o_vacio("error 10") is True

        # Valores válidos que no son errores
        assert InspectorTipos.es_patron_error_o_vacio("Buenos Aires") is False
        assert InspectorTipos.es_patron_error_o_vacio("FL-100") is False
        assert InspectorTipos.es_patron_error_o_vacio(150.0) is False
        assert InspectorTipos.es_patron_error_o_vacio(0) is False

    def test_obtener_tipo_general(self):
        assert InspectorTipos.obtener_tipo_general(pd.Series(["a", "b"])) == "texto"
        assert InspectorTipos.obtener_tipo_general(pd.Series([1, 2, 3])) == "numerico"
        assert InspectorTipos.obtener_tipo_general(pd.Series([1.5, 2.8])) == "numerico"
        assert InspectorTipos.obtener_tipo_general(pd.to_datetime(pd.Series(["2026-10-21"]))) == "fecha"
        s_periodo = pd.Series(pd.date_range("2026", periods=2).to_period("M"))
        assert InspectorTipos.obtener_tipo_general(s_periodo) == "otro"


# =====================================================================
# 4. Pruebas para Reglas de Validación de Esquema
# =====================================================================

class TestReglasValidacionEsquema:
    """Pruebas de reglas de contrato: campos requeridos, capacidades, precios y fechas."""

    @pytest.fixture
    def df_valido(self):
        return pd.DataFrame({
            "col_id": ["FL-1", "FL-2"],
            "col_precio": [150.0, 250.0],
            "col_cmax": [200, 180],
            "col_cusada": [150, 120],
            "col_orig": ["EZE", "COR"],
            "col_dest": ["MIA", "BRC"],
            "col_f_salida": ["2026-10-21 10:00:00", "2026-10-21 11:00:00"],
            "col_f_llegada": ["2026-10-21 18:00:00", "2026-10-21 14:00:00"],
            "col_fest_salida": ["2026-10-21 10:00:00", "2026-10-21 11:00:00"],
            "col_fest_llegada": ["2026-10-21 18:00:00", "2026-10-21 14:00:00"],
        })

    @pytest.fixture
    def mapeo_valido(self):
        return {
            "id_vuelo": "col_id",
            "precio": "col_precio",
            "capacidad_maxima_avion": "col_cmax",
            "capacidad_usada_avion": "col_cusada",
            "aeropuerto_origen": "col_orig",
            "aeropuerto_destino": "col_dest",
            "fechayhora_origen": "col_f_salida",
            "fechayhora_destino": "col_f_llegada",
            "fechayhora_origen_estipulado": "col_fest_salida",
            "fechayhora_destino_estipulado": "col_fest_llegada",
        }

    # --- ReglaCamposRequeridos ---

    def test_regla_campos_requeridos_falla_si_falta_asignacion(self, df_valido, mapeo_valido):
        mapeo_valido["precio"] = "(No asignar)"
        regla = ReglaCamposRequeridos()
        with pytest.raises(ValueError, match="Asignación obligatoria incompleta"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    def test_regla_campos_requeridos_falla_si_columna_100_pct_vacia(self, df_valido, mapeo_valido):
        df_valido["col_precio"] = [np.nan, "   "]
        regla = ReglaCamposRequeridos()
        with pytest.raises(ValueError, match="están completamente vacías"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    def test_regla_campos_requeridos_columna_inexistente(self, df_valido, mapeo_valido):
        mapeo_valido["precio"] = "col_inexistente_en_dataset"
        regla = ReglaCamposRequeridos()
        with pytest.raises(ValueError, match="están completamente vacías o no existen"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    def test_regla_precio_no_asignado_o_columna_inexistente(self, df_valido, mapeo_valido):
        regla = ReglaCapacidadesYPrecio()
        # 1. No asignado
        mapeo_sin_precio = mapeo_valido.copy()
        mapeo_sin_precio["precio"] = "(No asignar)"
        with pytest.raises(ValueError, match="El atributo 'precio' es estrictamente obligatorio"):
            regla.ejecutar(df_valido, mapeo_sin_precio, requeridos=["precio"])

        # 2. Asignado a columna que no existe
        mapeo_precio_inexistente = mapeo_valido.copy()
        mapeo_precio_inexistente["precio"] = "col_precio_fantasma"
        with pytest.raises(ValueError, match="La columna asignada al atributo 'precio' no existe"):
            regla.ejecutar(df_valido, mapeo_precio_inexistente, requeridos=["precio"])

    # --- ReglaCapacidadesYPrecio ---

    def test_regla_capacidades_no_enteras_falla(self, df_valido, mapeo_valido):
        df_valido["col_cmax"] = [200.5, 180]
        regla = ReglaCapacidadesYPrecio()
        with pytest.raises(ValueError, match="Solo se admiten números enteros"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    def test_regla_capacidades_tolera_etiquetas_error(self, df_valido, mapeo_valido):
        df_valido["col_cmax"] = ["200", "error_404"]
        regla = ReglaCapacidadesYPrecio()
        # Debe tolerar "error_404" sin lanzar excepción
        regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    def test_regla_capacidades_negativas_falla(self, df_valido, mapeo_valido):
        df_valido["col_cmax"] = [-100, 200]
        regla = ReglaCapacidadesYPrecio()
        with pytest.raises(ValueError, match="no pueden ser números negativos"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    def test_regla_capacidad_usada_mayor_a_maxima_falla(self, df_valido, mapeo_valido):
        df_valido["col_cusada"] = [250, 100]  # 250 > 200
        regla = ReglaCapacidadesYPrecio()
        with pytest.raises(ValueError, match="capacidad usada' es mayor a la 'capacidad máxima'"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    def test_regla_precio_no_numerico_o_negativo_falla(self, df_valido, mapeo_valido):
        regla = ReglaCapacidadesYPrecio()

        df_valido["col_precio"] = ["cien_pesos", 200]
        with pytest.raises(ValueError, match="Solo se admiten números"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

        df_valido["col_precio"] = [-50.0, 200.0]
        with pytest.raises(ValueError, match="valores numéricos negativos"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=["precio"])

    # --- ReglaParidadFormatos ---

    def test_regla_paridad_formatos_tipos_incompatibles_falla(self, df_valido, mapeo_valido):
        # Origen texto y Destino numérico
        df_valido["col_dest"] = [12345, 67890]
        regla = ReglaParidadFormatos()
        with pytest.raises(ValueError, match="deben compartir el mismo tipo de dato general"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=[])

    # --- ReglaCronologiaFechas ---

    def test_regla_cronologia_fechas_llegada_anterior_a_salida_falla(self, df_valido, mapeo_valido):
        # Llegada antes del despegue
        df_valido["col_f_salida"] = ["2026-10-21 15:00:00", "2026-10-21 10:00:00"]
        df_valido["col_f_llegada"] = ["2026-10-21 12:00:00", "2026-10-21 14:00:00"]
        regla = ReglaCronologiaFechas()
        with pytest.raises(ValueError, match="es igual o posterior a"):
            regla.ejecutar(df_valido, mapeo_valido, requeridos=[])

    # --- ValidadorEsquema Orquestador ---

    def test_validador_esquema_contrato_exitoso(self, df_valido, mapeo_valido):
        validador = ValidadorEsquema(df_valido, mapeo_valido, requeridos=["precio", "id_vuelo"])
        res = validador.validar()
        assert res == "Contrato validado exitosamente."

    def test_validar_estructura_tabular_deduplica_columnas_repetidas(self):
        df = pd.DataFrame([[1, 2]], columns=["col", "col"])
        df_res = validar_estructura_tabular(df)
        assert list(df_res.columns) == ["col", "col_2"]

    def test_validador_esquema_metodo_estatico_validar_estructura_tabular(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df_res = ValidadorEsquema.validar_estructura_tabular(df)
        assert list(df_res.columns) == ["a", "b"]

    def test_validar_estructura_tabular_columnas_ya_unicas(self):
        df = pd.DataFrame({"alpha": [1], "beta": [2]})
        df_res = validar_estructura_tabular(df)
        assert list(df_res.columns) == ["alpha", "beta"]

    def test_validar_estructura_tabular_tipo_invalido_lanza_type_error(self):
        with pytest.raises(TypeError, match="Se esperaba una instancia de pd.DataFrame"):
            validar_estructura_tabular("no_es_dataframe")

    def test_validar_estructura_tabular_dataframe_vacio(self):
        df = pd.DataFrame()
        assert validar_estructura_tabular(df).empty


# =====================================================================
# 5. Pruebas para ValidadorPreInstanciacion
# =====================================================================

class TestValidadorPreInstanciacion:
    """Pruebas del validador estricto ejecutado inmediatamente antes de instanciar Vuelos."""

    @pytest.fixture
    def df_pre_valido(self):
        return pd.DataFrame({
            "precio": [100.0, 200.0],
            "capacidad_maxima_avion": [200, 150],
            "capacidad_usada_avion": [150, 100],
            "fechayhora_origen_estipulado": ["2026-10-21 08:00:00", "2026-10-21 09:00:00"],
            "fechayhora_destino_estipulado": ["2026-10-21 12:00:00", "2026-10-21 14:00:00"],
        })

    def test_pre_validacion_exitosa(self, df_pre_valido):
        # No debe lanzar ninguna excepción
        ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_dataframe_nulo_o_vacio(self):
        with pytest.raises(ValueError, match="está vacío o es nulo"):
            ValidadorPreInstanciacion.validar(None)
        with pytest.raises(ValueError, match="está vacío o es nulo"):
            ValidadorPreInstanciacion.validar(pd.DataFrame())

    def test_pre_validacion_falta_columna_obligatoria(self, df_pre_valido):
        df_incompleto = df_pre_valido.drop(columns=["precio"])
        with pytest.raises(ValueError, match="El campo obligatorio 'precio' no se encuentra presente"):
            ValidadorPreInstanciacion.validar(df_incompleto)

    def test_pre_validacion_valores_nulos_o_error_en_campo_obligatorio(self, df_pre_valido):
        df_pre_valido["precio"] = [100.0, np.nan]
        with pytest.raises(ValueError, match="contiene 1 valores nulos, vacíos o sin tratar"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_precio_negativo(self, df_pre_valido):
        df_pre_valido["precio"] = [100.0, -20.0]
        with pytest.raises(ValueError, match="el precio no puede ser negativo"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_capacidad_usada_mayor_a_maxima(self, df_pre_valido):
        df_pre_valido["capacidad_usada_avion"] = [300, 100]  # 300 > 200
        with pytest.raises(ValueError, match="capacidad usada .* es mayor a capacidad máxima"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_fecha_invalida_o_cronologia_inversa(self, df_pre_valido):
        df_pre_valido["fechayhora_origen_estipulado"] = ["fecha_invalida", "2026-10-21 09:00:00"]
        with pytest.raises(ValueError, match="no tiene un formato de fecha válido"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

        df_pre_valido["fechayhora_origen_estipulado"] = ["2026-10-21 16:00:00", "2026-10-21 09:00:00"]
        df_pre_valido["fechayhora_destino_estipulado"] = ["2026-10-21 12:00:00", "2026-10-21 14:00:00"]
        with pytest.raises(ValueError, match="no puede ser anterior a la de origen estipulada"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_precio_no_numerico(self, df_pre_valido):
        df_pre_valido["precio"] = ["texto_invalido", 100.0]
        with pytest.raises(ValueError, match="no es numérico"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_capacidad_no_numerica(self, df_pre_valido):
        df_pre_valido["capacidad_maxima_avion"] = ["no_numero", 150]
        with pytest.raises(ValueError, match="no es numérico"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_capacidad_no_entera(self, df_pre_valido):
        df_pre_valido["capacidad_maxima_avion"] = [150.5, 150]
        with pytest.raises(ValueError, match="no es un número entero"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_capacidad_negativa(self, df_pre_valido):
        df_pre_valido["capacidad_maxima_avion"] = [-10, 150]
        with pytest.raises(ValueError, match="la capacidad no puede ser negativa"):
            ValidadorPreInstanciacion.validar(df_pre_valido)

    def test_pre_validacion_fecha_destino_invalida(self, df_pre_valido):
        df_pre_valido["fechayhora_destino_estipulado"] = ["fecha_invalida", "2026-10-21 14:00:00"]
        with pytest.raises(ValueError, match="no tiene un formato de fecha válido"):
            ValidadorPreInstanciacion.validar(df_pre_valido)


# =====================================================================
# 6. Pruebas para FabricaVuelos
# =====================================================================

class TestFabricaVuelos:
    """Pruebas para instanciación controlada de objetos Vuelo desde DataFrames."""

    @pytest.fixture
    def df_limpio(self):
        return pd.DataFrame({
            "id_vuelo": ["FL-001", "FL-002"],
            "aeropuerto_origen": ["EZE", "COR"],
            "aeropuerto_destino": ["MIA", "BRC"],
            "origen": ["Buenos Aires", "Cordoba"],
            "destino": ["Miami", "Bariloche"],
            "fechayhora_origen": ["2026-10-21 08:05:00", "2026-10-21 09:00:00"],
            "fechayhora_destino": ["2026-10-21 14:30:00", "2026-10-21 11:30:00"],
            "fechayhora_origen_estipulado": ["2026-10-21 08:00:00", "2026-10-21 09:00:00"],
            "fechayhora_destino_estipulado": ["2026-10-21 14:30:00", "2026-10-21 11:30:00"],
            "estado": ["A tiempo", "A tiempo"],
            "capacidad_maxima_avion": [200, 150],
            "capacidad_usada_avion": [160, 120],
            "precio": [350.0, 120.0],
        })

    def test_instanciar_desde_dataframe_exitoso(self, df_limpio):
        mapeo = {c: c for c in df_limpio.columns}
        vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, mapeo)

        assert len(vuelos) == 2
        assert isinstance(vuelos[0], Vuelo)
        assert vuelos[0].id_vuelo == "FL-001"
        assert vuelos[0].aeropuerto_origen == "EZE"
        assert vuelos[0].precio == 350.0
        assert vuelos[0].capacidad_maxima_avion == 200

    def test_instanciar_dataframe_vacio_o_none_retorna_lista_vacia(self):
        assert FabricaVuelos.instanciar_desde_dataframe(None, {}) == []
        assert FabricaVuelos.instanciar_desde_dataframe(pd.DataFrame(), {}) == []

    def test_instanciar_bloquea_si_falla_pre_validacion(self, df_limpio):
        # Alteramos precio a negativo para provocar bloqueo
        df_limpio["precio"] = [-10.0, 120.0]
        mapeo = {c: c for c in df_limpio.columns}
        with pytest.raises(ValueError, match="el precio no puede ser negativo"):
            FabricaVuelos.instanciar_desde_dataframe(df_limpio, mapeo)

    def test_instanciar_sin_mapeo_columnas_directas(self, df_limpio):
        # Mapeo vacío o None: debe buscar por los nombres de columnas canónicos
        vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, mapeo={})
        assert len(vuelos) == 2
        assert vuelos[0].precio == 350.0

    def test_instanciar_columnas_opcionales_ausentes(self, df_limpio):
        # Quitamos origen, destino e id_vuelo
        df_minimo = df_limpio.drop(columns=["origen", "destino", "id_vuelo"])
        vuelos = FabricaVuelos.instanciar_desde_dataframe(df_minimo, mapeo={})
        assert len(vuelos) == 2
        assert vuelos[0].origen is None
        assert vuelos[0].destino is None
        assert vuelos[0].id_vuelo is None

    def test_instanciar_capacidades_no_parseables_fallback_cero(self, df_limpio):
        import unittest.mock as mock
        # Mockeamos ValidadorPreInstanciacion para probar el bloque try/except de capacidades en la fábrica
        with mock.patch("modules.validador.ValidadorPreInstanciacion.validar"):
            df_limpio["capacidad_maxima_avion"] = ["no_entero", 100]
            df_limpio["capacidad_usada_avion"] = [None, 50]
            vuelos = FabricaVuelos.instanciar_desde_dataframe(df_limpio, mapeo={})
            assert vuelos[0].capacidad_maxima_avion == 0
            assert vuelos[0].capacidad_usada_avion == 0

    def test_instanciar_precio_invalido_lanza_error_en_fabrica(self, df_limpio):
        import unittest.mock as mock
        with mock.patch("modules.validador.ValidadorPreInstanciacion.validar"):
            # Caso 1: precio None
            df_none = df_limpio.copy()
            df_none["precio"] = [None, 100.0]
            with pytest.raises(ValueError, match="no cuenta con un 'precio' válido"):
                FabricaVuelos.instanciar_desde_dataframe(df_none, mapeo={})

            # Caso 2: precio texto no numérico
            df_str = df_limpio.copy()
            df_str["precio"] = ["texto_invalido", 100.0]
            with pytest.raises(ValueError, match="Error de precio"):
                FabricaVuelos.instanciar_desde_dataframe(df_str, mapeo={})

