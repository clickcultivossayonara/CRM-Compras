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
from tests.conftest import Cuenta, Entrar, csrf_de
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

# Rutas del sincronizador: sin sesión ni CSRF, con el token SYNC_TOKEN.
CON_TOKEN = {
    ("POST", "/sync/articulos"),
    ("POST", "/sync/centros"),
    ("POST", "/sync/precios"),
}

ADMINISTRADOR = frozenset({Rol.ADMINISTRADOR})

# Rutas con sesión y los roles que pueden usarlas.
MATRIZ: dict[tuple[str, str], frozenset[Rol]] = {
    ("GET", "/"): TODOS,
    ("GET", "/admin/usuarios"): ADMINISTRADOR,
    ("POST", "/admin/usuarios"): ADMINISTRADOR,
    ("GET", "/admin/usuarios/{usuario_id}"): ADMINISTRADOR,
    ("POST", "/admin/usuarios/{usuario_id}"): ADMINISTRADOR,
    ("POST", "/admin/usuarios/{usuario_id}/clave"): ADMINISTRADOR,
    ("POST", "/admin/usuarios/{usuario_id}/asignaciones"): ADMINISTRADOR,
    ("GET", "/admin/unidades"): ADMINISTRADOR,
    ("POST", "/admin/unidades"): ADMINISTRADOR,
    ("POST", "/admin/unidades/{unidad}/quitar"): ADMINISTRADOR,
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
    sin_declarar = rutas_de_la_app() - PUBLICAS - CON_TOKEN - set(MATRIZ)
    assert not sin_declarar, f"Rutas sin permisos declarados en S1: {sorted(sin_declarar)}"


def test_la_matriz_no_tiene_rutas_que_ya_no_existen() -> None:
    assert (PUBLICAS | CON_TOKEN | set(MATRIZ)) <= rutas_de_la_app()


@pytest.mark.parametrize("ruta", sorted(ruta for _, ruta in CON_TOKEN))
def test_las_rutas_con_token_lo_exigen_aunque_haya_sesion(
    cliente: httpx2.Client, entrar: Entrar, ruta: str
) -> None:
    # La app en memoria no tiene SYNC_TOKEN: ni siquiera un administrador con sesión pasa.
    entrar(cliente, "administrador")
    token = csrf_de(cliente.get("/").text)
    respuesta = cliente.post(ruta, json={}, headers={"X-CSRF-Token": token})
    assert respuesta.status_code == 401


def concreta(ruta: str, cuentas: dict[str, Cuenta]) -> str:
    """Ruta con valores reales en sus parámetros: un usuario que existe y una unidad de la lista."""
    return ruta.format(usuario_id=cuentas["jefe"][0].id, unidad="KL")


CASOS_GET = [
    (ruta, rol, rol in roles)
    for (metodo, ruta), roles in MATRIZ.items()
    if metodo == "GET"
    for rol in Rol
]
CASOS_POST_PROHIBIDOS = [
    (ruta, rol)
    for (metodo, ruta), roles in MATRIZ.items()
    if metodo == "POST"
    for rol in Rol
    if rol not in roles
]


@pytest.mark.parametrize(("ruta", "rol", "permitido"), CASOS_GET)
def test_cada_rol_en_cada_ruta(
    cliente_bd: httpx2.Client,
    entrar_bd: Entrar,
    cuentas_bd: dict[str, Cuenta],
    ruta: str,
    rol: Rol,
    permitido: bool,
) -> None:
    entrar_bd(cliente_bd, rol.value)
    respuesta = cliente_bd.get(concreta(ruta, cuentas_bd), follow_redirects=False)
    assert respuesta.status_code == (200 if permitido else 403)


@pytest.mark.parametrize(("ruta", "rol"), CASOS_POST_PROHIBIDOS)
def test_un_rol_sin_permiso_no_cambia_nada_aunque_traiga_csrf(
    cliente_bd: httpx2.Client,
    entrar_bd: Entrar,
    cuentas_bd: dict[str, Cuenta],
    ruta: str,
    rol: Rol,
) -> None:
    entrar_bd(cliente_bd, rol.value)
    token = csrf_de(cliente_bd.get("/").text)
    respuesta = cliente_bd.post(
        concreta(ruta, cuentas_bd), data={"csrf_token": token}, follow_redirects=False
    )
    assert respuesta.status_code == 403


@pytest.mark.parametrize("ruta", [ruta for metodo, ruta in MATRIZ if metodo == "GET"])
def test_sin_sesion_cada_ruta_redirige_al_login(
    cliente_bd: httpx2.Client, cuentas_bd: dict[str, Cuenta], ruta: str
) -> None:
    respuesta = cliente_bd.get(concreta(ruta, cuentas_bd), follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login"


@pytest.mark.parametrize("ruta", [ruta for metodo, ruta in MATRIZ if metodo == "POST"])
def test_sin_sesion_ningun_post_pasa(
    cliente_bd: httpx2.Client, cuentas_bd: dict[str, Cuenta], ruta: str
) -> None:
    token = csrf_de(cliente_bd.get("/login").text)
    respuesta = cliente_bd.post(
        concreta(ruta, cuentas_bd), data={"csrf_token": token}, follow_redirects=False
    )
    assert respuesta.status_code in (303, 422)
    if respuesta.status_code == 303:
        assert respuesta.headers["location"] == "/login"
