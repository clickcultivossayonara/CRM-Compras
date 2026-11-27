"""Consultas fijas a Softland (esquema SAYONARA), solo SELECT (D1, R6.2).

Las tablas y columnas son las confirmadas en Almacen (``C:\\Apps\\Almacen\\app.py``).
"""

from datetime import date
from typing import Any

from sincronizador.lectura import Conexion, ejecutar

ARTICULOS = (
    "SELECT ARTICULO AS codigo, DESCRIPCION AS descripcion, UNIDAD_ALMACEN AS unidad, "
    "ACTIVO AS activo FROM SAYONARA.ARTICULO ORDER BY ARTICULO"
)

CENTROS = (
    "SELECT CENTRO_COSTO AS codigo, DESCRIPCION AS descripcion, ACEPTA_DATOS AS acepta_datos "
    "FROM SAYONARA.CENTRO_COSTO ORDER BY CENTRO_COSTO"
)

# Última compra de cada artículo con cualquier proveedor (en Almacen es por artículo y
# proveedor). La normalización del 020215 se hace en Python con dominio.precios.
PRECIOS = (
    "WITH Compras AS ("
    " SELECT ocl.ARTICULO AS articulo, ocl.PRECIO_UNITARIO AS precio_unitario,"
    " ocl.COMENTARIO AS comentario, CAST(oc.FECHA AS DATE) AS fecha_compra,"
    " oc.ORDEN_COMPRA AS orden_compra,"
    " ROW_NUMBER() OVER (PARTITION BY ocl.ARTICULO"
    " ORDER BY oc.FECHA DESC, oc.ORDEN_COMPRA DESC) AS rn"
    " FROM SAYONARA.ORDEN_COMPRA oc"
    " INNER JOIN SAYONARA.ORDEN_COMPRA_LINEA ocl ON oc.ORDEN_COMPRA = ocl.ORDEN_COMPRA"
    " WHERE oc.FECHA >= ?"
    ") SELECT articulo, precio_unitario, comentario, fecha_compra, orden_compra"
    " FROM Compras WHERE rn = 1 ORDER BY articulo"
)


def leer_articulos(conexion: Conexion) -> list[dict[str, Any]]:
    return ejecutar(conexion, ARTICULOS)


def leer_centros(conexion: Conexion) -> list[dict[str, Any]]:
    return ejecutar(conexion, CENTROS)


def leer_precios(conexion: Conexion, desde: date) -> list[dict[str, Any]]:
    """Última compra de cada artículo desde una fecha (como Almacen: desde el año anterior)."""
    return ejecutar(conexion, PRECIOS, desde)
