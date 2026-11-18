"""T2.3s · S1: matriz de autorización ruta x rol (R2.5, R6.1).

La matriz es la fuente de verdad de los permisos. Toda ruta nueva debe agregarse aquí: si no,
la primera prueba falla. Cada ruta con sesión se prueba con cada rol y sin sesión.
"""

import secrets

import httpx2
import pytest
from fastapi.routing import APIRoute
from starlette.routing import Route

from crm_compras.dominio.pedido import Rol
from crm_compras.web.app import crear_app
from crm_compras.web.configuracion import Configuracion
from tests.conftest import Entrar
from tests.fabricas import RepositorioUsuariosMemoria

pytestmark = pytest.mark.autorizacion

TODOS = frozenset(Rol)

# Rutas sin sesión: la API de salud, la documentación, el login y el cierre de sesión.
PUBLICAS = {
    ("GET", "/salud"),
    ("GET", "/login"),
    ("POST", "/login"),
    ("POST", "/salir"),
    ("GET", "/openapi.json"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
}

# Rutas con sesión y los roles que pueden usarlas.
MATRIZ: dict[tuple[str, str], frozenset[Rol]] = {
    ("GET", "/"): TODOS,
}


def rutas_de_la_app() -> set[tuple[str, str]]:
    """Rutas del esquema OpenAPI más las de documentación (que no salen en el esquema).

    Por eso ninguna ruta de la app puede usar ``include_in_schema=False``.
    """
    app = crear_app(
        Configuracion(clave_secreta=secrets.token_hex(32)), RepositorioUsuariosMemoria([])
    )
    rutas = {
        (metodo.upper(), ruta)
        for ruta, operaciones in app.openapi()["paths"].items()
        for metodo in operaciones
    }
    for ruta_doc in app.routes:
        if isinstance(ruta_doc, Route) and not isinstance(ruta_doc, APIRoute):
            rutas.update((m, ruta_doc.path) for m in ruta_doc.methods or () if m != "HEAD")
    return rutas


def test_toda_ruta_esta_en_la_matriz() -> None:
    sin_declarar = rutas_de_la_app() - PUBLICAS - set(MATRIZ)
    assert not sin_declarar, f"Rutas sin permisos declarados en S1: {sorted(sin_declarar)}"


def test_la_matriz_no_tiene_rutas_que_ya_no_existen() -> None:
    assert (PUBLICAS | set(MATRIZ)) <= rutas_de_la_app()


CASOS_GET = [
    (ruta, rol, rol in roles)
    for (metodo, ruta), roles in MATRIZ.items()
    if metodo == "GET"
    for rol in Rol
]


@pytest.mark.parametrize(("ruta", "rol", "permitido"), CASOS_GET)
def test_cada_rol_en_cada_ruta(
    cliente: httpx2.Client, entrar: Entrar, ruta: str, rol: Rol, permitido: bool
) -> None:
    entrar(cliente, rol.value)
    respuesta = cliente.get(ruta, follow_redirects=False)
    assert respuesta.status_code == (200 if permitido else 403)


@pytest.mark.parametrize("ruta", [ruta for metodo, ruta in MATRIZ if metodo == "GET"])
def test_sin_sesion_cada_ruta_redirige_al_login(cliente: httpx2.Client, ruta: str) -> None:
    respuesta = cliente.get(ruta, follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login"
