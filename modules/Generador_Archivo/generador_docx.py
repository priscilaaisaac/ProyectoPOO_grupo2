import io
import pandas as pd
from modules.Generador_Archivo.generador_archivo_base import GeneradorArchivo

try:
    import docx
except ModuleNotFoundError:
    docx = None


class GeneradorDOCX(GeneradorArchivo):
    """
    Generador de informes ejecutivos en formato Word (DOCX).
    Hereda de GeneradorArchivo desacoplando la estructura de datos del renderizado físico.
    """

    def generar_archivo(self) -> bytes:
        if docx is None:
            raise ModuleNotFoundError("La librería 'python-docx' no está instalada. Instálala con: pip install python-docx")

        documento = docx.Document()
        documento.add_heading(self.TITULO_OFICIAL, 0)
        
        # Metadatos
        documento.add_paragraph(f"Fecha y hora de emisión: {self.fecha_emision}")
        documento.add_paragraph(f"Dataset Activo: {self.nombre_dataset}")
        documento.add_paragraph(f"Generado por: {self.usuario}")
        
        contador_seccion = 1
        
        # Sección 1: Simulaciones (Solo si hay datos)
        if self.simulaciones:
            documento.add_heading(f"{contador_seccion}. Simulaciones Comerciales y Precios Dinámicos", level=1)
            for idx, sim in enumerate(self.simulaciones, 1):
                documento.add_heading(f"Simulación #{idx}: Ruta: {sim.get('ruta')} | Franja: {sim.get('franja')}", level=2)
                p = documento.add_paragraph()
                p.add_run(f"Precio Base: ${sim.get('precio_base', 0):.2f}\n")
                p.add_run(f"Precio Dinámico Sugerido: ${sim.get('precio_sugerido', 0):.2f}").bold = True
            contador_seccion += 1
              
        # Sección 2: Gráficos y Tablas (Solo si hay datos)
        if self.graficos:
            documento.add_heading(f"{contador_seccion}. Visualizaciones y Gráficos Guardados", level=1)
            documento.add_paragraph("Nota: Los gráficos vectoriales están optimizados para PDF. A continuación se detallan las tablas de datos asociadas:")
            for idx, g in enumerate(self.graficos, 1):
                documento.add_heading(f"Gráfico #{idx}: {g.get('titulo')}", level=2)
                df_tabla = g.get('tabla')
                if isinstance(df_tabla, pd.DataFrame) and not df_tabla.empty:
                    tabla_docx = documento.add_table(rows=1, cols=len(df_tabla.columns))
                    tabla_docx.style = 'Table Grid'
                    hdr_cells = tabla_docx.rows[0].cells
                    for i, col in enumerate(df_tabla.columns):
                        hdr_cells[i].text = str(col)
                        if hdr_cells[i].paragraphs and hdr_cells[i].paragraphs[0].runs:
                            hdr_cells[i].paragraphs[0].runs[0].bold = True
                    for _, row in df_tabla.iterrows():
                        row_cells = tabla_docx.add_row().cells
                        for i, val in enumerate(row):
                            row_cells[i].text = f"{val:,.2f}" if isinstance(val, float) else str(val)
            contador_seccion += 1
              
        # Sección 3: Tablas Condicionales (Solo si hay datos)
        if self.tablas_condicionales:
            documento.add_heading(f"{contador_seccion}. Tablas de Probabilidades Condicionales", level=1)
            for idx, tc in enumerate(self.tablas_condicionales, 1):
                documento.add_heading(f"Tabla #{idx}: {tc.get('tipo')}", level=2)
                df_tc = tc.get('dataframe')
                if isinstance(df_tc, pd.DataFrame) and not df_tc.empty:
                    tabla_docx = documento.add_table(rows=1, cols=len(df_tc.columns))
                    tabla_docx.style = 'Table Grid'
                    hdr_cells = tabla_docx.rows[0].cells
                    for i, col in enumerate(df_tc.columns):
                        hdr_cells[i].text = str(col)
                        if hdr_cells[i].paragraphs and hdr_cells[i].paragraphs[0].runs:
                            hdr_cells[i].paragraphs[0].runs[0].bold = True
                    for _, row in df_tc.iterrows():
                        row_cells = tabla_docx.add_row().cells
                        for i, val in enumerate(row):
                            row_cells[i].text = f"{val:,.2f}" if isinstance(val, float) else str(val)
            contador_seccion += 1
              
        # Mensaje si todo está vacío
        if contador_seccion == 1:
            documento.add_paragraph("El analista no ha guardado ningún elemento (simulaciones, gráficos o tablas) para este informe.")
              
        # Guardar en memoria y retornar bytes
        buffer = io.BytesIO()
        documento.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
