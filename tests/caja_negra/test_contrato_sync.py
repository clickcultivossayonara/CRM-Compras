"""T3.2c · C1: lo que arma el sincronizador lo acepta la API real (contrato compartido).

El sincronizador lee el doble de Softland y envía a la app en memoria sobre PostgreSQL, en una
transacción que se revierte. Datos ficticios.
"""

from datetime import date

import httpx2
import pytest
from sqlalchemy import select

from crm_compras.datos.conexion import BaseDatos
from crm_compras.datos.modelos import Articulo, CentroCosto, Precio
from sincronizador.__main__ import sincronizar
from sincronizador.envio import ClienteAPI
from tests.sincronizador.doble_softland import ConexionFicticia

pytestmark = pytest.mark.contrato


class TransporteAlaApp:
    """Transporte del sincronizador que entrega los envíos a la app en memoria."""

    def __init__(self, cliente: httpx2.Client) -> None:
        self.cliente = cliente

    def post(self, ruta: str, cuerpo: bytes, encabezados: dict[str, str]) -> tuple[int, bytes]:
        respuesta = self.cliente.post(ruta, content=cuerpo, headers=encabezados)
        return respuesta.status_code, respuesta.content


def test_la_api_acepta_lo_que_envia_el_sincronizador(
    cliente_bd: httpx2.Client, bd: BaseDatos, token_sync: str
) -> None:
    cliente = ClienteAPI(TransporteAlaApp(cliente_bd), token_sync)
    resultados = sincronizar(ConexionFicticia(), cliente, date(2026, 11, 27))
    assert [(r.respuesta.recibidos, r.respuesta.inactivados) for r in resultados] == [
        (3, 0),
        (2, 0),
        (2, 0),
    ]
    with bd.sesion() as sesion:
        articulos = {a.codigo: a.activo for a in sesion.scalars(select(Articulo))}
        centros = {c.codigo: c.activo for c in sesion.scalars(select(CentroCosto))}
        precios = {p.articulo: p.precio_unitario for p in sesion.scalars(select(Precio))}
    assert articulos == {"020093": True, "020215": True, "000001": False}
    assert centros == {"513-01-2": True, "100-01-1": False}
    assert precios == {"020093": 1500, "020215": 1000}


def test_una_segunda_sincronizacion_inactiva_lo_que_salio_de_softland(
    cliente_bd: httpx2.Client, token_sync: str
) -> None:
    cliente = ClienteAPI(TransporteAlaApp(cliente_bd), token_sync)
    sincronizar(ConexionFicticia(), cliente, date(2026, 11, 27))
    # El 020215 (activo) deja de venir de Softland; el 000001 ya estaba inactivo y sigue.
    softland = ConexionFicticia()
    softland.filas["ARTICULO"] = [f for f in softland.filas["ARTICULO"] if f[0] != "020215"]
    resultados = sincronizar(softland, cliente, date(2026, 11, 28))
    articulos, _, precios = (r.respuesta for r in resultados)
    assert (articulos.recibidos, articulos.inactivados) == (2, 1)
    # Su precio ya no se envía (no está en el catálogo) y se retira.
    assert (precios.recibidos, precios.inactivados) == (1, 1)
