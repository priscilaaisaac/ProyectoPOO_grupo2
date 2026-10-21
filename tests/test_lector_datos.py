"""
Suite exhaustiva de pruebas unitarias para el subsistema de Ingestión y Lectura de Datos
(modules.Lector).

Cumple estrictamente con:
- Aislamiento absoluto (100% en memoria mediante io.StringIO, io.BytesIO y sqlite:///:memory:).
- Exclusión total de UI y dependencias de Streamlit.
- Cobertura integral (>= 70%, buscando >= 95%):
  - LectorDatos (interfaz abstracta, alias .leer(), lectura de cabeceras).
  - consolidar_dataframes_multiples (clave compuesta [ID, '_ocurrencia'], outer join,
    descarte de '_ocurrencia', prevención de producto cartesiano, concatenación horizontal y vertical).
  - LectorTextoDelimitado (detección de delimitadores ',', ';', '\t', '|', ' ', latin-1, malformed).
  - LectorExcel (lectura con openpyxl en memoria BytesIO, cabeceras, múltiples hojas).
  - LectorSQL (lectura con sqlite:///:memory:, validación de nombre_tabla).
  - FactoryLectorDatos y LectorOrquestadorMultiArchivo (resolución polimórfica homogénea y mixta).
  - detectar_formato y detectar_separador.
"""

import io
import sqlite3
import pytest
import pandas as pd
from typing import List, Tuple

from modules.Lector.lector_base import LectorDatos, consolidar_dataframes_multiples
from modules.Lector.lector_texto_delimitado import (
    LectorTextoDelimitado,
    detectar_separador,
    DELIMITADORES_VALIDOS,
)
from modules.Lector.lector_excel import LectorExcel
from modules.Lector.lector_sql import LectorSQL
from modules.Lector.lector import (
    LectorCSV,
    LectorTXT,
    LectorOrquestadorMultiArchivo,
    FactoryLectorDatos,
    detectar_formato,
)


# =====================================================================
# Clases Auxiliares en Memoria
# =====================================================================

class NamedStringIO(io.StringIO):
    """io.StringIO enriquecido con atributo .name para simular archivos de texto subidos."""
    def __init__(self, initial_value: str = "", name: str = "archivo.csv"):
        super().__init__(initial_value)
        self.name = name


class NamedBytesIO(io.BytesIO):
    """io.BytesIO enriquecido con atributo .name para simular archivos binarios subidos."""
    def __init__(self, initial_bytes: bytes = b"", name: str = "archivo.xlsx"):
        super().__init__(initial_bytes)
        self.name = name


def crear_excel_en_memoria(df: pd.DataFrame, sheet_name: str = "Sheet1", name: str = "datos.xlsx") -> NamedBytesIO:
    """Genera un archivo Excel en memoria utilizando openpyxl."""
    buf = NamedBytesIO(name=name)
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buf.seek(0)
    return buf


class LectorConcretoStub(LectorDatos):
    """Subclase mínima para probar la interfaz LectorDatos y sus métodos concretos."""
    EXTENSIONES_SOPORTADAS = ('.stub',)

    def leer_archivos(self, origen, **kwargs) -> pd.DataFrame:
        return pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})


# =====================================================================
# 1. Pruebas para LectorDatos (Clase Base Abstracta)
# =====================================================================

