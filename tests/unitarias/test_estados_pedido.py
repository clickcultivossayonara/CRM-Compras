"""T1.7 · Estados del pedido (R3.9, R3.10, R4.1, R4.2, R4.4). Casos del plan de pruebas §3.6."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest

from crm_compras.dominio.pedido import (
    Estado,
    LineaPedido,
    LineaValidada,
    Rol,
    SaldoPartida,
    TransicionInvalida,
    anular,
    aprobar,
    compromete_presupuesto,
    enviar,
    exportar,
    partidas_que_exceden,
    rechazar,
    verificar_editable,
)

# Lunes de la semana 46 de 2026 (posición 45).
FECHA = date(2026, 11, 9)
SEMANAS_2026 = 53


def validada(
    valor: int, partida: int | None = 1, fecha: date = FECHA, errores: list[str] | None = None
) -> LineaValidada:
    linea = LineaPedido("020093", "100-01-1", partida, Decimal(1), fecha)
    return LineaValidada(linea, errores=errores or [], valor=valor)


def saldo(asignado_semanal: int = 100) -> SaldoPartida:
    return SaldoPartida([asignado_semanal] * SEMANAS_2026, [0] * SEMANAS_2026)


# Hasta la semana 46 se acumulan 4.600.
SALDOS = {1: saldo(), 2: saldo()}


def test_enviar_si_cabe_pasa_a_enviado() -> None:
    assert enviar(Estado.BORRADOR, [validada(4600)], SALDOS) is Estado.ENVIADO


def test_enviar_si_excede_pasa_a_pendiente_gerencia() -> None:
    assert enviar(Estado.BORRADOR, [validada(4601)], SALDOS) is Estado.PENDIENTE_GERENCIA


def test_usar_saldo_de_semanas_futuras_requiere_gerencia() -> None:
    # Lo asignado a la semana 47 no se puede usar en la 46.
    assert enviar(Estado.BORRADOR, [validada(4700)], SALDOS) is Estado.PENDIENTE_GERENCIA


def test_lineas_de_la_misma_partida_se_suman() -> None:
    lineas = [validada(3000), validada(1601)]
    assert partidas_que_exceden(lineas, SALDOS) == [1]
    assert enviar(Estado.BORRADOR, lineas, SALDOS) is Estado.PENDIENTE_GERENCIA


def test_partidas_que_exceden_se_evaluan_por_separado() -> None:
    lineas = [validada(4600, partida=1), validada(5000, partida=2), validada(10, partida=1)]
    assert partidas_que_exceden(lineas, SALDOS) == [1, 2]
    assert partidas_que_exceden([validada(4600, partida=2)], SALDOS) == []


def test_linea_sin_partida_o_sin_valor_no_se_evalua() -> None:
    sin_valor = LineaValidada(LineaPedido("020093", "100-01-1", 1, Decimal(1), FECHA))
    with pytest.raises(ValueError, match="partida y valor"):
        partidas_que_exceden([validada(10, partida=None)], SALDOS)
    with pytest.raises(ValueError, match="partida y valor"):
        partidas_que_exceden([sin_valor], SALDOS)


def test_no_se_envia_un_pedido_con_errores_o_vacio() -> None:
    with pytest.raises(ValueError, match="errores"):
        enviar(Estado.BORRADOR, [validada(10, errores=["Falta la partida."])], SALDOS)
    with pytest.raises(ValueError, match="no tiene líneas"):
        enviar(Estado.BORRADOR, [], SALDOS)


def test_gerente_aprueba_con_justificacion() -> None:
    assert aprobar(Estado.PENDIENTE_GERENCIA, Rol.GERENTE, "Compra urgente") is Estado.ENVIADO


@pytest.mark.parametrize("justificacion", ["", "   "])
def test_gerente_no_aprueba_sin_justificacion(justificacion: str) -> None:
    with pytest.raises(ValueError, match="justificación"):
        aprobar(Estado.PENDIENTE_GERENCIA, Rol.GERENTE, justificacion)


def test_comprador_aprueba_lo_enviado() -> None:
    assert aprobar(Estado.ENVIADO, Rol.COMPRADOR) is Estado.APROBADO


@pytest.mark.parametrize(
    ("estado", "rol"),
    [(Estado.PENDIENTE_GERENCIA, Rol.GERENTE), (Estado.ENVIADO, Rol.COMPRADOR)],
)
def test_rechazar_con_motivo(estado: Estado, rol: Rol) -> None:
    assert rechazar(estado, rol, "Sin justificación de consumo") is Estado.RECHAZADO


@pytest.mark.parametrize(
    ("estado", "rol", "accion"),
    [
        (Estado.PENDIENTE_GERENCIA, Rol.COMPRADOR, "aprobar"),
        (Estado.ENVIADO, Rol.GERENTE, "aprobar"),
        (Estado.ENVIADO, Rol.JEFE, "rechazar"),
    ],
)
def test_rol_que_no_le_corresponde(estado: Estado, rol: Rol, accion: str) -> None:
    with pytest.raises(TransicionInvalida, match="Solo el rol"):
        if accion == "aprobar":
            aprobar(estado, rol, "justificación")
        else:
            rechazar(estado, rol, "motivo")


def test_rechazar_o_anular_sin_motivo() -> None:
    with pytest.raises(ValueError, match="Rechazar un pedido exige un motivo"):
        rechazar(Estado.ENVIADO, Rol.COMPRADOR, " ")
    with pytest.raises(ValueError, match="Anular un pedido exige un motivo"):
        anular(Estado.ENVIADO, "")


def test_aprobado_no_se_edita() -> None:
    with pytest.raises(TransicionInvalida, match="no se puede editar"):
        verificar_editable(Estado.APROBADO)
    verificar_editable(Estado.BORRADOR)


def test_rechazado_no_se_envia() -> None:
    with pytest.raises(TransicionInvalida):
        enviar(Estado.RECHAZADO, [validada(10)], SALDOS)


@pytest.mark.parametrize(
    "estado", [Estado.BORRADOR, Estado.RECHAZADO, Estado.EXPORTADO, Estado.ANULADO]
)
def test_estados_que_no_se_anulan(estado: Estado) -> None:
    with pytest.raises(TransicionInvalida, match="no se puede anular"):
        anular(estado, "motivo")


@pytest.mark.parametrize(
    "estado", [Estado.BORRADOR, Estado.APROBADO, Estado.RECHAZADO, Estado.ANULADO]
)
def test_estados_que_no_se_aprueban_ni_rechazan(estado: Estado) -> None:
    with pytest.raises(TransicionInvalida, match="no se puede aprobar"):
        aprobar(estado, Rol.GERENTE, "justificación")
    with pytest.raises(TransicionInvalida, match="no se puede rechazar"):
        rechazar(estado, Rol.COMPRADOR, "motivo")


@pytest.mark.parametrize("estado", [Estado.PENDIENTE_GERENCIA, Estado.ENVIADO, Estado.APROBADO])
def test_anular_libera_el_presupuesto(estado: Estado) -> None:
    assert compromete_presupuesto(estado)
    anulado = anular(estado, "Ya no se necesita")
    assert anulado is Estado.ANULADO
    assert not compromete_presupuesto(anulado)


def test_rechazar_libera_el_presupuesto() -> None:
    assert not compromete_presupuesto(rechazar(Estado.ENVIADO, Rol.COMPRADOR, "motivo"))


def test_exportar_solo_lo_aprobado() -> None:
    exportado = exportar(Estado.APROBADO)
    assert exportado is Estado.EXPORTADO
    assert compromete_presupuesto(exportado)
    with pytest.raises(TransicionInvalida):
        exportar(Estado.ENVIADO)


def test_borrador_no_compromete() -> None:
    assert not compromete_presupuesto(Estado.BORRADOR)


# Modelo de referencia del diagrama (diseño §4.5) para la propiedad P5.
_ACCIONES: dict[str, Callable[[Estado], Estado]] = {
    "enviar_cabe": lambda e: enviar(e, [validada(10)], SALDOS),
    "enviar_excede": lambda e: enviar(e, [validada(10**9)], SALDOS),
    "aprobar_gerente": lambda e: aprobar(e, Rol.GERENTE, "justificación"),
    "aprobar_comprador": lambda e: aprobar(e, Rol.COMPRADOR),
    "aprobar_jefe": lambda e: aprobar(e, Rol.JEFE, "justificación"),
    "rechazar_gerente": lambda e: rechazar(e, Rol.GERENTE, "motivo"),
    "rechazar_comprador": lambda e: rechazar(e, Rol.COMPRADOR, "motivo"),
    "rechazar_jefe": lambda e: rechazar(e, Rol.JEFE, "motivo"),
    "anular": lambda e: anular(e, "motivo"),
    "exportar": exportar,
}
_VALIDAS = {
    (Estado.BORRADOR, "enviar_cabe"): Estado.ENVIADO,
    (Estado.BORRADOR, "enviar_excede"): Estado.PENDIENTE_GERENCIA,
    (Estado.PENDIENTE_GERENCIA, "aprobar_gerente"): Estado.ENVIADO,
    (Estado.PENDIENTE_GERENCIA, "rechazar_gerente"): Estado.RECHAZADO,
    (Estado.ENVIADO, "aprobar_comprador"): Estado.APROBADO,
    (Estado.ENVIADO, "rechazar_comprador"): Estado.RECHAZADO,
    (Estado.APROBADO, "exportar"): Estado.EXPORTADO,
    (Estado.PENDIENTE_GERENCIA, "anular"): Estado.ANULADO,
    (Estado.ENVIADO, "anular"): Estado.ANULADO,
    (Estado.APROBADO, "anular"): Estado.ANULADO,
}


@pytest.mark.propiedad
def test_p5_transiciones_validas_siguen_el_diagrama_e_invalidas_fallan() -> None:
    """P5: toda secuencia de transiciones válidas termina en un estado del diagrama, y las
    inválidas siempre fallan sin cambiar el estado."""
    from hypothesis import given
    from hypothesis import strategies as st

    @given(st.lists(st.sampled_from(sorted(_ACCIONES)), max_size=25))
    def propiedad(acciones: list[str]) -> None:
        estado = Estado.BORRADOR
        for accion in acciones:
            esperado = _VALIDAS.get((estado, accion))
            if esperado is None:
                with pytest.raises(TransicionInvalida):
                    _ACCIONES[accion](estado)
            else:
                estado = _ACCIONES[accion](estado)
                assert estado is esperado
        assert estado in Estado

    propiedad()
