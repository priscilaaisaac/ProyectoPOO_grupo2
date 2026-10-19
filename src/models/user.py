from src.extensions import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    oauth_provider = db.Column(db.String(50), nullable=True)

    files = db.relationship('UserFile', backref='owner', lazy=True, cascade='all, delete-orphan')

    def to_dict(self) -> dict:
        return {
            'email': self.email,
            'password': self.password_hash,
            'verified': self.verified,
            'name': self.name,
            'oauth': self.oauth_provider
        }
