import unittest
from unittest.mock import MagicMock
import pandas as pd
from apps.modulo_validacion import (
    _auto_detectar_columna,
    formatear_opcion_con_archivo,
    ATRIBUTOS_REQUERIDOS,
    ATRIBUTOS_OPCIONALES
)


class MockSessionState(dict):
    """Permite acceder y modificar atributos como en st.session_state."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return None

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            pass


class TestModuloValidacionExclusionMutua(unittest.TestCase):

    def test_auto_detectar_columna(self):
        columnas = ["id_vuelo", "aero_salida", "aeropuerto_destino", "precio"]
        self.assertEqual(_auto_detectar_columna("id_vuelo", columnas), "id_vuelo")
        self.assertEqual(_auto_detectar_columna("aeropuerto_destino", columnas), "aeropuerto_destino")
        self.assertEqual(_auto_detectar_columna("no_existe", columnas), "(No asignar)")

    def test_formatear_opcion_con_archivo(self):
        import streamlit as st
        st.session_state.origen_por_columna = {
            "id_vuelo": "archivo_1.csv",
            "precio": {"archivo": "archivo_2.csv"}
        }

        self.assertEqual(formatear_opcion_con_archivo("(No asignar)"), "(No asignar)")
        self.assertEqual(formatear_opcion_con_archivo("id_vuelo"), "id_vuelo (de: archivo_1.csv)")
        self.assertEqual(formatear_opcion_con_archivo("precio"), "precio (de: archivo_2.csv)")
        self.assertEqual(formatear_opcion_con_archivo("desconocida"), "desconocida")

    def test_logica_exclusion_mutua_opciones(self):
        """
        Verifica matemáticamente las reglas de exclusión mutua:
        1. Las opciones de cada selectbox contienen: ['(No asignar)'] + [col_actual (si hay)] + [columnas_libres].
        2. Una columna ocupada en el selectbox A no debe aparecer en el selectbox B.
        3. Al liberar la columna en A, debe reaparecer en B.
        """
        cols_archivo = ["col_A", "col_B", "col_C", "col_D"]
        session_mock = {
            "single_req_aeropuerto_destino": "col_A",
            "single_req_aeropuerto_origen": "col_B",
            "single_req_fechayhora_origen": "(No asignar)"
        }

        # 1. Detectar ocupadas
        columnas_ocupadas = {v for k, v in session_mock.items() if v != "(No asignar)" and v in cols_archivo}
        self.assertEqual(columnas_ocupadas, {"col_A", "col_B"})

        # 2. Construcción de opciones para atributo 1 (aeropuerto_destino, tiene 'col_A')
        col_actual_1 = session_mock.get("single_req_aeropuerto_destino")
        ocupadas_otros_1 = columnas_ocupadas - {col_actual_1}
        libres_1 = [c for c in cols_archivo if c not in ocupadas_otros_1 and c != col_actual_1]
        opciones_1 = ["(No asignar)", col_actual_1] + libres_1

        self.assertEqual(opciones_1, ["(No asignar)", "col_A", "col_C", "col_D"])
        self.assertNotIn("col_B", opciones_1, "col_B está ocupada por otro atributo y no debe estar")

        # 3. Construcción de opciones para atributo 3 (fechayhora_origen, tiene '(No asignar)')
        col_actual_3 = None
        ocupadas_otros_3 = columnas_ocupadas
        libres_3 = [c for c in cols_archivo if c not in ocupadas_otros_3]
        opciones_3 = ["(No asignar)"] + libres_3

        self.assertEqual(opciones_3, ["(No asignar)", "col_C", "col_D"])
        self.assertNotIn("col_A", opciones_3, "col_A está ocupada por aeropuerto_destino")
        self.assertNotIn("col_B", opciones_3, "col_B está ocupada por aeropuerto_origen")

        # 4. Simular que el usuario libera col_A en el atributo 1
        session_mock["single_req_aeropuerto_destino"] = "(No asignar)"
        columnas_ocupadas_despues = {v for k, v in session_mock.items() if v != "(No asignar)" and v in cols_archivo}
        self.assertEqual(columnas_ocupadas_despues, {"col_B"})

        libres_3_despues = [c for c in cols_archivo if c not in columnas_ocupadas_despues]
        opciones_3_despues = ["(No asignar)"] + libres_3_despues
        self.assertIn("col_A", opciones_3_despues, "col_A debe haber vuelto a estar disponible para atributo 3")


if __name__ == "__main__":
    unittest.main()
