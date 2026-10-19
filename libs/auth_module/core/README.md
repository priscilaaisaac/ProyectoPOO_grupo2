# Documentación del Core

El directorio `core/` contiene toda la lógica agnóstica de negocio del Módulo de Autenticación. Esto significa que ninguna clase de este paquete depende de un framework web (como Flask o Django).

## Componentes Principales

### 1. AuthManager (`auth_manager.py`)
Es el orquestador principal. Utiliza Inyección de Dependencias para interactuar con la base de datos, el gestor de contraseñas y el servicio de correos.

```python
manager = AuthManager(
    mail_dispatcher=mail,
    user_repository=repo,
    base_url='http://localhost:5000',
    secret_key='secreto',
    locale='es',                      # Opcional: idioma o función callback para traducciones
    custom_translations=None          # Opcional: diccionario para sobrescribir traducciones
)
```
Provee métodos listos para usar como:
- `register_user(email, password)`
- `authenticate_user(email, password)`
- `verify_user(token)`
- `request_password_recovery(email)`

### 2. Base de Datos (`db/`)
Define la interfaz `UserRepository` que garantiza que cualquier implementación de base de datos expondrá los métodos necesarios (`create_user`, `get_user_by_email`, etc.).
Se provee una implementación por defecto: `SQLiteUserRepository`, ideal para un despliegue rápido sin infraestructura compleja.

### 3. Gestor de Tokens (`tokens.py`)
Utiliza `itsdangerous` para la generación segura de tokens cifrados con un tiempo de expiración.
- **Tokens Multipropósito:** Los tokens almacenan diccionarios con el payload y su finalidad (ej. `{'email': email, 'purpose': 'recovery'}`). Esto garantiza que un token emitido para confirmar un correo electrónico no pueda utilizarse como acceso de puerta trasera para cambiar contraseñas.
- **Manejo de Errores Seguro:** Las validaciones aíslan explícitamente fallos propios del token (como `SignatureExpired` y `BadSignature` que retornan `None`), mientras que cualquier otra anomalía o excepción del sistema se propaga libremente para un correcto rastreo de errores en los logs.
