"""Normalización del precio de última compra (reglas D2 y D4, R6.4)."""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Artículo que se compra por empaque: su precio se divide por el factor del comentario.
ARTICULO_POR_FACTOR = "020215"

# Igual que Almacen: desde el primer dígito, la secuencia de dígitos y puntos (hasta 20).
_FACTOR = re.compile(r"[0-9][0-9.]{0,19}")


def normalizar(articulo: str, precio_unitario: Decimal, comentario: str | None) -> int | None:
    """Precio por unidad en pesos enteros, o None si el factor del comentario no es válido."""
    precio = precio_unitario
    if articulo == ARTICULO_POR_FACTOR and comentario:
        coincidencia = _FACTOR.search(comentario)
        if coincidencia:
            try:
                factor = Decimal(coincidencia.group())
            except InvalidOperation:
                return None
            if factor == 0:
                return None
            precio = precio_unitario / factor
    return int(precio.quantize(Decimal(1), rounding=ROUND_HALF_UP))
