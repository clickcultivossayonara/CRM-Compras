"""Usuarios para la sesión: un repositorio que la web consulta en cada petición."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from crm_compras.datos.conexion import url_desde_entorno, url_sqlalchemy
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


def _a_sesion(fila: Usuario) -> UsuarioSesion:
    return UsuarioSesion(
        id=fila.id,
        usuario=fila.usuario,
        nombre=fila.nombre,
        rol=Rol(fila.rol),
        activo=fila.activo,
        hash_clave=fila.hash_clave,
    )


class RepositorioUsuariosSQL:
    """Lee usuarios de la base propia. El motor se crea al primer uso, no al importar."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url
        self._motor: Engine | None = None

    def _abrir(self) -> Session:
        if self._motor is None:
            url = url_sqlalchemy(self._url) if self._url else url_desde_entorno()
            self._motor = create_engine(url, pool_pre_ping=True)
        return Session(self._motor)

    def por_usuario(self, usuario: str) -> UsuarioSesion | None:
        with self._abrir() as sesion:
            fila = sesion.scalars(select(Usuario).where(Usuario.usuario == usuario)).first()
            return _a_sesion(fila) if fila else None

    def por_id(self, usuario_id: int) -> UsuarioSesion | None:
        with self._abrir() as sesion:
            fila = sesion.get(Usuario, usuario_id)
            return _a_sesion(fila) if fila else None
