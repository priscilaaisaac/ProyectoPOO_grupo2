# 📚 Bibliotecas (libs)

En este directorio se deben colocar las bibliotecas locales o dependencias de terceros que se manejen de forma manual (código reutilizable que funciona de manera independiente al proyecto principal).

### Uso de la biblioteca de Algoritmos y Estructuras de Datos (AyED)

Para utilizar la biblioteca desarrollada en la materia de Algoritmos y Estructuras de Datos, se debe seguir este procedimiento:
1. Colocar la carpeta completa `biblioteca_ayed_fiuner` (con su propio archivo `pyproject.toml` configurado) dentro de este directorio `libs`.
2. El archivo de requerimientos `deps/requirements.txt` del proyecto ya está configurado con la ruta `-e "./libs/biblioteca_ayed_fiuner"` para detectar la biblioteca como paquete instalable local. 
3. Al instalar las dependencias con `pip install -r deps/requirements.txt`, la biblioteca quedará disponible para ser importada en el código.
