# Documentación de Seguridad

El módulo `security/` gestiona todo lo relacionado con la fortaleza criptográfica y las reglas de contraseñas.

## 1. Hasheo de Contraseñas (`hasher.py`)
Para no acoplar el sistema a un algoritmo específico, se define la interfaz abstracta `PasswordHasher`.
El sistema incluye por defecto el `WerkzeugPasswordHasher`, que utiliza la librería de seguridad de Werkzeug (utilizada por Flask) para generar hashes en formato `scrypt` altamente seguros con salting automático.

## 2. Políticas de Contraseña (`password.py` y `rules/`)
El sistema de políticas utiliza validación dinámica (Chain of Responsibility).
La configuración `PasswordPolicyConfig` recibe una lista de **Reglas** que heredan de `PasswordRule`.

Reglas incluidas:
- `LengthPasswordRule`: Valida longitud mínima. Valor por defecto: 8 caracteres.
- `RegexPasswordRule`: Valida que la contraseña cumpla una expresión regular. Valor por defecto: None (no se aplica ninguna validación de expresiones regulares).

### Crear una Regla Personalizada
Puedes extender el sistema fácilmente creando tu propia regla:

```python
from auth_module.core.security.rules import PasswordRule

class NoEmailRule(PasswordRule):
    def validate(self, password: str) -> tuple[bool, str]:
        # Lógica de validación...
        return False, "La contraseña no puede ser igual al email."
```

Luego la inyectas en el `PasswordPolicyConfig(rules=[...])`.
