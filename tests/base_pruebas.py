"""Utilidades para las pruebas que usan PostgreSQL real (TEST_DATABASE_URL)."""

import os
from pathlib import Path

import pytest
from alembic.config import Config

RAIZ = Path(__file__).resolve().parents[1]
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