class TestLectorDatosBase:
    """Pruebas de la clase abstracta pura LectorDatos y métodos auxiliares."""

    def test_no_permite_instanciar_directamente_clase_abstracta(self):
        with pytest.raises(TypeError):
            LectorDatos()

    def test_subclase_sin_metodo_abstracto_falla(self):
        class LectorIncompleto(LectorDatos):
            pass
        with pytest.raises(TypeError):
            LectorIncompleto()

    def test_alias_leer_llama_a_leer_archivos(self):
        lector = LectorConcretoStub()
        df = lector.leer("origen_dummy")
        assert list(df.columns) == ["col1", "col2"]
        assert len(df) == 2

    def test_obtener_cabeceras_con_leer_archivos(self):
        lector = LectorConcretoStub()
        cabeceras = lector.obtener_cabeceras("origen_dummy")
        assert cabeceras == ["col1", "col2"]

    def test_obtener_cabeceras_con_metodo_leer_privado(self):
        class LectorConMetodoLeer(LectorDatos):
            def _leer(self, archivo, **kwargs):
                return pd.DataFrame({"id_vuelo": [], "precio": []})
            def leer_archivos(self, origen, **kwargs):
                return self._leer(origen, **kwargs)

        lector = LectorConMetodoLeer()
        buf = NamedStringIO("cabecera dummy", name="dummy.csv")
        cabeceras = lector.obtener_cabeceras(buf)
        assert cabeceras == ["id_vuelo", "precio"]
        assert buf.tell() == 0  # Debe haber reseteado el puntero


# =====================================================================
# 2. Pruebas para consolidar_dataframes_multiples
# =====================================================================

