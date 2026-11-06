"""T1.8 · Cargador para Softland (R5.1, R5.2, R5.4, R5.5). Casos del plan de pruebas §3.7.

Datos ficticios armados con fábricas.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from crm_compras.dominio.cargador import (
    ENCABEZADOS,
    CargadorError,
    LineaCargador,
    armar_cargador,
    lineas_para_lote,
)
from tests.fabricas import ANCHO_COMPLETO, ARABIGOS, otros_digitos

FECHA = date(2026, 11, 20)


def linea(linea_id: int = 1, **cambios: object) -> LineaCargador:
    base = LineaCargador(
        linea_id=linea_id,
        articulo="020093",
        descripcion="ARTICULO FICTICIO",
        centro_costo="513-01-2",
        descripcion_centro="CENTRO FICTICIO",
        cantidad=Decimal(4),
        fecha_requerida=FECHA,
        comentario="",
        prohibido=False,
        bodega=1,
    )
    return replace(base, **cambios)  # type: ignore[arg-type]


def prohibida(linea_id: int, **cambios: object) -> LineaCargador:
    return linea(linea_id, **{"prohibido": True, "bodega": 5, **cambios})


def test_encabezados_en_el_orden_de_la_plantilla() -> None:
    assert ENCABEZADOS == (
        "Artículo",
        "Descripción",
        "Centro Costo",
        "Descripción Centro de Costo",
        "Cantidad",
        "Fecha Requerida",
        "Comentario",
    )


def test_tres_bodegas_dan_tres_hojas() -> None:
    hojas = armar_cargador([prohibida(3), linea(2, bodega=2), linea(1, bodega=1)])
    assert list(hojas) == ["La Union", "La Ceja", "Prohibidos"]
    assert all(len(filas) == 1 for filas in hojas.values())


def test_solo_bodega_5_da_una_hoja() -> None:
    assert list(armar_cargador([prohibida(1), prohibida(2)])) == ["Prohibidos"]


def test_fila_en_el_orden_de_la_plantilla_con_textos() -> None:
    hojas = armar_cargador([linea(1, articulo="000123", comentario="Urgente")])
    assert hojas["La Union"] == [
        ("000123", "ARTICULO FICTICIO", "513-01-2", "CENTRO FICTICIO", 4, FECHA, "Urgente")
    ]


def test_cantidad_entera_como_int_y_decimal_conservada() -> None:
    hojas = armar_cargador([linea(1, cantidad=Decimal("3.00")), linea(2, cantidad=Decimal("2.5"))])
    cantidades = [fila[4] for fila in hojas["La Union"]]
    assert cantidades == [3, Decimal("2.5")]
    assert isinstance(cantidades[0], int)


def test_filas_ordenadas_por_linea() -> None:
    hojas = armar_cargador([linea(3, articulo="000003"), linea(1, articulo="000001")])
    assert [fila[0] for fila in hojas["La Union"]] == ["000001", "000003"]


def test_volver_a_armar_el_lote_da_lo_mismo() -> None:
    lineas = [prohibida(2), linea(1, bodega=2)]
    assert armar_cargador(lineas) == armar_cargador(list(reversed(lineas)))


def test_linea_sin_bodega_no_genera_el_archivo() -> None:
    with pytest.raises(CargadorError) as error:
        armar_cargador([linea(1), linea(7, bodega=None)])
    assert error.value.problemas == ["Línea 7: falta asignar la bodega."]


def test_se_reportan_todos_los_problemas() -> None:
    with pytest.raises(CargadorError) as error:
        armar_cargador(
            [
                linea(1, bodega=5),
                prohibida(2, bodega=1),
                linea(3, articulo="20093", centro_costo="51301-2"),
            ]
        )
    assert error.value.problemas == [
        "Línea 1: la bodega 5 no es 1 ni 2.",
        "Línea 2: el artículo es prohibido y debe ir a la bodega 5.",
        "Línea 3: el artículo '20093' no tiene 6 dígitos.",
        "Línea 3: el centro de costo '51301-2' no tiene el formato NNN-NN-N.",
    ]
    assert str(error.value).startswith("No se genera el cargador: Línea 1:")


def test_digitos_no_ascii_no_son_codigos_validos() -> None:
    # Dígitos de ancho completo y arábigos: Softland solo acepta 0 a 9.
    articulo = otros_digitos("020093", ANCHO_COMPLETO)
    centro = otros_digitos("513-01-2", ARABIGOS)
    with pytest.raises(CargadorError) as error:
        armar_cargador([linea(1, articulo=articulo, centro_costo=centro)])
    assert len(error.value.problemas) == 2


def test_sin_lineas_no_hay_cargador() -> None:
    with pytest.raises(CargadorError, match="No hay líneas"):
        armar_cargador([])


def test_linea_ya_exportada_no_entra_en_otro_lote() -> None:
    exportada = linea(1, lote_id=10)
    nueva = linea(2)
    assert lineas_para_lote([exportada, nueva]) == [nueva]


@pytest.mark.propiedad
def test_p6_codigos_conservan_su_texto_exacto() -> None:
    """P6: cualquier código de 6 dígitos sale igual en el cargador, con sus ceros a la izquierda."""
    from hypothesis import given
    from hypothesis import strategies as st

    @given(
        articulo=st.from_regex(r"[0-9]{6}", fullmatch=True),
        centro=st.from_regex(r"[0-9]{3}-[0-9]{2}-[0-9]", fullmatch=True),
        bodega=st.sampled_from([1, 2]),
    )
    def propiedad(articulo: str, centro: str, bodega: int) -> None:
        hojas = armar_cargador([linea(1, articulo=articulo, centro_costo=centro, bodega=bodega)])
        (fila,) = next(iter(hojas.values()))
        assert fila[0] == articulo
        assert fila[2] == centro
        assert isinstance(fila[0], str)
        assert isinstance(fila[2], str)

    propiedad()
