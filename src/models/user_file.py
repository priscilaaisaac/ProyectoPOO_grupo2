from datetime import datetime
from src.extensions import db

class UserFile(db.Model):
    __tablename__ = 'user_files'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False, default='crudo')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aislamiento multi-usuario: vinculación estricta con el usuario propietario
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