class TestConsolidarDataFramesMultiples:
    """Pruebas de la lógica de consolidación relacional y alineación por IDs."""

    def test_lista_vacia_retorna_dataframe_vacio(self):
        df_res, mapping = consolidar_dataframes_multiples([])
        assert df_res.empty
        assert mapping == {}

    def test_un_solo_dataframe_retorna_copia_y_mapping(self):
        df = pd.DataFrame({"id": [1, 2], "precio": [100, 200]})
        df_res, mapping = consolidar_dataframes_multiples([(df, "archivo1.csv")])
        assert df_res.equals(df)
        assert df_res is not df
        assert mapping == {"id": "archivo1.csv", "precio": "archivo1.csv"}
        assert df_res.attrs["origen_por_columna"] == mapping

    def test_consolidacion_por_id_con_alineacion_y_sin_producto_cartesiano(self):
        """
        Prueba clave: dos archivos con IDs duplicados.
        La clave temporal '_ocurrencia' debe alinear el primer ID con el primer ID,
        y el segundo con el segundo, produciendo exactamente 2 filas (sin producto cartesiano 2x2=4).
        """
        df1 = pd.DataFrame({
            "id_vuelo": ["FL-100", "FL-100"],
            "origen": ["EZE", "COR"]
        })
        df2 = pd.DataFrame({
            "id_vuelo": ["FL-100", "FL-100"],
            "precio": [150.0, 180.0]
        })

        lista_dfs = [(df1, "vuelos.csv"), (df2, "precios.csv")]
        columnas_id = {"vuelos.csv": "id_vuelo", "precios.csv": "id_vuelo"}

        df_res, mapping = consolidar_dataframes_multiples(lista_dfs, columnas_id=columnas_id)

        # Debe generar exactamente 2 filas y haber eliminado '_ocurrencia'
        assert len(df_res) == 2
        assert "_ocurrencia" not in df_res.columns
        assert "id_vuelo" in df_res.columns
        assert "origen" in df_res.columns
        assert "precio" in df_res.columns
        # Las columnas repetidas deben recibir sufijo si colisionan
        assert "id_vuelo (2)" in df_res.columns

    def test_consolidacion_por_id_filas_desfasadas_y_nuevos_registros(self):
        """
        Si un ID está en distintas posiciones (ej. fila 0 vs fila 1),
        pd.merge outer debe alinearlos.
        IDs presentes solo en df1 o solo en df2 deben conservarse rellenando con NaN.
        """
        df1 = pd.DataFrame({
            "id": ["A", "B"],
            "val1": [10, 20]
        })
        df2 = pd.DataFrame({
            "id": ["B", "C"],
            "val2": [200, 300]
        })

        lista = [(df1, "f1.csv"), (df2, "f2.csv")]
        columnas_id = {"f1.csv": "id", "f2.csv": "id"}

        df_res, mapping = consolidar_dataframes_multiples(lista, columnas_id=columnas_id)

        # Registros resultantes: A, B, C (3 filas)
        assert len(df_res) == 3
        assert "_ocurrencia" not in df_res.columns

        # Registro B debe estar alineado
        fila_b = df_res[df_res["id"] == "B"].iloc[0]
        assert fila_b["val1"] == 20
        assert fila_b["val2"] == 200

        # Registro A sólo tenía val1
        fila_a = df_res[df_res["id"] == "A"].iloc[0]
        assert fila_a["val1"] == 10
        assert pd.isna(fila_a["val2"])

        # Registro C sólo tenía val2 (rellenado con combine_first en id)
        fila_c = df_res[df_res["id"] == "C"].iloc[0]
        assert pd.isna(fila_c["val1"])
        assert fila_c["val2"] == 300

    def test_consolidacion_por_id_resolucion_claves_por_indice_o_nombre(self):
        """Prueba fallback de búsqueda de columnas ID por índice numérico o string."""
        df1 = pd.DataFrame({"codigo": [1, 2], "x": [10, 20]})
        df2 = pd.DataFrame({"codigo": [1, 2], "y": [30, 40]})

        # Claves por índice 0 y 1
        df_res, _ = consolidar_dataframes_multiples(
            [(df1, "a.csv"), (df2, "b.csv")],
            columnas_id={0: "codigo", 1: "codigo"}
        )
        assert len(df_res) == 2
        assert "x" in df_res.columns
        assert "y" in df_res.columns

    def test_consolidacion_por_id_coercion_tipos_diferentes(self):
        """Si la columna ID en df1 es int y en df2 es str, debe convertirlas sin fallar."""
        df1 = pd.DataFrame({"id": [101, 102], "col_a": ["a", "b"]})
        df2 = pd.DataFrame({"id": ["101", "102"], "col_b": ["c", "d"]})

        df_res, _ = consolidar_dataframes_multiples(
            [(df1, "f1.csv"), (df2, "f2.csv")],
            columnas_id={"f1.csv": "id", "f2.csv": "id"}
        )
        assert len(df_res) == 2
        assert df_res["col_a"].iloc[0] == "a"
        assert df_res["col_b"].iloc[0] == "c"

    def test_consolidacion_horizontal_sin_ids_renombra_repetidas(self):
        """Modo tradicional horizontal (pd.concat axis=1) sin columnas_id."""
        df1 = pd.DataFrame({"id": [1, 2], "dato": ["a", "b"]})
        df2 = pd.DataFrame({"id": [1, 2], "dato": ["c", "d"]})

        df_res, mapping = consolidar_dataframes_multiples(
            [(df1, "f1.csv"), (df2, "f2.csv")],
            modo_unificacion="horizontal",
            columnas_id=None
        )
        assert len(df_res) == 2
        assert "id" in df_res.columns
        assert "id (2)" in df_res.columns
        assert "dato" in df_res.columns
        assert "dato (2)" in df_res.columns
        assert mapping["id (2)"] == "f2.csv"

    def test_consolidacion_vertical_sin_ids(self):
        """Modo tradicional vertical (axis=0) sin columnas_id."""
        df1 = pd.DataFrame({"id": [1, 2], "val": [10, 20]})
        df2 = pd.DataFrame({"id": [3, 4], "val": [30, 40]})

        df_res, mapping = consolidar_dataframes_multiples(
            [(df1, "f1.csv"), (df2, "f2.csv")],
            modo_unificacion="vertical",
            columnas_id=None
        )
        assert len(df_res) == 4
        assert list(df_res["id"]) == [1, 2, 3, 4]
        assert mapping["id"] == "f1.csv"

    def test_consolidacion_por_id_columna_inexistente_fallback_a_primera_columna(self):
        """Si la columna ID indicada en columnas_id no existe, recurre a la primera columna."""
        df1 = pd.DataFrame({"col_a": [1, 2], "val1": [10, 20]})
        df2 = pd.DataFrame({"col_b": [1, 2], "val2": [30, 40]})

        df_res, _ = consolidar_dataframes_multiples(
            [(df1, "f1.csv"), (df2, "f2.csv")],
            columnas_id={"f1.csv": "col_fantasma", "f2.csv": "otra_fantasma"}
        )
        assert len(df_res) == 2
        assert "val1" in df_res.columns
        assert "val2" in df_res.columns

    def test_consolidacion_por_id_con_ocurrencia_preexistente(self):
        """Verifica que si df_sig ya contiene '_ocurrencia', se ignore en renombrados."""
        df1 = pd.DataFrame({"id": [1], "v": [10]})
        df2 = pd.DataFrame({"id": [1], "_ocurrencia": [999], "w": [20]})

        df_res, _ = consolidar_dataframes_multiples(
            [(df1, "f1.csv"), (df2, "f2.csv")],
            columnas_id={"f1.csv": "id", "f2.csv": "id"}
        )
        assert len(df_res) == 1
        assert "_ocurrencia" not in df_res.columns
        assert "w" in df_res.columns

    def test_consolidacion_por_id_triple_colision_columna(self):
        """Tres archivos con la misma columna: debe generar 'dato', 'dato (2)' y 'dato (3)'."""
        df1 = pd.DataFrame({"id": [1], "dato": [10]})
        df2 = pd.DataFrame({"id": [1], "dato": [20]})
        df3 = pd.DataFrame({"id": [1], "dato": [30]})

        df_res, _ = consolidar_dataframes_multiples(
            [(df1, "f1.csv"), (df2, "f2.csv"), (df3, "f3.csv")],
            columnas_id={"f1.csv": "id", "f2.csv": "id", "f3.csv": "id"}
        )
        assert "dato" in df_res.columns
        assert "dato (2)" in df_res.columns
        assert "dato (3)" in df_res.columns

    def test_consolidacion_sin_ids_axis_argumentos(self):
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"b": [3, 4]})

        # axis=0 (vertical)
        df_v, _ = consolidar_dataframes_multiples([(df1, "1"), (df2, "2")], axis=0)
        assert len(df_v) == 4

        # axis=1 (horizontal)
        df_h, _ = consolidar_dataframes_multiples([(df1, "1"), (df2, "2")], axis=1)
        assert len(df_h.columns) == 2

    def test_consolidacion_horizontal_sin_ids_triple_colision(self):
        df1 = pd.DataFrame({"x": [1]})
        df2 = pd.DataFrame({"x": [2]})
        df3 = pd.DataFrame({"x": [3]})

        df_res, _ = consolidar_dataframes_multiples(
            [(df1, "1"), (df2, "2"), (df3, "3")],
            modo_unificacion="horizontal"
        )
        assert "x" in df_res.columns
        assert "x (2)" in df_res.columns
        assert "x (3)" in df_res.columns


