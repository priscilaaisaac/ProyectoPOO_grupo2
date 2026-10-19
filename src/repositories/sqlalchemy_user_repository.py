from typing import Any
from auth_module.core.db.repository import UserRepository
from src.extensions import db
from src.models.user import User

class SQLAlchemyUserRepository(UserRepository):
    """
    Implementación de UserRepository para bases de datos relacionales (PostgreSQL/SQLite)
    mediante Flask-SQLAlchemy, desacoplando la persistencia de la lógica de negocio.
    """

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        user = User.query.filter_by(email=email).first()
        return user.to_dict() if user else None

    def create_user(
        self,
        email: str,
        password_hash: str | None,
        verified: bool,
        name: str | None = None,
        oauth_provider: str | None = None
    ) -> None:
        user = User(
            email=email,
            password_hash=password_hash,
            verified=verified,
            name=name,
            oauth_provider=oauth_provider
        )
        db.session.add(user)
        db.session.commit()

    def update_user_password(self, email: str, new_password_hash: str) -> None:
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = new_password_hash
            db.session.commit()

    def update_user_verification(self, email: str, verified: bool) -> None:
        user = User.query.filter_by(email=email).first()
        if user:
            user.verified = verified
            db.session.commit()
