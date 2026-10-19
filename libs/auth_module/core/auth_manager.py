"""
Authentication manager that encapsulates user registration, login, and recovery logic.
"""

from collections.abc import Callable
from typing import Any

from .db.repository import UserRepository
from .i18n import I18nManager
from .mail.base import MailDispatcher
from .security.hasher import PasswordHasher, WerkzeugPasswordHasher
from .security.password import PasswordPolicy
from .tokens import TokenManager


class AuthManager:
    """
    Core authentication manager handling framework-agnostic business logic.
    """

    def __init__(
        self,
        secret_key: str,
        mail_dispatcher: MailDispatcher,
        user_repository: UserRepository,
        base_url: str,
        password_policy: PasswordPolicy | None = None,
        password_hasher: PasswordHasher | None = None,
        locale: str | Callable[[], str] = 'es',
        custom_translations: dict[str, dict[str, str]] | None = None
    ) -> None:
        """
        Initializes the AuthManager.

        Args:
            secret_key (str): Secret key for token generation.
            mail_dispatcher (MailDispatcher): The email sending service.
            user_repository (UserRepository): The user database repository.
            base_url (str): The base URL of the application for email links.
            password_policy (PasswordPolicy | None): Custom password requirements.
            password_hasher (PasswordHasher | None): Custom password hashing mechanism. Defaults to Werkzeug.
            locale (str | Callable[[], str]): Locale code or callback for backend messages. Defaults to Spanish ('es').
            custom_translations (dict[str, dict[str, str]] | None): Custom overrides for backend translation dictionary.
        """
        self.__i18n = I18nManager(locale=locale, custom_translations=custom_translations)

        if not base_url:
            raise ValueError(self.__i18n.translate('base_url_required'))

        if not secret_key:
            raise ValueError(self.__i18n.translate('secret_key_required'))

        self.__token_manager = TokenManager(secret_key)
        self.__mail_dispatcher = mail_dispatcher
        self.__user_repository = user_repository
        self.__base_url = base_url.rstrip('/')

        if password_policy is not None and not isinstance(password_policy, PasswordPolicy):
            raise TypeError(self.__i18n.translate('invalid_password_policy_type', type=type(password_policy).__name__))
        self.__password_policy = password_policy or PasswordPolicy()

        self.__password_hasher = password_hasher or WerkzeugPasswordHasher()

        # Simulating state for used tokens (could also be moved to the DB)
        self.__used_pw_reset_tokens = set()

    def register_user(self, email: str, password: str) -> bool:
        """
        Registers a new user and sends a verification email.

        Args:
            email (str): The user's email.
            password (str): The user's plain text password.

        Returns:
            bool: True if registration is successful.

        Raises:
            ValueError: If the user already exists or the password doesn't meet the policy.
        """
        if self.__user_repository.get_user_by_email(email):
            raise ValueError(self.__i18n.translate('user_exists'))

        is_valid_pwd, pwd_msg = self.__password_policy.validate(password, i18n_manager=self.__i18n)
        if not is_valid_pwd:
            raise ValueError(pwd_msg)

        pwd_hash = self.__password_hasher.hash(password)
        self.__user_repository.create_user(email=email, password_hash=pwd_hash, verified=False)

        token = self.__token_manager.generate_token({'email': email, 'purpose': 'verification'})
        verify_url = f'{self.__base_url}/verify/{token}'

        self.__mail_dispatcher.send(
            to_email=email,
            subject=self.__i18n.translate('confirm_email_subject'),
            body=self.__i18n.translate('confirm_email_body', url=verify_url)
        )
        return True

    def reset_password(self, token: str, password: str) -> bool:
        """
        Resets the password for an existing user using a recovery token.

        Args:
            token (str): The recovery token.
            password (str): The new plain text password.

        Returns:
            bool: True if password reset was successful.

        Raises:
            ValueError: If the token is invalid or password policy fails.
        """
        email = self.verify_password_reset_token(token)
        if not email:
            raise ValueError(self.__i18n.translate('flash_link_invalid_expired'))

        is_valid_pwd, pwd_msg = self.__password_policy.validate(password, i18n_manager=self.__i18n)
        if not is_valid_pwd:
            raise ValueError(pwd_msg)

        pwd_hash = self.__password_hasher.hash(password)
        self.__user_repository.update_user_password(email, pwd_hash)
        self.__used_pw_reset_tokens.add(token)
        return True

    def verify_user(self, token: str) -> bool:
        """
        Verifies a user's email using the provided token.

        Args:
            token (str): The verification token.

        Returns:
            bool: True if successful, False otherwise.
        """
        data = self.__token_manager.confirm_token(token)
        if not isinstance(data, dict) or data.get('purpose') != 'verification':
            return False

        email = data.get('email')
        if not email:
            return False

        user = self.__user_repository.get_user_by_email(email)
        if not user:
            return False

        self.__user_repository.update_user_verification(email, True)
        return True

    def verify_password_reset_token(self, token: str) -> str | None:
        """
        Verifies if the password reset token is valid and hasn't expired or been used.

        Args:
            token (str): The password reset token.

        Returns:
            str | None: The associated email if valid, None otherwise.
        """
        data = self.__token_manager.confirm_token(token)

        if not isinstance(data, dict) or data.get('purpose') != 'recovery':
            return None

        email = data.get('email')
        user = self.__user_repository.get_user_by_email(email) if email else None

        if token in self.__used_pw_reset_tokens or not user:
            return None

        return email

    def authenticate_user(self, email: str, password: str) -> bool:
        """
        Authenticates a user using email and password.

        Args:
            email (str): The user's email.
            password (str): The user's plain text password.

        Returns:
            bool: True if authentication is successful, False otherwise.

        Raises:
            ValueError: If the user's email is not verified.
        """
        user = self.__user_repository.get_user_by_email(email)
        if not user:
            return False

        if not user.get('verified'):
            raise ValueError(self.__i18n.translate('email_not_verified'))
        if not user.get('password'):
            return False

        return self.__password_hasher.verify(password, user['password'])

    def get_or_create_oauth_user(self, email: str, name: str | None = None, provider: str | None = None) -> dict[str, Any]:
        """
        Gets a user or creates a new one marked as verified if they come from an OAuth provider.

        Args:
            email (str): The user's email.
            name (str | None): The user's name.
            provider (str | None): The OAuth provider name (e.g., 'google').

        Returns:
            dict[str, Any]: The user's data dictionary.
        """
        user = self.__user_repository.get_user_by_email(email)
        if user:
            return user

        self.__user_repository.create_user(
            email=email,
            password_hash=None,
            verified=True,
            name=name,
            oauth_provider=provider
        )
        return self.__user_repository.get_user_by_email(email)

    def request_password_recovery(self, email: str) -> bool:
        """
        Initiates a password recovery process and sends a recovery email.

        Args:
            email (str): The user's email.

        Returns:
            bool: True if the email was successfully sent.

        Raises:
            ValueError: If the user does not exist.
        """
        if not self.__user_repository.get_user_by_email(email):
            raise ValueError(self.__i18n.translate('no_user_with_email'))

        token = self.__token_manager.generate_token({'email': email, 'purpose': 'recovery'})
        recovery_url = f'{self.__base_url}/reset-password/{token}'

        self.__mail_dispatcher.send(
            to_email=email,
            subject=self.__i18n.translate('password_recovery_subject'),
            body=self.__i18n.translate('password_recovery_body', url=recovery_url)
        )
        return True

    def set_locale(self, locale: str) -> None:
        """Sets the locale for the backend translator."""
        self.__i18n.set_locale(locale)
