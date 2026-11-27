"""T3.2x · X1: las consultas del sincronizador contra Softland real (manual, solo lectura).

Se ejecuta a mano con ``uv run pytest -m softland`` desde la red de la empresa, con las
variables SOFTLAND_*. Solo comprueba cantidades y proporciones: no imprime datos de Softland.
"""

import os
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from sincronizador import consultas, lectura
from sincronizador.preparar import preparar_articulos, preparar_centros, preparar_precios

pytestmark = pytest.mark.softland

PROPORCION_MINIMA_VALIDA = 0.95


@pytest.fixture(scope="module")
def softland() -> Iterator[Any]:
    if any(not os.environ.get(v) for v in lectura.VARIABLES):
        pytest.skip("Faltan las variables SOFTLAND_* para conectarse a Softland")
    conexion = lectura.conectar(os.environ)
    try:
        yield conexion
    finally:
        conexion.close()


def test_articulos_reales_cumplen_el_contrato(softland: Any) -> None:
    filas = consultas.leer_articulos(softland)
    articulos, descartes = preparar_articulos(filas)
    assert articulos, "Softland no devolvió artículos"
    assert len(articulos) / len(filas) >= PROPORCION_MINIMA_VALIDA, descartes[:5]


def test_centros_reales_cumplen_el_contrato(softland: Any) -> None:
    filas = consultas.leer_centros(softland)
    centros, descartes = preparar_centros(filas)
    assert centros, "Softland no devolvió centros de costo"
    assert len(centros) / len(filas) >= PROPORCION_MINIMA_VALIDA, descartes[:5]


def test_precios_reales_cumplen_el_contrato(softland: Any) -> None:
    articulos, _ = preparar_articulos(consultas.leer_articulos(softland))
    hoy = datetime.now(ZoneInfo("America/Bogota")).date()
    filas = consultas.leer_precios(softland, hoy.replace(year=hoy.year - 1, month=1, day=1))
    precios, descartes = preparar_precios(filas, {a.codigo for a in articulos})
    assert precios, "Softland no devolvió precios de compras recientes"
    assert len(precios) / len(filas) >= PROPORCION_MINIMA_VALIDA, descartes[:5]
