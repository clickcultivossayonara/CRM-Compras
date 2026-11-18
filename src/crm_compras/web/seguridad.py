"""Contraseñas con argon2, token CSRF y control de acceso por rol (R6.1, R2.5)."""

import secrets
from collections.abc import Callable

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, status

from crm_compras.datos.usuarios import RepositorioUsuarios, UsuarioSesion
from crm_compras.dominio.pedido import Rol

CAMPO_CSRF = "csrf_token"
ENCABEZADO_CSRF = "X-CSRF-Token"
CLAVE_SESION_USUARIO = "usuario_id"
CLAVE_SESION_CSRF = "csrf"
METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})

_cifrador = PasswordHasher()
# Hash de relleno: si el usuario no existe, se verifica contra él para no revelarlo por tiempo.
_HASH_DE_RELLENO = _cifrador.hash(secrets.token_hex(16))


def cifrar_clave(clave: str) -> str:
    return _cifrador.hash(clave)


def clave_valida(hash_clave: str, clave: str) -> bool:
    try:
        return _cifrador.verify(hash_clave, clave)
    except (VerificationError, InvalidHashError):
        return False


def autenticar(usuarios: RepositorioUsuarios, usuario: str, clave: str) -> UsuarioSesion | None:
    """Usuario activo con esa clave; si no, None, gastando el mismo tiempo en cualquier caso."""
    encontrado = usuarios.por_usuario(usuario)
    if encontrado is None:
        clave_valida(_HASH_DE_RELLENO, clave)
        return None
    if not clave_valida(encontrado.hash_clave, clave) or not encontrado.activo:
        return None
    return encontrado


def token_csrf(request: Request) -> str:
    """Token CSRF de la sesión; se crea si aún no existe."""
    token = request.session.get(CLAVE_SESION_CSRF)
    if not isinstance(token, str):
        token = secrets.token_urlsafe(32)
        request.session[CLAVE_SESION_CSRF] = token
    return token


def renovar_csrf(request: Request) -> str:
    request.session.pop(CLAVE_SESION_CSRF, None)
    return token_csrf(request)


async def verificar_csrf(request: Request) -> None:
    """Rechaza con 403 toda petición que cambia datos sin el token CSRF de la sesión."""
    if request.method in METODOS_SEGUROS:
        return
    esperado = request.session.get(CLAVE_SESION_CSRF)
    recibido = request.headers.get(ENCABEZADO_CSRF)
    if recibido is None:
        formulario = await request.form()
        valor = formulario.get(CAMPO_CSRF)
        recibido = valor if isinstance(valor, str) else None
    if not (isinstance(esperado, str) and recibido and secrets.compare_digest(esperado, recibido)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Falta el token CSRF o no es válido.")


class SinSesion(Exception):  # noqa: N818 (no es un error: la web redirige al login)
    """La petición necesita un usuario con sesión."""


def repositorio(request: Request) -> RepositorioUsuarios:
    usuarios: RepositorioUsuarios = request.app.state.usuarios
    return usuarios


def usuario_actual(request: Request) -> UsuarioSesion:
    """Usuario de la sesión, releído en cada petición: un cambio de rol o una baja aplican ya."""
    usuario_id = request.session.get(CLAVE_SESION_USUARIO)
    usuario = repositorio(request).por_id(usuario_id) if isinstance(usuario_id, int) else None
    if usuario is None or not usuario.activo:
        request.session.clear()
        raise SinSesion
    return usuario


def requiere_roles(*roles: Rol) -> Callable[[Request], UsuarioSesion]:
    """Dependencia de ruta: sin sesión redirige al login; con otro rol responde 403."""
    permitidos = frozenset(roles)

    def dependencia(request: Request) -> UsuarioSesion:
        usuario = usuario_actual(request)
        if usuario.rol not in permitidos:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Su rol no tiene acceso a esta página.")
        return usuario

    return dependencia