# =====================================================================
# 3. Pruebas para LectorTextoDelimitado (CSV, TXT, Delimitadores)
# =====================================================================

class TestLectorTextoDelimitado:
    """Pruebas del lector de texto delimitado, sniffers y casos borde de formato."""

    def test_detectar_separadores_validos_en_stringio(self):
        lector = LectorTextoDelimitado()

        csv_coma = NamedStringIO("id,origen,destino\n1,EZE,MIA\n2,COR,BRC\n")
        assert lector.detectar_separador(csv_coma) == ","

        csv_puntoycoma = NamedStringIO("id;origen;destino\n1;EZE;MIA\n2;COR;BRC\n")
        assert lector.detectar_separador(csv_puntoycoma) == ";"

        csv_tab = NamedStringIO("id\torigen\tdestino\n1\tEZE\tMIA\n2\tCOR\tBRC\n")
        assert lector.detectar_separador(csv_tab) == "\t"

        csv_pipe = NamedStringIO("id|origen|destino\n1|EZE|MIA\n2|COR|BRC\n")
        assert lector.detectar_separador(csv_pipe) == "|"

        csv_espacio = NamedStringIO("id origen destino\n1 EZE MIA\n2 COR BRC\n")
        assert lector.detectar_separador(csv_espacio) == " "

    def test_detectar_separador_en_bytesio(self):
        lector = LectorTextoDelimitado()
        bytes_stream = NamedBytesIO(b"id,precio\n1,100\n2,200\n")
        assert lector.detectar_separador(bytes_stream) == ","

    def test_detectar_separador_stream_vacio_retorna_default(self):
        lector = LectorTextoDelimitado()
        vacio = NamedStringIO("")
        assert lector.detectar_separador(vacio, default=";") == ";"

    def test_detectar_separador_fallback_manual_cuando_sniffer_falla(self):
        lector = LectorTextoDelimitado()
        # Texto con líneas cortas donde sniffer estándar podría vacilar
        texto = NamedStringIO("a|b\n1|2\n3|4\n")
        assert lector.detectar_separador(texto) == "|"

    def test_funcion_conveniencia_detectar_separador(self):
        buf = NamedStringIO("col1;col2\nval1;val2\n")
        assert detectar_separador(buf) == ";"

    def test_leer_archivo_individual_csv_simple(self):
        lector = LectorTextoDelimitado()
        buf = NamedStringIO("id_vuelo,precio\nFL-1,100.5\nFL-2,200.0\n", name="vuelos.csv")
        df = lector._leer(buf)
        assert len(df) == 2
        assert list(df.columns) == ["id_vuelo", "precio"]
        assert df["precio"].iloc[0] == 100.5

    def test_leer_archivo_con_separador_espacio(self):
        lector = LectorTextoDelimitado()
        buf = NamedStringIO("id precio origen\n1 100 EZE\n2 200 COR\n", name="vuelos.txt")
        df = lector._leer(buf)
        assert len(df) == 2
        assert list(df.columns) == ["id", "precio", "origen"]

    def test_leer_archivo_latin1_encoding_fallback(self):
        lector = LectorTextoDelimitado()
        contenido = "id,descripción\n1,operación válida\n2,canción\n".encode("latin-1")
        buf = NamedBytesIO(contenido, name="latin1.csv")
        df = lector._leer(buf)
        assert len(df) == 2
        assert "descripción" in df.columns

    def test_obtener_cabeceras_preserva_seek(self):
        lector = LectorTextoDelimitado()
        buf = NamedStringIO("colA,colB,colC\n1,2,3\n", name="test.csv")
        cabeceras = lector.obtener_cabeceras(buf)
        assert cabeceras == ["colA", "colB", "colC"]
        assert buf.tell() == 0

    def test_leer_archivos_multiples_con_columnas_id(self):
        lector = LectorTextoDelimitado()
        f1 = NamedStringIO("id,origen\n1,EZE\n2,COR\n", name="f1.csv")
        f2 = NamedStringIO("id,destino\n1,MIA\n2,BRC\n", name="f2.csv")

        df_res = lector.leer_archivos([f1, f2], columnas_id={"f1.csv": "id", "f2.csv": "id"})
        assert len(df_res) == 2
        assert "origen" in df_res.columns
        assert "destino" in df_res.columns
        assert "id" in df_res.columns

    def test_alias_lector_csv_y_txt(self):
        assert LectorCSV is LectorTextoDelimitado
        assert LectorTXT is LectorTextoDelimitado

    def test_detectar_separador_con_ruta_string_mock_open(self):
        lector = LectorTextoDelimitado()
        import unittest.mock as mock
        with mock.patch("builtins.open", mock.mock_open(read_data="col1,col2\n1,2\n")):
            sep = lector.detectar_separador("archivo_virtual.csv")
            assert sep == ","

    def test_detectar_separador_con_ruta_string_latin1_fallback(self):
        lector = LectorTextoDelimitado()
        import unittest.mock as mock

        def mock_open_func(file, mode="r", encoding="utf-8", **kwargs):
            if encoding == "utf-8":
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
            return io.StringIO("col1;col2\n1;2\n")

        with mock.patch("builtins.open", side_effect=mock_open_func):
            sep = lector.detectar_separador("archivo_latin1.csv")
            assert sep == ";"

    def test_detectar_separador_con_ruta_string_error_total(self):
        lector = LectorTextoDelimitado()
        import unittest.mock as mock
        with mock.patch("builtins.open", side_effect=OSError("Disk read failed")):
            sep = lector.detectar_separador("archivo_inexistente.csv", default="|")
            assert sep == "|"

    def test_detectar_separador_sniffer_falla_con_fallback_manual(self):
        lector = LectorTextoDelimitado()
        import unittest.mock as mock
        with mock.patch("csv.Sniffer.sniff", side_effect=Exception("Sniffer failed")):
            # Caso 1: punto y coma regular
            buf_pc = NamedStringIO("a;b\n1;2\n3;4\n")
            assert lector.detectar_separador(buf_pc) == ";"

            # Caso 2: espacio regular
            buf_sp = NamedStringIO("a b c\n1 2 3\n4 5 6\n")
            assert lector.detectar_separador(buf_sp) == " "

            # Caso 3: texto irregular sin separadores estándar
            buf_irr = NamedStringIO("palabra_sin_separador\notra_palabra\n")
            assert lector.detectar_separador(buf_irr, default=",") == ","

    def test_leer_fallback_python_engine_bad_lines(self):
        lector = LectorTextoDelimitado()
        # CSV con línea malformada que provoca ParserError en el motor C
        contenido = "a,b\n1,2,3,4,extra\n5,6\n"
        buf = NamedStringIO(contenido, name="malformado.csv")
        df = lector._leer(buf)
        assert len(df) >= 1
        assert list(df.columns) == ["a", "b"]


