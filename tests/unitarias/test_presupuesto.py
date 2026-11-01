"""T1.2 · Reparto semanal del presupuesto (R2.2). Casos del plan de pruebas §3.2."""

import pytest

from crm_compras.dominio.presupuesto import repartir_mes


@pytest.mark.parametrize(
    ("valor_mes", "n_semanas", "esperado"),
    [
        # Partición: valor divisible entre las semanas.
        (400, 4, [100, 100, 100, 100]),
        # Límite: el residuo del redondeo va a la última semana.
        (403, 4, [100, 100, 100, 103]),
        # Límite: mes sin presupuesto.
        (0, 5, [0, 0, 0, 0, 0]),
        # Límite: valor menor que el número de semanas.
        (3, 5, [0, 0, 0, 0, 3]),
    ],
)
def test_repartir_mes(valor_mes: int, n_semanas: int, esperado: list[int]) -> None:
    reparto = repartir_mes(valor_mes, n_semanas)
    assert reparto == esperado
    assert sum(reparto) == valor_mes


def test_valor_negativo_es_error() -> None:
    with pytest.raises(ValueError, match="negativo"):
        repartir_mes(-1, 4)


@pytest.mark.parametrize("n_semanas", [0, 3, 6])
def test_solo_se_aceptan_4_o_5_semanas(n_semanas: int) -> None:
    with pytest.raises(ValueError, match="4 o 5 semanas"):
        repartir_mes(400, n_semanas)


@pytest.mark.propiedad
def test_p1_reparto_suma_el_mes_sin_semanas_negativas() -> None:
    """P1: la suma del reparto es el valor del mes y ninguna semana es negativa."""
    from hypothesis import given
    from hypothesis import strategies as st

    @given(
        valor_mes=st.integers(min_value=0, max_value=10**12),
        n_semanas=st.sampled_from([4, 5]),
    )
    def propiedad(valor_mes: int, n_semanas: int) -> None:
        reparto = repartir_mes(valor_mes, n_semanas)
        assert len(reparto) == n_semanas
        assert sum(reparto) == valor_mes
        assert all(semana >= 0 for semana in reparto)
        # El residuo solo cae en la última semana: las demás son iguales.
        assert len(set(reparto[:-1])) == 1

    propiedad()
