"""Consultas fijas de solo lectura a Softland para el MCP de desarrollo.

La garantía de solo lectura (SQL fijo, filtro de SELECT, READ UNCOMMITTED y ROLLBACK) está en
``sincronizador.lectura`` y se comparte con el sincronizador.
"""

import re
from typing import Any

from sincronizador.lectura import (
    Conexion,
    ConsultaNoPermitidaError,
    ejecutar,
    validar_solo_lectura,
)

__all__ = ["Conexion", "ConsultaNoPermitidaError", "ejecutar", "validar_solo_lectura"]

ESQUEMA = "SAYONARA"
LIMITE_MAXIMO = 20
LARGO_MAXIMO_TEXTO = 50

_NOMBRE_TABLA = re.compile(r"^[A-Z0-9_]{1,128}$")


def _texto(valor: str) -> str:
    valor = valor.strip()
    if len(valor) > LARGO_MAXIMO_TEXTO:
        raise ConsultaNoPermitidaError(f"El texto no puede superar {LARGO_MAXIMO_TEXTO} caracteres")
    return valor


def _patron_like(texto: str) -> str:
    """Escapa los comodines de LIKE para que el texto se busque literal."""
    escapado = texto.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]")
    return f"%{escapado}%"


def _limite(limite: int) -> int:
    return max(1, min(int(limite), LIMITE_MAXIMO))


def listar_tablas(conexion: Conexion, filtro: str = "") -> list[str]:
    filas = ejecutar(
        conexion,
        "SELECT TOP 100 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = ? AND TABLE_NAME LIKE ? ORDER BY TABLE_NAME",
        ESQUEMA,
        _patron_like(_texto(filtro).upper()),
    )
    return [str(f["table_name"]) for f in filas]


def describir_tabla(conexion: Conexion, tabla: str) -> list[dict[str, Any]]:
    tabla = _texto(tabla).upper()
    if not _NOMBRE_TABLA.match(tabla):
        raise ConsultaNoPermitidaError("Nombre de tabla inválido")
    return ejecutar(
        conexion,
        "SELECT COLUMN_NAME AS columna, DATA_TYPE AS tipo, IS_NULLABLE AS admite_nulos, "
        "CHARACTER_MAXIMUM_LENGTH AS largo FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
        ESQUEMA,
        tabla,
    )


def buscar_articulos(conexion: Conexion, texto: str, limite: int = 10) -> list[dict[str, Any]]:
    patron = _patron_like(_texto(texto))
    return ejecutar(
        conexion,
        f"SELECT TOP {_limite(limite)} ARTICULO AS codigo, DESCRIPCION AS descripcion, "  # noqa: S608 - el límite es un entero acotado
        "UNIDAD_ALMACEN AS unidad, ACTIVO AS activo FROM SAYONARA.ARTICULO "
        "WHERE ARTICULO LIKE ? OR DESCRIPCION LIKE ? ORDER BY ARTICULO",
        patron,
        patron,
    )


def buscar_centros_costo(conexion: Conexion, texto: str, limite: int = 10) -> list[dict[str, Any]]:
    patron = _patron_like(_texto(texto))
    return ejecutar(
        conexion,
        f"SELECT TOP {_limite(limite)} CENTRO_COSTO AS codigo, DESCRIPCION AS descripcion, "  # noqa: S608 - el límite es un entero acotado
        "ACEPTA_DATOS AS acepta_datos FROM SAYONARA.CENTRO_COSTO "
        "WHERE CENTRO_COSTO LIKE ? OR DESCRIPCION LIKE ? ORDER BY CENTRO_COSTO",
        patron,
        patron,
    )


def unidades_de_medida(conexion: Conexion) -> list[dict[str, Any]]:
    return ejecutar(
        conexion,
        "SELECT UNIDAD_ALMACEN AS unidad, COUNT(*) AS articulos FROM SAYONARA.ARTICULO "
        "GROUP BY UNIDAD_ALMACEN ORDER BY COUNT(*) DESC",
    )
