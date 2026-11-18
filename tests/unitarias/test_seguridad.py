"""T2.3 · Configuración de la web, contraseñas con argon2 y rutas por rol (R6.1, R2.5)."""

import secrets
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from crm_compras.datos.usuarios import UsuarioSesion
from crm_compras.dominio.pedido import Rol
from crm_compras.web.app import crear_app
from crm_compras.web.configuracion import Configuracion
from crm_compras.web.seguridad import autenticar, cifrar_clave, clave_valida, requiere_roles
from tests.conftest import csrf_de
from tests.fabricas import RepositorioUsuariosMemoria, clave_aleatoria, usuario


@pytest.mark.parametrize(("rol", "codigo"), [(Rol.GERENTE, 200), (Rol.JEFE, 403)])
def test_una_ruta_solo_para_un_rol(rol: Rol, codigo: int) -> None:
    clave = clave_aleatoria()
    cuenta = usuario(1, rol, clave)
    app = crear_app(
        Configuracion(clave_secreta=secrets.token_hex(32)), RepositorioUsuariosMemoria([cuenta])
    )

    @app.get("/solo-gerente")
    def solo_gerente(
        quien: Annotated[UsuarioSesion, Depends(requiere_roles(Rol.GERENTE))],
    ) -> dict[str, str]:
        return {"nombre": quien.nombre}

    with TestClient(app, base_url="https://testserver") as cliente:
        token = csrf_de(cliente.get("/login").text)
        cliente.post(
            "/login", data={"usuario": cuenta.usuario, "clave": clave, "csrf_token": token}
        )
        respuesta = cliente.get("/solo-gerente")
    assert respuesta.status_code == codigo
    if codigo == 403:
        assert respuesta.json() == {"detail": "Su rol no tiene acceso a esta página."}


def test_la_clave_se_guarda_cifrada_con_argon2() -> None:
    clave = clave_aleatoria()
    cifrada = cifrar_clave(clave)
    assert cifrada.startswith("$argon2id$")
    assert clave not in cifrada
    assert cifrar_clave(clave) != cifrada
    assert clave_valida(cifrada, clave)
    assert not clave_valida(cifrada, clave + "x")


def test_un_hash_danado_no_es_valido() -> None:
    assert not clave_valida("no-es-un-hash", clave_aleatoria())


def test_autenticar() -> None:
    clave = clave_aleatoria()
    activo = usuario(1, Rol.JEFE, clave)
    inactivo = usuario(2, Rol.JEFE, clave, activo=False)
    repositorio = RepositorioUsuariosMemoria([activo, inactivo])
    assert autenticar(repositorio, activo.usuario, clave) == activo
    assert autenticar(repositorio, activo.usuario, clave + "x") is None
    assert autenticar(repositorio, inactivo.usuario, clave) is None
    assert autenticar(repositorio, "no.existe", clave) is None


def test_configuracion_desde_el_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    clave = secrets.token_hex(32)
    monkeypatch.setenv("SECRET_KEY", clave)
    monkeypatch.setenv("CRM_COOKIES_SEGURAS", "0")
    configuracion = Configuracion.desde_entorno()
    assert configuracion.clave_secreta == clave
    assert configuracion.cookies_seguras is False
    monkeypatch.delenv("CRM_COOKIES_SEGURAS")
    assert Configuracion.desde_entorno().cookies_seguras is True


@pytest.mark.parametrize("clave", ["", "corta", "x" * 31])
def test_secret_key_corta_o_ausente_es_error(monkeypatch: pytest.MonkeyPatch, clave: str) -> None:
    monkeypatch.setenv("SECRET_KEY", clave)
    with pytest.raises(ValueError, match="al menos 32 caracteres"):
        Configuracion.desde_entorno()
