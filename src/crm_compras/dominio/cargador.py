"""Cargador consolidado para Softland (reglas D14 y D17).

Arma las hojas y filas del archivo; la escritura del ``.xlsx`` va en ``web/``.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from crm_compras.dominio.pedido import BODEGA_PROHIBIDOS

ENCABEZADOS = (
    "Artículo",
    "Descripción",
    "Centro Costo",
    "Descripción Centro de Costo",
    "Cantidad",
    "Fecha Requerida",
    "Comentario",
)
HOJAS = {1: "La Union", 2: "La Ceja", BODEGA_PROHIBIDOS: "Prohibidos"}
BODEGAS_DE_COMPRAS = frozenset({1, 2})

# Solo dígitos ASCII: \d también acepta dígitos de otros alfabetos.
_ARTICULO = re.compile(r"[0-9]{6}")
_CENTRO_COSTO = re.compile(r"[0-9]{3}-[0-9]{2}-[0-9]")

FilaCargador = tuple[str, str, str, str, int | Decimal, date, str]


@dataclass(frozen=True)
class LineaCargador:
    """Línea de un pedido aprobado, con las descripciones de Softland."""

    linea_id: int
    articulo: str
    descripcion: str
    centro_costo: str
    descripcion_centro: str
    cantidad: Decimal
    fecha_requerida: date
    comentario: str
    prohibido: bool
    bodega: int | None
    lote_id: int | None = None


class CargadorError(ValueError):
    """El cargador no se genera; ``problemas`` dice qué falta en cada línea."""

    def __init__(self, problemas: list[str]) -> None:
        super().__init__("No se genera el cargador: " + " ".join(problemas))
        self.problemas = problemas


def lineas_para_lote(lineas: Sequence[LineaCargador]) -> list[LineaCargador]:
    """Líneas que pueden entrar en un lote nuevo: las que aún no se exportaron."""
    return [linea for linea in lineas if linea.lote_id is None]


def armar_cargador(lineas: Sequence[LineaCargador]) -> dict[str, list[FilaCargador]]:
    """Hojas por bodega con sus filas en el orden de la plantilla, ordenadas por línea."""
    if not lineas:
        raise CargadorError(["No hay líneas para exportar."])
    problemas = [p for linea in lineas for p in _problemas(linea)]
    if problemas:
        raise CargadorError(problemas)

    hojas: dict[str, list[FilaCargador]] = {}
    for bodega, nombre in sorted(HOJAS.items()):
        filas = [_fila(linea) for linea in sorted(lineas, key=_id) if linea.bodega == bodega]
        if filas:
            hojas[nombre] = filas
    return hojas


def _id(linea: LineaCargador) -> int:
    return linea.linea_id


def _problemas(linea: LineaCargador) -> list[str]:
    prefijo = f"Línea {linea.linea_id}:"
    problemas = []
    if not _ARTICULO.fullmatch(linea.articulo):
        problemas.append(f"{prefijo} el artículo {linea.articulo!r} no tiene 6 dígitos.")
    if not _CENTRO_COSTO.fullmatch(linea.centro_costo):
        problemas.append(
            f"{prefijo} el centro de costo {linea.centro_costo!r} no tiene el formato NNN-NN-N."
        )
    if linea.prohibido and linea.bodega != BODEGA_PROHIBIDOS:
        problemas.append(f"{prefijo} el artículo es prohibido y debe ir a la bodega 5.")
    elif not linea.prohibido and linea.bodega is None:
        problemas.append(f"{prefijo} falta asignar la bodega.")
    elif not linea.prohibido and linea.bodega not in BODEGAS_DE_COMPRAS:
        problemas.append(f"{prefijo} la bodega {linea.bodega} no es 1 ni 2.")
    return problemas


def _fila(linea: LineaCargador) -> FilaCargador:
    cantidad: int | Decimal = linea.cantidad
    if linea.cantidad == linea.cantidad.to_integral_value():
        cantidad = int(linea.cantidad)
    return (
        linea.articulo,
        linea.descripcion,
        linea.centro_costo,
        linea.descripcion_centro,
        cantidad,
        linea.fecha_requerida,
        linea.comentario,
    )
