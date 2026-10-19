"""
Password hashing, validation, and policy enforcement utilities.
"""

from dataclasses import dataclass, field
from typing import Any

from ..i18n import I18nManager
from .rules import LengthPasswordRule, PasswordRule, RegexPasswordRule


@dataclass
class PasswordPolicyConfig:
    """
    Configuration data structure for password strength requirements.
    Rules and their error messages are grouped together dynamically.
    """
    rules: list[PasswordRule] = field(default_factory=lambda: [LengthPasswordRule(), RegexPasswordRule()])
    msg_valid: str = 'password_valid'


class PasswordPolicy:
    """Configuration for password strength requirements using a customizable config."""

    def __init__(self, config: PasswordPolicyConfig | None = None) -> None:
        """
        Initializes the password policy with the given configuration.

        Args:
            config (PasswordPolicyConfig | None): Configuration and customized messages.
        """
        self.__config = config or PasswordPolicyConfig()

    def validate(self, password: str, i18n_manager: Any | None = None) -> tuple[bool, str]:
        """
        Validates a password against the defined policy.

        Args:
            password (str): The password to check.
            i18n_manager (Any | None): Internationalization manager.

        Returns:
            tuple[bool, str]: A boolean indicating success, and an error message if failed.
        """
        translator = i18n_manager
        if not translator:
            translator = I18nManager(locale='en')

        for rule in self.__config.rules:
            if not isinstance(rule, PasswordRule):
                raise TypeError(translator.translate('invalid_password_rule_type', type=type(rule).__name__))

            is_valid, msg = rule.validate(password)
            if not is_valid:
                # Pass all rule attributes dynamically as translation kwargs
                translated_msg = translator.translate(msg, **vars(rule))
                return False, translated_msg

        valid_msg = translator.translate(self.__config.msg_valid)
        return True, valid_msg


def is_password_valid(password: str, repassword: str) -> bool:
    """
    Checks if two passwords match.

    Args:
        password (str): The primary password.
        repassword (str): The confirmation password.

    Returns:
        bool: True if they match, False otherwise.
    """
    return password == repassword
