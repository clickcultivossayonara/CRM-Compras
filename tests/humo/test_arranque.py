"""Humo: la aplicación arranca como proceso real, responde y permite iniciar sesión.

El inicio de sesión necesita PostgreSQL (TEST_DATABASE_URL); sin ella, esa prueba se salta.
"""

import os
import re
import secrets
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import httpx2
import psycopg
import pytest
from alembic import command

from crm_compras.web.seguridad import cifrar_clave
from tests.fabricas import clave_aleatoria
from tests.integracion.conftest import SEGUNDOS_CONEXION, configuracion_alembic

USUARIO_HUMO = "humo.administrador"


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def clave_humo() -> str | None:
    """Con PostgreSQL, deja la base migrada con un administrador ficticio y devuelve su clave."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        return None
    command.upgrade(configuracion_alembic(url), "head")
    clave = clave_aleatoria()
    with psycopg.connect(url, connect_timeout=SEGUNDOS_CONEXION) as conexion:
        conexion.execute(
            "INSERT INTO usuario (usuario, nombre, hash_clave, rol) "
            "VALUES (%s, 'Administrador de humo', %s, 'administrador') "
            "ON CONFLICT (usuario) DO UPDATE SET hash_clave = EXCLUDED.hash_clave",
            (USUARIO_HUMO, cifrar_clave(clave)),
        )
    return clave


@pytest.fixture(scope="module")
def servidor(clave_humo: str | None) -> Iterator[str]:
    puerto = _puerto_libre()
    entorno = {
        **os.environ,
        "SECRET_KEY": secrets.token_hex(32),
        # Por HTTP en local: la cookie Secure no viajaría.
        "CRM_COOKIES_SEGURAS": "0",
    }
    if os.environ.get("TEST_DATABASE_URL"):
        entorno["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
    proceso = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--factory",
            "crm_compras.web.app:crear_app",
            "--host",
            "127.0.0.1",
            "--port",
            str(puerto),
        ],
        env=entorno,
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


def test_inicio_de_sesion(servidor: str, clave_humo: str | None) -> None:
    if clave_humo is None:
        pytest.skip("TEST_DATABASE_URL no está definida")
    with httpx2.Client(base_url=servidor, timeout=10, follow_redirects=True) as cliente:
        formulario = cliente.get("/login").text
        token = re.search(r'name="csrf_token" value="([^"]+)"', formulario)
        assert token
        respuesta = cliente.post(
            "/login",
            data={"usuario": USUARIO_HUMO, "clave": clave_humo, "csrf_token": token.group(1)},
        )
        assert respuesta.status_code == 200
        assert "Administrador de humo (administrador)" in respuesta.text
