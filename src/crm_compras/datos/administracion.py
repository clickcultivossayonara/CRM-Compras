"""Operaciones de administración sobre la base propia. Todo cambio queda en la auditoría (D19).

Las funciones reciben claves ya cifradas: la capa de datos nunca ve una contraseña en texto.
"""

from collections.abc import Collection

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from crm_compras.datos.auditoria import registrar
from crm_compras.datos.modelos import (
    CentroCosto,
    JefeCentro,
    JefePartida,
    Partida,
    UnidadDecimal,
    Usuario,
)
from crm_compras.dominio.pedido import Rol
from crm_compras.dominio.usuarios import (
    errores_autoedicion,
    errores_unidad,
    errores_usuario,
    normalizar_unidad,
    normalizar_usuario,
)

ENTIDAD_USUARIO = "usuario"


class AdministracionError(ValueError):
    """La operación no se hace; ``problemas`` dice por qué."""

    def __init__(self, problemas: list[str]) -> None:
        super().__init__(" ".join(problemas))
        self.problemas = problemas


class NoEncontrado(LookupError):  # noqa: N818 (se traduce a un 404)
    """El registro pedido no existe."""


def _datos_usuario(fila: Usuario) -> dict[str, object]:
    """Lo que se audita de un usuario: nunca el hash de la clave."""
    return {"usuario": fila.usuario, "nombre": fila.nombre, "rol": fila.rol, "activo": fila.activo}


def _exigir(errores: list[str]) -> None:
    if errores:
        raise AdministracionError(errores)


def listar_usuarios(sesion: Session) -> list[Usuario]:
    return list(sesion.scalars(select(Usuario).order_by(Usuario.usuario)))


def obtener_usuario(sesion: Session, usuario_id: int) -> Usuario:
    fila = sesion.get(Usuario, usuario_id)
    if fila is None:
        raise NoEncontrado(f"No existe el usuario {usuario_id}.")
    return fila


def crear_usuario(
    sesion: Session, editor_id: int | None, usuario: str, nombre: str, rol: str, hash_clave: str
) -> Usuario:
    usuario = normalizar_usuario(usuario)
    _exigir(errores_usuario(usuario, nombre, rol))
    if sesion.scalars(select(Usuario).where(Usuario.usuario == usuario)).first():
        raise AdministracionError([f"El usuario {usuario} ya existe."])
    fila = Usuario(usuario=usuario, nombre=nombre.strip(), rol=rol, hash_clave=hash_clave)
    sesion.add(fila)
    sesion.flush()
    registrar(
        sesion,
        usuario_id=editor_id,
        entidad=ENTIDAD_USUARIO,
        entidad_id=fila.id,
        accion="crear",
        despues=_datos_usuario(fila),
    )
    return fila


def actualizar_usuario(
    sesion: Session, editor_id: int, usuario_id: int, nombre: str, rol: str, activo: bool
) -> Usuario:
    fila = obtener_usuario(sesion, usuario_id)
    errores = errores_usuario(fila.usuario, nombre, rol)
    if not errores:
        errores = errores_autoedicion(editor_id, usuario_id, Rol(rol), activo)
    _exigir(errores)
    antes = _datos_usuario(fila)
    fila.nombre, fila.rol, fila.activo = nombre.strip(), rol, activo
    despues = _datos_usuario(fila)
    if despues != antes:
        registrar(
            sesion,
            usuario_id=editor_id,
            entidad=ENTIDAD_USUARIO,
            entidad_id=usuario_id,
            accion="actualizar",
            antes=antes,
            despues=despues,
        )
    return fila


def cambiar_clave(sesion: Session, editor_id: int, usuario_id: int, hash_clave: str) -> None:
    fila = obtener_usuario(sesion, usuario_id)
    fila.hash_clave = hash_clave
    registrar(
        sesion,
        usuario_id=editor_id,
        entidad=ENTIDAD_USUARIO,
        entidad_id=usuario_id,
        accion="cambiar_clave",
    )


