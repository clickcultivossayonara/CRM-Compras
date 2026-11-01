"""Reparto y control del presupuesto por semana (regla D5)."""

SEMANAS_VALIDAS = (4, 5)


def repartir_mes(valor_mes: int, n_semanas: int) -> list[int]:
    """Divide el valor del mes entre sus semanas; el residuo va a la última semana."""
    if n_semanas not in SEMANAS_VALIDAS:
        raise ValueError(f"Un mes tiene 4 o 5 semanas, no {n_semanas}.")
    if valor_mes < 0:
        raise ValueError(f"El valor del mes no puede ser negativo: {valor_mes}.")
    cuota, residuo = divmod(valor_mes, n_semanas)
    return [cuota] * (n_semanas - 1) + [cuota + residuo]