# =====================================================================
# 4. Pruebas para LectorExcel
# =====================================================================

class TestLectorExcel:
    """Pruebas del lector de hojas de cálculo Excel usando openpyxl en memoria."""

    def test_leer_archivo_excel_simple(self):
        df_original = pd.DataFrame({"id": [1, 2], "aerolinea": ["Aerolineas", "Iberia"]})
        excel_buf = crear_excel_en_memoria(df_original, name="vuelos.xlsx")

        lector = LectorExcel()
        df_leido = lector._leer(excel_buf)
        assert len(df_leido) == 2
        assert list(df_leido.columns) == ["id", "aerolinea"]
        assert df_leido["aerolinea"].iloc[1] == "Iberia"
        assert excel_buf.tell() == 0

    def test_obtener_cabeceras_excel(self):
        df_original = pd.DataFrame({"id_vuelo": [], "precio": [], "capacidad": []})
        excel_buf = crear_excel_en_memoria(df_original, name="cab.xlsx")

        lector = LectorExcel()
        cabeceras = lector.obtener_cabeceras(excel_buf)
        assert cabeceras == ["id_vuelo", "precio", "capacidad"]
        assert excel_buf.tell() == 0

    def test_leer_archivos_excel_multiples_con_columnas_id(self):
        df1 = pd.DataFrame({"id": ["A1", "A2"], "tramo1": [10, 20]})
        df2 = pd.DataFrame({"id": ["A1", "A2"], "tramo2": [30, 40]})

        b1 = crear_excel_en_memoria(df1, name="e1.xlsx")
        b2 = crear_excel_en_memoria(df2, name="e2.xlsx")

        lector = LectorExcel()
        df_res = lector.leer_archivos([b1, b2], columnas_id={"e1.xlsx": "id", "e2.xlsx": "id"})
        assert len(df_res) == 2
        assert "tramo1" in df_res.columns
        assert "tramo2" in df_res.columns


