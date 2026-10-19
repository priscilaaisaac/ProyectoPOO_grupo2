from flask import Blueprint, render_template, session, redirect, url_for
from auth_module.flask_ext.decorators import login_required
from src.models.user import User
from src.models.user_file import UserFile

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('home.html', user_email=session.get('email'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Ruta protegida por @login_required.
    Garantiza aislamiento total: solo carga los archivos pertenecientes
    al usuario autenticado en la sesión actual.
    """
    current_email = session.get('email')
    user = User.query.filter_by(email=current_email).first()
    
    # Consulta filtrada por ID de usuario: el profesor u ot0ros usuarios
    # jamás verán archivos de compañeros.
    user_files = UserFile.query.filter_by(user_id=user.id).all() if user else []

    return render_template('dashboard.html', user=user, files=user_files)
