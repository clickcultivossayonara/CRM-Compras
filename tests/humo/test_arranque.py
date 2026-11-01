"""Humo: la aplicación arranca como proceso real y responde."""

import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import httpx2
import pytest


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def servidor() -> Iterator[str]:
    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "crm_compras.web.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(puerto),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{puerto}"
    try:
        limite = time.monotonic() + 15
        while time.monotonic() < limite:
            try:
                httpx2.get(f"{url}/salud", timeout=1)
                break
            except httpx2.TransportError:
                time.sleep(0.2)
        else:
            pytest.fail("La aplicación no arrancó en 15 segundos")
        yield url
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)


def test_la_aplicacion_arranca_y_responde_salud(servidor: str) -> None:
    respuesta = httpx2.get(f"{servidor}/salud", timeout=5)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}


def test_la_documentacion_de_la_api_carga(servidor: str) -> None:
    assert httpx2.get(f"{servidor}/openapi.json", timeout=5).status_code == 200