# =====================================================================
# 5. Pruebas para LectorSQL
# =====================================================================

class TestLectorSQL:
    """Pruebas del lector de bases de datos relacionales SQL con SQLite en memoria."""

    def test_falta_nombre_tabla_lanza_value_error(self):
        lector = LectorSQL()
        with pytest.raises(ValueError, match="Se requiere el nombre de la tabla"):
            lector.leer_archivos("sqlite:///:memory:", nombre_tabla=None)

    def test_lectura_tabla_sqlite_en_memoria(self):
        # Creamos una base de datos SQLite en memoria con datos
        uri = "sqlite://"  # SQLite in-memory engine por defecto en SQLAlchemy
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE vuelos_test (id INTEGER, precio REAL);")
        cursor.execute("INSERT INTO vuelos_test VALUES (1, 150.0);")
        cursor.execute("INSERT INTO vuelos_test VALUES (2, 250.0);")
        conn.commit()

        # Usamos una base sqlite URI temporal válida para sqlalchemy
        # Mockeamos pd.read_sql para aislar completamente
        lector = LectorSQL()
        df_esperado = pd.DataFrame({"id": [1, 2], "precio": [150.0, 250.0]})

        import unittest.mock as mock
        with mock.patch("modules.Lector.lector_sql.create_engine") as mock_engine:
            with mock.patch("pandas.read_sql", return_value=df_esperado) as mock_read:
                df_res = lector.leer_archivos("sqlite:///:memory:", nombre_tabla="vuelos_test")
                assert len(df_res) == 2
                assert list(df_res["id"]) == [1, 2]
                mock_read.assert_called_once()


