"""T1.4 · Lector del Excel de presupuesto (R1.1 a R1.6). Casos del plan de pruebas §3.4.

La hoja ficticia imita el formato real: título, fila "Semanas" sobre los meses, fila "PPTO",
total general que suma rubros, rubros con SUM y con +, un rubro dentro de otro y filas sueltas.
Los valores son inventados.
"""

import pytest

from crm_compras.dominio.lector_presupuesto import (
    AREA_GENERAL,
    Lectura,
    PartidaLeida,
    leer_presupuesto,
    normalizar_nombre,
)

COLUMNAS = "BCDEF"
MESES = ["AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
POMPON = 9


def formula(plantilla: str) -> list[object]:
    return [plantilla.format(c=c) for c in COLUMNAS]


def hoja_ficticia() -> list[list[object]]:
    return [
        [],
        ["CONTROL COMPRAS - CULTIVOS FICTICIOS 2025"],
        [],
        ["Semanas ", 4, 4, 5, 4, 4],
        [None, *MESES],
        [None, *["PPTO"] * 5],
        ["MATERIA PRIMA", *formula("=+SUM({c}8,{c}12,{c}15,{c}20,{c}21)")],
        ["ABONOS Y FERTILIZANTES", *formula("=+SUM({c}9:{c}11)")],
        ["POMPON", 1000.4, 1000.5, 1500, 1000, 1000],
        ["ALSTRO", 2000, 2000, 2500, 2000, 2000],
        ["LA CEJA", 3000, 3000, 3500, 3000, 3000],
        ["OTROS QUIMICOS", *formula("=+{c}13+{c}14")],
        ["POSCOSECHA", *[400] * 5],
        ["CULTIVOS (CALDERA y CAMPO)", *[500] * 5],
        ["HERRAMIENTAS", *formula("=+{c}16+{c}17")],
        ["POSCOSECHA", *[600] * 5],
        ["CULTIVOS (CAMPO)", *formula("=+SUM({c}18:{c}19)")],
        ["POMPON LA UNION", *[700] * 5],
        ["LA CEJA", 800, None, 800, 800, 800],
        ["POLIETILENO", *[900] * 5],
        ["PAPELERÍA", *[100] * 5],
        ["PROYECTOS"],
    ]


def claves(lectura: Lectura) -> list[tuple[str, str]]:
    return [(p.rubro, p.area) for p in lectura.partidas]


def partida(lectura: Lectura, fila: int) -> PartidaLeida:
    return next(p for p in lectura.partidas if p.fila == fila)


def test_formato_valido() -> None:
    lectura = leer_presupuesto(hoja_ficticia(), 2025)
    assert lectura.errores == []
    assert lectura.semanas == {8: 4, 9: 4, 10: 5, 11: 4, 12: 4}
    assert sorted(claves(lectura)) == sorted(
        [
            ("ABONOS Y FERTILIZANTES", "POMPON"),
            ("ABONOS Y FERTILIZANTES", "ALSTRO"),
            ("ABONOS Y FERTILIZANTES", "LA CEJA"),
            ("OTROS QUIMICOS", "POSCOSECHA"),
            ("OTROS QUIMICOS", "CULTIVOS (CALDERA Y CAMPO)"),
            ("HERRAMIENTAS", "POSCOSECHA"),
            ("HERRAMIENTAS", "CULTIVOS (CAMPO) - POMPON LA UNION"),
            ("HERRAMIENTAS", "CULTIVOS (CAMPO) - LA CEJA"),
            ("POLIETILENO", AREA_GENERAL),
            ("PAPELERÍA", AREA_GENERAL),
        ]
    )
    assert partida(lectura, 10).valores == {8: 2000, 9: 2000, 10: 2500, 11: 2000, 12: 2000}


def test_fila_suelta_es_partida_general() -> None:
    lectura = leer_presupuesto(hoja_ficticia(), 2025)
    assert partida(lectura, 20) == PartidaLeida(
        "POLIETILENO", AREA_GENERAL, 20, dict.fromkeys(range(8, 13), 900)
    )


def test_total_general_y_rubros_no_son_partidas() -> None:
    filas_de_partidas = {p.fila for p in leer_presupuesto(hoja_ficticia(), 2025).partidas}
    assert filas_de_partidas.isdisjoint({7, 8, 12, 15, 17})


def test_fila_con_nombre_y_sin_valores_se_ignora_con_advertencia() -> None:
    lectura = leer_presupuesto(hoja_ficticia(), 2025)
    assert lectura.advertencias == ["Fila 22 (PROYECTOS) no tiene valores; se ignora."]


def test_columnas_sin_mes_se_ignoran_con_advertencia() -> None:
    hoja = hoja_ficticia()
    hoja[POMPON - 1] += [123.4] * 12  # Columnas G a R.
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == []
    assert "Las columnas G, H, I, J, K, L, M, N, O, P, Q, R tienen datos" in lectura.advertencias[0]
    assert set(partida(lectura, POMPON).valores) == set(range(8, 13))


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (65040809.987, 65040810),
        (0.5, 1),
        (1.5, 2),
        (None, 0),
        (0, 0),
    ],
)
def test_redondeo_y_celda_vacia(valor: object, esperado: int) -> None:
    hoja = hoja_ficticia()
    hoja[POMPON - 1][1] = valor
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == []
    assert partida(lectura, POMPON).valores[8] == esperado


