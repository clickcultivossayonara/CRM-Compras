"""Configuración común: marca cada prueba según su carpeta y entrega un cliente HTTP."""

import os
from collections.abc import Iterator
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from crm_compras.web.app import crear_app

_MARCAS = {
    "unitarias": "unitaria",
    "caja_negra": "caja_negra",
    "humo": "humo",
    "integracion": "integracion",
    "herramientas": "unitaria",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        carpeta = Path(str(item.fspath)).parent.name
        if carpeta in _MARCAS:
            item.add_marker(getattr(pytest.mark, _MARCAS[carpeta]))


@pytest.fixture
def cliente() -> Iterator[httpx2.Client]:
    """Cliente solo por HTTP. Con CRM_URL_BASE prueba un servidor real; si no, la app en memoria."""
    url_base = os.environ.get("CRM_URL_BASE")
    if url_base:
        with httpx2.Client(base_url=url_base, timeout=10) as c:
            yield c
    else:
        with TestClient(crear_app()) as c:
            yield c
