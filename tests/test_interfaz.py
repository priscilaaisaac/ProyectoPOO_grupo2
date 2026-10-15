import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
import streamlit as st
import pandas as pd
from apps.modulo_usuario import limpiar_estado_analisis
from apps.modulo_validacion import modulo_validacion
from apps.modulo_limpieza import modulo_limpieza_y_dominio

RUTA_APP = str(Path(__file__).parent.parent / "apps" / "app_1.py")

class TestInterfazUsuario(unittest.TestCase):
    
    def test_boton_csv_muestra_carga_local(self):
        """Verifica que al hacer clic en 'Subir archivo local' aparezca el menú correcto."""
        at = AppTest.from_file(RUTA_APP, default_timeout=30)
        at.run(timeout=30)
        
        # Encontramos el botón buscando en la colección de botones disponibles
        for btn in at.button:
            if btn.label == "Subir archivo local":
                btn.click()
                break
        at.run(timeout=30)
        
        self.assertEqual(at.session_state.origen_datos, "CSV")
        subtitulos = [s.value for s in at.subheader]
        self.assertIn("Carga de archivo local", subtitulos)

    def test_boton_sql_muestra_conexion(self):
        """Verifica que al hacer clic en 'Conectar base SQL' cambien los campos."""
        at = AppTest.from_file(RUTA_APP, default_timeout=30)
        at.run(timeout=30)
        
        for btn in at.button:
            if btn.label == "Conectar base SQL":
                btn.click()
                break
        at.run()
        
        self.assertEqual(at.session_state.origen_datos, "SQL")
        subtitulos = [s.value for s in at.subheader]
        self.assertIn("Conexión a Base de Datos", subtitulos)

    def test_fabrica_vuelos_es_global_en_modulo_limpieza(self):
        """Verifica que FabricaVuelos no sea variable local en modulo_limpieza_y_dominio."""
        code = modulo_limpieza_y_dominio.__code__
        self.assertNotIn("FabricaVuelos", code.co_varnames, "FabricaVuelos no debe ser tratada como variable local para evitar UnboundLocalError")
        self.assertIn("FabricaVuelos", code.co_names, "FabricaVuelos debe ser resuelta desde el ámbito global del módulo")

    def test_limpiar_estado_analisis_restablece_variables_completamente(self):
        """Verifica que limpiar_estado_analisis restablezca a None o valores por defecto el estado de análisis."""
        # Simular sesión cargada tras inspeccionar un archivo en perfil
        st.session_state.df_crudo = pd.DataFrame({"col": [1, 2]})
        st.session_state.df_crudo_completo = pd.DataFrame({"col": [1, 2]})
        st.session_state.df_estandarizado = pd.DataFrame({"col": [1, 2]})
        st.session_state.df_limpio = pd.DataFrame({"col": [1, 2]})
        st.session_state.contrato_validado = True
        st.session_state.archivos_procesados = True
        st.session_state.archivo_es_limpio = True
        st.session_state.modo_limpieza_directa = True
        st.session_state.nombre_archivo_actual = "archivo_prueba.csv"
        st.session_state.lista_vuelos = ["vuelo1", "vuelo2"]
        st.session_state.columnas_disponibles = ["col"]
        st.session_state.origen_por_columna = {"col": "archivo_prueba.csv"}
        st.session_state.archivos_dfs = {"archivo_prueba.csv": pd.DataFrame()}

        # Ejecutar limpieza
        limpiar_estado_analisis()

        # Comprobar que todas las variables vuelvan a su estado inactivo
        self.assertIsNone(st.session_state.df_crudo)
        self.assertIsNone(st.session_state.df_crudo_completo)
        self.assertIsNone(st.session_state.df_estandarizado)
        self.assertIsNone(st.session_state.df_limpio)
        self.assertFalse(st.session_state.contrato_validado)
        self.assertFalse(st.session_state.archivos_procesados)
        self.assertFalse(st.session_state.archivo_es_limpio)
        self.assertFalse(st.session_state.modo_limpieza_directa)
        self.assertIsNone(st.session_state.nombre_archivo_actual)
        self.assertEqual(st.session_state.lista_vuelos, [])
        self.assertEqual(st.session_state.columnas_disponibles, [])
        self.assertEqual(st.session_state.origen_por_columna, {})
        self.assertEqual(st.session_state.archivos_dfs, {})

    def test_condicional_escape_rapido_modulos_inferiores(self):
        """Verifica que modulo_validacion y modulo_limpieza_y_dominio aborten inmediatamente sin archivo activo."""
        limpiar_estado_analisis()
        # No deben lanzar excepciones ni renderizar nada cuando el estado está limpio
        modulo_validacion()
        modulo_limpieza_y_dominio(None)


if __name__ == '__main__':
    unittest.main()