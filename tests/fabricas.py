"""Fábricas de datos ficticios compartidas por las pruebas."""

import secrets
from datetime import datetime

from crm_compras.datos.usuarios import UsuarioSesion
from crm_compras.dominio.pedido import Rol
from crm_compras.web.seguridad import cifrar_clave

ANCHO_COMPLETO = 0xFF10
ARABIGOS = 0x0660


def otros_digitos(texto: str, cero: int) -> str:
    """Cambia los dígitos ASCII por los de otro alfabeto, a partir del código de su cero."""
    return "".join(chr(cero + int(c)) if c.isdigit() else c for c in texto)


def clave_aleatoria() -> str:
    """Contraseña ficticia nueva en cada corrida: nunca se escribe una clave en el código."""
    return secrets.token_urlsafe(16)


def usuario(
    usuario_id: int, rol: Rol, clave: str, *, activo: bool = True, nombre: str = ""
) -> UsuarioSesion:
    return UsuarioSesion(
        id=usuario_id,
        usuario=f"{rol.value}.{usuario_id}",
        nombre=nombre or f"Usuario Ficticio {usuario_id}",
        rol=rol,
        activo=activo,
        hash_clave=cifrar_clave(clave),
    )


class RepositorioUsuariosMemoria:
    """Doble de prueba del repositorio de usuarios."""

    def __init__(self, usuarios: list[UsuarioSesion]) -> None:
        self.usuarios = {u.id: u for u in usuarios}

    def por_usuario(self, nombre_usuario: str) -> UsuarioSesion | None:
        return next((u for u in self.usuarios.values() if u.usuario == nombre_usuario), None)

    def por_id(self, usuario_id: int) -> UsuarioSesion | None:
        return self.usuarios.get(usuario_id)


class RepositorioSincronizacionMemoria:
    """Doble de prueba del registro de sincronizaciones."""

    def __init__(self, ultimas: dict[str, datetime] | None = None) -> None:
        self.ultimas_registradas = ultimas or {}

    def ultimas(self) -> dict[str, datetime]:
        return dict(self.ultimas_registradas)
