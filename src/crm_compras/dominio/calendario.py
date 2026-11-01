"""Calendario de semanas ISO para el presupuesto (regla D5).

Las semanas van de lunes a domingo. Una semana que cruza dos meses pertenece al mes en que
cae su jueves, igual que en el Excel de presupuesto.
"""

from datetime import date, timedelta
from typing import NamedTuple


class Semana(NamedTuple):
    """Semana ISO: año ISO y número de semana (1 a 53)."""

    anio: int
    numero: int

    def __str__(self) -> str:
        return f"{self.anio}-W{self.numero:02d}"


class Mes(NamedTuple):
    anio: int
    mes: int


def semana_de(fecha: date) -> Semana:
    anio, numero, _ = fecha.isocalendar()
    return Semana(anio, numero)


def lunes_de(semana: Semana) -> date:
    """Primer día de la semana. Falla si la semana no existe en ese año ISO."""
    return date.fromisocalendar(semana.anio, semana.numero, 1)


def mes_de_semana(semana: Semana) -> Mes:
    jueves = lunes_de(semana) + timedelta(days=3)
    return Mes(jueves.year, jueves.month)


def semanas_del_mes(anio: int, mes: int) -> list[Semana]:
    """Semanas ISO cuyo jueves cae en el mes indicado, en orden."""
    primer_dia = date(anio, mes, 1)
    # Primer jueves del mes.
    jueves = primer_dia + timedelta(days=(3 - primer_dia.weekday()) % 7)
    semanas = []
    while jueves.month == mes:
        semanas.append(semana_de(jueves))
        jueves += timedelta(weeks=1)
    return semanas
