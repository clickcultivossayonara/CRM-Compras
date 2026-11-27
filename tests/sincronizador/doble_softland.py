"""Doble de prueba de Softland: responde las consultas del sincronizador con datos ficticios.

Registra cada consulta, sus parámetros y cada ROLLBACK, para comprobar que solo se lee.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

COLUMNAS = {
    "ARTICULO": ("codigo", "descripcion", "unidad", "activo"),
    "CENTRO_COSTO": ("codigo", "descripcion", "acepta_datos"),
    "ORDEN_COMPRA": ("articulo", "precio_unitario", "comentario", "fecha_compra", "orden_compra"),
}


def articulos_ficticios() -> list[tuple[Any, ...]]:
    return [
        ("020093  ", "ARTICULO FICTICIO A ", "und", "S"),
        ("020215", "ARTICULO POR EMPAQUE", "UND", "S"),
        ("000001", "ARTICULO INACTIVO", "LT", "N"),
        ("12345", "CODIGO MAL FORMADO", "UND", "S"),
    ]


def centros_ficticios() -> list[tuple[Any, ...]]:
    return [
        ("513-01-2", "CENTRO FICTICIO", "S"),
        ("100-01-1", "CENTRO QUE NO ACEPTA DATOS", "N"),
        ("51301", "CENTRO MAL FORMADO", "S"),
    ]


def precios_ficticios() -> list[tuple[Any, ...]]:
    return [
        ("020093", Decimal("1500.40"), None, datetime(2026, 10, 20), "OC-1 "),
        ("020215", Decimal("24000"), "CAJA X 24", datetime(2026, 9, 1), "OC-2"),
        ("999999", Decimal("100"), None, datetime(2026, 8, 1), "OC-3"),
    ]


@dataclass
class CursorFicticio:
    conexion: "ConexionFicticia"
    description: Any = None
    _filas: list[tuple[Any, ...]] = field(default_factory=list)

    def execute(self, sql: str, *params: Any) -> None:
        self.conexion.consultas.append((sql, params))
        if sql.startswith("SET TRANSACTION"):
            return
        tabla = next(
            t for t in ("ORDEN_COMPRA", "CENTRO_COSTO", "ARTICULO") if f"SAYONARA.{t}" in sql
        )
        self.description = [(columna,) for columna in COLUMNAS[tabla]]
        self._filas = list(self.conexion.filas[tabla])

    def fetchall(self) -> Sequence[Sequence[Any]]:
        return self._filas


@dataclass
class ConexionFicticia:
    filas: dict[str, list[tuple[Any, ...]]] = field(
        default_factory=lambda: {
            "ARTICULO": articulos_ficticios(),
            "CENTRO_COSTO": centros_ficticios(),
            "ORDEN_COMPRA": precios_ficticios(),
        }
    )
    consultas: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)
    rollbacks: int = 0
    cerrada: bool = False

    def cursor(self) -> CursorFicticio:
        return CursorFicticio(self)

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.cerrada = True
