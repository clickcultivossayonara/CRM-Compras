"""Pedido: validación de líneas y estados (reglas D2, D4, D7 a D11 y D13 a D16)."""

import re
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from crm_compras.dominio.calendario import Semana, mes_de_semana, semana_de
from crm_compras.dominio.presupuesto import cabe

BODEGA_PROHIBIDOS = 5
UNIDADES_DECIMALES = frozenset({"KL", "CC", "MT", "GR", "GL", "LB", "LT"})
DECIMALES_CANTIDAD = 2

# Solo dígitos ASCII: \d también acepta dígitos de otros alfabetos.
_CODIGO_ARTICULO = re.compile(r"[0-9]{6}")


@dataclass(frozen=True)
class Articulo:
    codigo: str
    descripcion: str
    unidad: str
    activo: bool


@dataclass(frozen=True)
class LineaPedido:
    articulo: str
    centro_costo: str
    partida_id: int | None
    cantidad: Decimal
    fecha_requerida: date
    comentario: str = ""


@dataclass(frozen=True)
class ContextoValidacion:
    """Datos de Softland y de la base propia que necesita la validación."""

    hoy: date
    articulos: Mapping[str, Articulo]
    precios: Mapping[str, int]
    """Precio normalizado por artículo; un artículo sin compras previas no está."""
    centros_costo: Set[str]
    centros_del_jefe: Set[str]
    partidas_del_jefe: Mapping[int, int]
    """Año del presupuesto de cada partida asignada al jefe."""
    anios_con_presupuesto: Set[int]
    prohibidos: Set[str]
    otros_pedidos: Set[tuple[str, str, Semana]] = frozenset()
    """Artículo, centro de costo y semana de las líneas de otros pedidos activos."""
    unidades_decimales: Set[str] = UNIDADES_DECIMALES


@dataclass
class LineaValidada:
    linea: LineaPedido
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    valor: int | None = None
    """Cantidad por precio en pesos enteros, antes de IVA; None si no se puede calcular."""
    bodega: int | None = None
    """Bodega 5 si el artículo está prohibido; las demás las define Compras."""


def anio_presupuesto(fecha: date) -> int:
    """Año del presupuesto que consume una fecha: el del mes de su semana ISO."""
    return mes_de_semana(semana_de(fecha)).anio


