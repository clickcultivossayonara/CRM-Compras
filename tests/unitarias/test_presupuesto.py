"""Presupuesto por semana. Casos del plan de pruebas §3.2 (T1.2 · R2.2) y §3.3 (T1.3 · R2.1 a R2.4).

Las semanas se indican por posición: la posición 0 es la semana 1 del año.
"""

import pytest

from crm_compras.dominio.presupuesto import cabe, disponibles, repartir_mes, saldos


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


def test_saldo_y_disponible_sin_consumo() -> None:
    asignado = [100] * 5
    consumido = [0] * 5
    assert saldos(asignado, consumido)[2] == 300
    assert disponibles(asignado, consumido)[2] == 300


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        # Límite: exactamente el disponible de la semana 3.
        (300, True),
        # Límite: el disponible + 1 va a Gerencia.
        (301, False),
    ],
)
def test_linea_contra_el_disponible(valor: int, esperado: bool) -> None:
    assert cabe([100] * 4, [0] * 4, [(2, valor)]) is esperado


@pytest.mark.parametrize(("valor", "esperado"), [(100, True), (101, False)])
def test_linea_en_la_primera_semana_del_anio(valor: int, esperado: bool) -> None:
    assert cabe([100] * 4, [0] * 4, [(0, valor)]) is esperado


def test_disponible_cero_no_admite_una_linea_de_1() -> None:
    asignado = [100, 0]
    consumido = [100, 0]
    assert disponibles(asignado, consumido) == [0, 0]
    assert cabe(asignado, consumido, [(1, 1)]) is False


def test_lo_que_sobra_de_enero_se_usa_en_febrero() -> None:
    # Enero: 400 en 4 semanas, se consumen 100. Febrero: 500 en 4 semanas.
    asignado = repartir_mes(400, 4) + repartir_mes(500, 4)
    consumido = [100, 0, 0, 0, 0, 0, 0, 0]
    # Primera semana de febrero: 300 de enero + 125 de febrero.
    assert disponibles(asignado, consumido)[4] == 425
    assert cabe(asignado, consumido, [(4, 425)]) is True
    assert cabe(asignado, consumido, [(4, 426)]) is False


def test_consumo_futuro_limita_el_disponible() -> None:
    # Consumo de 900 en la semana 10 que deja su saldo en 100.
    asignado = [100] * 12
    consumido = [0] * 9 + [900, 0, 0]
    assert saldos(asignado, consumido)[4] == 500
    assert disponibles(asignado, consumido)[4] == min(saldos(asignado, consumido)[4:]) == 100
    assert cabe(asignado, consumido, [(4, 100)]) is True
    assert cabe(asignado, consumido, [(4, 101)]) is False


def test_lineas_de_la_misma_semana_se_suman() -> None:
    # Cada línea cabe sola en 300, pero juntas suman 310.
    assert cabe([100] * 4, [0] * 4, [(2, 150)]) is True
    assert cabe([100] * 4, [0] * 4, [(2, 150), (2, 160)]) is False


def test_lineas_de_semanas_distintas_se_evaluan_juntas() -> None:
    # Solas caben (150 ≤ 200 y 300 ≤ 400), pero juntas dejan la semana 4 en -50.
    assert cabe([100] * 4, [0] * 4, [(1, 150), (3, 300)]) is False


def test_pedido_sin_lineas_cabe() -> None:
    assert cabe([0], [0], []) is True


def test_semanas_distintas_entre_asignado_y_consumido_es_error() -> None:
    with pytest.raises(ValueError, match="mismas semanas"):
        saldos([100] * 4, [0] * 5)


@pytest.mark.parametrize(("semana", "mensaje"), [(-1, "La semana 0"), (4, "La semana 5")])
def test_linea_fuera_del_anio_es_error(semana: int, mensaje: str) -> None:
    with pytest.raises(ValueError, match=f"^{mensaje} está fuera del año"):
        cabe([100] * 4, [0] * 4, [(semana, 1)])


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


@pytest.mark.propiedad
def test_p2_disponible_no_supera_el_saldo_ni_aumenta_con_consumo() -> None:
    """P2: disponible(s) ≤ saldo(s), y disponible nunca aumenta al agregar consumo."""
    from hypothesis import given
    from hypothesis import strategies as st

    valores = st.integers(min_value=0, max_value=10**9)

    @given(
        semanas=st.lists(st.tuples(valores, valores), min_size=1, max_size=53),
        extra=st.tuples(st.integers(min_value=0, max_value=52), valores),
    )
    def propiedad(semanas: list[tuple[int, int]], extra: tuple[int, int]) -> None:
        asignado = [a for a, _ in semanas]
        consumido = [c for _, c in semanas]
        antes = disponibles(asignado, consumido)
        assert all(d <= s for d, s in zip(antes, saldos(asignado, consumido), strict=True))

        semana, valor = extra[0] % len(semanas), extra[1]
        consumido[semana] += valor
        despues = disponibles(asignado, consumido)
        assert all(d <= a for d, a in zip(despues, antes, strict=True))

    propiedad()


@pytest.mark.propiedad
def test_p3_aceptar_solo_lo_que_cabe_no_deja_saldos_negativos() -> None:
    """P3: si toda línea aceptada cumple valor ≤ disponible(s), ningún saldo queda negativo."""
    from hypothesis import given
    from hypothesis import strategies as st

    @given(
        asignado=st.lists(st.integers(min_value=0, max_value=10**6), min_size=1, max_size=53),
        lineas=st.lists(
            st.tuples(st.integers(min_value=0, max_value=52), st.integers(1, 10**6)),
            max_size=30,
        ),
    )
    def propiedad(asignado: list[int], lineas: list[tuple[int, int]]) -> None:
        consumido = [0] * len(asignado)
        for semana, valor in lineas:
            linea = (semana % len(asignado), valor)
            if cabe(asignado, consumido, [linea]):
                consumido[linea[0]] += valor
        assert all(saldo >= 0 for saldo in saldos(asignado, consumido))

    propiedad()
