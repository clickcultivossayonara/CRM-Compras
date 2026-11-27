"""T2.3 · Caja negra del inicio y cierre de sesión (R6.1). Plan de pruebas §3.8."""

import base64
import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx2
import pytest
from fastapi.testclient import TestClient

from crm_compras.datos.usuarios import UsuarioSesion
from tests.conftest import INACTIVO, Cuenta, Entrar, csrf_de
from tests.fabricas import RepositorioSincronizacionMemoria, RepositorioUsuariosMemoria

MENSAJE_FALLIDO = "Usuario o contraseña incorrectos."


def formulario(cliente: httpx2.Client, usuario: str, clave: str, csrf: str) -> httpx2.Response:
    return cliente.post(
        "/login",
        data={"usuario": usuario, "clave": clave, "csrf_token": csrf},
        follow_redirects=False,
    )


def test_pagina_de_login(cliente: httpx2.Client) -> None:
    respuesta = cliente.get("/login")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert 'type="password"' in respuesta.text
    assert csrf_de(respuesta.text)


def test_ingreso_correcto_crea_la_sesion(
    cliente: httpx2.Client, entrar: Entrar, cuentas: dict[str, Cuenta]
) -> None:
    respuesta = entrar(cliente, "jefe")
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/"
    cookie = respuesta.headers["set-cookie"].lower()
    assert cookie.startswith("crm_sesion=")
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie

    inicio = cliente.get("/")
    assert inicio.status_code == 200
    assert cuentas["jefe"][0].nombre in inicio.text
    assert "(jefe)" in inicio.text


@pytest.mark.parametrize(
    ("cuenta", "usuario_distinto", "clave_distinta"),
    [
        ("jefe", None, "clave-equivocada"),
        ("jefe", "no.existe", None),
        (INACTIVO, None, None),
    ],
)
def test_ingreso_fallido_no_revela_el_motivo(
    cliente: httpx2.Client,
    cuentas: dict[str, Cuenta],
    cuenta: str,
    usuario_distinto: str | None,
    clave_distinta: str | None,
) -> None:
    usuario_prueba, clave = cuentas[cuenta]
    csrf = csrf_de(cliente.get("/login").text)
    respuesta = formulario(
        cliente, usuario_distinto or usuario_prueba.usuario, clave_distinta or clave, csrf
    )
    assert respuesta.status_code == 401
    assert MENSAJE_FALLIDO in respuesta.text
    assert cliente.get("/", follow_redirects=False).status_code == 303


@pytest.mark.parametrize("csrf", [None, "", "token-inventado"])
def test_login_sin_token_csrf_valido(
    cliente: httpx2.Client, cuentas: dict[str, Cuenta], csrf: str | None
) -> None:
    usuario_prueba, clave = cuentas["jefe"]
    cliente.get("/login")
    datos = {"usuario": usuario_prueba.usuario, "clave": clave}
    if csrf is not None:
        datos["csrf_token"] = csrf
    assert cliente.post("/login", data=datos, follow_redirects=False).status_code == 403


def test_login_con_el_token_en_el_encabezado(
    cliente: httpx2.Client, cuentas: dict[str, Cuenta]
) -> None:
    usuario_prueba, clave = cuentas["jefe"]
    csrf = csrf_de(cliente.get("/login").text)
    respuesta = cliente.post(
        "/login",
        data={"usuario": usuario_prueba.usuario, "clave": clave},
        headers={"X-CSRF-Token": csrf},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def test_el_token_csrf_cambia_al_ingresar(cliente: httpx2.Client, entrar: Entrar) -> None:
    antes = csrf_de(cliente.get("/login").text)
    entrar(cliente, "jefe")
    assert csrf_de(cliente.get("/").text) != antes


def test_campos_demasiado_largos(cliente: httpx2.Client) -> None:
    csrf = csrf_de(cliente.get("/login").text)
    assert formulario(cliente, "u" * 129, "x", csrf).status_code == 422


def test_salir_cierra_la_sesion(cliente: httpx2.Client, entrar: Entrar) -> None:
    entrar(cliente, "comprador")
    csrf = csrf_de(cliente.get("/").text)
    respuesta = cliente.post("/salir", data={"csrf_token": csrf}, follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login"
    assert cliente.get("/", follow_redirects=False).status_code == 303


def test_salir_sin_token_csrf(cliente: httpx2.Client, entrar: Entrar) -> None:
    entrar(cliente, "comprador")
    assert cliente.post("/salir", follow_redirects=False).status_code == 403
    assert cliente.get("/").status_code == 200


def test_sin_sesion_redirige_al_login(cliente: httpx2.Client) -> None:
    respuesta = cliente.get("/", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login"


def test_cookie_alterada_no_da_sesion(cliente: httpx2.Client, entrar: Entrar) -> None:
    # Se cambia el usuario de la cookie real sin poder rehacer su firma.
    entrar(cliente, "jefe")
    contenido, *firma = cliente.cookies["crm_sesion"].split(".")
    otro_usuario = base64.b64encode(json.dumps({"usuario_id": 4}).encode()).decode()
    assert otro_usuario != contenido
    cliente.cookies.clear()
    cliente.cookies.set("crm_sesion", ".".join([otro_usuario, *firma]))
    assert cliente.get("/", follow_redirects=False).status_code == 303


def test_un_usuario_desactivado_pierde_la_sesion_de_inmediato(
    cliente: httpx2.Client, entrar: Entrar, cuentas: dict[str, Cuenta]
) -> None:
    if not isinstance(cliente, TestClient):
        pytest.skip("Requiere la app en memoria para desactivar al usuario")
    entrar(cliente, "jefe")
    repositorio: RepositorioUsuariosMemoria = cliente.app.state.usuarios  # type: ignore[attr-defined]
    jefe = cuentas["jefe"][0]
    repositorio.usuarios[jefe.id] = UsuarioSesion(
        jefe.id, jefe.usuario, jefe.nombre, jefe.rol, False, jefe.hash_clave
    )
    assert cliente.get("/", follow_redirects=False).status_code == 303


AVISO = "tienen más de 24 horas sin actualizarse"


def test_inicio_muestra_la_ultima_sincronizacion_en_hora_de_bogota(
    cliente: httpx2.Client, entrar: Entrar, sincronizaciones: RepositorioSincronizacionMemoria
) -> None:
    hace_una_hora = datetime.now(UTC) - timedelta(hours=1)
    sincronizaciones.ultimas_registradas = dict.fromkeys(
        ("articulos", "centros", "precios"), hace_una_hora
    )
    entrar(cliente, "jefe")
    pagina = cliente.get("/").text
    local = hace_una_hora.astimezone(ZoneInfo("America/Bogota")).strftime("%d/%m/%Y %H:%M")
    assert f"Última sincronización con Softland: {local}." in pagina
    assert AVISO not in pagina


def test_inicio_avisa_si_la_sincronizacion_esta_atrasada(
    cliente: httpx2.Client, entrar: Entrar, sincronizaciones: RepositorioSincronizacionMemoria
) -> None:
    sincronizaciones.ultimas_registradas = dict.fromkeys(
        ("articulos", "centros", "precios"), datetime.now(UTC) - timedelta(days=2)
    )
    entrar(cliente, "comprador")
    assert AVISO in cliente.get("/").text


def test_inicio_sin_ninguna_sincronizacion(cliente: httpx2.Client, entrar: Entrar) -> None:
    entrar(cliente, "gerente")
    pagina = cliente.get("/").text
    assert "Última sincronización con Softland: todavía no se ha completado." in pagina
    assert AVISO in pagina
