# Repositorio de plantilla inicial de Programación Orientada a Objetos
## 📚 Uso de la plantilla inicial

> [!NOTE]
> Una vez que hayan creado su propio repositorio a partir de esta plantilla y lo hayan clonado, **pueden eliminar esta sección técnica** (secciones "Repositorio de plantilla inicial de Programación Orientada a Objetos" y "Uso de la plantilla inicial") y dejar únicamente la documentación correspondiente a su proyecto.

Este repositorio cuenta con una estructura de directorios que permiten tener el código organizado, separando la lógica principal, módulos, aplicaciones y bibliotecas. Además, facilita contar con código reutilizable de forma local.

Para lograr esto último, se provee de un directorio `libs` que funciona como un espacio para almacenar bibliotecas de código reutilizable local (por ejemplo, la `biblioteca_ayed_fiuner` de la materia de Algoritmos y Estructuras de Datos).

### Pasos generales para inicializar

1 - Crea tu propio repositorio a partir de la plantilla (botón "Use this template" en GitHub).

2 - Clona el nuevo repositorio en tu computadora.

3 - En VSCode, abre la carpeta raíz del proyecto clonado. Si les aparece un mensaje indicando que la carpeta se abrió en **Modo restringido**, deben seleccionar **Confiar** en la carpeta.

4 - Crea un entorno virtual e instala las dependencias necesarias. En el archivo [`deps/requirements.txt`](./deps/requirements.txt) se encuentra configurada la dependencia para importar la biblioteca local desde la carpeta [`libs/biblioteca_ayed_fiuner`](./libs/biblioteca_ayed_fiuner) en modo editable:

```bash
pip install -r .\deps\requirements.txt
```

5 - **Variables de Entorno (.env)**: Se recomienda gestionar configuraciones (como URLs o credenciales) mediante variables de entorno usando la librería `python-dotenv`.
- Como buena práctica, debes mantener actualizado el archivo `.env.example` en la raíz de tu repositorio. En él debes documentar (solo listar los nombres seguidos de '=', sin los valores) todas las variables que tu sistema necesita. De este modo, quien vea el repositorio sabrá qué variables están disponibles para configurar.
- Para tu desarrollo local, copia ese archivo y renómbralo a `.env` (este archivo está ignorado por Git por seguridad) y asígnale los valores reales.
- A nivel código, las variables que son obligatorias para el funcionamiento del sistema no deben tener un valor por defecto. Las variables que configuran comportamientos opcionales deben tener un valor default al leerse (ej: `DEBUG=False` si no se configura).
- Se recomienda fuertemente tener un único archivo centralizado (por ejemplo, `settings.py` o `config.py`) que sea el único lugar donde se leen las variables del `.env`. Cualquier otra parte del sistema que requiera de alguna configuración o variable debe importar directamente desde este archivo, evitando leer el entorno múltiples veces a lo largo del código.

6 - Ya puedes comenzar a organizar tu código en los directorios [`apps`](./apps), [`modules`](./modules), y utilizar código reutilizable alojando las bibliotecas en el directorio [`libs`](./libs).

---

# 🐍 Nombre del Proyecto

Breve descripción del proyecto:

Ejemplo: "Este es el proyecto integrador de la materia Programación Orientada a Objetos. Permite [describir funcionalidades principales del sistema]."

---
## 🏗 Arquitectura General

Explica brevemente cómo está organizado el código (módulos, clases, aplicaciones, etc.)

La estructura de directorios del proyecto se organiza de la siguiente manera:
- [**`apps/`**](./apps): Scripts principales y puntos de entrada de las aplicaciones.
- [**`data/`**](./data): Datos utilizados o generados por el proyecto.
- [**`deps/`**](./deps): Dependencias del proyecto.
- [**`docs/`**](./docs): Documentación e informes del proyecto.
- [**`libs/`**](./libs): Bibliotecas locales reutilizables (ej. `biblioteca_ayed_fiuner`).
- [**`modules/`**](./modules): Lógica de dominio, clases y controladores del sistema orientado a objetos.
- [**`templates/`**](./templates): Plantillas HTML para el renderizado de vistas (si el proyecto requiere interfaz web).
- [**`tests/`**](./tests): Pruebas unitarias del proyecto.

---

## 🙎‍♀️🙎‍♂️ Autores:
    - Apellido y Nombre del primer integrante
    - Apellido y Nombre del segundo integrante

## 📅 Cuatrimestre de cursado:
    1er/2do cuatrimestre del 20xx

---

> **Consejo**: Mantén este README **actualizado** conforme evoluciona el proyecto, y elimina (o añade) secciones según necesites. Esta plantilla es sólo un punto de partida general.
