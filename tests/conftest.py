import sys
import os

# Asegura que la raíz del proyecto y la carpeta libs estén en sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBS_DIR = os.path.join(BASE_DIR, "libs")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if LIBS_DIR not in sys.path:
    sys.path.insert(0, LIBS_DIR)
