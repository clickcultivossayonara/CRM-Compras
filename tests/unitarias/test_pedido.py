"""T1.6 · Validación de líneas y pedido (R3.5, R3.6, R3.8). Casos del plan de pruebas §3.5.

Datos ficticios armados con fábricas.
"""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from crm_compras.dominio.calendario import semana_de
from crm_compras.dominio.pedido import (
    BODEGA_PROHIBIDOS,
    Articulo,
    ContextoValidacion,
    LineaPedido,
    anio_presupuesto,
    validar_linea,
    validar_pedido,
)

HOY = date(2026, 11, 5)
PARTIDA = 1
PARTIDA_2027 = 2
PARTIDA_AJENA = 99


def articulo(codigo: str = "020093", unidad: str = "UND", activo: bool = True) -> Articulo:
    return Articulo(codigo, f"ARTICULO FICTICIO {codigo}", unidad, activo)


def contexto(**cambios: object) -> ContextoValidacion:
    base = ContextoValidacion(
        hoy=HOY,
        articulos={
            a.codigo: a
            for a in (
                articulo("020093"),
                articulo("000001", unidad="LT"),
                articulo("000002", activo=False),
                articulo("000003"),
            )
        },
        precios={"020093": 1500, "000001": 2000, "000002": 100},
        centros_costo={"100-01-1", "200-02-2"},
        centros_del_jefe={"100-01-1"},
        partidas_del_jefe={PARTIDA: 2026, PARTIDA_2027: 2027},
        anios_con_presupuesto={2026},
        prohibidos=set(),
    )
    return replace(base, **cambios)  # type: ignore[arg-type]


def linea(**cambios: object) -> LineaPedido:
    base = LineaPedido(
        articulo="020093",
        centro_costo="100-01-1",
        partida_id=PARTIDA,
        cantidad=Decimal(4),
        fecha_requerida=HOY + timedelta(days=7),
    )
    return replace(base, **cambios)  # type: ignore[arg-type]


def errores(**cambios: object) -> list[str]:
    return validar_linea(linea(**cambios), contexto()).errores


def test_linea_valida() -> None:
    resultado = validar_linea(linea(), contexto())
    assert resultado.errores == []
    assert resultado.advertencias == []
    assert resultado.valor == 4 * 1500
    assert resultado.bodega is None


def test_codigo_con_cero_a_la_izquierda_se_conserva_como_texto() -> None:
    resultado = validar_linea(linea(articulo="020093"), contexto())
    assert resultado.errores == []
    assert resultado.linea.articulo == "020093"


@pytest.mark.parametrize("codigo", ["20093", "0200930", "02009A", "", " 020093"])
def test_codigo_con_formato_invalido(codigo: str) -> None:
    assert errores(articulo=codigo) == [f"El código {codigo!r} no tiene el formato de 6 dígitos."]


def test_codigo_inexistente() -> None:
    assert errores(articulo="999999") == ["El artículo 999999 no existe en Softland."]


def test_codigo_inactivo() -> None:
    assert errores(articulo="000002") == ["El artículo 000002 está inactivo en Softland."]


def test_articulo_sin_precio() -> None:
    resultado = validar_linea(linea(articulo="000003"), contexto())
    assert resultado.errores == ["El artículo 000003 no tiene compras previas y no tiene precio."]
    assert resultado.valor is None


@pytest.mark.parametrize(
    ("centro", "mensaje"),
    [
        ("200-02-2", "El centro de costo 200-02-2 no está asignado al jefe."),
        ("999-99-9", "El centro de costo 999-99-9 no existe en Softland."),
    ],
)
def test_centro_de_costo_ajeno_o_inexistente(centro: str, mensaje: str) -> None:
    assert errores(centro_costo=centro) == [mensaje]


@pytest.mark.parametrize(
    ("partida", "mensaje"),
    [
        (None, "Falta la partida presupuestal."),
        (PARTIDA_AJENA, "La partida no está asignada al jefe."),
    ],
)
def test_partida_ausente_o_ajena(partida: int | None, mensaje: str) -> None:
    assert errores(partida_id=partida) == [mensaje]


def test_partida_de_otro_anio() -> None:
    assert errores(partida_id=PARTIDA_2027) == [
        "La partida es del presupuesto 2027 y la fecha requerida consume el de 2026."
    ]


@pytest.mark.parametrize("cantidad", ["0", "-1"])
def test_cantidad_cero_o_negativa(cantidad: str) -> None:
    resultado = validar_linea(linea(cantidad=Decimal(cantidad)), contexto())
    assert resultado.errores == ["La cantidad debe ser mayor que cero."]
    assert resultado.valor is None


