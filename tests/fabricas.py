"""Fábricas de datos ficticios compartidas por las pruebas."""

ANCHO_COMPLETO = 0xFF10
ARABIGOS = 0x0660


def otros_digitos(texto: str, cero: int) -> str:
    """Cambia los dígitos ASCII por los de otro alfabeto, a partir del código de su cero."""
    return "".join(chr(cero + int(c)) if c.isdigit() else c for c in texto)
