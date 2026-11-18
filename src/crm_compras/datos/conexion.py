"""Conexión a la base propia. El URL viene siempre de variables de entorno."""

import os

VARIABLE_URL = "DATABASE_URL"
_ESQUEMAS_POSTGRES = ("postgresql://", "postgres://")


def url_sqlalchemy(url: str) -> str:
    """Convierte ``postgresql://`` al dialecto de SQLAlchemy con el driver psycopg 3."""
    for esquema in _ESQUEMAS_POSTGRES:
        if url.startswith(esquema):
            return "postgresql+psycopg://" + url.removeprefix(esquema)
    return url


def url_desde_entorno() -> str:
    url = os.environ.get(VARIABLE_URL)
    if not url:
        raise RuntimeError(f"Falta la variable de entorno {VARIABLE_URL}.")
    return url_sqlalchemy(url)
