"""Configuración común: marca cada prueba según su carpeta y entrega un cliente HTTP."""

import os
import re
import secrets
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from crm_compras.datos.usuarios import UsuarioSesion
from crm_compras.dominio.pedido import Rol
from crm_compras.web.app import crear_app
from crm_compras.web.configuracion import Configuracion
from tests.fabricas import RepositorioUsuariosMemoria, clave_aleatoria, usuario

_MARCAS = {
    "unitarias": "unitaria",
    "caja_negra": "caja_negra",
    "humo": "humo",
    "integracion": "integracion",
    "herramientas": "unitaria",
}
INACTIVO = "inactivo"
_CSRF_EN_HTML = re.compile(r'name="csrf_token" value="([^"]+)"')

Cuenta = tuple[UsuarioSesion, str]
Entrar = Callable[[httpx2.Client, str], httpx2.Response]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        carpeta = Path(str(item.fspath)).parent.name
        if carpeta in _MARCAS:
            item.add_marker(getattr(pytest.mark, _MARCAS[carpeta]))


@pytest.fixture(scope="session")
def cuentas() -> dict[str, Cuenta]:
    """Un usuario ficticio por rol y uno inactivo, con claves nuevas en cada corrida."""
    resultado: dict[str, Cuenta] = {}
    for numero, rol in enumerate(Rol, start=1):
        clave = clave_aleatoria()
        resultado[rol.value] = (usuario(numero, rol, clave), clave)
    clave = clave_aleatoria()
    resultado[INACTIVO] = (usuario(99, Rol.JEFE, clave, activo=False), clave)
    return resultado


@pytest.fixture
def cliente(cuentas: dict[str, Cuenta]) -> Iterator[httpx2.Client]:
    """Cliente solo por HTTP. Con CRM_URL_BASE prueba un servidor real; si no, la app en memoria.

    En memoria se usa https para que la cookie Secure viaje igual que en producción.
    """
    url_base = os.environ.get("CRM_URL_BASE")
    if url_base:
        with httpx2.Client(base_url=url_base, timeout=10) as c:
            yield c
    else:
        app = crear_app(
            Configuracion(clave_secreta=secrets.token_hex(32)),
            RepositorioUsuariosMemoria([u for u, _ in cuentas.values()]),
        )
        with TestClient(app, base_url="https://testserver") as c:
            yield c


def csrf_de(html: str) -> str:
    encontrado = _CSRF_EN_HTML.search(html)
    assert encontrado, "La página no trae el token CSRF"
    return encontrado.group(1)


@pytest.fixture
def entrar(cuentas: dict[str, Cuenta]) -> Entrar:
    """Inicia sesión por HTTP con la cuenta ficticia de un rol (solo con la app en memoria)."""
    if os.environ.get("CRM_URL_BASE"):
        pytest.skip("Las cuentas ficticias solo existen en la app en memoria")

    def _entrar(cliente: httpx2.Client, cuenta: str) -> httpx2.Response:
        usuario_prueba, clave = cuentas[cuenta]
        token = csrf_de(cliente.get("/login").text)
        return cliente.post(
            "/login",
            data={"usuario": usuario_prueba.usuario, "clave": clave, "csrf_token": token},
            follow_redirects=False,
        )

    return _entrar