# =====================================================================
# 6. Pruebas para FactoryLectorDatos y Detección de Formato
# =====================================================================

class TestFactoryYOrquestador:
    """Pruebas de la fábrica de lectores, orquestador multiformato y detección."""

    def test_factory_obtener_lector_por_tipo(self):
        assert isinstance(FactoryLectorDatos.obtener_lector("CSV"), LectorTextoDelimitado)
        assert isinstance(FactoryLectorDatos.obtener_lector("TXT"), LectorTextoDelimitado)
        assert isinstance(FactoryLectorDatos.obtener_lector("TEXTO_DELIMITADO"), LectorTextoDelimitado)
        assert isinstance(FactoryLectorDatos.obtener_lector("EXCEL"), LectorExcel)
        assert isinstance(FactoryLectorDatos.obtener_lector("SQL"), LectorSQL)

        with pytest.raises(ValueError, match="Tipo de origen desconocido"):
            FactoryLectorDatos.obtener_lector("FORMATO_DESCONOCIDO")

    def test_factory_obtener_lector_por_archivo_individual(self):
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo("datos.csv"), LectorTextoDelimitado)
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo("datos.txt"), LectorTextoDelimitado)
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo("datos.xlsx"), LectorExcel)
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo("datos.xls"), LectorExcel)

        # Con objeto provisto de .name
        obj_csv = NamedStringIO(name="mi_archivo.csv")
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo(obj_csv), LectorTextoDelimitado)

        with pytest.raises(ValueError, match="Extensión de archivo no soportada"):
            FactoryLectorDatos.obtener_lector_por_archivo("archivo.pdf")

    def test_factory_obtener_lector_lista_homogenea_y_vacia(self):
        # Lista vacía retorna default LectorTextoDelimitado
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo([]), LectorTextoDelimitado)

        # Lista homogénea CSV
        lista_csv = ["v1.csv", "v2.csv"]
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo(lista_csv), LectorTextoDelimitado)

        # Lista homogénea Excel
        lista_xlsx = ["v1.xlsx", "v2.xlsx"]
        assert isinstance(FactoryLectorDatos.obtener_lector_por_archivo(lista_xlsx), LectorExcel)

    def test_factory_obtener_lector_lista_mixta_retorna_orquestador(self):
        # Lista mixta (.csv y .xlsx)
        lista_mixta = ["vuelos.csv", "precios.xlsx"]
        lector = FactoryLectorDatos.obtener_lector_por_archivo(lista_mixta)
        assert isinstance(lector, LectorOrquestadorMultiArchivo)

    def test_factory_obtener_cabeceras_archivo(self):
        buf = NamedStringIO("id,precio,estado\n1,100,A tiempo\n", name="test.csv")
        cabeceras = FactoryLectorDatos.obtener_cabeceras_archivo(buf)
        assert cabeceras == ["id", "precio", "estado"]

    def test_orquestador_multi_archivo_lectura_mixta(self):
        """Lectura e integración combinada de un archivo CSV y un archivo Excel en memoria."""
        csv_buf = NamedStringIO("id,aeropuerto\n1,EZE\n2,COR\n", name="aeropuertos.csv")
        df_excel = pd.DataFrame({"id": [1, 2], "precio": [500.0, 300.0]})
        xlsx_buf = crear_excel_en_memoria(df_excel, name="tarifas.xlsx")

        orquestador = LectorOrquestadorMultiArchivo()
        df_res = orquestador.leer_archivos(
            [csv_buf, xlsx_buf],
            columnas_id={"aeropuertos.csv": "id", "tarifas.xlsx": "id"}
        )

        assert len(df_res) == 2
        assert "aeropuerto" in df_res.columns
        assert "precio" in df_res.columns
        assert "id" in df_res.columns

    def test_orquestador_obtener_cabeceras(self):
        orquestador = LectorOrquestadorMultiArchivo()
        csv_buf = NamedStringIO("colX,colY\n1,2\n", name="test.csv")
        cabeceras = orquestador.obtener_cabeceras(csv_buf)
        assert cabeceras == ["colX", "colY"]

    def test_detectar_formato_completo(self):
        # Con encabezado y delimitador coma
        buf_con_cab = NamedStringIO("nombre,edad,ciudad\nJuan,30,BsAs\nPedro,25,Cordoba\n")
        sep, has_header = detectar_formato(buf_con_cab)
        assert sep == ","
        assert isinstance(has_header, bool)

        # Buffer vacío
        buf_vacio = NamedStringIO("")
        sep_vacio, has_hdr_vacio = detectar_formato(buf_vacio)
        assert sep_vacio == ","
        assert has_hdr_vacio is True

    def test_detectar_formato_con_bytesio(self):
        buf = NamedBytesIO(b"id;nombre\n1;Ana\n")
        sep, has_header = detectar_formato(buf)
        assert sep == ";"
        assert has_header is True

    def test_detectar_formato_con_ruta_string_mock_open(self):
        import unittest.mock as mock
        with mock.patch("builtins.open", mock.mock_open(read_data="id,nombre\n1,Juan\n")):
            sep, has_header = detectar_formato("archivo_virtual.csv")
            assert sep == ","
            assert has_header is True

    def test_detectar_formato_sniffer_has_header_falla(self):
        import unittest.mock as mock
        buf = NamedStringIO("id,nombre\n1,Juan\n")
        with mock.patch("csv.Sniffer.has_header", side_effect=Exception("Sniff header error")):
            sep, has_header = detectar_formato(buf)
            assert sep == ","
            assert has_header is True

    def test_factory_obtener_lector_por_archivo_lista_extension_desconocida_default_csv(self):
        # Lista con extensión no estándar (ej. .dat) debe asociarse a CSV por defecto
        lista_desconocida = ["datos.dat"]
        lector = FactoryLectorDatos.obtener_lector_por_archivo(lista_desconocida)
        assert isinstance(lector, LectorTextoDelimitado)

