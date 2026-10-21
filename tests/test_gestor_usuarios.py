"""
Suite exhaustiva de pruebas unitarias para el subsistema de Gestión de Usuarios,
Autenticación y Sesiones de Análisis (modules.gestor_usuarios).

Cumple estrictamente con:
- Aislamiento absoluto (100% en memoria mediante mocks de almacenamiento virtual,
  sin tocar el disco duro).
- Exclusión total de UI y dependencias de Streamlit.
- Cobertura integral (>= 70%, buscando >= 95%):
  - SesionAnalisis (inicialización, actualización de metadatos, registro y normalización
    de comandos de historial, serialización to_dict).
  - Usuario (entidad, verificación criptográfica de contraseña mediante hasher Werkzeug).
  - GestorUsuarios (políticas de contraseña, registro con validaciones, hashing seguro,
    autenticación positiva/negativa, sanitización de directorios de usuario aislados,
    persistencia y carga desde almacenamiento virtual).
"""

import io
import json
import os
import pytest
from unittest import mock
from typing import Dict, Any

from modules.gestor_usuarios import (
    SesionAnalisis,
    Usuario,
    GestorUsuarios,
)
from auth_module.core.security.password import PasswordPolicy, PasswordPolicyConfig
from auth_module.core.security.rules import LengthPasswordRule


# =====================================================================
# Fixture de Aislamiento 100% en Memoria (Virtual File System)
# =====================================================================

@pytest.fixture
def virtual_fs():
    """
    Simula un sistema de archivos en memoria (RAM) para aislar por completo
    a GestorUsuarios del disco físico.
    """
    storage: Dict[str, str] = {}

    def mock_exists(path):
        # Normalizar separadores para compatibilidad
        p_norm = os.path.normpath(str(path))
        return p_norm in storage

    def mock_open_impl(file, mode="r", *args, **kwargs):
        p_norm = os.path.normpath(str(file))
        if "w" in mode:
            buf = io.StringIO()
            orig_close = buf.close
            def close_and_persist():
                storage[p_norm] = buf.getvalue()
                orig_close()
            buf.close = close_and_persist
            return buf
        elif "r" in mode:
            if p_norm not in storage:
                raise FileNotFoundError(f"Archivo inexistente: {file}")
            return io.StringIO(storage[p_norm])
        raise ValueError(f"Modo no soportado en mock: {mode}")

    with mock.patch("os.makedirs"), \
         mock.patch("os.path.exists", side_effect=mock_exists), \
         mock.patch("builtins.open", side_effect=mock_open_impl):
        yield storage


# =====================================================================
# 1. Pruebas para SesionAnalisis
# =====================================================================

class TestSesionAnalisis:
    """Pruebas de la entidad de sesión de analista, historial y serialización."""

    def test_inicializacion_por_defecto(self):
        sesion = SesionAnalisis()
        data = sesion.to_dict()
        assert data["ultima_actualizacion"] is None
        assert data["origen_datos"] is None
        assert data["variables_excluidas"] == []
        assert data["mapeo_columnas"] == {}
        assert data["configuracion_imputacion"] == {}
        assert data["historial_comandos"] == []

    def test_inicializacion_con_datos_preexistentes(self):
        data_inicial = {
            "ultima_actualizacion": "2026-10-21 10:00:00",
            "origen_datos": "datos.csv",
            "variables_excluidas": ["id"],
            "mapeo_columnas": {"precio": "tarifa"},
            "configuracion_imputacion": {},
            "historial_comandos": []
        }
        sesion = SesionAnalisis(data_inicial)
        assert sesion.to_dict() == data_inicial

    def test_actualizar_sesion(self):
        sesion = SesionAnalisis()
        sesion.actualizar(
            origen="vuelos_limpios.csv",
            excluidas=["col_irrelevante"],
            mapeo={"precio": "col_precio"},
            imputacion={"metodo": "mediana"}
        )
        data = sesion.to_dict()
        assert data["origen_datos"] == "vuelos_limpios.csv"
        assert data["variables_excluidas"] == ["col_irrelevante"]
        assert data["mapeo_columnas"] == {"precio": "col_precio"}
        assert data["configuracion_imputacion"] == {"metodo": "mediana"}
        assert data["ultima_actualizacion"] is not None

    def test_registrar_comando_accion_vacia_no_hace_nada(self):
        sesion = SesionAnalisis()
        sesion.registrar_comando("", {"param": 1})
        sesion.registrar_comando(None, {"param": 1})
        sesion.registrar_comando("   ", {"param": 1})
        assert len(sesion.data["historial_comandos"]) == 0

    def test_registrar_comando_normalizacion_de_archivo_por_defecto(self):
        """
        Si el parámetro de archivo es vacío, None, 'Archivo desconocido' o 'Dataset Activo',
        debe normalizarlo a 'dataset_vuelos.csv'.
        """
        sesion = SesionAnalisis()
        # Caso 1: Archivo desconocido
        sesion.registrar_comando("imputar", {"archivo": "Archivo desconocido"})
        assert sesion.data["historial_comandos"][0]["parametros"]["archivo"] == "dataset_vuelos.csv"
        assert sesion.data["historial_comandos"][0]["parametros"]["archivos"] == "dataset_vuelos.csv"

        # Caso 2: None / vacío
        sesion.registrar_comando("filtrar", {"archivo": None})
        assert sesion.data["historial_comandos"][1]["parametros"]["archivo"] == "dataset_vuelos.csv"

        # Caso 3: Archivo explícito válido
        sesion.registrar_comando("exportar", {"archivo": "  mi_dataset.csv  "})
        assert sesion.data["historial_comandos"][2]["parametros"]["archivo"] == "mi_dataset.csv"


