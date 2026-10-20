import io
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.pdfgen import canvas
from modules.Generador_Archivo.generador_archivo_base import GeneradorArchivo


PALETA_COLORES = [
    colors.HexColor('#1E88E5'), # Azul primario
    colors.HexColor('#43A047'), # Verde
    colors.HexColor('#FB8C00'), # Naranja
    colors.HexColor('#E53935'), # Rojo
    colors.HexColor('#8E24AA'), # Morado
    colors.HexColor('#00ACC1'), # Cyan
    colors.HexColor('#3949AB'), # Indigo
    colors.HexColor('#D81B60'), # Rosa fuerte
    colors.HexColor('#7CB342'), # Verde lima
    colors.HexColor('#757575')  # Gris para Otros
]


class NumberedCanvas(canvas.Canvas):
    """
    Canvas de ReportLab de dos pasadas para calcular y numerar páginas
    en formato 'Página X de Y', agregando pie de página estándar.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#757575"))
        texto_pie = f"Página {self._pageNumber} de {page_count}  |  Sistema de Gestión de Vuelos POO - Grupo 2"
        self.drawRightString(letter[0] - 36, 25, texto_pie)
        self.drawString(36, 25, "Documento Confidencial - Uso Interno Comercial")
        self.setStrokeColor(colors.HexColor("#E0E0E0"))
        self.setLineWidth(0.5)
        self.line(36, 36, letter[0] - 36, 36)
        self.restoreState()


class GeneradorReportePDF(GeneradorArchivo):
    """
    Generador de informes ejecutivos en formato PDF orientado a la toma de decisiones.
    Estructura estrictamente el reporte en 3 secciones independientes:
      1. Simulaciones Comerciales y Precios Dinámicos Guardados.
      2. Visualizaciones y Gráficos Guardados (con gráficos visuales vectoriales y tablas).
      3. Tablas de Probabilidades Condicionales Cruzadas Guardadas.
    """

    TITULO_OFICIAL = "Análisis Histórico de Vuelos para la Toma de Decisiones"

    def __init__(
        self,
        simulaciones: Optional[List[Dict[str, Any]]] = None,
        graficos: Optional[List[Dict[str, Any]]] = None,
        tablas_condicionales: Optional[List[Dict[str, Any]]] = None,
        nombre_dataset: str = "Dataset Activo",
        usuario: Optional[str] = None,
        metricas: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            simulaciones=simulaciones,
            graficos=graficos,
            tablas_condicionales=tablas_condicionales,
            nombre_dataset=nombre_dataset,
            usuario=usuario,
            metricas=metricas
        )

    def generar_archivo(self) -> bytes:
        """Compila y retorna el informe en formato PDF crudo (bytes)."""
        return self.construir_pdf()

    def _crear_estilos(self):
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(
            name="ReportHeaderTitle",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0D47A1"),
            alignment=0,
            spaceAfter=4
        ))

        styles.add(ParagraphStyle(
            name="ReportHeaderSubtitle",
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#424242"),
            alignment=0,
            spaceAfter=8
        ))

        styles.add(ParagraphStyle(
            name="SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1565C0"),
            spaceBefore=14,
            spaceAfter=6
        ))

        styles.add(ParagraphStyle(
            name="ItemHeading",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1A237E"),
            spaceBefore=8,
            spaceAfter=4
        ))

        styles.add(ParagraphStyle(
            name="TableCell",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#212121"),
            alignment=0
        ))

        styles.add(ParagraphStyle(
            name="TableCellCenter",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#212121"),
            alignment=1
        ))

        styles.add(ParagraphStyle(
            name="TableCellBold",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1
        ))

        styles.add(ParagraphStyle(
            name="EmptySectionText",
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#757575"),
            spaceBefore=4,
            spaceAfter=8
        ))

        return styles

    def _generar_grafico_torta_vector(self, df_torta: pd.DataFrame) -> Optional[Drawing]:
        """Crea un gráfico de torta vectorial nativo para ReportLab."""
        try:
            if df_torta is None or df_torta.empty or "Cantidad" not in df_torta.columns:
                return None

            cantidades = [float(c) for c in df_torta["Cantidad"].tolist()]
            total_cant = sum(cantidades)
            if total_cant == 0:
                return None

            porcentajes = [(c / total_cant) * 100.0 for c in cantidades]
            labels = [f"{p:.1f}%" for p in porcentajes]
            nombres = [str(x) for x in df_torta.iloc[:, 0].tolist()]

            d = Drawing(540, 180)
            pie = Pie()
            pie.x = 40
            pie.y = 15
            pie.width = 150
            pie.height = 150
            pie.data = cantidades
            pie.labels = labels
            pie.sideLabels = 0
            pie.slices.strokeWidth = 0.5

            for i in range(len(cantidades)):
                pie.slices[i].fillColor = PALETA_COLORES[i % len(PALETA_COLORES)]
            d.add(pie)

            leg = Legend()
            leg.x = 240
            leg.y = 155
            leg.dx = 9
            leg.dy = 9
            leg.fontName = 'Helvetica'
            leg.fontSize = 8
            leg.boxAnchor = 'nw'
            leg.columnMaximum = 5
            leg.colorNamePairs = [(PALETA_COLORES[i % len(PALETA_COLORES)], nombres[i][:22]) for i in range(len(nombres))]
            d.add(leg)

            return d
        except Exception:
            return None

    def _generar_grafico_barras_vector(self, df_contingencia: pd.DataFrame) -> Optional[Drawing]:
        """Crea un gráfico de barras vectorial agrupado nativo para ReportLab."""
        try:
            if df_contingencia is None or df_contingencia.empty:
                return None

            # Filtrar fila de Total si existe
            df_chart = df_contingencia[df_contingencia.iloc[:, 0] != "Total"].copy()
            # Columnas de series (excluir primera columna categórica y columna Total)
            cols_series = [c for c in df_chart.columns[1:] if c != "Total"]
            if not cols_series:
                return None

            x_labels = [str(v)[:15] for v in df_chart.iloc[:, 0].tolist()]

            data_series = []
            for c in cols_series:
                data_series.append([float(val) for val in df_chart[c].tolist()])

            if not data_series or not data_series[0]:
                return None

            max_val = max(max(s) for s in data_series) if data_series else 10

            d = Drawing(540, 190)
            bc = VerticalBarChart()
            bc.x = 45
            bc.y = 35
            bc.height = 120
            bc.width = 330
            bc.data = data_series
            bc.categoryAxis.categoryNames = x_labels
            bc.categoryAxis.labels.fontSize = 8
            bc.categoryAxis.labels.dy = -10
            bc.valueAxis.valueMin = 0
            bc.valueAxis.valueMax = max(10, int(max_val * 1.25))
            bc.valueAxis.labels.fontSize = 8

            for i in range(len(cols_series)):
                bc.bars[i].fillColor = PALETA_COLORES[i % len(PALETA_COLORES)]
            d.add(bc)

            leg = Legend()
            leg.x = 395
            leg.y = 155
            leg.dx = 8
            leg.dy = 8
            leg.fontName = 'Helvetica'
            leg.fontSize = 8
            leg.boxAnchor = 'nw'
            leg.columnMaximum = 6
            leg.colorNamePairs = [(PALETA_COLORES[i % len(PALETA_COLORES)], str(cols_series[i])[:15]) for i in range(len(cols_series))]
            d.add(leg)

            return d
        except Exception:
            return None

    def construir_pdf(self) -> bytes:
        """Compila y genera el archivo PDF completo en memoria retornando los bytes crudos."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=40,
            bottomMargin=45
        )

        styles = self._crear_estilos()
        story = []

        # ------------------------------------------------------------------
        # Encabezado Principal y Metadatos
        # ------------------------------------------------------------------
        story.append(Paragraph(self.TITULO_OFICIAL, styles["ReportHeaderTitle"]))
        meta_texto = (
            f"<b>Fecha y hora de emisión:</b> {self.fecha_emision} &nbsp;|&nbsp; "
            f"<b>Dataset Activo:</b> {self.nombre_dataset} &nbsp;|&nbsp; "
            f"<b>Generado por:</b> {self.usuario}"
        )
        story.append(Paragraph(meta_texto, styles["ReportHeaderSubtitle"]))
        story.append(HRFlowable(
            width="100%", thickness=1.5, color=colors.HexColor("#1E88E5"),
            spaceBefore=2, spaceAfter=10
        ))

        # ------------------------------------------------------------------
        # SECCIÓN 1: Simulaciones Comerciales y Precios Dinámicos
        # ------------------------------------------------------------------
        story.append(Paragraph("1. Simulaciones Comerciales y Precios Dinámicos", styles["SectionHeading"]))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#90CAF9"), spaceBefore=1, spaceAfter=8))

        if not self.simulaciones:
            story.append(Paragraph("No se registraron simulaciones guardadas por el usuario para este dataset.", styles["EmptySectionText"]))
        else:
            for idx, sim in enumerate(self.simulaciones, 1):
                ruta = sim.get("ruta", "N/A")
                franja = sim.get("franja", "N/A")
                ocup = sim.get("ocupacion", "N/A")
                subtitulo_sim = f"Simulación #{idx}: Ruta: {ruta} | Franja: {franja} | Nivel Ocupación: {ocup}"
                story.append(Paragraph(subtitulo_sim, styles["ItemHeading"]))

                datos_sim = [
                    [
                        Paragraph("<b>Variable / Indicador</b>", styles["TableCellBold"]),
                        Paragraph("<b>Valor Parámetro</b>", styles["TableCellBold"]),
                        Paragraph("<b>Métrica Financiera</b>", styles["TableCellBold"]),
                        Paragraph("<b>Valor Calculado</b>", styles["TableCellBold"])
                    ],
                    [
                        Paragraph("Precio Base", styles["TableCell"]),
                        Paragraph(f"${sim.get('precio_base', 0.0):,.2f}", styles["TableCellCenter"]),
                        Paragraph("<b>Precio Dinámico Sugerido</b>", styles["TableCell"]),
                        Paragraph(f"<b>${sim.get('precio_sugerido', 0.0):,.2f}</b>", styles["TableCellCenter"])
                    ],
                    [
                        Paragraph("P(Atraso)", styles["TableCell"]),
                        Paragraph(f"{sim.get('p_atrasado_pct', 0.0):.2f}%", styles["TableCellCenter"]),
                        Paragraph("Ajuste Total Monetario", styles["TableCell"]),
                        Paragraph(f"+${sim.get('ajuste_total_monetario', 0.0):,.2f} (+{sim.get('ajuste_porcentual_total', 0.0):.1f}%)", styles["TableCellCenter"])
                    ],
                    [
                        Paragraph("P(Cancelación)", styles["TableCell"]),
                        Paragraph(f"{sim.get('p_cancelado_pct', 0.0):.2f}%", styles["TableCellCenter"]),
                        Paragraph("Recargo Riesgo Monetario", styles["TableCell"]),
                        Paragraph(f"+${sim.get('recargo_riesgo_monetario', 0.0):,.2f}", styles["TableCellCenter"])
                    ],
                    [
                        Paragraph("Riesgo Logístico Total", styles["TableCell"]),
                        Paragraph(f"{sim.get('riesgo_logistico_pct', 0.0):.2f}%", styles["TableCellCenter"]),
                        Paragraph("Fondo Contingencia Vuelo", styles["TableCell"]),
                        Paragraph(f"${sim.get('fondo_contingencia_vuelo', 0.0):,.2f}", styles["TableCellCenter"])
                    ],
                    [
                        Paragraph("Muestra Analizada", styles["TableCell"]),
                        Paragraph(f"{sim.get('muestra_tamano', 0):,} vuelos", styles["TableCellCenter"]),
                        Paragraph("Asientos Promedio Ocupados", styles["TableCell"]),
                        Paragraph(f"{sim.get('asientos_ocupados_media', 0):,} pax", styles["TableCellCenter"])
                    ]
                ]

                tabla_sim = Table(datos_sim, colWidths=[140, 120, 140, 140])
                tabla_sim.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
                    ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F5F9FD")),
                    ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#F5F9FD")),
                    ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor("#F5F9FD")),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(tabla_sim)
                story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # SECCIÓN 2: Visualizaciones y Gráficos Guardados
        # (Gráficos vectoriales renderizados Y tablas adjuntas)
        # ------------------------------------------------------------------
        story.append(Spacer(1, 6))
        story.append(Paragraph("2. Visualizaciones y Gráficos Guardados", styles["SectionHeading"]))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#90CAF9"), spaceBefore=1, spaceAfter=8))

        if not self.graficos:
            story.append(Paragraph("No se registraron gráficos ni visualizaciones guardadas para este dataset.", styles["EmptySectionText"]))
        else:
            for idx, g in enumerate(self.graficos, 1):
                titulo_graf = g.get("titulo", f"Visualización #{idx}")
                tipo_graf = g.get("tipo", "Gráfico")
                desc_graf = g.get("descripcion", "")
                df_tabla: Optional[pd.DataFrame] = g.get("tabla")

                story.append(Paragraph(f"<b>Gráfico #{idx}:</b> {titulo_graf} ({tipo_graf})", styles["ItemHeading"]))
                if desc_graf:
                    story.append(Paragraph(f"<i>Detalle:</i> {desc_graf}", styles["TableCell"]))
                    story.append(Spacer(1, 4))

                # Renderizado del gráfico visual correspondiente
                if df_tabla is not None and not df_tabla.empty:
                    if tipo_graf == "Gráfico de Torta":
                        dibujo_chart = self._generar_grafico_torta_vector(df_tabla)
                    else:
                        dibujo_chart = self._generar_grafico_barras_vector(df_tabla)

                    if dibujo_chart is not None:
                        story.append(dibujo_chart)
                        story.append(Spacer(1, 6))

                    # Tabla adjunta (contingencia o porcentajes)
                    filas_tabla = []
                    encabezados = [Paragraph(f"<b>{str(col)}</b>", styles["TableCellBold"]) for col in df_tabla.columns]
                    filas_tabla.append(encabezados)

                    for _, row in df_tabla.iterrows():
                        fila_c = []
                        for val in row:
                            if isinstance(val, (float, int)):
                                val_str = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
                            else:
                                val_str = str(val)
                            fila_c.append(Paragraph(val_str, styles["TableCellCenter"]))
                        filas_tabla.append(fila_c)

                    num_cols = len(df_tabla.columns)
                    ancho_total = 540
                    ancho_col = max(45, ancho_total / num_cols)
                    col_widths = [ancho_col] * num_cols

                    t_platypus = Table(filas_tabla, colWidths=col_widths)
                    color_cabecera = "#2E7D32" if tipo_graf == "Gráfico de Torta" else "#1565C0"
                    t_platypus.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color_cabecera)),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ]))
                    story.append(KeepTogether([t_platypus]))
                story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # SECCIÓN 3: Tablas de Probabilidades Condicionales Cruzadas Guardadas
        # ------------------------------------------------------------------
        story.append(Spacer(1, 6))
        story.append(Paragraph("3. Tablas de Probabilidades Condicionales Cruzadas", styles["SectionHeading"]))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#90CAF9"), spaceBefore=1, spaceAfter=8))

        if not self.tablas_condicionales:
            story.append(Paragraph("No se registraron tablas de probabilidades condicionales guardadas para este dataset.", styles["EmptySectionText"]))
        else:
            for idx, tc in enumerate(self.tablas_condicionales, 1):
                tipo_tc = tc.get("tipo", f"Tabla Condicional #{idx}")
                story.append(Paragraph(f"<b>Tabla #{idx}:</b> {tipo_tc}", styles["ItemHeading"]))

                df_m = tc.get("dataframe")
                if isinstance(df_m, pd.DataFrame) and not df_m.empty:
                    filas_df = []
                    encabezados = [Paragraph(f"<b>{str(c)}</b>", styles["TableCellBold"]) for c in df_m.columns]
                    filas_df.append(encabezados)

                    for _, r in df_m.iterrows():
                        fila_r = []
                        for v in r:
                            if isinstance(v, float):
                                v_txt = f"{v:,.2f}"
                            elif isinstance(v, int):
                                v_txt = f"{v:,}"
                            else:
                                v_txt = str(v)
                            fila_r.append(Paragraph(v_txt, styles["TableCellCenter"]))
                        filas_df.append(fila_r)

                    n_cols = len(df_m.columns)
                    col_w = max(40, 540 / n_cols)
                    t_cond = Table(filas_df, colWidths=[col_w] * n_cols)
                    t_cond.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#455A64")),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ]))
                    story.append(KeepTogether([t_cond]))

                story.append(Spacer(1, 10))

        # Construcción del documento
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()
