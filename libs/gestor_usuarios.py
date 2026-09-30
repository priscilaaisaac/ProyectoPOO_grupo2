import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash


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

    def verificar_clave(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class GestorUsuarios:
    """Gestiona el almacenamiento físico y recuperación de usuarios y sesiones."""

    DIRECTORIO_USUARIOS = "data/usuarios"

    def __init__(self):
        os.makedirs(self.DIRECTORIO_USUARIOS, exist_ok=True)

    def _ruta_usuario(self, username: str) -> str:
        return os.path.join(self.DIRECTORIO_USUARIOS, f"{username}.json")

    def existe_usuario(self, username: str) -> bool:
        return os.path.exists(self._ruta_usuario(username))

    def registrar_usuario(self, username: str, password_plano: str) -> Optional[Usuario]:
        if not username.strip() or not password_plano.strip():
            raise ValueError("El nombre de usuario y la contraseña no pueden estar vacíos.")
        if self.existe_usuario(username):
            raise ValueError(f"El usuario '{username}' ya se encuentra registrado.")

        # Hash con werkzeug.security (base del módulo provisto)
        hashed_password = generate_password_hash(password_plano)
        usuario = Usuario(username, hashed_password)
        self.guardar_usuario(usuario)
        return usuario

    def autenticar(self, username: str, password_plano: str) -> Optional[Usuario]:
        if not self.existe_usuario(username):
            return None
        usuario = self.cargar_usuario(username)
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