# =====================================================================
# 2. Pruebas para Usuario
# =====================================================================

class TestUsuario:
    """Pruebas de la entidad Usuario y validación criptográfica de contraseña."""

    def test_creacion_usuario_y_verificacion_clave_correcta(self):
        from auth_module.core.security.hasher import WerkzeugPasswordHasher
        hasher = WerkzeugPasswordHasher()
        hash_pass = hasher.hash("clave_segura_123")

        usuario = Usuario(username="analista_vuelos", password_hash=hash_pass)
        assert usuario.username == "analista_vuelos"
        assert usuario.verificar_clave("clave_segura_123") is True
        assert usuario.verificar_clave("clave_equivocada") is False


# =====================================================================
# 3. Pruebas para GestorUsuarios
# =====================================================================

class TestGestorUsuarios:
    """Pruebas de registro, autenticación, políticas y directorios aislados."""

    def test_obtener_directorio_archivos_sanitizacion(self):
        # Usuario None o vacío -> 'general'
        dir_gen = GestorUsuarios.obtener_directorio_archivos(None)
        assert dir_gen.endswith("general")

        dir_vacio = GestorUsuarios.obtener_directorio_archivos("   ")
        assert dir_vacio.endswith("general")

        # Usuario con caracteres especiales peligrosos (ej. / .. *)
        dir_seguro = GestorUsuarios.obtener_directorio_archivos("user/../admin*")
        assert ".." not in dir_seguro
        assert "/" not in os.path.basename(dir_seguro)
        assert os.path.basename(dir_seguro) == "useradmin"

        # Usuario donde todos los caracteres son eliminados -> 'general'
        dir_todos_invalidos = GestorUsuarios.obtener_directorio_archivos("!@#$%^&*")
        assert dir_todos_invalidos.endswith("general")

    def test_registro_usuario_exitoso_y_autenticacion(self, virtual_fs):
        gestor = GestorUsuarios()
        usuario = gestor.registrar_usuario("marina", "contraseña_segura")

        assert usuario is not None
        assert usuario.username == "marina"
        assert gestor.existe_usuario("marina") is True

        # Autenticación exitosa
        u_aut = gestor.autenticar("marina", "contraseña_segura")
        assert u_aut is not None
        assert u_aut.username == "marina"

    def test_registro_usuario_nombre_o_clave_vacia_falla(self, virtual_fs):
        gestor = GestorUsuarios()
        with pytest.raises(ValueError, match="no pueden estar vacíos"):
            gestor.registrar_usuario("", "clave123")

        with pytest.raises(ValueError, match="no pueden estar vacíos"):
            gestor.registrar_usuario("usuario", "   ")

    def test_registro_usuario_duplicado_falla(self, virtual_fs):
        gestor = GestorUsuarios()
        gestor.registrar_usuario("carlos", "clave123")

        with pytest.raises(ValueError, match="ya se encuentra registrado"):
            gestor.registrar_usuario("carlos", "clave123")

    def test_registro_usuario_clave_no_cumple_politica_falla(self, virtual_fs):
        # Política por defecto exige al menos 6 caracteres
        gestor = GestorUsuarios()
        with pytest.raises(ValueError, match="al menos 6 caracteres"):
            gestor.registrar_usuario("pedro", "123")

    def test_inicializacion_con_politica_personalizada(self, virtual_fs):
        custom_config = PasswordPolicyConfig(
            rules=[LengthPasswordRule(value=10, message="Requiere {value} caracteres.")],
            msg_valid="OK"
        )
        custom_policy = PasswordPolicy(custom_config)
        gestor = GestorUsuarios(password_policy=custom_policy)

        # 8 caracteres falla con la política personalizada de 10
        with pytest.raises(ValueError, match="Requiere 10 caracteres"):
            gestor.registrar_usuario("lucas", "12345678")

    def test_autenticar_usuario_inexistente_o_clave_incorrecta(self, virtual_fs):
        gestor = GestorUsuarios()
        gestor.registrar_usuario("ana_analista", "claveValida123")

        # Usuario inexistente
        assert gestor.autenticar("fantasma", "claveValida123") is None

        # Clave incorrecta
        assert gestor.autenticar("ana_analista", "clave_erronea") is None

    def test_cargar_usuario_archivo_inexistente_retorna_none(self, virtual_fs):
        gestor = GestorUsuarios()
        assert gestor.cargar_usuario("nadie") is None

    def test_persistencia_y_restauracion_de_sesion(self, virtual_fs):
        """Verifica que el estado de la sesión se preserve íntegro tras guardar y cargar."""
        gestor = GestorUsuarios()
        user = gestor.registrar_usuario("laura", "password123")

        # Modificamos la sesión del usuario
        user.sesion.actualizar(
            origen="dataset_test.csv",
            excluidas=["temp_col"],
            mapeo={"id": "id_vuelo"},
            imputacion={"precio": "mediana"}
        )
        user.sesion.registrar_comando("imputar_mediana", {"archivo": "dataset_test.csv"})
        gestor.guardar_usuario(user)

        # Recargamos desde el almacenamiento virtual
        user_cargado = gestor.cargar_usuario("laura")
        assert user_cargado is not None
        assert user_cargado.username == "laura"
        sesion_dict = user_cargado.sesion.to_dict()
        assert sesion_dict["origen_datos"] == "dataset_test.csv"
        assert sesion_dict["variables_excluidas"] == ["temp_col"]
        assert len(sesion_dict["historial_comandos"]) == 1
        assert sesion_dict["historial_comandos"][0]["accion"] == "imputar_mediana"
