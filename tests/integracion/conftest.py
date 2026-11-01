"""Integración: requiere PostgreSQL real en TEST_DATABASE_URL; sin ella, las pruebas se saltan."""

import os
from collections.abc import Iterator

import psycopg
import pytest


@pytest.fixture
def conexion() -> Iterator[psycopg.Connection]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL no está definida")
    with psycopg.connect(url) as conn:
        yield conn
        conn.rollback()
