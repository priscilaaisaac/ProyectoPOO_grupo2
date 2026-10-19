"""
Token generation and validation using itsdangerous.
"""

import hashlib
import hmac
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


class TokenManager:
    """
    Manages the creation and validation of secure, timed tokens.
    """

    def __init__(self, secret_key: str, salt: str | None = None) -> None:
        """
        Initializes the TokenManager.

        Args:
            secret_key (str): The secret key used to sign the tokens.
            salt (str | None): The salt used to namespace the tokens.
        """
        if not secret_key:
            raise ValueError('secret_key_required')

        self.__secret_key = secret_key

        if salt is None:
            self.__salt = hmac.new(
                secret_key.encode('utf-8'),
                msg=b'auth_module_secure_salt_derivation',
                digestmod=hashlib.sha256
            ).hexdigest()
        else:
            self.__salt = salt

        self.__serializer = URLSafeTimedSerializer(self.__secret_key)

    def generate_token(self, data: Any) -> str:
        """
        Generates a secure token for the provided data (e.g., an email address).

        Args:
            data (Any): The data to encode in the token.

        Returns:
            str: The generated token.
        """
        return self.__serializer.dumps(data, salt=self.__salt)

    def confirm_token(self, token: str, expiration_seconds: int = 3600) -> Any | None:
        """
        Confirms the validity of a token and extracts the embedded data.

        Args:
            token (str): The token to verify.
            expiration_seconds (int): Maximum age of the token in seconds.

        Returns:
            Any | None: The extracted data if valid and not expired, None otherwise.

        Raises:
            Unexpected exceptions from itsdangerous or decoding issues are propagated.
        """
        try:
            data = self.__serializer.loads(
                token,
                salt=self.__salt,
                max_age=expiration_seconds
            )
            return data
        except (SignatureExpired, BadSignature):
            return None
