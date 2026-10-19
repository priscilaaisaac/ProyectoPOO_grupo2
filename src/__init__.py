import os
import sys
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

# Asegurar que libs esté disponible para importaciones
raiz_proyecto = Path(__file__).resolve().parent.parent
ruta_libs = raiz_proyecto / "libs"
for ruta in (raiz_proyecto, ruta_libs):
    if str(ruta) not in sys.path:
        sys.path.append(str(ruta))

from src.extensions import db
from src.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from auth_module.core.auth_manager import AuthManager
from auth_module.core.mail.console_dispatcher import ConsoleMailDispatcher
from auth_module.flask_ext.extension import FlaskExtension

def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Configuración de base de datos y sesión
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'desarrollo_secret_key_poo_fiuner_2026')
    db_uri = os.getenv('DATABASE_URL')
    if not db_uri:
        # Fallback a SQLite local si no se definió PostgreSQL en el .env
        db_path = os.path.join(app.root_path, 'app_database.db')
        db_uri = f'sqlite:///{db_path}'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = os.getenv('SESSION_TYPE', 'filesystem')

    # Inicializar SQLAlchemy
    db.init_app(app)

    # Inicializar componentes del AuthModule Core
    user_repository = SQLAlchemyUserRepository()
    mail_dispatcher = ConsoleMailDispatcher()
    base_url = os.getenv('BASE_URL', 'http://localhost:5000/auth')

    auth_manager = AuthManager(
        mail_dispatcher=mail_dispatcher,
        user_repository=user_repository,
        base_url=base_url,
        secret_key=app.config['SECRET_KEY']
    )

    # Registrar la extensión de Flask configurando el dashboard como destino post-login
    FlaskExtension(app, auth_manager, login_redirect_endpoint='main.dashboard')

    # Registrar Blueprints de la aplicación
    from src.routes.main_routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
