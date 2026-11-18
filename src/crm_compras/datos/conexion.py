"""Conexión a la base propia. El URL viene siempre de variables de entorno."""

import os

from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.orm import Session

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


class BaseDatos:
    """Entrega sesiones de SQLAlchemy. El motor se crea al primer uso, no al importar.

    Con ``conexion`` todas las sesiones trabajan dentro de su transacción y sus ``commit`` son
    puntos de guardado: así las pruebas revierten todo al final, incluida la auditoría.
    """

    def __init__(self, url: str | None = None, conexion: Connection | None = None) -> None:
        self._url = url
        self._conexion = conexion
        self._motor: Engine | None = None

    def sesion(self) -> Session:
        if self._conexion is not None:
            return Session(bind=self._conexion, join_transaction_mode="create_savepoint")
        if self._motor is None:
            url = url_sqlalchemy(self._url) if self._url else url_desde_entorno()
            self._motor = create_engine(url, pool_pre_ping=True)
        return Session(self._motor)
