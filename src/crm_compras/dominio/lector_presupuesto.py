"""Lectura del Excel de presupuesto (reglas D5, D6 y D7).

Recibe las filas de la hoja como las entrega openpyxl con fórmulas (la posición 0 es la fila 1
y la posición 0 de cada fila es la columna A) y devuelve las partidas, advertencias y errores.

Estructura esperada, igual al Excel de compras:
- Una fila con los meses como encabezado y una fila "Semanas" con las semanas de cada mes.
- Un rubro es una fila con una fórmula que suma otras filas (``SUM(B9:B13)`` o ``+B43+B44``);
  las filas que suma son sus áreas. Si una de ellas es otra fórmula, sus filas son áreas del
  mismo rubro con el nombre compuesto (``CULTIVOS (CAMPO) - LA CEJA``).
- El total general es una fórmula que no suma ninguna otra fila y que suma rubros. Las filas
  con valores que suma directamente, o que no suma ninguna fórmula, son partidas ``GENERAL``.
"""

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from crm_compras.dominio.calendario import semanas_del_mes

MESES = (
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
)
AREA_GENERAL = "GENERAL"

# Referencia a una celda o a un rango (B9, $B$9, B9:B13); se usan solo los números de fila.
_REFERENCIA = re.compile(r"\$?[A-Z]{1,3}\$?(\d+)(?::\$?[A-Z]{1,3}\$?(\d+))?")


@dataclass(frozen=True)
class PartidaLeida:
    rubro: str
    area: str
    fila: int
    valores: dict[int, int]
    """Valor en pesos por número de mes."""


@dataclass
class Lectura:
    semanas: dict[int, int] = field(default_factory=dict)
    """Semanas por número de mes."""
    partidas: list[PartidaLeida] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


def normalizar_nombre(texto: str) -> str:
    """Sin espacios sobrantes, en mayúsculas y conservando las tildes."""
    return " ".join(texto.split()).upper()


def leer_presupuesto(filas: Sequence[Sequence[object]], anio: int) -> Lectura:
    lectura = Lectura()
    columnas = _columnas_de_meses(filas, lectura)
    fila_semanas = _fila_por_nombre(filas, "SEMANAS")
    if fila_semanas is None:
        lectura.errores.append('No se encontró la fila "Semanas".')
    if columnas is None or fila_semanas is None:
        return lectura
    fila_meses, meses = columnas

    _leer_semanas(filas[fila_semanas - 1], meses, anio, lectura)
    inicio = max(fila_meses, fila_semanas) + 1
    _advertir_columnas_sin_mes(filas, meses, inicio, lectura)
    _leer_partidas(filas, meses, inicio, lectura)
    return lectura


def _celda(fila: Sequence[object], columna: int) -> object:
    return fila[columna] if columna < len(fila) else None


def _nombre(fila: Sequence[object]) -> str:
    valor = _celda(fila, 0)
    return normalizar_nombre(valor) if isinstance(valor, str) else ""


def _letra(columna: int) -> str:
    """Letra de la columna (0 → A)."""
    letras = ""
    columna += 1
    while columna:
        columna, resto = divmod(columna - 1, 26)
        letras = chr(ord("A") + resto) + letras
    return letras


def _es_formula(valor: object) -> bool:
    return isinstance(valor, str) and valor.startswith("=")


def _columnas_de_meses(
    filas: Sequence[Sequence[object]], lectura: Lectura
) -> tuple[int, dict[int, int]] | None:
    """Número de la fila de meses y columnas con su número de mes."""
    for numero, fila in enumerate(filas, start=1):
        meses: dict[int, int] = {}
        for columna, valor in enumerate(fila[1:], start=1):
            if not isinstance(valor, str) or normalizar_nombre(valor) not in MESES:
                continue
            mes = MESES.index(normalizar_nombre(valor)) + 1
            if mes in meses.values():
                lectura.errores.append(
                    f"El mes {MESES[mes - 1]} está repetido en la fila {numero}."
                )
            meses[columna] = mes
        if meses:
            return numero, meses
    lectura.errores.append("No se encontró la fila con los meses como encabezado.")
    return None


def _fila_por_nombre(filas: Sequence[Sequence[object]], nombre: str) -> int | None:
    for numero, fila in enumerate(filas, start=1):
        if _nombre(fila) == nombre:
            return numero
    return None


def _leer_semanas(
    fila: Sequence[object], meses: dict[int, int], anio: int, lectura: Lectura
) -> None:
    for columna, mes in meses.items():
        valor = _celda(fila, columna)
        esperadas = len(semanas_del_mes(anio, mes))
        if isinstance(valor, bool) or not isinstance(valor, int | float) or valor != int(valor):
            lectura.errores.append(
                f"Las semanas de {MESES[mes - 1]} (columna {_letra(columna)}) deben ser un "
                "número entero."
            )
        elif valor != esperadas:
            lectura.errores.append(
                f"{MESES[mes - 1]} debe tener {esperadas} semanas, no {int(valor)}."
            )
        else:
            lectura.semanas[mes] = esperadas


def _advertir_columnas_sin_mes(
    filas: Sequence[Sequence[object]], meses: dict[int, int], inicio: int, lectura: Lectura
) -> None:
    sin_mes = sorted(
        {
            columna
            for fila in filas[inicio - 1 :]
            for columna, valor in enumerate(fila)
            if columna > 0 and columna not in meses and valor is not None
        }
    )
    if sin_mes:
        letras = ", ".join(_letra(c) for c in sin_mes)
        lectura.advertencias.append(
            f"Las columnas {letras} tienen datos y no tienen un mes como encabezado; se ignoran."
        )


