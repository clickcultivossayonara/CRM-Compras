"""T2.4 · Comando para crear el primer administrador, contra PostgreSQL."""

import pytest
from sqlalchemy import select

from crm_compras.crear_administrador import main
from crm_compras.datos.conexion import BaseDatos
from crm_compras.datos.modelos import Auditoria, Usuario
from crm_compras.web.seguridad import clave_valida
from tests.fabricas import clave_aleatoria


def respuestas(*valores: str) -> object:
    pendientes = list(valores)
    return lambda _mensaje: pendientes.pop(0)


def test_crea_el_administrador_con_la_clave_cifrada(
    bd: BaseDatos, capsys: pytest.CaptureFixture[str]
) -> None:
    clave = clave_aleatoria()
    codigo = main(["Admin.Inicial", "Administrador Inicial"], bd, respuestas(clave, clave))  # type: ignore[arg-type]
    assert codigo == 0
    assert "Administrador admin.inicial creado." in capsys.readouterr().out
    with bd.sesion() as sesion:
        usuario = sesion.scalars(select(Usuario).where(Usuario.usuario == "admin.inicial")).one()
        assert usuario.rol == "administrador"
        assert clave_valida(usuario.hash_clave, clave)
        registro = sesion.scalars(select(Auditoria).where(Auditoria.accion == "crear")).one()
        assert registro.usuario_id is None


@pytest.mark.parametrize(
    ("claves", "mensaje"),
    [
        (("corta",), "al menos 12 caracteres"),
        (("una-clave-larga-1", "otra-clave-larga-2"), "Las contraseñas no coinciden."),
    ],
)
def test_clave_invalida_no_crea_nada(
    bd: BaseDatos, capsys: pytest.CaptureFixture[str], claves: tuple[str, ...], mensaje: str
) -> None:
    assert main(["admin.inicial", "Administrador"], bd, respuestas(*claves)) == 1  # type: ignore[arg-type]
    assert mensaje in capsys.readouterr().err
    with bd.sesion() as sesion:
        nuevo = sesion.scalars(select(Usuario).where(Usuario.usuario == "admin.inicial")).first()
        assert nuevo is None


def test_usuario_repetido(bd: BaseDatos, capsys: pytest.CaptureFixture[str]) -> None:
    clave = clave_aleatoria()
    assert main(["admin.inicial", "A"], bd, respuestas(clave, clave)) == 0  # type: ignore[arg-type]
    assert main(["admin.inicial", "B"], bd, respuestas(clave, clave)) == 1  # type: ignore[arg-type]
    assert "El usuario admin.inicial ya existe." in capsys.readouterr().err
