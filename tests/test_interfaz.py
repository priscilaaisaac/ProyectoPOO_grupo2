import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

RUTA_APP = str(Path(__file__).parent.parent / "apps" / "app_1.py")

class TestInterfazUsuario(unittest.TestCase):
    
    def test_boton_csv_muestra_carga_local(self):
        """Verifica que al hacer clic en 'Subir archivo local' aparezca el menú correcto."""
        at = AppTest.from_file(RUTA_APP)
        at.run()
        
        # Encontramos el botón buscando en la colección de botones disponibles
        for btn in at.button:
            if btn.label == "Subir archivo local":
                btn.click()
                break
        at.run()
        
        self.assertEqual(at.session_state.origen_datos, "CSV")
        subtitulos = [s.value for s in at.subheader]
        self.assertIn("Carga de archivo local", subtitulos)

    def test_boton_sql_muestra_conexion(self):
        """Verifica que al hacer clic en 'Conectar base SQL' cambien los campos."""
        at = AppTest.from_file(RUTA_APP)
        at.run()
        
        for btn in at.button:
            if btn.label == "Conectar base SQL":
                btn.click()
                break
        at.run()
        
        self.assertEqual(at.session_state.origen_datos, "SQL")
        subtitulos = [s.value for s in at.subheader]
        self.assertIn("Conexión a Base de Datos", subtitulos)

if __name__ == '__main__':
    unittest.main()

    