"""
Suite exhaustiva de pruebas unitarias para el subsistema de Generación de Archivos y Reportes
(modules.Generador_Archivo).

Cumple estrictamente con:
- Aislamiento absoluto (100% en memoria mediante io.BytesIO, sin escribir archivos en disco).
- Exclusión total de UI y dependencias de Streamlit.
- Cobertura integral (>= 70%, buscando >= 95%):
  - GeneradorArchivo (interfaz abstracta bajo OCP, inicialización por defecto y metadatos).
  - GeneradorDOCX (renderizado de secciones, tablas de gráficos, tablas condicionales,
    caso borde sin datos y manejo de ModuleNotFoundError).
  - NumberedCanvas (mecanismo de dos pasadas para numeración de páginas 'X de Y').
  - GeneradorReportePDF (renderizado completo de las 3 secciones, gráficos vectoriales nativos
    de torta y barras, manejo de tablas contingentes, casos borde n=0/vacíos y captura de excepciones).
"""

import io
import pandas as pd
import pytest
from unittest import mock
from typing import Dict, Any, List

from modules.Generador_Archivo.generador_archivo_base import GeneradorArchivo
from modules.Generador_Archivo.generador_docx import GeneradorDOCX
from modules.Generador_Archivo.generador_pdf import (
    GeneradorReportePDF,
    NumberedCanvas,
    PALETA_COLORES,
)


# =====================================================================
# Clases y Fixtures Auxiliares en Memoria
# =====================================================================

class GeneradorArchivoConcretoStub(GeneradorArchivo):
    """Subclase mínima concreta para verificar el contrato de GeneradorArchivo."""
    def generar_archivo(self) -> bytes:
        return b"contenido_dummy"


@pytest.fixture
def datos_simulacion_dummy() -> List[Dict[str, Any]]:
    return [{
        "ruta": "EZE -> MIA",
        "franja": "Mañana (06:00 - 12:00)",
        "ocupacion": "Media (50% - 80%)",
        "precio_base": 300.0,
        "precio_sugerido": 345.50,
        "p_atrasado_pct": 15.0,
        "p_cancelado_pct": 5.0,
        "ajuste_total_monetario": 45.50,
        "ajuste_porcentual_total": 15.17,
        "recargo_riesgo_monetario": 20.0,
        "riesgo_logistico_pct": 6.75,
        "fondo_contingencia_vuelo": 3000.0,
        "muestra_tamano": 50,
        "asientos_ocupados_media": 150,
    }]


@pytest.fixture
def datos_graficos_dummy() -> List[Dict[str, Any]]:
    # 1. Gráfico de Torta con cantidades válidas
    df_torta = pd.DataFrame({
        "Estado": ["A tiempo", "Atrasado", "Cancelado"],
        "Cantidad": [70, 20, 10]
    })

    # 2. Gráfico de Barras con tabla de contingencia y fila de Total
    df_barras = pd.DataFrame({
        "Franja": ["Mañana", "Tarde", "Noche", "Total"],
        "A tiempo": [40, 30, 20, 90],
        "Atrasado": [10, 5, 5, 20],
        "Total": [50, 35, 25, 110]
    })

    return [
        {
            "titulo": "Distribución General de Estados",
            "tipo": "Gráfico de Torta",
            "descripcion": "Proporción observada en la flota",
            "tabla": df_torta,
        },
        {
            "titulo": "Estados por Franja Horaria",
            "tipo": "Gráfico de Barras",
            "descripcion": "Contingencia de puntualidad horaria",
            "tabla": df_barras,
        }
    ]


@pytest.fixture
def datos_tablas_condicionales_dummy() -> List[Dict[str, Any]]:
    df_cond = pd.DataFrame({
        "Ruta": ["EZE -> MIA", "COR -> BRC"],
        "Total Vuelos": [100, 50],
        "% Atrasado": [12.5, 8.0],
        "% A tiempo": [80.0, 90.0],
        "Precio Promedio ($)": [350.25, 180.50]
    })
    return [{
        "tipo": "Probabilidad Condicional por Ruta",
        "dataframe": df_cond
    }]


# =====================================================================
# 1. Pruebas para GeneradorArchivo (Clase Base Abstracta)
# =====================================================================

