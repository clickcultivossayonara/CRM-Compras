"""T3.3 · Frescura de los datos de Softland (R6.5): regla de las 24 horas."""

from datetime import UTC, datetime, timedelta

import pytest

from crm_compras.dominio.sincronizacion import EstadoSincronizacion, evaluar

AHORA = datetime(2026, 11, 27, 15, 0, tzinfo=UTC)


def todas(hace: timedelta) -> dict[str, datetime]:
    return dict.fromkeys(("articulos", "centros", "precios"), AHORA - hace)


def test_sin_ninguna_sincronizacion() -> None:
    assert evaluar({}, AHORA) == EstadoSincronizacion(ultima=None, atrasada=True)


def test_si_falta_un_tipo_esta_atrasada() -> None:
    ultimas = todas(timedelta(hours=1))
    del ultimas["precios"]
    assert evaluar(ultimas, AHORA) == EstadoSincronizacion(ultima=None, atrasada=True)


@pytest.mark.parametrize(
    ("hace", "atrasada"),
    [
        (timedelta(hours=1), False),
        (timedelta(hours=24), False),
        (timedelta(hours=24, seconds=1), True),
        (timedelta(days=3), True),
    ],
)
def test_limite_de_24_horas(hace: timedelta, atrasada: bool) -> None:
    assert evaluar(todas(hace), AHORA) == EstadoSincronizacion(AHORA - hace, atrasada)


def test_manda_la_sincronizacion_mas_vieja() -> None:
    ultimas = todas(timedelta(hours=1))
    ultimas["precios"] = AHORA - timedelta(hours=30)
    estado = evaluar(ultimas, AHORA)
    assert estado.ultima == AHORA - timedelta(hours=30)
    assert estado.atrasada
