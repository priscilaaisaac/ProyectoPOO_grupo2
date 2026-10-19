# Documentación de Mail

El paquete de correos gestiona toda la comunicación saliente con el usuario (verificación de cuentas y recuperación de contraseñas).

## Interfaz Abstracta (`base.py`)
Todas las clases de despacho de correos implementan la clase abstracta `MailDispatcher`, que define el método `send(to_email, subject, body, logo_image_file) -> None`. 
Este método ante cualquier fallo o impedimento crítico durante el envío (como credenciales inválidas o conexión rechazada), la implementación levantará una excepción. Esto permite intercambiar proveedores de manera completamente transparente sin modificar el flujo ni el manejo de errores del `AuthManager`.

## Despachadores Incluidos

### 1. ConsoleMailDispatcher (`console_dispatcher.py`)
**Ideal para desarrollo local.**
Este despachador intercepta el correo y lo imprime de manera legible por la terminal. No requiere configuración de servidores SMTP ni variables de entorno. 
Te permite hacer clic directamente en los enlaces de validación y recuperación que aparecen en la consola.

### 2. SmtpMailDispatcher (`smtp_dispatcher.py`)
**Ideal para entornos de producción.**
Envía correos electrónicos reales utilizando un servidor SMTP. 
Se configura mediante la clase `EmailEnvConfig`, que espera las siguientes variables de entorno:
- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `NAME_SENDER`
- `MAIL_SENDER_ADDRESS`

**Uso:**
```python
from auth_module.core.mail.config import EmailEnvConfig
from auth_module.core.mail.smtp_dispatcher import SmtpMailDispatcher

# Cargará los valores automáticamente desde el sistema/archivo .env
config = EmailEnvConfig()
mail = SmtpMailDispatcher(config)
```
