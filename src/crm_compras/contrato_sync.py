"""Contrato entre el sincronizador local y la API (diseño §5, R6.2).

Lo usan los dos lados: la API para validar lo que recibe y el sincronizador para armar lo que
envía. Así una diferencia de formato se detecta en las pruebas de contrato (C1), no en producción.
"""

from collections import Counter
from collections.abc import Sequence
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

MAXIMO_REGISTROS = 100_000

CodigoArticulo = Annotated[str, Field(pattern=r"^[0-9]{6}$")]
CodigoCentro = Annotated[str, Field(pattern=r"^[0-9]{3}-[0-9]{2}-[0-9]$")]
Descripcion = Annotated[str, Field(min_length=1, max_length=500)]


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArticuloSync(_Estricto):
    codigo: CodigoArticulo
    descripcion: Descripcion
    unidad: Annotated[str, Field(min_length=1, max_length=10)]
    activo: StrictBool


class CentroSync(_Estricto):
    codigo: CodigoCentro
    descripcion: Descripcion
    activo: StrictBool


class PrecioSync(_Estricto):
    """Precio de última compra ya normalizado (regla del 020215), en pesos enteros (D2)."""

    articulo: CodigoArticulo
    precio_unitario: Annotated[StrictInt, Field(ge=0)]
    fecha_compra: date
    orden_compra: Annotated[str, Field(min_length=1, max_length=30)]


def _sin_repetidos(codigos: Sequence[str], que: str) -> None:
    repetidos = sorted(codigo for codigo, veces in Counter(codigos).items() if veces > 1)
    if repetidos:
        raise ValueError(f"{que} repetidos en el envío: {', '.join(repetidos[:10])}")


class EnvioArticulos(_Estricto):
    articulos: Annotated[list[ArticuloSync], Field(max_length=MAXIMO_REGISTROS)]

    @model_validator(mode="after")
    def _unicos(self) -> "EnvioArticulos":
        _sin_repetidos([a.codigo for a in self.articulos], "Artículos")
        return self


class EnvioCentros(_Estricto):
    centros: Annotated[list[CentroSync], Field(max_length=MAXIMO_REGISTROS)]

    @model_validator(mode="after")
    def _unicos(self) -> "EnvioCentros":
        _sin_repetidos([c.codigo for c in self.centros], "Centros de costo")
        return self


class EnvioPrecios(_Estricto):
    precios: Annotated[list[PrecioSync], Field(max_length=MAXIMO_REGISTROS)]

    @model_validator(mode="after")
    def _unicos(self) -> "EnvioPrecios":
        _sin_repetidos([p.articulo for p in self.precios], "Precios de artículos")
        return self


class RespuestaSync(BaseModel):
    recibidos: int
    inactivados: int
    """Artículos o centros marcados inactivos; en precios, los precios retirados."""
