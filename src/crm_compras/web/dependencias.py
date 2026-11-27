"""Dependencias compartidas por las rutas web."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session


def sesion_bd(request: Request) -> Iterator[Session]:
    """Sesión de la base propia para una petición; cada ruta decide cuándo hace commit."""
    with request.app.state.base.sesion() as sesion:
        yield sesion


SesionBD = Annotated[Session, Depends(sesion_bd)]
