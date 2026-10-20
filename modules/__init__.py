"""
Módulo raíz del paquete modules.
Exporta los subpaquetes Lector, Estadistica y Generador_Archivo,
así como los componentes centrales (calidad, validador, pipeline, fabrica, vuelos, usuarios).
Garantiza retrocompatibilidad total con rutas previas.
"""

import sys
from . import Lector
from . import Estadistica
from . import Generador_Archivo

# Alias de compatibilidad por si se referencia en plural
Lectores = Lector
sys.modules["modules.Lectores"] = Lector

# Retrocompatibilidad de módulos movidos a subcarpetas
from modules.Lector import lector_base
from modules.Lector import lector_sql
from modules.Lector import lector_excel
from modules.Lector import lector_texto_delimitado
from modules.Lector import lector
from modules.Estadistica import motor_analisis_base
from modules.Estadistica import motor_estadistico_descriptivo
from modules.Estadistica import simulador_precios
from modules.Generador_Archivo import generador_archivo_base
from modules.Generador_Archivo import generador_pdf

sys.modules["modules.lector_base"] = lector_base
sys.modules["modules.lector_sql"] = lector_sql
sys.modules["modules.lector_excel"] = lector_excel
sys.modules["modules.lector_texto_delimitado"] = lector_texto_delimitado
sys.modules["modules.lector"] = lector
sys.modules["modules.lector.lector"] = lector
sys.modules["modules.motor_analisis_base"] = motor_analisis_base
sys.modules["modules.motor_estadistico_descriptivo"] = motor_estadistico_descriptivo
sys.modules["modules.simulador_precios"] = simulador_precios
sys.modules["modules.analisis_estadistico"] = motor_estadistico_descriptivo
sys.modules["modules.generador_archivo_base"] = generador_archivo_base
sys.modules["modules.generador_pdf"] = generador_pdf

__all__ = [
    "Lector",
    "Lectores",
    "Estadistica",
    "Generador_Archivo",
]