@pytest.mark.parametrize(("cantidad", "valor"), [("1", 2000), ("0.01", 20), ("2.50", 5000)])
def test_cantidad_en_unidad_decimal(cantidad: str, valor: int) -> None:
    resultado = validar_linea(linea(articulo="000001", cantidad=Decimal(cantidad)), contexto())
    assert resultado.errores == []
    assert resultado.valor == valor


def test_unidad_decimal_admite_maximo_dos_decimales() -> None:
    assert errores(articulo="000001", cantidad=Decimal("0.001")) == [
        "La cantidad admite máximo 2 decimales."
    ]


@pytest.mark.parametrize("cantidad", ["1.5", "0.01"])
def test_decimales_en_unidad_entera(cantidad: str) -> None:
    assert errores(cantidad=Decimal(cantidad)) == ["La unidad UND solo admite cantidades enteras."]


@pytest.mark.parametrize("cantidad", ["3.00", "1E+2"])
def test_cantidad_entera_escrita_con_decimales_o_exponente(cantidad: str) -> None:
    assert errores(cantidad=Decimal(cantidad)) == []


def test_fecha_requerida_hoy_se_acepta() -> None:
    assert errores(fecha_requerida=HOY) == []


def test_fecha_requerida_ayer_es_error() -> None:
    assert errores(fecha_requerida=HOY - timedelta(days=1)) == [
        "La fecha requerida no puede ser anterior a hoy."
    ]


def test_fecha_en_un_anio_sin_presupuesto() -> None:
    assert errores(fecha_requerida=date(2027, 3, 1), partida_id=PARTIDA_2027) == [
        "No hay presupuesto cargado para 2027."
    ]


def test_anio_del_presupuesto_es_el_del_mes_de_la_semana() -> None:
    # El 29/12/2025 es de la semana 1 de 2026 (su jueves es el 01/01/2026).
    assert anio_presupuesto(date(2025, 12, 29)) == 2026
    assert anio_presupuesto(date(2027, 1, 1)) == 2026


def test_articulo_prohibido_va_a_bodega_5() -> None:
    resultado = validar_linea(linea(), contexto(prohibidos={"020093"}))
    assert resultado.errores == []
    assert resultado.bodega == BODEGA_PROHIBIDOS


def test_varios_errores_se_reportan_juntos() -> None:
    resultado = validar_linea(
        linea(
            articulo="000002",
            centro_costo="200-02-2",
            partida_id=None,
            cantidad=Decimal("1.5"),
            fecha_requerida=HOY - timedelta(days=1),
        ),
        contexto(),
    )
    assert resultado.errores == [
        "El artículo 000002 está inactivo en Softland.",
        "El centro de costo 200-02-2 no está asignado al jefe.",
        "Falta la partida presupuestal.",
        "La unidad UND solo admite cantidades enteras.",
        "La fecha requerida no puede ser anterior a hoy.",
    ]


def test_valor_grande_sin_perdida() -> None:
    resultado = validar_linea(linea(cantidad=Decimal(10**6)), contexto(precios={"020093": 10**7}))
    assert resultado.valor == 10**13


def test_valor_redondea_half_up() -> None:
    # 0,25 por 2.002 = 500,5.
    resultado = validar_linea(
        linea(articulo="000001", cantidad=Decimal("0.25")),
        contexto(precios={"000001": 2002}),
    )
    assert resultado.valor == 501


def test_mismo_articulo_y_centro_dos_veces_en_el_pedido() -> None:
    resultados = validar_pedido(
        [linea(), linea(articulo="000001"), linea(cantidad=Decimal(1))], contexto()
    )
    assert [r.errores for r in resultados] == [
        [],
        [],
        ["El artículo 020093 con el centro de costo 100-01-1 ya está en la línea 1 del pedido."],
    ]


def test_mismo_articulo_en_otro_pedido_de_la_semana_es_advertencia() -> None:
    fecha = HOY + timedelta(days=7)
    otros = {("020093", "100-01-1", semana_de(fecha))}
    resultado = validar_linea(linea(fecha_requerida=fecha), contexto(otros_pedidos=otros))
    assert resultado.errores == []
    assert resultado.advertencias == [
        "El artículo 020093 con el centro de costo 100-01-1 ya está en otro pedido de la "
        "misma semana."
    ]


def test_otro_pedido_de_otra_semana_no_advierte() -> None:
    otros = {("020093", "100-01-1", semana_de(HOY + timedelta(days=21)))}
    assert validar_linea(linea(), contexto(otros_pedidos=otros)).advertencias == []
