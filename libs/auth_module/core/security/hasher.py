"""
Password hashing abstractions and default implementations.
"""

from abc import ABC, abstractmethod

from werkzeug.security import check_password_hash, generate_password_hash


class PasswordHasher(ABC):
    """
    Abstract base class for password hashing algorithms.
    """

    @abstractmethod
    def hash(self, password: str) -> str:
        """
        Hashes a plain text password.

        Args:
            password (str): The plain text password.

        Returns:
            str: The resulting hash.
        """

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool:
        """
        Verifies a plain text password against a hashed one.

        Args:
            password (str): The plain text password.
            hashed (str): The hash to check against.

        Returns:
            bool: True if they match, False otherwise.
        """


class WerkzeugPasswordHasher(PasswordHasher):
    """
    Default password hasher using Werkzeug's security utilities.
    """

    def hash(self, password: str) -> str:
        return generate_password_hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        return check_password_hash(hashed, password)