class TestGeneradorArchivoBase:
    """Pruebas del contrato base, inicialización y metadatos del reporte."""

    def test_no_permite_instanciar_directamente_clase_abstracta(self):
        with pytest.raises(TypeError):
            GeneradorArchivo()

    def test_subclase_sin_implementar_metodo_abstracto_falla(self):
        class GeneradorIncompleto(GeneradorArchivo):
            pass
        with pytest.raises(TypeError):
            GeneradorIncompleto()

    def test_inicializacion_con_valores_por_defecto(self):
        generador = GeneradorArchivoConcretoStub()
        assert generador.simulaciones == []
        assert generador.graficos == []
        assert generador.tablas_condicionales == []
        assert generador.nombre_dataset == "Dataset Activo"
        assert generador.usuario == "Analista de Operaciones"
        assert isinstance(generador.fecha_emision, str)
        assert generador.TITULO_OFICIAL == "Análisis Histórico de Vuelos para la Toma de Decisiones"
        assert generador.generar_archivo() == b"contenido_dummy"

    def test_inicializacion_con_parametro_retrocompatible_metricas(self):
        metricas_dummy = [{"tipo": "Metrica 1"}]
        generador = GeneradorArchivoConcretoStub(metricas=metricas_dummy)
        assert generador.tablas_condicionales == metricas_dummy


# =====================================================================
# 2. Pruebas para GeneradorDOCX (Exportador Word en Memoria)
# =====================================================================

