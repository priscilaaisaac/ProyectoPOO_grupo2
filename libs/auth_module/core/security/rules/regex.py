"""Regex constraint rule."""

import re
from dataclasses import dataclass

from .base import PasswordRule


@dataclass
class RegexPasswordRule(PasswordRule):
    """Validates that a password matches a regex pattern."""
    pattern: str | None = None
    message: str = 'password_regex_err'

    def validate(self, password: str) -> tuple[bool, str]:
        if self.pattern and not re.match(self.pattern, password):
            return False, self.message
        return True, ''
