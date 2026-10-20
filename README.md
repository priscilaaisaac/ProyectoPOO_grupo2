✈️ Análisis Histórico de Vuelos para la Toma de Decisiones

Sistema integral de ingestión, limpieza, análisis estadístico y simulación comercial para empresas de aviación.

Este proyecto integrador de la materia Programación Orientada a Objetos permite a las aerolíneas transformar grandes volúmenes de información histórica cruda proveniente de orígenes heterogéneos (CSV, TXT, Excel, bases de datos SQL) en indicadores útiles para la optimización logística y comercial.

A través de un motor backend 100% orientado a objetos y una interfaz visual en Streamlit, el sistema evalúa la calidad de los datos mediante contratos de esquema, ejecuta pipelines dinámicos de saneamiento y simula estrategias de precios dinámicos basados en el riesgo logístico (retrasos y cancelaciones).

✨ Características Principales

Ingestión Polimórfica: Soporte para múltiples formatos de archivo de manera transparente mediante el patrón Factory y Template Method.

Validación por Contrato (Esquema): Verificación estricta de variables obligatorias, tipos de datos y coherencia cronológica antes de permitir el análisis.

Pipeline de Limpieza Dinámico: Módulo interactivo que permite apilar estrategias de imputación (estadísticas o por reglas de negocio) y eliminación de datos anómalos.

Modelo de Dominio Autónomo: Objetos de tipo Vuelo que calculan de manera independiente sus métricas de duración, factor de ocupación e ingresos.

Simulación Estocástica y Precios Dinámicos: Cálculo de riesgo logístico aplicando el Principio de Inversión de Dependencias (DIP), lo que permite escalar hacia futuros modelos predictivos (Machine Learning).

Exportación Ejecutiva: Generación algorítmica de reportes en formato PDF con gráficos vectoriales utilizando ReportLab.

🏗 Arquitectura General y Patrones de Diseño

El sistema está estrictamente dividido en dos capas, cumpliendo con el principio de Responsabilidad Única (SRP) y garantizando que la lógica de negocio esté completamente desacoplada de la interfaz gráfica.

Capas del Sistema

Capa de Presentación (apps/): Desarrollada en Streamlit. Maneja el estado de la sesión, la navegación (Router) y captura las decisiones del usuario, delegando todo el procesamiento al backend.

Capa de Dominio y Negocio (modules/): Lógica pura en Python orientada a objetos estructurada en subpaquetes especializados.

Patrones de Diseño Aplicados

Factory Method: Implementado en FactoryLectorDatos para instanciar lectores específicos según el tipo de archivo, y en FabricaVuelos para transformar DataFrames en entidades de dominio.

Template Method: Base de la arquitectura de extensibilidad. Utilizado en MotorAnalisisBase, LectorDatos y GeneradorArchivo para definir esqueletos algorítmicos que las clases hijas (MotorEstadisticoDescriptivo, LectorCSV, GeneradorPDF) especializan.

Strategy & Pipeline: El PipelineLimpieza apila objetos de tipo OperacionLimpieza (estrategias de imputación) que se ejecutan secuencialmente sobre los datos.

Command: Implementado en SesionAnalisis para serializar y persistir el historial de acciones y simulaciones del analista, permitiendo auditorías.

Estructura de Directorios

apps/: Scripts de la interfaz gráfica en Streamlit (app_1.py como entrypoint, modulo_ingestion.py, modulo_analisis.py, etc.).

modules/: Lógica de dominio y reglas de negocio.

Lectores/: Jerarquía de clases para ingestión de datos (LectorCSV, LectorExcel, LectorSQL).

Estadistica/: Motores de análisis y simuladores de precios.

Generador_Archivo/: Exportadores de informes (PDF).

Vuelos.py, fabrica_vuelos.py, validador.py, calidad.py.

data/: Almacenamiento local generado por el sistema (datasets consolidados limpios y base de datos de usuarios JSON).

deps/: Archivo requirements.txt con las dependencias del proyecto.

🚀 Instalación y Uso

Clonar el repositorio:

git clone https://github.com/priscilaaisaac/ProyectoPOO_grupo2.git
cd ProyectoPOO_grupo2


Crear y activar un entorno virtual:

python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate


Instalar dependencias:

pip install -r deps/requirements.txt


Ejecutar la aplicación:
Inicia el entrypoint del framework Streamlit.

streamlit run apps/app_1.py


🙎‍♀️🙎‍♂️ Autores:

Isaac, Priscila Rocio

Andrade, Eric Daniel

📅 Cuatrimestre de cursado:

Programación Orientada a Objetos - Facultad de Ingeniería (UNER) | 2026