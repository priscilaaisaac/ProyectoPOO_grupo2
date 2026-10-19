# Security Documentation

The `security/` module manages everything related to cryptographic strength and password rules.

## 1. Password Hashing (`hasher.py`)
To avoid coupling the system to a specific algorithm, the abstract interface `PasswordHasher` is defined.
The system includes by default the `WerkzeugPasswordHasher`, which uses the Werkzeug security library (used by Flask) to generate highly secure `scrypt` hashes with automatic salting.

## 2. Password Policies (`password.py` and `rules/`)
The policy system uses dynamic validation (Chain of Responsibility).
The `PasswordPolicyConfig` receives a list of **Rules** that inherit from `PasswordRule`.

Included rules:
- `LengthPasswordRule`: Validates minimum length.
- `RegexPasswordRule`: Validates that the password meets a regular expression.

### Creating a Custom Rule
You can easily extend the system by creating your own rule:

```python
from auth_module.core.security.rules import PasswordRule

class NoEmailRule(PasswordRule):
    def validate(self, password: str) -> tuple[bool, str]:
        # Validation logic...
        return False, "Password cannot be the same as your email."
```

Then you inject it into the `PasswordPolicyConfig(rules=[...])`.
