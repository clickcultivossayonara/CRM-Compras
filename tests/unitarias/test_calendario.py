"""T1.1 · Calendario (R1.6, R2.2). Casos del plan de pruebas §3.1."""

from datetime import date

import pytest

from crm_compras.dominio.calendario import (
    Mes,
    Semana,
    lunes_de,
    mes_de_semana,
    semana_de,
    semanas_del_mes,
)


@pytest.mark.parametrize(
    ("fecha", "semana", "mes"),
    [
        # Partición: fecha a mitad de mes.
        (date(2025, 10, 15), Semana(2025, 42), Mes(2025, 10)),
        # Límites: lunes y domingo de una semana que cruza septiembre y octubre (jueves 02/10).
        (date(2025, 9, 29), Semana(2025, 40), Mes(2025, 10)),
        (date(2025, 10, 5), Semana(2025, 40), Mes(2025, 10)),
        # Límites de año: el 01/01/2027 es de la semana 53 de 2026 (diciembre).
        (date(2027, 1, 1), Semana(2026, 53), Mes(2026, 12)),
        # El 29/12/2025 es de la semana 1 de 2026 (enero, su jueves es 01/01/2026).
        (date(2025, 12, 29), Semana(2026, 1), Mes(2026, 1)),
    ],
)
def test_semana_y_mes_de_una_fecha(fecha: date, semana: Semana, mes: Mes) -> None:
    assert semana_de(fecha) == semana
    assert mes_de_semana(semana_de(fecha)) == mes


def test_semanas_de_agosto_a_diciembre_2025_coinciden_con_el_excel() -> None:
    conteo = [len(semanas_del_mes(2025, m)) for m in range(8, 13)]
    assert conteo == [4, 4, 5, 4, 4]


def test_octubre_2025_empieza_en_la_semana_40() -> None:
    assert semanas_del_mes(2025, 10) == [Semana(2025, n) for n in range(40, 45)]


@pytest.mark.parametrize(("anio", "total"), [(2025, 52), (2026, 53), (2027, 52)])
def test_cada_semana_del_anio_pertenece_a_un_solo_mes(anio: int, total: int) -> None:
    semanas = [s for m in range(1, 13) for s in semanas_del_mes(anio, m)]
    assert len(semanas) == total
    assert len(set(semanas)) == total
    assert semanas == sorted(semanas)
    assert all(s.anio == anio for s in semanas)


@pytest.mark.parametrize(("anio", "mes"), [(2026, 1), (2026, 12), (2025, 6)])
def test_cada_mes_tiene_4_o_5_semanas(anio: int, mes: int) -> None:
    assert len(semanas_del_mes(anio, mes)) in (4, 5)


def test_lunes_de_una_semana() -> None:
    assert lunes_de(Semana(2025, 40)) == date(2025, 9, 29)
    assert str(Semana(2025, 4)) == "2025-W04"


@pytest.mark.parametrize("semana", [Semana(2025, 53), Semana(2025, 0), Semana(2026, 54)])
def test_semana_inexistente_falla(semana: Semana) -> None:
    with pytest.raises(ValueError):
        lunes_de(semana)


@pytest.mark.parametrize("mes", [0, 13])
def test_mes_invalido_falla(mes: int) -> None:
    with pytest.raises(ValueError):
        semanas_del_mes(2025, mes)
