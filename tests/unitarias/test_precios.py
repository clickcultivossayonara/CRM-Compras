"""T1.5 · Normalización de precios (R6.4): regla del artículo 020215."""

from decimal import Decimal

import pytest

from crm_compras.dominio.precios import ARTICULO_POR_FACTOR, normalizar


@pytest.mark.parametrize(
    ("comentario", "esperado"),
    [
        # Partición: comentario con un factor entero.
        ("CAJA X 24 UNIDADES", 1000),
        # Comentario que empieza con el número.
        ("24", 1000),
        # Factor con decimales.
        ("factor 2.5", 9600),
        # El número termina en el primer carácter que no es dígito ni punto.
        ("x 12, 2 cajas", 2000),
        # Sin número, vacío o nulo: el precio no cambia.
        ("SIN FACTOR", 24000),
        ("", 24000),
        (None, 24000),
    ],
)
def test_articulo_020215_divide_por_el_factor(comentario: str | None, esperado: int) -> None:
    assert normalizar(ARTICULO_POR_FACTOR, Decimal(24000), comentario) == esperado


@pytest.mark.parametrize("comentario", ["x 0 und", "x 1.2.3"])
def test_factor_invalido_deja_el_articulo_sin_precio(comentario: str) -> None:
    assert normalizar(ARTICULO_POR_FACTOR, Decimal(24000), comentario) is None


def test_otros_articulos_ignoran_el_comentario() -> None:
    assert normalizar("020093", Decimal(24000), "x 24") == 24000


@pytest.mark.parametrize(
    ("precio", "esperado"),
    [
        (Decimal("1234.5"), 1235),
        (Decimal("1234.4999"), 1234),
        (Decimal("0.5"), 1),
    ],
)
def test_redondeo_a_pesos_enteros(precio: Decimal, esperado: int) -> None:
    assert normalizar("020093", precio, None) == esperado


def test_division_redondea_half_up() -> None:
    # 1000 / 3 = 333,33… y 1001 / 2 = 500,5.
    assert normalizar(ARTICULO_POR_FACTOR, Decimal(1000), "3") == 333
    assert normalizar(ARTICULO_POR_FACTOR, Decimal(1001), "2") == 501
