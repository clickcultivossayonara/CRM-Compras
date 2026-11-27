"""Aplica en la base propia lo que envía el sincronizador (R6.2, R6.3).

Artículos y centros: se insertan o actualizan, y lo que no llega queda inactivo (nunca se borra).
Precios: se reemplazan; un precio que no llega se retira. Cada envío queda en ``sincronizacion``.
"""

from collections.abc import Iterator, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import String, any_, bindparam, delete, not_, select, update
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import BindParameter

from crm_compras.contrato_sync import ArticuloSync, CentroSync, PrecioSync
from crm_compras.datos.modelos import Articulo, CentroCosto, Precio, Sincronizacion

TAMANO_LOTE = 1000


class PreciosSinArticulo(ValueError):  # noqa: N818 (se traduce a un 422)
    """Hay precios de artículos que no existen: primero se sincronizan los artículos."""

    def __init__(self, codigos: list[str]) -> None:
        super().__init__(
            "Precios de artículos que no existen (sincronice primero los artículos): "
            + ", ".join(codigos[:10])
        )
        self.codigos = codigos


def _lotes[T](filas: Sequence[T]) -> Iterator[Sequence[T]]:
    for inicio in range(0, len(filas), TAMANO_LOTE):
        yield filas[inicio : inicio + TAMANO_LOTE]


def _upsert(sesion: Session, modelo: Any, clave: str, filas: list[dict[str, object]]) -> None:
    for lote in _lotes(filas):
        sentencia = insert(modelo).values(list(lote))
        cambios = {c: sentencia.excluded[c] for c in lote[0] if c != clave}
        sesion.execute(sentencia.on_conflict_do_update(index_elements=[clave], set_=cambios))


def _registrar(sesion: Session, tipo: str, registros: int) -> None:
    sesion.add(Sincronizacion(tipo=tipo, registros=registros))


def _codigos(codigos: Sequence[str]) -> BindParameter[Sequence[str]]:
    """La lista como un solo parámetro de tipo arreglo (``= ANY(:codigos)``).

    Con ``IN (...)`` cada código sería un parámetro y un catálogo grande superaría el límite
    de PostgreSQL de 65.535 parámetros por consulta.
    """
    return bindparam("codigos", list(codigos), type_=ARRAY(String()))


def _sincronizar_catalogo(
    sesion: Session,
    modelo: type[Articulo] | type[CentroCosto],
    tipo: str,
    filas: Sequence[ArticuloSync] | Sequence[CentroSync],
    ahora: datetime,
) -> tuple[int, int]:
    """Inserta o actualiza lo recibido e inactiva lo que no llegó (R6.3: nunca se borra).

    Todo lo recibido queda con ``sincronizado_en = ahora``; lo que tenga una marca anterior y
    siga activo es lo que no llegó.
    """
    _upsert(sesion, modelo, "codigo", [{**f.model_dump(), "sincronizado_en": ahora} for f in filas])
    inactivados = sesion.scalars(
        update(modelo)
        .where(modelo.activo, modelo.sincronizado_en < ahora)
        .values(activo=False, sincronizado_en=ahora)
        .returning(modelo.codigo)
    ).all()
    _registrar(sesion, tipo, len(filas))
    return len(filas), len(inactivados)


def sincronizar_articulos(
    sesion: Session, articulos: Sequence[ArticuloSync], ahora: datetime
) -> tuple[int, int]:
    return _sincronizar_catalogo(sesion, Articulo, "articulos", articulos, ahora)


def sincronizar_centros(
    sesion: Session, centros: Sequence[CentroSync], ahora: datetime
) -> tuple[int, int]:
    return _sincronizar_catalogo(sesion, CentroCosto, "centros", centros, ahora)


def sincronizar_precios(sesion: Session, precios: Sequence[PrecioSync]) -> tuple[int, int]:
    """Reemplaza los precios: un precio que no llega se retira (el artículo no tiene compras)."""
    codigos = [p.articulo for p in precios]
    existentes = set(
        sesion.scalars(select(Articulo.codigo).where(Articulo.codigo == any_(_codigos(codigos))))
    )
    if faltan := sorted(set(codigos) - existentes):
        raise PreciosSinArticulo(faltan)
    _upsert(sesion, Precio, "articulo", [p.model_dump() for p in precios])
    retirados = sesion.scalars(
        delete(Precio)
        .where(not_(Precio.articulo == any_(_codigos(codigos))))
        .returning(Precio.articulo)
    ).all()
    _registrar(sesion, "precios", len(precios))
    return len(precios), len(retirados)