def listar_partidas(sesion: Session) -> list[Partida]:
    return list(sesion.scalars(select(Partida).order_by(Partida.anio, Partida.rubro, Partida.area)))


def listar_centros(sesion: Session) -> list[CentroCosto]:
    return list(sesion.scalars(select(CentroCosto).order_by(CentroCosto.codigo)))


def asignaciones(sesion: Session, usuario_id: int) -> tuple[set[int], set[str]]:
    """Partidas y centros de costo asignados a un usuario."""
    partidas = sesion.scalars(
        select(JefePartida.partida_id).where(JefePartida.usuario_id == usuario_id)
    )
    centros = sesion.scalars(
        select(JefeCentro.centro_codigo).where(JefeCentro.usuario_id == usuario_id)
    )
    return set(partidas), set(centros)


def asignar(
    sesion: Session,
    editor_id: int,
    usuario_id: int,
    partidas: Collection[int],
    centros: Collection[str],
) -> None:
    """Reemplaza las partidas y los centros de costo de un jefe (R1.10)."""
    fila = obtener_usuario(sesion, usuario_id)
    errores = []
    if fila.rol != Rol.JEFE.value and (partidas or centros):
        errores.append("Solo a un jefe se le asignan partidas y centros de costo.")
    existentes = set(sesion.scalars(select(Partida.id).where(Partida.id.in_(partidas))))
    if faltan := set(partidas) - existentes:
        errores.append(f"No existen las partidas {sorted(faltan)}.")
    centros_existentes = set(
        sesion.scalars(select(CentroCosto.codigo).where(CentroCosto.codigo.in_(centros)))
    )
    if faltan_centros := set(centros) - centros_existentes:
        errores.append(f"No existen los centros de costo {sorted(faltan_centros)}.")
    _exigir(errores)

    antes_partidas, antes_centros = asignaciones(sesion, usuario_id)
    if (antes_partidas, antes_centros) == (set(partidas), set(centros)):
        return
    sesion.execute(delete(JefePartida).where(JefePartida.usuario_id == usuario_id))
    sesion.execute(delete(JefeCentro).where(JefeCentro.usuario_id == usuario_id))
    sesion.add_all(JefePartida(usuario_id=usuario_id, partida_id=p) for p in set(partidas))
    sesion.add_all(JefeCentro(usuario_id=usuario_id, centro_codigo=c) for c in set(centros))
    registrar(
        sesion,
        usuario_id=editor_id,
        entidad=ENTIDAD_USUARIO,
        entidad_id=usuario_id,
        accion="asignar",
        antes={"partidas": sorted(antes_partidas), "centros": sorted(antes_centros)},
        despues={"partidas": sorted(set(partidas)), "centros": sorted(set(centros))},
    )


def listar_unidades(sesion: Session) -> list[str]:
    return list(sesion.scalars(select(UnidadDecimal.unidad).order_by(UnidadDecimal.unidad)))


def agregar_unidad(sesion: Session, editor_id: int, unidad: str) -> str:
    unidad = normalizar_unidad(unidad)
    _exigir(errores_unidad(unidad))
    if sesion.get(UnidadDecimal, unidad):
        raise AdministracionError([f"La unidad {unidad} ya admite decimales."])
    sesion.add(UnidadDecimal(unidad=unidad))
    registrar(
        sesion,
        usuario_id=editor_id,
        entidad="unidad_decimal",
        entidad_id=unidad,
        accion="agregar",
        despues={"unidad": unidad},
    )
    return unidad


def quitar_unidad(sesion: Session, editor_id: int, unidad: str) -> None:
    fila = sesion.get(UnidadDecimal, normalizar_unidad(unidad))
    if fila is None:
        raise NoEncontrado(f"La unidad {unidad} no está en la lista.")
    sesion.delete(fila)
    registrar(
        sesion,
        usuario_id=editor_id,
        entidad="unidad_decimal",
        entidad_id=fila.unidad,
        accion="quitar",
        antes={"unidad": fila.unidad},
    )