def _referencias(fila: Sequence[object], meses: dict[int, int]) -> set[int] | None:
    """Filas que suman las fórmulas de la fila, o None si la fila no tiene fórmulas."""
    formulas = [str(_celda(fila, c)) for c in meses if _es_formula(_celda(fila, c))]
    if not formulas:
        return None
    referencias: set[int] = set()
    for formula in formulas:
        for desde, hasta in _REFERENCIA.findall(formula.upper()):
            referencias.update(range(int(desde), int(hasta or desde) + 1))
    return referencias


def _leer_partidas(
    filas: Sequence[Sequence[object]], meses: dict[int, int], inicio: int, lectura: Lectura
) -> None:
    formulas: dict[int, set[int]] = {}
    hojas: set[int] = set()
    for numero in range(inicio, len(filas) + 1):
        fila = filas[numero - 1]
        referencias = _referencias(fila, meses)
        tiene_valores = any(_celda(fila, c) is not None for c in meses)
        if referencias is not None:
            if not referencias:
                lectura.errores.append(f"Fila {numero}: la fórmula no suma ninguna fila.")
            formulas[numero] = referencias
        elif _nombre(fila) and tiene_valores:
            hojas.add(numero)
        elif _nombre(fila):
            lectura.advertencias.append(
                f"Fila {numero} ({_nombre(fila)}) no tiene valores; se ignora."
            )
        elif any(_es_numero(_celda(fila, c)) for c in meses):
            lectura.errores.append(f"Fila {numero}: tiene valores y no tiene nombre.")

    referenciadas = set().union(*formulas.values())
    asignadas: dict[int, str] = {}
    for raiz in sorted(set(formulas) - referenciadas):
        if formulas[raiz] & formulas.keys():
            # Total general: sus fórmulas son rubros y sus filas con valores, partidas GENERAL.
            for hija in sorted(formulas[raiz]):
                if hija in formulas:
                    _agregar_rubro(filas, formulas, hojas, hija, asignadas, lectura, meses)
                elif hija in hojas:
                    _agregar(
                        filas,
                        hija,
                        _nombre(filas[hija - 1]),
                        AREA_GENERAL,
                        asignadas,
                        lectura,
                        meses,
                    )
        else:
            _agregar_rubro(filas, formulas, hojas, raiz, asignadas, lectura, meses)

    for hoja in sorted(hojas - asignadas.keys()):
        _agregar(filas, hoja, _nombre(filas[hoja - 1]), AREA_GENERAL, asignadas, lectura, meses)
    _validar_repetidas(lectura)


def _agregar_rubro(
    filas: Sequence[Sequence[object]],
    formulas: dict[int, set[int]],
    hojas: set[int],
    rubro: int,
    asignadas: dict[int, str],
    lectura: Lectura,
    meses: dict[int, int],
) -> None:
    nombre_rubro = _nombre(filas[rubro - 1])
    for hoja, area in _areas(filas, formulas, hojas, rubro, "", {rubro}):
        _agregar(filas, hoja, nombre_rubro, area, asignadas, lectura, meses)


def _areas(
    filas: Sequence[Sequence[object]],
    formulas: dict[int, set[int]],
    hojas: set[int],
    fila: int,
    prefijo: str,
    visitadas: set[int],
) -> Iterator[tuple[int, str]]:
    """Filas con valores bajo una fórmula, con el nombre de área compuesto por los niveles."""
    for hija in sorted(formulas[fila] - visitadas):
        nombre = prefijo + _nombre(filas[hija - 1]) if hija <= len(filas) else ""
        if hija in formulas:
            yield from _areas(filas, formulas, hojas, hija, nombre + " - ", visitadas | {hija})
        elif hija in hojas:
            yield hija, nombre


def _agregar(
    filas: Sequence[Sequence[object]],
    numero: int,
    rubro: str,
    area: str,
    asignadas: dict[int, str],
    lectura: Lectura,
    meses: dict[int, int],
) -> None:
    if numero in asignadas:
        lectura.errores.append(
            f"Fila {numero}: está en más de un rubro ({asignadas[numero]} y {rubro})."
        )
        return
    asignadas[numero] = rubro
    valores: dict[int, int] = {}
    for columna, mes in meses.items():
        valor = _convertir(_celda(filas[numero - 1], columna), numero, columna, lectura)
        if valor is not None:
            valores[mes] = valor
    lectura.partidas.append(PartidaLeida(rubro, area, numero, valores))


def _es_numero(valor: object) -> bool:
    return isinstance(valor, int | float | Decimal) and not isinstance(valor, bool)


def _convertir(valor: object, fila: int, columna: int, lectura: Lectura) -> int | None:
    """Valor en pesos enteros con ROUND_HALF_UP; una celda vacía es 0."""
    if valor is None:
        return 0
    if not _es_numero(valor):
        lectura.errores.append(
            f"Fila {fila}, columna {_letra(columna)}: {valor!r} no es un número."
        )
        return None
    decimal = Decimal(str(valor))
    if decimal < 0:
        lectura.errores.append(f"Fila {fila}, columna {_letra(columna)}: el valor es negativo.")
        return None
    return int(decimal.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _validar_repetidas(lectura: Lectura) -> None:
    vistas: dict[tuple[str, str], int] = {}
    for partida in lectura.partidas:
        clave = (partida.rubro, partida.area)
        if clave in vistas:
            lectura.errores.append(
                f"La partida {partida.rubro} / {partida.area} está repetida "
                f"(filas {vistas[clave]} y {partida.fila})."
            )
        else:
            vistas[clave] = partida.fila
