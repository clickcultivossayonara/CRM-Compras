"""Sincroniza artículos, centros de costo y precios de Softland con la API.

Uso (en un equipo de la red de la empresa, por ejemplo con el Programador de tareas):
``uv run python -m sincronizador``. Variables de entorno: SOFTLAND_SERVIDOR, SOFTLAND_USUARIO,
SOFTLAND_CLAVE, SOFTLAND_BASE (opcional), CRM_URL_API y SYNC_TOKEN.
"""

import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from crm_compras.contrato_sync import EnvioArticulos, EnvioCentros, EnvioPrecios, RespuestaSync
from sincronizador import consultas, lectura
from sincronizador.envio import ClienteAPI, Transporte, TransporteHTTPS
from sincronizador.lectura import Conexion
from sincronizador.preparar import preparar_articulos, preparar_centros, preparar_precios

ZONA = ZoneInfo("America/Bogota")
EJEMPLOS_DESCARTE = 10


class CatalogoVacioError(RuntimeError):
    """Softland no devolvió filas: enviar una lista vacía inactivaría todo el catálogo."""


@dataclass
class Resultado:
    tipo: str
    respuesta: RespuestaSync
    descartes: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        texto = (
            f"{self.tipo}: {self.respuesta.recibidos} recibidos, "
            f"{self.respuesta.inactivados} inactivados, {len(self.descartes)} descartados"
        )
        ejemplos = "".join(f"\n  - {d}" for d in self.descartes[:EJEMPLOS_DESCARTE])
        return texto + ejemplos


def _no_vacio(lista: list[Any], que: str) -> None:
    if not lista:
        raise CatalogoVacioError(f"Softland no devolvió {que}; no se envía nada.")


def sincronizar(conexion: Conexion, cliente: ClienteAPI, hoy: date) -> list[Resultado]:
    """Lee Softland y envía artículos, centros y precios, en ese orden.

    Los precios van al final porque la API exige que sus artículos ya existan.
    """
    articulos, descartes_a = preparar_articulos(consultas.leer_articulos(conexion))
    _no_vacio(articulos, "artículos válidos")
    centros, descartes_c = preparar_centros(consultas.leer_centros(conexion))
    _no_vacio(centros, "centros de costo válidos")
    filas_precios = consultas.leer_precios(conexion, date(hoy.year - 1, 1, 1))
    precios, descartes_p = preparar_precios(filas_precios, {a.codigo for a in articulos})

    return [
        Resultado(
            "artículos",
            cliente.enviar("articulos", EnvioArticulos(articulos=articulos)),
            descartes_a,
        ),
        Resultado("centros", cliente.enviar("centros", EnvioCentros(centros=centros)), descartes_c),
        Resultado("precios", cliente.enviar("precios", EnvioPrecios(precios=precios)), descartes_p),
    ]


def main(
    entorno: Mapping[str, str] | None = None,
    conectar: Callable[[Mapping[str, str]], Any] = lectura.conectar,
    transporte: Transporte | None = None,
) -> int:
    entorno = os.environ if entorno is None else entorno
    faltan = [v for v in ("CRM_URL_API", "SYNC_TOKEN") if not entorno.get(v)]
    if faltan:
        print(f"Faltan variables de entorno: {', '.join(faltan)}", file=sys.stderr)
        return 2
    try:
        cliente = ClienteAPI(
            transporte or TransporteHTTPS(entorno["CRM_URL_API"]), entorno["SYNC_TOKEN"]
        )
        conexion = conectar(entorno)
        try:
            resultados = sincronizar(conexion, cliente, datetime.now(ZONA).date())
        finally:
            conexion.close()
    except (ValueError, RuntimeError) as error:  # incluye CatalogoVacioError y EnvioError
        print(f"La sincronización no se completó: {error}", file=sys.stderr)
        return 1
    for resultado in resultados:
        print(resultado.resumen())
    return 0


if __name__ == "__main__":
    sys.exit(main())
