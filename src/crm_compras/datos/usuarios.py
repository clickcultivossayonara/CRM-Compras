"""Usuarios para la sesión: un repositorio que la web consulta en cada petición."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select

from crm_compras.datos.conexion import BaseDatos
from crm_compras.datos.modelos import Usuario
from crm_compras.dominio.pedido import Rol


@dataclass(frozen=True)
class UsuarioSesion:
    id: int
    usuario: str
    nombre: str
    rol: Rol
    activo: bool
    hash_clave: str


class RepositorioUsuarios(Protocol):
    def por_usuario(self, usuario: str) -> UsuarioSesion | None: ...

    def por_id(self, usuario_id: int) -> UsuarioSesion | None: ...


def a_sesion(fila: Usuario) -> UsuarioSesion:
    return UsuarioSesion(
        id=fila.id,
        usuario=fila.usuario,
        nombre=fila.nombre,
        rol=Rol(fila.rol),
        activo=fila.activo,
        hash_clave=fila.hash_clave,
    )


class RepositorioUsuariosSQL:
    """Lee usuarios de la base propia."""

    def __init__(self, base: BaseDatos) -> None:
        self._base = base

    def por_usuario(self, usuario: str) -> UsuarioSesion | None:
        with self._base.sesion() as sesion:
            fila = sesion.scalars(select(Usuario).where(Usuario.usuario == usuario)).first()
            return a_sesion(fila) if fila else None

    def por_id(self, usuario_id: int) -> UsuarioSesion | None:
        with self._base.sesion() as sesion:
            fila = sesion.get(Usuario, usuario_id)
            return a_sesion(fila) if fila else None
