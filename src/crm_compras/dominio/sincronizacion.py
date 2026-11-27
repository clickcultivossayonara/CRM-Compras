"""Frescura de los datos de Softland en la app (R6.5)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

TIPOS = ("articulos", "centros", "precios")
LIMITE = timedelta(hours=24)


@dataclass(frozen=True)
class EstadoSincronizacion:
    ultima: datetime | None
    """La más vieja entre las últimas de cada tipo; None si algún tipo nunca llegó."""
    atrasada: bool


def evaluar(ultimas: Mapping[str, datetime], ahora: datetime) -> EstadoSincronizacion:
    """Los datos valen lo que su parte más vieja: un precio viejo no se esconde tras un catálogo
    al día. Hay advertencia si algún tipo nunca llegó o si pasaron más de 24 horas."""
    if any(tipo not in ultimas for tipo in TIPOS):
        return EstadoSincronizacion(ultima=None, atrasada=True)
    ultima = min(ultimas[tipo] for tipo in TIPOS)
    return EstadoSincronizacion(ultima=ultima, atrasada=ahora - ultima > LIMITE)
