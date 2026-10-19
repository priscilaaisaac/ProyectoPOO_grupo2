# Internacionalización (i18n)

Este submódulo se encarga de proveer una capa de internacionalización y traducción agnóstica para todo el sistema de autenticación. Su principal propósito es separar los mensajes y textos estáticos de la lógica del código, permitiendo soportar múltiples idiomas sin acoplamientos rígidos.

## Cómo funciona
El componente central es la clase `I18nManager`. Ésta se encarga de:
1. Almacenar y consolidar los diccionarios de traducciones (por defecto, utiliza los de la variable `BACKEND_TRANSLATIONS` definidos en `translations.py`).
2. Resolver cuál es el idioma activo. Puede ser un simple *string* (ej. `'es'`) o una función dinámica (*callable*) que devuelva el idioma en tiempo de ejecución (ideal para entornos web donde el idioma se evalúa por petición).
3. Evaluar e interpolar variables en los mensajes utilizando `format(**kwargs)`, lo cual permite que reglas y clases dinámicas inyecten sus propios valores.

## Traducciones por defecto
La librería incluye dos idiomas integrados: **Español (`es`)** e **Inglés (`en`)**. Por convención de este proyecto, **el idioma base y por defecto es el español.** 

Las claves del backend (definidas en `BACKEND_TRANSLATIONS`) contemplan los mensajes más profundos del sistema:
- Errores de validación o base de datos (`user_exists`, `user_not_exists`).
- Errores originados en las políticas de seguridad (Ej: `password_length_err`).
- Cuerpos de texto y asuntos para los despachadores de correos (MailDispatchers).
- Excepciones explícitas destinadas a los desarrolladores.

*Nota: La extensión de Flask cuenta con un manejador gemelo y su propio diccionario independiente, abarcando exclusivas traducciones para las interfaces visuales, alertas flash y formularios de HTML.*

## Inyectar Traducciones (Custom Translations)
Siguiendo las mejores prácticas, **nunca** se deben modificar los archivos internos para cambiar una traducción o añadir un nuevo idioma (como Francés `fr`).

El manejador está preparado para recibir un diccionario llamado `custom_translations` al momento de inicializar los managers (ya sea `AuthManager` o `FlaskExtension`). Cualquier diccionario inyectado se fusionará sobre la configuración en memoria, sobreescribiendo las claves existentes y añadiendo los idiomas nuevos automáticamente.

## Ejemplos de implementación
Inicializa el `AuthManager` o `FlaskExtension` con el parámetro `custom_translations` para sobrescribir o añadir nuevas traducciones. Por ejemplo:
```python
# Traducciones personalizadas para el backend
custom_backend_translations = {
    'es': {
        'user_exists': '¡Esta dirección de correo ya está en uso!'
    },
    'en': {
        'user_exists': 'This email is already registered.'
    }
}

auth_manager = AuthManager(
    mail_dispatcher=mail,
    user_repository=repo,
    base_url='http://localhost:5000',
    secret_key='my_secret',
    locale='es',
    custom_translations=custom_backend_translations
)
```
