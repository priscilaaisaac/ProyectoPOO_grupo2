"""
Abstract repository definition for user storage.
"""

from abc import ABC, abstractmethod
from typing import Any


class UserRepository(ABC):
    """
    Abstract base class defining the contract for user storage operations.
    """

    @abstractmethod
    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Retrieves a user by their email address.

        Args:
            email (str): The user's email.

        Returns:
            dict[str, Any] | None: The user data if found, None otherwise.
        """

    @abstractmethod
    def create_user(self, email: str, password_hash: str | None, verified: bool, name: str | None = None, oauth_provider: str | None = None) -> None:
        """
        Creates a new user record.

        Args:
            email (str): The user's email.
            password_hash (str | None): The hashed password.
            verified (bool): Verification status.
            name (str | None): Optional user's name.
            oauth_provider (str | None): Optional OAuth provider name.
        """

    @abstractmethod
    def update_user_password(self, email: str, new_password_hash: str) -> None:
        """
        Updates a user's password.

        Args:
            email (str): The user's email.
            new_password_hash (str): The new hashed password.
        """

    @abstractmethod
    def update_user_verification(self, email: str, verified: bool) -> None:
        """
        Updates a user's verification status.

        Args:
            email (str): The user's email.
            verified (bool): The new verification status.
        """
