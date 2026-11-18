"""Integración: requiere PostgreSQL real en TEST_DATABASE_URL; sin ella, las pruebas se saltan.

La base de pruebas se lleva a cero y se migra una vez por sesión. Cada prueba trabaja en una
transacción que se revierte al final, así no deja datos.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config

RAIZ = Path(__file__).resolve().parents[2]
SEGUNDOS_CONEXION = 10


def url_pruebas() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL no está definida")
    return url


def configuracion_alembic(url: str) -> Config:
    configuracion = Config(toml_file=str(RAIZ / "pyproject.toml"))
    configuracion.attributes["url"] = url
    return configuracion


@pytest.fixture(scope="session")
def alembic_pruebas() -> Config:
    """Base de pruebas vacía y migrada a la última versión."""
    configuracion = configuracion_alembic(url_pruebas())
    command.downgrade(configuracion, "base")
    command.upgrade(configuracion, "head")
    return configuracion


@pytest.fixture
def conexion(alembic_pruebas: Config) -> Iterator[psycopg.Connection]:
    with psycopg.connect(url_pruebas(), connect_timeout=SEGUNDOS_CONEXION) as conn:
        yield conn
        conn.rollback()
