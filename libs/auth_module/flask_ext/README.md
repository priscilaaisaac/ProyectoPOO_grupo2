# Documentación de la Extensión de Flask (`flask_ext`)

Este subpaquete toma la lógica independiente del `AuthManager` y provee una integración completa, lista para usarse, dentro del framework Flask.

## Inicialización (`extension.py`)
La integración principal se realiza mediante la clase `FlaskExtension`. 
Al inicializarla, ésta registra automáticamente el **Blueprint de Autenticación** y los **Manejadores de Errores** necesarios.

```python
from auth_module.flask_ext.extension import FlaskExtension

# manager = AuthManager(...)
FlaskExtension(app, manager)
```

## Rutas Automáticas
El Blueprint monta automáticamente los siguientes endpoints bajo el prefijo `/auth`:
- `/auth/register`
- `/auth/login`
- `/auth/logout`
- `/auth/verify/<token>`
- `/auth/password-recovery`
- `/auth/reset-password/<token>`

## Control de Acceso (`decorators.py`)
Para proteger tus propias rutas de Flask, la extensión expone decoradores nativos:

```python
from auth_module.flask_ext.decorators import login_required

@app.route('/dashboard')
@login_required
def dashboard():
    return "Bienvenido a tu panel protegido."
```
*(El decorador automáticamente redirigirá al usuario a `/auth/login` si no está autenticado).*

### Redirección Personalizada
Si deseas que, después de hacer login exitoso, el usuario sea redirigido a una página distinta en lugar del dashboard por defecto, puedes configurarlo mediante el parámetro `login_redirect_endpoint` durante la inicialización:

```python
from auth_module.flask_ext.extension import FlaskExtension

FlaskExtension(app, manager, login_redirect_endpoint='mi_app.dashboard')
```


## Configuración de Idioma (i18n)
La extensión detecta automáticamente la configuración de idioma del `AuthManager`. Adicionalmente, puedes sobrescribir el idioma configurando las variables correspondientes en el objeto `app.config` de Flask antes o después de inicializar la extensión:

```python
app = Flask(__name__)
app.config['AUTH_BACKEND_LOCALE'] = 'es'   # Idioma del backend
app.config['AUTH_FRONTEND_LOCALE'] = 'en'  # Idioma de las vistas y mensajes flash
```

## Interfaz Gráfica (`templates/`)
La extensión incluye todas las plantillas HTML renderizadas con Jinja2. Las pantallas de inicio de sesión, registro y notificaciones flash ya tienen estilos CSS integrados. Todo el código base y los identificadores están en inglés, mientras que los textos renderizados para el usuario están en español.
