"""Servidor MCP `softland-lectura`. Credenciales solo por variables de entorno."""

import os
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from mcp_softland import consultas

SOLO_LECTURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)
VARIABLES = ("SOFTLAND_SERVIDOR", "SOFTLAND_USUARIO", "SOFTLAND_CLAVE")

servidor: MCPServer = MCPServer(
    "softland-lectura",
    instructions="Consultas de solo lectura al ERP Softland (esquema SAYONARA). No modifica datos.",
)


def cadena_conexion(entorno: dict[str, str]) -> str:
    faltantes = [v for v in VARIABLES if not entorno.get(v)]
    if faltantes:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(faltantes)}")
    driver = entorno.get("SOFTLAND_DRIVER", "ODBC Driver 17 for SQL Server")
    return (
        f"DRIVER={{{driver}}};SERVER={entorno['SOFTLAND_SERVIDOR']};"
        f"DATABASE={entorno.get('SOFTLAND_BASE', 'SAYOERP')};"
        f"UID={entorno['SOFTLAND_USUARIO']};PWD={entorno['SOFTLAND_CLAVE']};"
        "ApplicationIntent=ReadOnly;"
    )


def _conectar() -> Any:  # pragma: no cover - requiere el servidor SQL real
    import pyodbc  # solo al conectar: las pruebas no necesitan el driver

    conexion = pyodbc.connect(
        cadena_conexion(dict(os.environ)), timeout=10, autocommit=False, readonly=True
    )
    conexion.timeout = 15
    return conexion


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
