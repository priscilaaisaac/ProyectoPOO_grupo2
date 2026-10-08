import os
import sys
import pandas as pd
from pathlib import Path

# Agregar el directorio al sys.path para poder importar los módulos
proyecto_dir = r"C:\Users\T14s\Desktop\POO\ProyectoPOO_grupo2"
if proyecto_dir not in sys.path:
    sys.path.append(proyecto_dir)

from modules.lector_datos import FactoryLectorDatos, detectar_formato

carpeta_pruebas = r"C:\Users\T14s\Desktop\POO practica\ARCHIVOS PRUEBA"
archivos = [
    f for f in os.listdir(carpeta_pruebas)
    if f.endswith(('.csv', '.txt', '.xlsx', '.xltx', '.xltm'))
]

print(f"Buscando en {carpeta_pruebas}")
print(f"Se encontraron {len(archivos)} archivos.\n")

for nombre in archivos:
    ruta_completa = os.path.join(carpeta_pruebas, nombre)
    tipo = "CSV" if nombre.endswith('.csv') else "TXT" if nombre.endswith('.txt') else "EXCEL"
    
    print("-" * 60)
    print(f"Probando archivo: {nombre} (Tipo: {tipo})")
    
    # 1. Probar la detección del formato si no es Excel
    if tipo in ["CSV", "TXT"]:
        try:
            sep, has_header = detectar_formato(ruta_completa)
            print(f"   [Detección] Separador detectado: '{sep}', Tiene encabezado: {has_header}")
        except Exception as e:
            print(f"   [Detección ERROR] Falló la detección de formato: {e}")
            
    # 2. Probar la carga con FactoryLectorDatos
    try:
        lector = FactoryLectorDatos.obtener_lector(tipo)
        with open(ruta_completa, 'rb') as f_obj:
            df = lector.leer(origen=f_obj)
            print(f"   [Carga] ÉXITO. Shape del DataFrame: {df.shape}")
    except Exception as e:
        print(f"   [Carga ERROR] Excepción lanzada: {e}")

print("-" * 60)
print("Pruebas finalizadas.")