def valor_linea(cantidad: Decimal, precio: int) -> int:
    return int((cantidad * precio).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def validar_linea(linea: LineaPedido, contexto: ContextoValidacion) -> LineaValidada:
    """Valida una línea y reporta todos sus problemas juntos."""
    resultado = LineaValidada(linea)
    errores = resultado.errores
    articulo = _validar_articulo(linea.articulo, contexto, errores)
    _validar_centro(linea.centro_costo, contexto, errores)
    _validar_partida(linea, contexto, errores)
    _validar_cantidad(linea.cantidad, articulo, contexto, errores)
    _validar_fecha(linea.fecha_requerida, contexto, errores)

    precio = contexto.precios.get(linea.articulo)
    if articulo is not None and precio is None:
        errores.append(f"El artículo {linea.articulo} no tiene compras previas y no tiene precio.")
    if precio is not None and linea.cantidad > 0:
        resultado.valor = valor_linea(linea.cantidad, precio)

    if linea.articulo in contexto.prohibidos:
        resultado.bodega = BODEGA_PROHIBIDOS
    if (linea.articulo, linea.centro_costo, semana_de(linea.fecha_requerida)) in (
        contexto.otros_pedidos
    ):
        resultado.advertencias.append(
            f"El artículo {linea.articulo} con el centro de costo {linea.centro_costo} ya está "
            "en otro pedido de la misma semana."
        )
    return resultado


def validar_pedido(
    lineas: Sequence[LineaPedido], contexto: ContextoValidacion
) -> list[LineaValidada]:
    """Valida cada línea y agrega el error de artículo y centro de costo repetidos."""
    resultados = [validar_linea(linea, contexto) for linea in lineas]
    primera: dict[tuple[str, str], int] = {}
    for numero, resultado in enumerate(resultados, start=1):
        clave = (resultado.linea.articulo, resultado.linea.centro_costo)
        if clave in primera:
            resultado.errores.append(
                f"El artículo {clave[0]} con el centro de costo {clave[1]} ya está en la "
                f"línea {primera[clave]} del pedido."
            )
        else:
            primera[clave] = numero
    return resultados


def _validar_articulo(
    codigo: str, contexto: ContextoValidacion, errores: list[str]
) -> Articulo | None:
    if not _CODIGO_ARTICULO.fullmatch(codigo):
        errores.append(f"El código {codigo!r} no tiene el formato de 6 dígitos.")
        return None
    articulo = contexto.articulos.get(codigo)
    if articulo is None:
        errores.append(f"El artículo {codigo} no existe en Softland.")
        return None
    if not articulo.activo:
        errores.append(f"El artículo {codigo} está inactivo en Softland.")
    return articulo


def _validar_centro(codigo: str, contexto: ContextoValidacion, errores: list[str]) -> None:
    if codigo not in contexto.centros_costo:
        errores.append(f"El centro de costo {codigo} no existe en Softland.")
    elif codigo not in contexto.centros_del_jefe:
        errores.append(f"El centro de costo {codigo} no está asignado al jefe.")


def _validar_partida(linea: LineaPedido, contexto: ContextoValidacion, errores: list[str]) -> None:
    if linea.partida_id is None:
        errores.append("Falta la partida presupuestal.")
        return
    anio = contexto.partidas_del_jefe.get(linea.partida_id)
    if anio is None:
        errores.append("La partida no está asignada al jefe.")
    elif anio != anio_presupuesto(linea.fecha_requerida):
        errores.append(
            f"La partida es del presupuesto {anio} y la fecha requerida consume el de "
            f"{anio_presupuesto(linea.fecha_requerida)}."
        )


def _validar_cantidad(
    cantidad: Decimal, articulo: Articulo | None, contexto: ContextoValidacion, errores: list[str]
) -> None:
    if cantidad <= 0:
        errores.append("La cantidad debe ser mayor que cero.")
        return
    exponente = cantidad.normalize().as_tuple().exponent
    decimales = -exponente if isinstance(exponente, int) else 0
    if articulo is not None and articulo.unidad not in contexto.unidades_decimales:
        if decimales > 0:
            errores.append(f"La unidad {articulo.unidad} solo admite cantidades enteras.")
    elif decimales > DECIMALES_CANTIDAD:
        errores.append(f"La cantidad admite máximo {DECIMALES_CANTIDAD} decimales.")


def _validar_fecha(fecha: date, contexto: ContextoValidacion, errores: list[str]) -> None:
    if fecha < contexto.hoy:
        errores.append("La fecha requerida no puede ser anterior a hoy.")
    if anio_presupuesto(fecha) not in contexto.anios_con_presupuesto:
        errores.append(f"No hay presupuesto cargado para {anio_presupuesto(fecha)}.")


class Estado(StrEnum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    PENDIENTE_GERENCIA = "pendiente_gerencia"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    EXPORTADO = "exportado"
    ANULADO = "anulado"


class Rol(StrEnum):
    JEFE = "jefe"
    COMPRADOR = "comprador"
    GERENTE = "gerente"
    ADMINISTRADOR = "administrador"


ESTADOS_QUE_COMPROMETEN = frozenset(
    {Estado.PENDIENTE_GERENCIA, Estado.ENVIADO, Estado.APROBADO, Estado.EXPORTADO}
)
ESTADOS_ANULABLES = frozenset({Estado.PENDIENTE_GERENCIA, Estado.ENVIADO, Estado.APROBADO})

# Quién aprueba o rechaza en cada estado.
_REVISOR = {Estado.PENDIENTE_GERENCIA: Rol.GERENTE, Estado.ENVIADO: Rol.COMPRADOR}
_APROBADO_A = {Estado.PENDIENTE_GERENCIA: Estado.ENVIADO, Estado.ENVIADO: Estado.APROBADO}


class TransicionInvalida(Exception):  # noqa: N818 (nombre fijado en el diseño §4.5)
    """Transición que no está en el diagrama de estados o que no le corresponde al rol."""


@dataclass(frozen=True)
class SaldoPartida:
    """Asignado y consumido por semana de una partida (posición i = semana i + 1)."""

    asignado: Sequence[int]
    consumido: Sequence[int]


def compromete_presupuesto(estado: Estado) -> bool:
    """Un pedido compromete presupuesto desde que sale de borrador hasta que se rechaza o anula."""
    return estado in ESTADOS_QUE_COMPROMETEN


def verificar_editable(estado: Estado) -> None:
    if estado is not Estado.BORRADOR:
        raise TransicionInvalida(f"Un pedido en {estado} no se puede editar.")


def partidas_que_exceden(
    lineas: Sequence[LineaValidada], saldos: Mapping[int, SaldoPartida]
) -> list[int]:
    """Partidas cuyas líneas, sumadas por semana, no caben en lo disponible."""
    por_partida: dict[int, list[tuple[int, int]]] = {}
    for validada in lineas:
        linea = validada.linea
        if linea.partida_id is None or validada.valor is None:
            raise ValueError("Solo se evalúan líneas con partida y valor.")
        semana = semana_de(linea.fecha_requerida).numero - 1
        por_partida.setdefault(linea.partida_id, []).append((semana, validada.valor))
    return [
        partida
        for partida, usos in sorted(por_partida.items())
        if not cabe(saldos[partida].asignado, saldos[partida].consumido, usos)
    ]


def enviar(
    estado: Estado, lineas: Sequence[LineaValidada], saldos: Mapping[int, SaldoPartida]
) -> Estado:
    """Envía un borrador sin errores: a Gerencia si alguna partida excede lo disponible."""
    verificar_editable(estado)
    if not lineas:
        raise ValueError("El pedido no tiene líneas.")
    if any(validada.errores for validada in lineas):
        raise ValueError("El pedido tiene líneas con errores.")
    if partidas_que_exceden(lineas, saldos):
        return Estado.PENDIENTE_GERENCIA
    return Estado.ENVIADO


def aprobar(estado: Estado, rol: Rol, justificacion: str = "") -> Estado:
    """Gerente aprueba lo pendiente con justificación; Comprador aprueba lo enviado."""
    _verificar_revisor(estado, rol, "aprobar")
    if estado is Estado.PENDIENTE_GERENCIA and not justificacion.strip():
        raise ValueError("Aprobar un pedido que excede el presupuesto exige una justificación.")
    return _APROBADO_A[estado]


def rechazar(estado: Estado, rol: Rol, motivo: str) -> Estado:
    _verificar_revisor(estado, rol, "rechazar")
    _exigir_motivo(motivo, "Rechazar")
    return Estado.RECHAZADO


def anular(estado: Estado, motivo: str) -> Estado:
    if estado not in ESTADOS_ANULABLES:
        raise TransicionInvalida(f"Un pedido en {estado} no se puede anular.")
    _exigir_motivo(motivo, "Anular")
    return Estado.ANULADO


def exportar(estado: Estado) -> Estado:
    if estado is not Estado.APROBADO:
        raise TransicionInvalida(f"Solo se exportan pedidos aprobados, no en {estado}.")
    return Estado.EXPORTADO


def _verificar_revisor(estado: Estado, rol: Rol, accion: str) -> None:
    revisor = _REVISOR.get(estado)
    if revisor is None:
        raise TransicionInvalida(f"Un pedido en {estado} no se puede {accion}.")
    if rol is not revisor:
        raise TransicionInvalida(f"Solo el rol {revisor} puede {accion} un pedido en {estado}.")


def _exigir_motivo(motivo: str, accion: str) -> None:
    if not motivo.strip():
        raise ValueError(f"{accion} un pedido exige un motivo.")