class TestGeneradorDOCX:
    """Pruebas para generación de documentos Word (.docx) 100% en memoria."""

    def test_generar_docx_completo_con_todas_las_secciones(
        self,
        datos_simulacion_dummy,
        datos_graficos_dummy,
        datos_tablas_condicionales_dummy
    ):
        generador = GeneradorDOCX(
            simulaciones=datos_simulacion_dummy,
            graficos=datos_graficos_dummy,
            tablas_condicionales=datos_tablas_condicionales_dummy,
            nombre_dataset="Vuelos_2026.csv",
            usuario="Auditor Principal"
        )
        contenido_bytes = generador.generar_archivo()

        assert isinstance(contenido_bytes, bytes)
        assert len(contenido_bytes) > 0
        # Verificación de firma mágica de archivo ZIP / DOCX (PK\x03\x04)
        assert contenido_bytes.startswith(b"PK\x03\x04")

    def test_generar_docx_sin_datos_seccion_vacia(self):
        """Caso borde: generador inicializado sin elementos guardados."""
        generador = GeneradorDOCX(
            simulaciones=[],
            graficos=[],
            tablas_condicionales=[]
        )
        contenido_bytes = generador.generar_archivo()

        assert isinstance(contenido_bytes, bytes)
        assert contenido_bytes.startswith(b"PK\x03\x04")

    def test_generar_docx_con_dataframes_vacios_o_nulos_en_graficos_y_tablas(self):
        """Tolerancia a gráficos y tablas con DataFrame vacío o None."""
        graficos_vacios = [
            {"titulo": "G1", "tabla": pd.DataFrame()},
            {"titulo": "G2", "tabla": None}
        ]
        tablas_vacias = [
            {"tipo": "T1", "dataframe": pd.DataFrame()},
            {"tipo": "T2", "dataframe": None}
        ]
        generador = GeneradorDOCX(
            graficos=graficos_vacios,
            tablas_condicionales=tablas_vacias
        )
        contenido_bytes = generador.generar_archivo()
        assert isinstance(contenido_bytes, bytes)
        assert contenido_bytes.startswith(b"PK\x03\x04")

    def test_generar_docx_con_buffer_grafico_en_memoria(self):
        """Verifica que GeneradorDOCX procese correctamente buffers de gráficos en memoria (seek(0) y add_picture)."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(50)  # Dejar el cursor desfasado deliberadamente para verificar buffer.seek(0)

        graficos = [
            {"titulo": "Gráfico Buffer", "buffer": buf, "descripcion": "Detalle buffer"}
        ]
        generador = GeneradorDOCX(graficos=graficos)
        contenido = generador.generar_archivo()
        assert isinstance(contenido, bytes)
        assert contenido.startswith(b"PK\x03\x04")

    def test_generar_docx_sin_modulo_docx_lanza_error(self):
        generador = GeneradorDOCX()
        with mock.patch("modules.Generador_Archivo.generador_docx.docx", None):
            with pytest.raises(ModuleNotFoundError, match="La librería 'python-docx' no está instalada"):
                generador.generar_archivo()


# =====================================================================
# 3. Pruebas para GeneradorReportePDF y NumberedCanvas
# =====================================================================

class TestGeneradorReportePDF:
    """Pruebas para generación de informes PDF ejecutivos y gráficos vectoriales."""

    def test_generar_pdf_completo_con_todas_las_secciones(
        self,
        datos_simulacion_dummy,
        datos_graficos_dummy,
        datos_tablas_condicionales_dummy
    ):
        generador = GeneradorReportePDF(
            simulaciones=datos_simulacion_dummy,
            graficos=datos_graficos_dummy,
            tablas_condicionales=datos_tablas_condicionales_dummy,
            nombre_dataset="Dataset_Vuelos_Test.xlsx",
            usuario="Analista Senior"
        )
        contenido_pdf = generador.generar_archivo()

        assert isinstance(contenido_pdf, bytes)
        assert len(contenido_pdf) > 0
        # Verificación de firma mágica de archivo PDF (%PDF)
        assert contenido_pdf.startswith(b"%PDF")

    def test_generar_pdf_sin_datos_secciones_vacias(self):
        """Caso borde: informe PDF sin simulaciones, sin gráficos y sin tablas."""
        generador = GeneradorReportePDF(
            simulaciones=[],
            graficos=[],
            tablas_condicionales=[]
        )
        contenido_pdf = generador.generar_archivo()

        assert isinstance(contenido_pdf, bytes)
        assert contenido_pdf.startswith(b"%PDF")

    def test_generador_grafico_torta_vector_casos_borde(self):
        generador = GeneradorReportePDF()

        # 1. Caso None o vacío
        assert generador._generar_grafico_torta_vector(None) is None
        assert generador._generar_grafico_torta_vector(pd.DataFrame()) is None

        # 2. Sin columna 'Cantidad'
        df_sin_cant = pd.DataFrame({"Estado": ["A", "B"], "Valor": [10, 20]})
        assert generador._generar_grafico_torta_vector(df_sin_cant) is None

        # 3. Suma total de cantidades igual a 0
        df_cero = pd.DataFrame({"Estado": ["A", "B"], "Cantidad": [0, 0]})
        assert generador._generar_grafico_torta_vector(df_cero) is None

        # 4. Caso válido exitoso
        df_valido = pd.DataFrame({"Estado": ["A", "B"], "Cantidad": [15, 25]})
        drawing = generador._generar_grafico_torta_vector(df_valido)
        assert drawing is not None

    def test_generador_grafico_barras_vector_casos_borde(self):
        generador = GeneradorReportePDF()

        # 1. Caso None o vacío
        assert generador._generar_grafico_barras_vector(None) is None
        assert generador._generar_grafico_barras_vector(pd.DataFrame()) is None

        # 2. Sin columnas de series (solo 1 columna o solo Total)
        df_solo_cat = pd.DataFrame({"Franja": ["Mañana", "Tarde"]})
        assert generador._generar_grafico_barras_vector(df_solo_cat) is None

        # 3. Solo columna Total (se descarta y queda sin series)
        df_solo_total = pd.DataFrame({"Franja": ["Mañana", "Total"], "Total": [10, 10]})
        assert generador._generar_grafico_barras_vector(df_solo_total) is None

        # 4. Caso válido con múltiples series y fila Total a filtrar
        df_valido = pd.DataFrame({
            "Categoria": ["Cat1", "Cat2", "Total"],
            "SerieA": [10, 20, 30],
            "SerieB": [5, 15, 20],
            "Total": [15, 35, 50]
        })
        drawing = generador._generar_grafico_barras_vector(df_valido)
        assert drawing is not None

    def test_graficos_y_tablas_con_dataframes_vacios_en_pdf(self):
        """Verifica que el generador PDF maneje limpiamente DataFrames vacíos dentro de la lista de gráficos."""
        graficos = [
            {"titulo": "G_Vacio", "tipo": "Gráfico de Barras", "tabla": pd.DataFrame()},
            {"titulo": "G_None", "tipo": "Gráfico de Torta", "tabla": None}
        ]
        tablas = [
            {"tipo": "T_Vacia", "dataframe": pd.DataFrame()},
            {"tipo": "T_None", "dataframe": None}
        ]
        generador = GeneradorReportePDF(graficos=graficos, tablas_condicionales=tablas)
        pdf_bytes = generador.generar_archivo()
        assert pdf_bytes.startswith(b"%PDF")

    def test_captura_excepcion_en_graficos_vectoriales(self):
        generador = GeneradorReportePDF()
        # Pasamos un DataFrame con datos no convertibles a float en Cantidad para forzar excepción
        df_erroneo = pd.DataFrame({"Estado": ["A"], "Cantidad": ["no_numerico"]})
        assert generador._generar_grafico_torta_vector(df_erroneo) is None

        df_barras_err = pd.DataFrame({"Cat": ["C1"], "Serie": ["no_numerico"]})
        assert generador._generar_grafico_barras_vector(df_barras_err) is None

    def test_numbered_canvas_dos_pasadas_en_memoria(self):
        """Prueba directa del canvas de ReportLab y la numeración dinámica."""
        buf = io.BytesIO()
        canv = NumberedCanvas(buf)
        canv.drawString(100, 100, "Texto de prueba")
        canv.showPage()
        canv.save()
        res = buf.getvalue()
        assert res.startswith(b"%PDF")
