"""Pedido: validación de líneas (reglas D2, D4, D7, D10, D11, D13, D14 y D15)."""

import re
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from crm_compras.dominio.calendario import Semana, mes_de_semana, semana_de

BODEGA_PROHIBIDOS = 5
UNIDADES_DECIMALES = frozenset({"KL", "CC", "MT", "GR", "GL", "LB", "LT"})
DECIMALES_CANTIDAD = 2

_CODIGO_ARTICULO = re.compile(r"\d{6}")


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
