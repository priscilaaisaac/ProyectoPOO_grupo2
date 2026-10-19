# Flask Extension Documentation (`flask_ext`)

This subpackage takes the independent logic from the `AuthManager` and provides a complete, ready-to-use integration within the Flask framework.

## Initialization (`extension.py`)
The main integration is done through the `FlaskExtension` class. 
When initialized, it automatically registers the **Authentication Blueprint** and the necessary **Error Handlers**.

```python
from auth_module.flask_ext.extension import FlaskExtension

# manager = AuthManager(...)
FlaskExtension(app, manager)
```

## Automatic Routes
The Blueprint automatically mounts the following endpoints under the `/auth` prefix:
- `/auth/register`
- `/auth/login`
- `/auth/logout`
- `/auth/verify/<token>`
- `/auth/password-recovery`
- `/auth/reset-password/<token>`

## Access Control (`decorators.py`)
To protect your own Flask routes, the extension exposes native decorators:

```python
from auth_module.flask_ext.decorators import login_required

@app.route('/dashboard')
@login_required
def dashboard():
    return "Welcome to your protected panel."
```
*(The decorator will automatically redirect the user to `/auth/login` if they are not authenticated).*

### Custom Redirection
If you want the user to be redirected to a different page after a successful login instead of the default dashboard, you can configure it via the `login_redirect_endpoint` parameter during initialization:

```python
from auth_module.flask_ext.extension import FlaskExtension

FlaskExtension(app, manager, login_redirect_endpoint='my_app.dashboard')
```


## Language Configuration (i18n)
The extension automatically detects the language settings of the `AuthManager`. Additionally, you can override the locales by configuring the corresponding variables in Flask's `app.config` object before or after initializing the extension:

```python
app = Flask(__name__)
app.config['AUTH_BACKEND_LOCALE'] = 'es'   # Backend language
app.config['AUTH_FRONTEND_LOCALE'] = 'en'  # Frontend views and flash messages language
```

## Graphical Interface (`templates/`)
The extension includes all HTML templates rendered with Jinja2. The login, registration, and flash notification screens already have built-in CSS styling. All base code and identifiers are in English, while the texts rendered for the user are in Spanish.
