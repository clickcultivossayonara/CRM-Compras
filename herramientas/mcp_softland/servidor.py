"""Servidor MCP `softland-lectura`. Credenciales solo por variables de entorno."""

import os
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from mcp_softland import consultas
from sincronizador.lectura import VARIABLES, cadena_conexion, conectar

__all__ = ["VARIABLES", "cadena_conexion", "servidor"]

SOLO_LECTURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)

servidor: MCPServer = MCPServer(
    "softland-lectura",
    instructions="Consultas de solo lectura al ERP Softland (esquema SAYONARA). No modifica datos.",
)


def _conectar() -> Any:  # pragma: no cover - requiere el servidor SQL real
    return conectar(dict(os.environ))


def _con_conexion(funcion: Callable[..., Any], *args: Any) -> Any:
    conexion = _conectar()
    try:
        return funcion(conexion, *args)
    finally:
        conexion.close()


@servidor.tool(annotations=SOLO_LECTURA)
def listar_tablas(filtro: str = "") -> list[str]:
    """Tablas del esquema SAYONARA cuyo nombre contiene el filtro (máximo 100)."""
    return list(_con_conexion(consultas.listar_tablas, filtro))


@servidor.tool(annotations=SOLO_LECTURA)
def describir_tabla(tabla: str) -> list[dict[str, Any]]:
    """Columnas, tipos, nulabilidad y largo de una tabla del esquema SAYONARA."""
    return list(_con_conexion(consultas.describir_tabla, tabla))


@servidor.tool(annotations=SOLO_LECTURA)
def buscar_articulos(texto: str, limite: int = 10) -> list[dict[str, Any]]:
    """Artículos por código o descripción: código, descripción, unidad y activo (máx. 20)."""
    return list(_con_conexion(consultas.buscar_articulos, texto, limite))


@servidor.tool(annotations=SOLO_LECTURA)
def buscar_centros_costo(texto: str, limite: int = 10) -> list[dict[str, Any]]:
    """Centros de costo por código o descripción (máximo 20)."""
    return list(_con_conexion(consultas.buscar_centros_costo, texto, limite))


@servidor.tool(annotations=SOLO_LECTURA)
def unidades_de_medida() -> list[dict[str, Any]]:
    """Unidades de medida en uso y cuántos artículos tiene cada una."""
    return list(_con_conexion(consultas.unidades_de_medida))


if __name__ == "__main__":  # pragma: no cover
    servidor.run("stdio")
