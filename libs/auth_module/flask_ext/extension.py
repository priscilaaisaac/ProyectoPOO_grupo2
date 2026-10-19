"""
Flask extension initialization.
"""

from collections.abc import Callable

from flask import Flask

from flask_session import Session

from ..core.auth_manager import AuthManager
from ..core.i18n import FRONTEND_TRANSLATIONS, I18nManager
from .routes import _set_login_redirect, auth_bp


class FlaskExtension:
    """
    Flask extension to integrate the AuthManager and authentication routes.
    """

    def __init__(
        self,
        app: Flask | None = None,
        auth_manager: AuthManager | None = None,
        locale: str | Callable[[], str] = 'es',
        custom_translations: dict[str, dict[str, str]] | None = None,
        login_redirect_endpoint: str | None = None
    ) -> None:
        """
        Initializes the extension.

        Args:
            app (Flask | None): The Flask application instance.
            auth_manager (AuthManager | None): The configured AuthManager instance.
            locale: Locale code or callback for the frontend/templates. Defaults to Spanish ('es').
            custom_translations: Custom overrides for frontend translations.
            login_redirect_endpoint: Endpoint to redirect to after successful login.
        """
        self.auth_manager = auth_manager
        self.__locale = locale
        self.__custom_translations = custom_translations

        if login_redirect_endpoint:
            _set_login_redirect(login_redirect_endpoint)

        if app is not None:
            self.init_app(app, auth_manager)

    def init_app(
        self,
        app: Flask,
        auth_manager: AuthManager | None = None,
        login_redirect_endpoint: str | None = None
    ) -> None:
        """
        Registers the extension with the Flask application.

        Args:
            app (Flask): The Flask application instance.
            auth_manager (AuthManager | None): The configured AuthManager instance.
            login_redirect_endpoint: Endpoint to redirect to after successful login.
        """
        if login_redirect_endpoint:
            _set_login_redirect(login_redirect_endpoint)

        if auth_manager:
            self.auth_manager = auth_manager

        if not self.auth_manager:
            raise ValueError('An AuthManager instance must be provided to FlaskExtension.')

        # Store the manager in app extensions for route access
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['auth_module'] = self.auth_manager

        # Set up a dedicated frontend translator using frontend-specific keys
        # Read the locales from Flask config if available, fallback to parameters
        app_backend = app.config.get('AUTH_BACKEND_LOCALE')
        if app_backend:
            self.auth_manager.set_locale(app_backend)

        app_frontend = app.config.get('AUTH_FRONTEND_LOCALE') or self.__locale

        self.i18n = I18nManager(
            locale=app_frontend,
            default_translations=FRONTEND_TRANSLATIONS,
            custom_translations=self.__custom_translations
        )

        app.extensions['auth_frontend_i18n'] = self.i18n

        # Initialize Flask-Session if it's not already initialized
        if 'session' not in app.extensions:
            Session(app)

        # Register the authentication blueprint
        app.register_blueprint(auth_bp, url_prefix='/auth')
