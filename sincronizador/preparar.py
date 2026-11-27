"""Convierte filas de Softland al contrato de la API (``crm_compras.contrato_sync``).

Una fila que la API rechazaría (código mal formado, precio sin factor válido, artículo que no
está en el catálogo) se descarta y se reporta: si se enviara, la API rechazaría todo el envío.
"""

from collections.abc import Iterable, Mapping, Set
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ValidationError

from crm_compras.contrato_sync import ArticuloSync, CentroSync, PrecioSync
from crm_compras.dominio.precios import normalizar

LARGO_DESCRIPCION = 500
LARGO_ORDEN = 30

Fila = Mapping[str, Any]


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor).strip()


def _si(valor: object) -> bool:
    """Softland guarda los indicadores como 'S' o 'N'."""
    return _texto(valor).upper() == "S"


def _motivo(error: ValidationError) -> str:
    primero = error.errors()[0]
    campo = ".".join(str(parte) for parte in primero["loc"])
    return f"{campo}: {primero['msg']}"


def _validar[M: BaseModel](
    modelo: type[M], datos: dict[str, Any], etiqueta: str, descartes: list[str]
) -> M | None:
    try:
        return modelo.model_validate(datos)
    except ValidationError as error:
        descartes.append(f"{etiqueta}: {_motivo(error)}")
        return None


def preparar_articulos(filas: Iterable[Fila]) -> tuple[list[ArticuloSync], list[str]]:
    articulos: dict[str, ArticuloSync] = {}
    descartes: list[str] = []
    for fila in filas:
        codigo = _texto(fila.get("codigo"))
        datos = {
            "codigo": codigo,
            "descripcion": _texto(fila.get("descripcion"))[:LARGO_DESCRIPCION],
            "unidad": _texto(fila.get("unidad")).upper(),
            "activo": _si(fila.get("activo")),
        }
        if codigo in articulos:
            descartes.append(f"Artículo {codigo!r}: repetido")
        elif articulo := _validar(ArticuloSync, datos, f"Artículo {codigo!r}", descartes):
            articulos[codigo] = articulo
    return list(articulos.values()), descartes


def preparar_centros(filas: Iterable[Fila]) -> tuple[list[CentroSync], list[str]]:
    centros: dict[str, CentroSync] = {}
    descartes: list[str] = []
    for fila in filas:
        codigo = _texto(fila.get("codigo"))
        datos = {
            "codigo": codigo,
            "descripcion": _texto(fila.get("descripcion"))[:LARGO_DESCRIPCION],
            "activo": _si(fila.get("acepta_datos")),
        }
        if codigo in centros:
            descartes.append(f"Centro de costo {codigo!r}: repetido")
        elif centro := _validar(CentroSync, datos, f"Centro de costo {codigo!r}", descartes):
            centros[codigo] = centro
    return list(centros.values()), descartes


def _decimal(valor: object) -> Decimal | None:
    try:
        return Decimal(str(valor)) if valor is not None else None
    except InvalidOperation:
        return None


def _fecha(valor: object) -> object:
    return valor.date() if isinstance(valor, datetime) else valor


def preparar_precios(
    filas: Iterable[Fila], articulos: Set[str]
) -> tuple[list[PrecioSync], list[str]]:
    """Precio por unidad en pesos enteros (regla del 020215) de los artículos del catálogo."""
    precios: dict[str, PrecioSync] = {}
    descartes: list[str] = []
    for fila in filas:
        codigo = _texto(fila.get("articulo"))
        etiqueta = f"Precio de {codigo!r}"
        unitario = _decimal(fila.get("precio_unitario"))
        normalizado = (
            normalizar(codigo, unitario, _texto(fila.get("comentario")) or None)
            if unitario is not None and unitario.is_finite()
            else None
        )
        if codigo not in articulos:
            descartes.append(f"{etiqueta}: el artículo no está en el catálogo sincronizado")
        elif normalizado is None:
            descartes.append(f"{etiqueta}: precio o factor del comentario no válido")
        elif codigo in precios:
            descartes.append(f"{etiqueta}: repetido")
        else:
            datos = {
                "articulo": codigo,
                "precio_unitario": normalizado,
                "fecha_compra": _fecha(fila.get("fecha_compra")),
                "orden_compra": _texto(fila.get("orden_compra"))[:LARGO_ORDEN],
            }
            if precio := _validar(PrecioSync, datos, etiqueta, descartes):
                precios[codigo] = precio
    return list(precios.values()), descartes
