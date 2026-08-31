# 🗄️ Datos

En esta carpeta se guardan todos los archivos, ya sean de texto, csv, JSON, etc. de los cuales se obtuvieron datos para realizar el proyecto. También se guardan los archivos que contengan los resultados del proyecto o que sirvan para almacenar información.

> [!WARNING]
> **Se recomienda fuertemente no almacenar bases de datos (ej. archivos `.sqlite3`, `.db`) en el repositorio.**
> Por cuestiones de seguridad y límite de tamaño de almacenamiento, las bases de datos deben ser ignoradas por Git. En el archivo `.gitignore` ya se encuentran configuradas las extensiones correspondientes para evitar trackeos accidentales.
> 
> Si deseas subir la base de datos al repositorio (por cuestiones de practicidad, portabilidad entre dispositivos, o porque contiene datos pre-cargados necesarios), deberás comentar las líneas correspondientes en el `.gitignore`.
> 
> **IMPORTANTE PARA LA EVALUACIÓN/CORRECCIÓN:** Si optas por NO trackear la base de datos, el sistema **debe** poder inicializarse de manera transparente. Si al levantar el proyecto no se detecta la base de datos, tu código debe encargarse de crear una vacía automáticamente y poblarla con los datos mínimos requeridos para su funcionamiento. Se debe poder clonar y probar el sistema fácilmente sin procesos manuales. Si la creación automática de la DB requiere especificar una ruta en el archivo `.env`, esto debe estar claramente documentado.
