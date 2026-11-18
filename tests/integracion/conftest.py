"""Integración: requiere PostgreSQL real en TEST_DATABASE_URL; sin ella, las pruebas se saltan.

Cada prueba trabaja en una transacción que se revierte al final, así no deja datos.
"""

from collections.abc import Iterator

import psycopg
import pytest
from alembic.config import Config

from tests.base_pruebas import SEGUNDOS_CONEXION, url_pruebas


@pytest.fixture
def conexion(alembic_pruebas: Config) -> Iterator[psycopg.Connection]:
    with psycopg.connect(url_pruebas(), connect_timeout=SEGUNDOS_CONEXION) as conn:
        yield conn
        conn.rollback()