def test_lectura_de_valores_con_redondeo_de_la_hoja() -> None:
    valores = partida(leer_presupuesto(hoja_ficticia(), 2025), POMPON).valores
    assert (valores[8], valores[9]) == (1000, 1001)


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [
        (-1, "Fila 9, columna C: el valor es negativo."),
        (-0.4, "Fila 9, columna C: el valor es negativo."),
        ("mil", "Fila 9, columna C: 'mil' no es un número."),
        (True, "Fila 9, columna C: True no es un número."),
    ],
)
def test_valor_invalido_es_error_con_fila_y_columna(valor: object, mensaje: str) -> None:
    hoja = hoja_ficticia()
    hoja[POMPON - 1][2] = valor
    assert leer_presupuesto(hoja, 2025).errores == [mensaje]


def test_sin_fila_de_meses_es_error() -> None:
    hoja = hoja_ficticia()
    hoja[4] = [None, *["PPTO"] * 5]
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == ["No se encontró la fila con los meses como encabezado."]
    assert lectura.partidas == []


def test_sin_fila_de_semanas_es_error() -> None:
    hoja = hoja_ficticia()
    hoja[3][0] = "Total"
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == ['No se encontró la fila "Semanas".']
    assert lectura.partidas == []


def test_semanas_que_no_coinciden_con_el_calendario() -> None:
    hoja = hoja_ficticia()
    hoja[3][3] = 4
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == ["OCTUBRE debe tener 5 semanas, no 4."]
    assert 10 not in lectura.semanas


@pytest.mark.parametrize("valor", [None, 4.5, "cinco"])
def test_semanas_no_enteras_es_error(valor: object) -> None:
    hoja = hoja_ficticia()
    hoja[3][3] = valor
    assert leer_presupuesto(hoja, 2025).errores == [
        "Las semanas de OCTUBRE (columna D) deben ser un número entero."
    ]


def test_semanas_con_decimal_cero_se_aceptan() -> None:
    hoja = hoja_ficticia()
    hoja[3][3] = 5.0
    assert leer_presupuesto(hoja, 2025).semanas[10] == 5


def test_rubro_y_area_repetidos_es_error() -> None:
    hoja = hoja_ficticia()
    hoja[10][0] = "pompon "
    assert leer_presupuesto(hoja, 2025).errores == [
        "La partida ABONOS Y FERTILIZANTES / POMPON está repetida (filas 9 y 11)."
    ]


def test_mes_repetido_es_error() -> None:
    hoja = hoja_ficticia()
    hoja[4][5] = "agosto"
    assert "El mes AGOSTO está repetido en la fila 5." in leer_presupuesto(hoja, 2025).errores


def test_formula_sin_referencias_es_error() -> None:
    hoja = hoja_ficticia()
    hoja[19] = ["POLIETILENO", *["=1000*3"] * 5]
    assert "Fila 20: la fórmula no suma ninguna fila." in leer_presupuesto(hoja, 2025).errores


def test_fila_con_valores_y_sin_nombre_es_error() -> None:
    hoja = hoja_ficticia()
    hoja.append([None, 5, 5, 5, 5, 5])
    assert leer_presupuesto(hoja, 2025).errores == ["Fila 23: tiene valores y no tiene nombre."]


def test_fila_en_dos_rubros_es_error() -> None:
    hoja = hoja_ficticia()
    # OTROS QUIMICOS también suma la fila de POMPON.
    hoja[11] = ["OTROS QUIMICOS", *formula("=+{c}13+{c}14+{c}9")]
    assert leer_presupuesto(hoja, 2025).errores == [
        "Fila 9: está en más de un rubro (ABONOS Y FERTILIZANTES y OTROS QUIMICOS)."
    ]


def test_sin_total_general_cada_formula_raiz_es_rubro() -> None:
    hoja = hoja_ficticia()
    hoja[6] = ["MATERIA PRIMA"]
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == []
    assert ("ABONOS Y FERTILIZANTES", "LA CEJA") in claves(lectura)
    assert ("POLIETILENO", AREA_GENERAL) in claves(lectura)


def test_referencias_absolutas_y_filas_fuera_de_la_hoja() -> None:
    hoja = hoja_ficticia()
    hoja[11] = ["OTROS QUIMICOS", *formula("=SUM(${c}$13:${c}$14,{c}99)")]
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == []
    assert ("OTROS QUIMICOS", "POSCOSECHA") in claves(lectura)


def test_total_que_suma_una_fila_sin_valores() -> None:
    hoja = hoja_ficticia()
    hoja[6] = ["MATERIA PRIMA", *formula("=+SUM({c}8,{c}12,{c}15,{c}20,{c}21,{c}22)")]
    lectura = leer_presupuesto(hoja, 2025)
    assert lectura.errores == []
    assert len(lectura.partidas) == 10


def test_normalizar_nombre_conserva_tildes() -> None:
    assert normalizar_nombre("  material   eléctrico ") == "MATERIAL ELÉCTRICO"
