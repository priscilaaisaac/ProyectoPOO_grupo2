import unittest
import io
import pandas as pd
import numpy as np
from modules.lector import (
    detectar_separador,
    LectorDatos,
    LectorTextoDelimitado,
    LectorCSV,
    LectorExcel,
    LectorOrquestadorMultiArchivo,
    FactoryLectorDatos
)
from modules.calidad import sanear_dataframe_individual


class MockUploadedFile(io.BytesIO):
    """Simula un objeto UploadedFile de Streamlit."""
    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.name = name


class TestLectorDatos(unittest.TestCase):

    def test_deteccion_separadores_validos(self):
        """Prueba detección de delimitadores estándar."""
        casos = [
            (b"col1,col2,col3\nval1,val2,val3\n", ","),
            (b"col1;col2;col3\nval1;val2;val3\n", ";"),
            (b"col1\tcol2\tcol3\nval1\tval2\tval3\n", "\t"),
            (b"col1|col2|col3\nval1|val2|val3\n", "|"),
        ]
        for contenido, esperado in casos:
            archivo = io.BytesIO(contenido)
            sep = detectar_separador(archivo)
            self.assertEqual(sep, esperado, f"Falló para separador {esperado}")
            self.assertEqual(archivo.tell(), 0, "El puntero debe regresar al inicio con seek(0)")

    def test_guion_no_es_separador(self):
        """
        Prueba crítica: 'FL-9768,JFK,ORY' tiene un guión, pero debe detectarse ','
        y no romper el código de vuelo.
        """
        contenido = (
            b"id_vuelo,aeropuerto_origen,aeropuerto_destino\n"
            b"FL-9768,JFK,ORY\n"
            b"FL-1234,EZE,MIA\n"
        )
        archivo = MockUploadedFile(contenido, "vuelos.csv")
        sep = detectar_separador(archivo)
        self.assertEqual(sep, ",")

        lector = LectorCSV()
        df = lector.leer_archivos(archivo)
        self.assertIn("id_vuelo", df.columns)
        self.assertIn("aeropuerto_origen", df.columns)
        self.assertIn("aeropuerto_destino", df.columns)
        self.assertEqual(df["id_vuelo"].iloc[0], "FL-9768")
        self.assertEqual(df["aeropuerto_origen"].iloc[0], "JFK")
        self.assertEqual(df["aeropuerto_destino"].iloc[0], "ORY")

    def test_limpieza_espacios_blanco(self):
        """
        Prueba que las cabeceras y los datos de texto se limpien con strip(),
        preservando valores None / NaN.
        """
        df_raw = pd.DataFrame({
            "  col1  ": ["  dato1 ", " dato2", None, np.nan],
            "col2 ": [10, 20, 30, 40],
            " col3": ["  texto con espacios internos  ", "normal", " ", "a"]
        })
        df_saneado = sanear_dataframe_individual(df_raw)

        self.assertEqual(list(df_saneado.columns), ["col1", "col2", "col3"])
        self.assertEqual(df_saneado["col1"].iloc[0], "dato1")
        self.assertEqual(df_saneado["col1"].iloc[1], "dato2")
        self.assertTrue(pd.isna(df_saneado["col1"].iloc[2]))
        self.assertTrue(pd.isna(df_saneado["col1"].iloc[3]))
        self.assertEqual(df_saneado["col3"].iloc[0], "texto con espacios internos")
        self.assertEqual(df_saneado["col3"].iloc[2], "")

    def test_unificacion_horizontal_multiples_archivos(self):
        """
        Prueba la unificación horizontal (axis=1) por defecto, manejo de colisión
        de nombres de columnas (col (2)) y preservación del origen de columnas.
        """
        arch1 = MockUploadedFile(
            b"id,origen,fecha\n1,JFK,2026-10-01\n2,EZE,2026-10-02\n",
            "archivo_1.csv"
        )
        arch2 = MockUploadedFile(
            b"id,destino,precio\n101,MAD,500\n102,BCN,600\n",
            "archivo_2.csv"
        )

        lector = LectorCSV()
        df = lector.leer_archivos([arch1, arch2])

        # Columnas esperadas: id, origen, fecha, id (2), destino, precio
        esperadas = ["id", "origen", "fecha", "id (2)", "destino", "precio"]
        self.assertEqual(list(df.columns), esperadas)

        # Verificar orígenes
        origen_map = lector.origen_por_columna
        self.assertEqual(origen_map["id"], "archivo_1.csv")
        self.assertEqual(origen_map["origen"], "archivo_1.csv")
        self.assertEqual(origen_map["fecha"], "archivo_1.csv")
        self.assertEqual(origen_map["id (2)"], "archivo_2.csv")
        self.assertEqual(origen_map["destino"], "archivo_2.csv")
        self.assertEqual(origen_map["precio"], "archivo_2.csv")

        # Verificar metadata en df.attrs
        self.assertEqual(df.attrs["origen_por_columna"], origen_map)

    def test_unificacion_vertical(self):
        """
        Prueba la unificación vertical (axis=0) cuando se especifica.
        """
        arch1 = MockUploadedFile(
            b"id,origen\n1,JFK\n2,EZE\n",
            "archivo_1.csv"
        )
        arch2 = MockUploadedFile(
            b"id,destino\n3,MAD\n4,BCN\n",
            "archivo_2.csv"
        )

        lector = LectorCSV()
        df = lector.leer_archivos([arch1, arch2], modo_unificacion="vertical")

        self.assertEqual(len(df), 4)
        self.assertIn("id", df.columns)
        self.assertIn("origen", df.columns)
        self.assertIn("destino", df.columns)
        self.assertTrue(pd.isna(df["destino"].iloc[0]))
        self.assertTrue(pd.isna(df["origen"].iloc[2]))

    def test_delimitador_espacio_simple(self):
        """Prueba detección y lectura de archivos delimitados por espacio simple."""
        contenido = (
            b"id_vuelo aeropuerto_origen aeropuerto_destino\n"
            b"FL-9768 JFK ORY\n"
            b"FL-1234 EZE MIA\n"
        )
        archivo = MockUploadedFile(contenido, "vuelos_espacios.txt")
        sep = detectar_separador(archivo)
        self.assertEqual(sep, " ")

        lector = LectorCSV()
        df = lector.leer_archivos(archivo)
        self.assertEqual(list(df.columns), ["id_vuelo", "aeropuerto_origen", "aeropuerto_destino"])
        self.assertEqual(len(df), 2)
        self.assertEqual(df["id_vuelo"].iloc[0], "FL-9768")
        self.assertEqual(df["aeropuerto_origen"].iloc[0], "JFK")
        self.assertEqual(df["aeropuerto_destino"].iloc[0], "ORY")

    def test_delimitador_espacios_multiples_sin_columnas_vacias(self):
        r"""
        Prueba lectura con espacios múltiples entre columnas (sep=r'\s+').
        Asegura que no se generen columnas vacías espurias y se preserven los IDs con guion.
        """
        contenido = (
            b"id_vuelo   aeropuerto_origen    aeropuerto_destino\n"
            b"FL-9768    JFK                  ORY\n"
            b"FL-5544    MIA                  EZE\n"
        )
        archivo = MockUploadedFile(contenido, "vuelos_multi_espacio.txt")
        sep = detectar_separador(archivo)
        self.assertEqual(sep, " ")

        lector = LectorCSV()
        df = lector.leer_archivos(archivo)
        self.assertEqual(list(df.columns), ["id_vuelo", "aeropuerto_origen", "aeropuerto_destino"])
        self.assertEqual(len(df), 2)
        self.assertEqual(df["id_vuelo"].iloc[0], "FL-9768")
        self.assertEqual(df["aeropuerto_origen"].iloc[0], "JFK")
        self.assertEqual(df["aeropuerto_destino"].iloc[0], "ORY")
        self.assertEqual(df["id_vuelo"].iloc[1], "FL-5544")

    def test_unificacion_archivos_mixtos_csv_y_espacios(self):
        """
        Prueba que un archivo separado por comas y otro por espacios puedan
        cargarse juntos en una sola llamada y unificarse horizontalmente.
        """
        arch_coma = MockUploadedFile(
            b"id_vuelo,origen\nFL-9768,JFK\nFL-1234,EZE\n",
            "vuelos_coma.csv"
        )
        arch_espacio = MockUploadedFile(
            b"id_vuelo   destino\nFL-9768    ORY\nFL-1234    MIA\n",
            "vuelos_espacio.txt"
        )

        lector = LectorCSV()
        df = lector.leer_archivos([arch_coma, arch_espacio])

        self.assertEqual(list(df.columns), ["id_vuelo", "origen", "id_vuelo (2)", "destino"])
        self.assertEqual(lector.origen_por_columna["id_vuelo"], "vuelos_coma.csv")
        self.assertEqual(lector.origen_por_columna["origen"], "vuelos_coma.csv")
        self.assertEqual(lector.origen_por_columna["id_vuelo (2)"], "vuelos_espacio.txt")
        self.assertEqual(lector.origen_por_columna["destino"], "vuelos_espacio.txt")
        self.assertEqual(df["id_vuelo"].iloc[0], "FL-9768")
        self.assertEqual(df["id_vuelo (2)"].iloc[0], "FL-9768")
        self.assertEqual(df["destino"].iloc[0], "ORY")

    def test_archivos_combinados_csv_txt_y_excel(self):
        """
        Prueba la combinación de archivos CSV, TXT y Excel (.xlsx) juntos.
        Verifica que la ramificación temprana por extensión omita csv.Sniffer para Excel
        y que no ocurra el error de determinación de engine en Excel.
        """
        # 1. Crear archivo Excel en memoria
        excel_buf = io.BytesIO()
        df_excel = pd.DataFrame({"id_vuelo": ["FL-9768", "FL-1234"], "precio": [500, 650]})
        df_excel.to_excel(excel_buf, index=False, engine="openpyxl")
        excel_buf.seek(0)
        arch_excel = MockUploadedFile(excel_buf.getvalue(), "tarifas.xlsx")

        # 2. Archivo CSV tradicional
        arch_csv = MockUploadedFile(
            b"id_vuelo,aeropuerto_origen\nFL-9768,JFK\nFL-1234,EZE\n",
            "vuelos_origen.csv"
        )

        # 3. Archivo TXT delimitado por tabulaciones o espacios
        arch_txt = MockUploadedFile(
            b"id_vuelo\taeropuerto_destino\nFL-9768\tORY\nFL-1234\tMIA\n",
            "vuelos_destino.txt"
        )

        lector = FactoryLectorDatos.obtener_lector_por_archivo([arch_csv, arch_txt, arch_excel])
        df_consolidado = lector.leer_archivos([arch_csv, arch_txt, arch_excel])

        # Verificar columnas y desduplicación horizontal
        esperadas = ["id_vuelo", "aeropuerto_origen", "id_vuelo (2)", "aeropuerto_destino", "id_vuelo (3)", "precio"]
        self.assertEqual(list(df_consolidado.columns), esperadas)
        self.assertEqual(len(df_consolidado), 2)
        self.assertEqual(df_consolidado["aeropuerto_origen"].iloc[0], "JFK")
        self.assertEqual(df_consolidado["aeropuerto_destino"].iloc[0], "ORY")
        self.assertEqual(df_consolidado["precio"].iloc[0], 500)

        # Verificar orígenes registrados
        self.assertEqual(lector.origen_por_columna["aeropuerto_origen"], "vuelos_origen.csv")
        self.assertEqual(lector.origen_por_columna["aeropuerto_destino"], "vuelos_destino.txt")
        self.assertEqual(lector.origen_por_columna["precio"], "tarifas.xlsx")

    def test_lector_excel_individual(self):
        """Verifica que un archivo Excel individual se lea correctamente con openpyxl."""
        excel_buf = io.BytesIO()
        pd.DataFrame({"vuelo": ["FL-99"], "asientos": [180]}).to_excel(excel_buf, index=False, engine="openpyxl")
        excel_buf.seek(0)
        arch_excel = MockUploadedFile(excel_buf.getvalue(), "datos.xlsx")

        lector = FactoryLectorDatos.obtener_lector_por_archivo(arch_excel)
        df = lector.leer_archivos(arch_excel)
        self.assertEqual(list(df.columns), ["vuelo", "asientos"])
        self.assertEqual(df["vuelo"].iloc[0], "FL-99")
        self.assertEqual(df["asientos"].iloc[0], 180)

    def test_factory_lector(self):
        """Verifica que FactoryLectorDatos retorne la clase correcta."""
        self.assertIsInstance(FactoryLectorDatos.obtener_lector("csv"), LectorTextoDelimitado)
        self.assertIsInstance(FactoryLectorDatos.obtener_lector("txt"), LectorTextoDelimitado)
        self.assertIsInstance(FactoryLectorDatos.obtener_lector("texto_delimitado"), LectorTextoDelimitado)
        self.assertIsInstance(FactoryLectorDatos.obtener_lector("excel"), LectorExcel)

        f_csv = MockUploadedFile(b"a,b\n1,2\n", "datos.csv")
        f_txt = MockUploadedFile(b"a\tb\n1\t2\n", "datos.txt")
        self.assertIsInstance(FactoryLectorDatos.obtener_lector_por_archivo(f_csv), LectorTextoDelimitado)
        self.assertIsInstance(FactoryLectorDatos.obtener_lector_por_archivo(f_txt), LectorTextoDelimitado)
        f_excel = MockUploadedFile(b"", "datos.xlsx")
        self.assertIsInstance(FactoryLectorDatos.obtener_lector_por_archivo(f_excel), LectorExcel)
        self.assertIsInstance(FactoryLectorDatos.obtener_lector_por_archivo([f_csv, f_excel]), LectorOrquestadorMultiArchivo)
        self.assertIsInstance(FactoryLectorDatos.obtener_lector_por_archivo([f_csv, f_csv]), LectorTextoDelimitado)

    def test_jerarquia_polimorfica_y_responsabilidades(self):
        """Verifica el cumplimiento de la jerarquía POO limpia y ubicación de responsabilidades."""
        # 1. Jerarquía de lectores: LectorTextoDelimitado unifica CSV y TXT y hereda de LectorDatos
        self.assertTrue(issubclass(LectorTextoDelimitado, LectorDatos))
        self.assertTrue(issubclass(LectorExcel, LectorDatos))
        self.assertFalse(issubclass(LectorExcel, LectorTextoDelimitado), "LectorExcel NO debe heredar de LectorTextoDelimitado")

        # 2. Método detectar_separador en instancia de LectorTextoDelimitado
        lector_txt_del = LectorTextoDelimitado()
        self.assertTrue(hasattr(lector_txt_del, "detectar_separador"))
        buf = io.BytesIO(b"x;y;z\n1;2;3\n")
        self.assertEqual(lector_txt_del.detectar_separador(buf), ";")

        # 3. Soporte de extensiones unificadas (.csv y .txt)
        self.assertIn('.csv', lector_txt_del.EXTENSIONES_SOPORTADAS)
        self.assertIn('.txt', lector_txt_del.EXTENSIONES_SOPORTADAS)

        # 4. Validar existencia en modules/validador y modules/calidad
        from modules.validador import ValidadorEsquema
        from modules.calidad import EstandarizadorDatos

        df_prueba = pd.DataFrame({"  col_a  ": [" val "], " col_b": [10]})
        df_saneado = EstandarizadorDatos.sanear_dataframe_individual(df_prueba)
        self.assertEqual(list(df_saneado.columns), ["col_a", "col_b"])
        self.assertEqual(df_saneado["col_a"].iloc[0], "val")

        df_validado = ValidadorEsquema.validar_estructura_tabular(df_saneado)
        self.assertEqual(list(df_validado.columns), ["col_a", "col_b"])


if __name__ == "__main__":
    unittest.main()


