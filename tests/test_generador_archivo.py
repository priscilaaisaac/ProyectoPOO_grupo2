import unittest
import pandas as pd
from modules.Generador_Archivo.generador_archivo_base import GeneradorArchivo
from modules.Generador_Archivo.generador_pdf import GeneradorReportePDF
from modules.Generador_Archivo.generador_docx import GeneradorDOCX


class GeneradorDummy(GeneradorArchivo):
    """Generador concreto simulado para verificar la extensibilidad OCP."""
    def generar_archivo(self) -> bytes:
        return b"archivo_simulado"


class TestGeneradorArchivo(unittest.TestCase):

    def test_generador_archivo_es_abstracto(self):
        """Verifica que GeneradorArchivo no pueda instanciarse directamente."""
        with self.assertRaises(TypeError):
            GeneradorArchivo()

    def test_subclase_concreta_y_almacenamiento_datos(self):
        """Verifica que la clase base almacene los datos y la subclase funcione bajo OCP."""
        dummy = GeneradorDummy(
            simulaciones=[{"test": 1}],
            graficos=[],
            nombre_dataset="Dataset Test",
            usuario="TestUser"
        )
        self.assertEqual(dummy.nombre_dataset, "Dataset Test")
        self.assertEqual(dummy.usuario, "TestUser")
        self.assertEqual(dummy.simulaciones, [{"test": 1}])
        self.assertEqual(dummy.TITULO_OFICIAL, "Análisis Histórico de Vuelos para la Toma de Decisiones")
        self.assertEqual(dummy.generar_archivo(), b"archivo_simulado")

    def test_generador_pdf_herencia_y_contrato(self):
        """Verifica que GeneradorReportePDF herede de GeneradorArchivo y cumpla el contrato."""
        self.assertTrue(issubclass(GeneradorReportePDF, GeneradorArchivo))
        gen_pdf = GeneradorReportePDF(usuario="Tester")
        self.assertEqual(gen_pdf.usuario, "Tester")
        self.assertTrue(hasattr(gen_pdf, "generar_archivo"))
        self.assertTrue(hasattr(gen_pdf, "construir_pdf"))

    def test_renderizado_pdf_dinamico_vacio(self):
        """Verifica que un reporte sin secciones se genere válidamente en PDF sin errores."""
        gen_pdf = GeneradorReportePDF(
            simulaciones=[],
            graficos=[],
            tablas_condicionales=[],
            nombre_dataset="Vuelos_2026",
            usuario="Admin"
        )
        pdf_bytes = gen_pdf.generar_archivo()
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_renderizado_pdf_dinamico_solo_tablas_condicionales(self):
        """Verifica que si solo hay tablas condicionales, se renderice dinámicamente en PDF."""
        df_dummy = pd.DataFrame({"Franja": ["Mañana"], "Vuelos": [10]})
        gen_pdf = GeneradorReportePDF(
            simulaciones=[],
            graficos=[],
            tablas_condicionales=[{"tipo": "Por Franja", "dataframe": df_dummy}],
            nombre_dataset="Vuelos_2026",
            usuario="Admin"
        )
        pdf_bytes = gen_pdf.generar_archivo()
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_renderizado_pdf_completo(self):
        """Verifica que con todas las secciones pobladas se compile el PDF correctamente."""
        sim = {
            "ruta": "EZE -> MIA",
            "franja": "Mañana",
            "ocupacion": "Alta",
            "precio_base": 300.0,
            "precio_sugerido": 360.0,
            "p_atrasado_pct": 10.0,
            "ajuste_total_monetario": 60.0,
            "ajuste_porcentual_total": 20.0,
            "p_cancelado_pct": 2.0,
            "recargo_riesgo_monetario": 25.0,
            "riesgo_logistico_pct": 5.0,
            "fondo_contingencia_vuelo": 2500.0,
            "muestra_tamano": 50,
            "asientos_ocupados_media": 150
        }
        df_chart = pd.DataFrame({"Estado": ["A tiempo", "Atrasado"], "Cantidad": [40, 10]})
        df_cond = pd.DataFrame({"Ruta": ["EZE -> MIA"], "Total": [50]})

        gen_pdf = GeneradorReportePDF(
            simulaciones=[sim],
            graficos=[{"titulo": "Estados", "tipo": "Gráfico de Torta", "tabla": df_chart}],
            tablas_condicionales=[{"tipo": "Por Ruta", "dataframe": df_cond}],
            nombre_dataset="Vuelos_2026",
            usuario="Admin"
        )
        pdf_bytes = gen_pdf.generar_archivo()
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generador_docx_herencia_y_contrato(self):
        """Verifica que GeneradorDOCX herede de GeneradorArchivo y cumpla el contrato."""
        self.assertTrue(issubclass(GeneradorDOCX, GeneradorArchivo))
        gen_docx = GeneradorDOCX(usuario="Tester")
        self.assertEqual(gen_docx.usuario, "Tester")
        self.assertTrue(hasattr(gen_docx, "generar_archivo"))

    def test_renderizado_docx_vacio(self):
        """Verifica que un reporte DOCX vacío se compile correctamente con el mensaje de advertencia."""
        gen_docx = GeneradorDOCX(
            simulaciones=[],
            graficos=[],
            tablas_condicionales=[],
            nombre_dataset="Dataset Vacio",
            usuario="Admin"
        )
        docx_bytes = gen_docx.generar_archivo()
        self.assertTrue(isinstance(docx_bytes, bytes))
        self.assertTrue(docx_bytes.startswith(b"PK\x03\x04"))

    def test_renderizado_docx_con_datos(self):
        """Verifica que el reporte DOCX se compile correctamente con simulaciones, gráficos y tablas."""
        sim = {
            "ruta": "EZE -> MIA",
            "franja": "Mañana",
            "precio_base": 300.0,
            "precio_sugerido": 360.0
        }
        df_chart = pd.DataFrame({"Estado": ["A tiempo"], "Cantidad": [10]})
        df_cond = pd.DataFrame({"Ruta": ["EZE -> MIA"], "Vuelos": [10]})

        gen_docx = GeneradorDOCX(
            simulaciones=[sim],
            graficos=[{"titulo": "Distribución Estados", "tabla": df_chart}],
            tablas_condicionales=[{"tipo": "Condicional Rutas", "dataframe": df_cond}],
            nombre_dataset="Vuelos_2026",
            usuario="Operaciones"
        )
        docx_bytes = gen_docx.generar_archivo()
        self.assertTrue(isinstance(docx_bytes, bytes))
        self.assertTrue(docx_bytes.startswith(b"PK\x03\x04"))


if __name__ == "__main__":
    unittest.main()
