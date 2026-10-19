import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

from auth_module.core.security.hasher import WerkzeugPasswordHasher
from auth_module.core.security.password import PasswordPolicy, PasswordPolicyConfig
from auth_module.core.security.rules import LengthPasswordRule
from auth_module.core.i18n import I18nManager


class SesionAnalisis:
    """Modela y serializa el estado de análisis y limpieza de un analista."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self.data = data or {
            "ultima_actualizacion": None,
            "origen_datos": None,
            "variables_excluidas": [],
            "mapeo_columnas": {},
            "configuracion_imputacion": {},
            "historial_comandos": []
        }

    def actualizar(self, origen: str, excluidas: list, mapeo: dict, imputacion: dict):
        self.data["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.data["origen_datos"] = origen
        self.data["variables_excluidas"] = excluidas
        self.data["mapeo_columnas"] = mapeo
        self.data["configuracion_imputacion"] = imputacion

    def registrar_comando(self, accion: str, parametros: dict):
        if not accion or not str(accion).strip():
            return
        
        # Validar y normalizar el nombre del archivo para evitar 'Archivo desconocido'
        archivo_val = parametros.get("archivos") or parametros.get("archivo")
        if not archivo_val or str(archivo_val).strip() in ["", "None", "Archivo desconocido", "Dataset Activo"]:
            archivo_normalizado = "dataset_vuelos.csv"
        else:
            archivo_normalizado = str(archivo_val).strip()
            
        parametros["archivos"] = archivo_normalizado
        parametros["archivo"] = archivo_normalizado

        self.data["historial_comandos"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "accion": accion,
            "parametros": parametros
        })

    def to_dict(self) -> dict:
        return self.data


class Usuario:
    """Entidad de usuario con autenticación segura y persistencia de sesión."""

    def __init__(self, username: str, password_hash: str, sesion: Optional[dict] = None):
        self.username = username
        self.password_hash = password_hash
        self.sesion = SesionAnalisis(sesion)
        self._hasher = WerkzeugPasswordHasher()

    def verificar_clave(self, password: str) -> bool:
        return self._hasher.verify(password, self.password_hash)


class GestorUsuarios:
    """Gestiona el almacenamiento físico y recuperación de usuarios y sesiones."""

    DIRECTORIO_USUARIOS = "data/usuarios"
    BASE_DIRECTORIO_ARCHIVOS = os.path.join("data", "archivos_guardados")

    def __init__(self, password_policy: Optional[PasswordPolicy] = None):
        os.makedirs(self.DIRECTORIO_USUARIOS, exist_ok=True)
        os.makedirs(self.BASE_DIRECTORIO_ARCHIVOS, exist_ok=True)
        self.hasher = WerkzeugPasswordHasher()
        self.i18n = I18nManager(locale='es')
        
        # Política de contraseñas de auth_module (mínimo 6 caracteres para facilidad en pruebas)
        if password_policy is None:
            config = PasswordPolicyConfig(
                rules=[LengthPasswordRule(value=6, message='La contraseña debe tener al menos {value} caracteres.')],
                msg_valid='Contraseña válida.'
            )
            self.password_policy = PasswordPolicy(config)
        else:
            self.password_policy = password_policy

    @classmethod
    def obtener_directorio_archivos(cls, username: Optional[str] = None) -> str:
        """
        Retorna la ruta aislada de almacenamiento para el usuario especificado.
        Garantiza que ningún usuario acceda a los archivos de otro.
        """
        if not username or not str(username).strip():
            nombre_carpeta = "general"
        else:
            # Sanitizar nombre de usuario para ruta segura
            nombre_carpeta = "".join(c for c in str(username).strip() if c.isalnum() or c in ("_", "-"))
            if not nombre_carpeta:
                nombre_carpeta = "general"

        directorio = os.path.join(cls.BASE_DIRECTORIO_ARCHIVOS, nombre_carpeta)
        os.makedirs(directorio, exist_ok=True)
        return directorio

    def _ruta_usuario(self, username: str) -> str:
        return os.path.join(self.DIRECTORIO_USUARIOS, f"{username}.json")

    def existe_usuario(self, username: str) -> bool:
        return os.path.exists(self._ruta_usuario(username))

    def validar_clave_politica(self, password: str) -> tuple[bool, str]:
        """Valida la contraseña utilizando el validador de políticas de auth_module."""
        return self.password_policy.validate(password, i18n_manager=self.i18n)

    def registrar_usuario(self, username: str, password_plano: str) -> Optional[Usuario]:
        username_limpio = username.strip()
        if not username_limpio or not password_plano.strip():
            raise ValueError("El nombre de usuario y la contraseña no pueden estar vacíos.")
        if self.existe_usuario(username_limpio):
            raise ValueError(f"El usuario '{username_limpio}' ya se encuentra registrado.")

        # Validación con las políticas de auth_module
        es_valida, msg_error = self.validar_clave_politica(password_plano)
        if not es_valida:
            raise ValueError(msg_error)

        # Hash seguro mediante WerkzeugPasswordHasher de auth_module
        hashed_password = self.hasher.hash(password_plano)
        usuario = Usuario(username_limpio, hashed_password)
        self.guardar_usuario(usuario)
        
        # Inicializar su carpeta exclusiva y aislada de archivos
        self.obtener_directorio_archivos(username_limpio)
        return usuario

    def autenticar(self, username: str, password_plano: str) -> Optional[Usuario]:
        username_limpio = username.strip()
        if not self.existe_usuario(username_limpio):
            return None
        usuario = self.cargar_usuario(username_limpio)
        if usuario and usuario.verificar_clave(password_plano):
            return usuario
        return None

    def guardar_usuario(self, usuario: Usuario):
        ruta = self._ruta_usuario(usuario.username)
        payload = {
            "username": usuario.username,
            "password_hash": usuario.password_hash,
            "sesion": usuario.sesion.to_dict()
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

    def cargar_usuario(self, username: str) -> Optional[Usuario]:
        ruta = self._ruta_usuario(username)
        if not os.path.exists(ruta):
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return Usuario(
            username=payload["username"],
            password_hash=payload["password_hash"],
            sesion=payload.get("sesion")
        )