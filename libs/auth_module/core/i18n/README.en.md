# Internationalization (i18n)

This sub-module provides an agnostic internationalization and translation layer for the entire authentication system. Its primary purpose is to separate static messages and text from code logic, allowing multiple languages to be supported without rigid coupling.

## How it works
The core component is the `I18nManager` class. This component is responsible for:
1. Storing and consolidating translation dictionaries (by default, it uses the `BACKEND_TRANSLATIONS` defined in `translations.py`).
2. Resolving the currently active locale. This can be a simple string (e.g. `'es'`) or a dynamic *callable* function that returns the language at runtime (ideal for web environments where the language is evaluated per request).
3. Evaluating and interpolating variables within messages using `format(**kwargs)`, allowing dynamic rules and classes to inject their own formatting values.

## Default Translations
The library includes two built-in languages: **Spanish (`es`)** and **English (`en`)**. By project convention, **the base and default language is Spanish.**

The backend keys (defined in `BACKEND_TRANSLATIONS`) cover the deepest messages of the system:
- Database or validation errors (`user_exists`, `user_not_exists`).
- Errors originating from security policies (e.g. `password_length_err`).
- Subjects and body texts for the mail dispatchers (MailDispatchers).
- Explicit exceptions intended for developers.

*Note: The Flask extension relies on a twin manager and its own independent dictionary, covering exclusive translations for visual user interfaces, flash alerts, and HTML forms.*

## Injecting Custom Translations
Following best practices, you should **never** modify the internal files to change a translation or add a new language (such as French `fr`).

The manager is prepared to receive a dictionary called `custom_translations` upon initialization of the upper managers (either `AuthManager` or `FlaskExtension`). Any injected dictionary will be merged into the in-memory configuration, seamlessly overriding existing keys and adding new languages automatically.

## Implementation Examples
Initialize the `AuthManager` or `FlaskExtension` with the `custom_translations` parameter to override or add new translations. For example:
```python
# Custom translations for the backend
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
    locale='es',                      # Backend locale ('es' or 'en', defaults to 'es')
    custom_translations=custom_backend_translations
)
```
