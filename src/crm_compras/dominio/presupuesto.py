"""Reparto y control del presupuesto por semana (reglas D5 y D9).

Los valores de una partida van en listas por semana del año: la posición i es la semana i + 1.
"""

from collections.abc import Sequence
from itertools import accumulate

SEMANAS_VALIDAS = (4, 5)


def repartir_mes(valor_mes: int, n_semanas: int) -> list[int]:
    """Divide el valor del mes entre sus semanas; el residuo va a la última semana."""
    if n_semanas not in SEMANAS_VALIDAS:
        raise ValueError(f"Un mes tiene 4 o 5 semanas, no {n_semanas}.")
    if valor_mes < 0:
        raise ValueError(f"El valor del mes no puede ser negativo: {valor_mes}.")
    cuota, residuo = divmod(valor_mes, n_semanas)
    return [cuota] * (n_semanas - 1) + [cuota + residuo]


def saldos(asignado: Sequence[int], consumido: Sequence[int]) -> list[int]:
    """Saldo acumulado de cada semana: lo asignado menos lo consumido hasta esa semana."""
    if len(asignado) != len(consumido):
        raise ValueError("Lo asignado y lo consumido deben tener las mismas semanas.")
    return list(accumulate(a - c for a, c in zip(asignado, consumido, strict=True)))


def disponibles(asignado: Sequence[int], consumido: Sequence[int]) -> list[int]:
    """Disponible de cada semana: el menor saldo desde esa semana hasta el fin del año."""
    return list(accumulate(reversed(saldos(asignado, consumido)), min))[::-1]


def cabe(
    asignado: Sequence[int], consumido: Sequence[int], lineas: Sequence[tuple[int, int]]
) -> bool:
    """Indica si las líneas de un pedido (posición de la semana, valor) caben sin aprobación.

    Las líneas se evalúan juntas: se suman por semana y cabe si ningún saldo queda negativo
    desde la primera semana afectada hasta el fin del año. Equivale a exigir, línea por
    línea, valor ≤ disponible de su semana.
    """
    if not lineas:
        return True
    consumo = list(consumido)
    for semana, valor in lineas:
        if not 0 <= semana < len(consumo):
            raise ValueError(f"La semana {semana + 1} está fuera del año.")
        consumo[semana] += valor
    primera = min(semana for semana, _ in lineas)
    return disponibles(asignado, consumo)[primera] >= 0
