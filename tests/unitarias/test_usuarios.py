"""T2.4 · Reglas de la administración de usuarios y unidades (dominio, sin I/O)."""

import pytest

from crm_compras.dominio.pedido import Rol
from crm_compras.dominio.usuarios import (
    errores_autoedicion,
    errores_clave,
    errores_unidad,
    errores_usuario,
    normalizar_unidad,
    normalizar_usuario,
)
from tests.fabricas import ANCHO_COMPLETO, otros_digitos

USUARIO_INVALIDO = "El usuario debe tener de 3 a 50 caracteres: minúsculas, dígitos, punto o guion."


@pytest.mark.parametrize("usuario", ["abc", "jefe.pompon", "a_b-c.1", "x" * 50])
def test_usuarios_validos(usuario: str) -> None:
    assert errores_usuario(usuario, "Nombre", "jefe") == []


@pytest.mark.parametrize(
    "usuario",
    [
        "ab",
        "x" * 51,
        "Jefe",
        ".jefe",
        "jefe pompon",
        "jéfe",
        "",
        otros_digitos("abc1", ANCHO_COMPLETO),
    ],
)
def test_usuarios_invalidos(usuario: str) -> None:
    assert errores_usuario(usuario, "Nombre", "jefe") == [USUARIO_INVALIDO]


def test_nombre_y_rol() -> None:
    assert errores_usuario("abc", "   ", "jefe") == ["El nombre es obligatorio."]
    assert errores_usuario("abc", "N" * 121, "jefe") == ["El nombre admite máximo 120 caracteres."]
    assert errores_usuario("abc", "N" * 120, "gerente") == []
    assert errores_usuario("abc", "N", "dueño") == ["El rol 'dueño' no existe."]


def test_normalizar() -> None:
    assert normalizar_usuario("  Jefe.Pompon ") == "jefe.pompon"
    assert normalizar_unidad(" kg ") == "KG"


@pytest.mark.parametrize(
    ("largo", "errores"),
    [
        (11, ["La contraseña debe tener al menos 12 caracteres."]),
        (12, []),
        (128, []),
        (129, ["La contraseña admite máximo 128 caracteres."]),
    ],
)
def test_largo_de_la_clave(largo: int, errores: list[str]) -> None:
    assert errores_clave("x" * largo) == errores


def test_mensaje_de_unidad_invalida() -> None:
    assert errores_unidad("K1") == [
        "La unidad debe tener de 1 a 10 letras, como en Softland (por ejemplo, KL)."
    ]


@pytest.mark.parametrize(
    ("unidad", "valida"),
    [
        ("K", True),
        ("KL", True),
        ("A" * 10, True),
        ("", False),
        ("A" * 11, False),
        ("K1", False),
        ("kl", False),
    ],
)
def test_unidades(unidad: str, valida: bool) -> None:
    assert (errores_unidad(unidad) == []) is valida


def test_un_administrador_no_se_quita_el_acceso() -> None:
    assert errores_autoedicion(1, 1, Rol.ADMINISTRADOR, True) == []
    assert errores_autoedicion(1, 1, Rol.JEFE, False) == [
        "No puede quitarse a sí mismo el rol de administrador.",
        "No puede desactivar su propio usuario.",
    ]
    assert errores_autoedicion(1, 2, Rol.JEFE, False) == []
