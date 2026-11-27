"""Lectura de Softland garantizada en el código (D1).

El usuario de conexión disponible tiene permisos de escritura (es el de Almacen), por eso la
solo lectura se impone aquí: SQL fijo con parámetros, un filtro que rechaza todo lo que no sea
SELECT, nivel READ UNCOMMITTED para no bloquear el ERP y ROLLBACK siempre al terminar.
"""

import re
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

VARIABLES = ("SOFTLAND_SERVIDOR", "SOFTLAND_USUARIO", "SOFTLAND_CLAVE")

_PALABRAS_PROHIBIDAS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE"
    r"|GRANT|REVOKE|DENY|INTO|BACKUP|RESTORE|DBCC)\b",
    re.IGNORECASE,
)


class Cursor(Protocol):
    description: Any

    def execute(self, sql: str, *params: Any) -> Any: ...
    def fetchall(self) -> Sequence[Sequence[Any]]: ...


class Conexion(Protocol):
    def cursor(self) -> Cursor: ...
    def rollback(self) -> None: ...


class ConsultaNoPermitidaError(ValueError):
    """La consulta no es de solo lectura o los parámetros no son válidos."""


def validar_solo_lectura(sql: str) -> None:
    limpio = sql.strip()
    if not limpio.upper().startswith(("SELECT", "WITH")):
        raise ConsultaNoPermitidaError("Solo se permiten consultas SELECT")
    if ";" in limpio or _PALABRAS_PROHIBIDAS.search(limpio):
        raise ConsultaNoPermitidaError("La consulta contiene instrucciones no permitidas")


def ejecutar(conexion: Conexion, sql: str, *params: Any) -> list[dict[str, Any]]:
    """Ejecuta una consulta de solo lectura y devuelve filas con columnas en minúsculas."""
    validar_solo_lectura(sql)
    cursor = conexion.cursor()
    try:
        # Lectura sin bloquear al ERP; nada de lo que se ejecuta aquí se confirma.
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        cursor.execute(sql, *params)
        columnas = [c[0].lower() for c in cursor.description]
        return [dict(zip(columnas, fila, strict=True)) for fila in cursor.fetchall()]
    finally:
        conexion.rollback()


def cadena_conexion(entorno: Mapping[str, str]) -> str:
    """Cadena ODBC desde variables de entorno; nunca se escribe una credencial en el código."""
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


def conectar(entorno: Mapping[str, str]) -> Any:  # pragma: no cover - requiere el servidor real
    import pyodbc  # solo al conectar: las pruebas no necesitan el driver

    conexion = pyodbc.connect(cadena_conexion(entorno), timeout=10, autocommit=False, readonly=True)
    conexion.timeout = 60
    return conexion
