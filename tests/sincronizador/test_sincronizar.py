"""T3.2 · Orquestación del sincronizador con un doble de Softland y un transporte falso."""

import http.server
import json
import re
import threading
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest

from crm_compras.contrato_sync import RespuestaSync
from sincronizador import consultas, lectura
from sincronizador.__main__ import CatalogoVacioError, main, sincronizar
from sincronizador.envio import ClienteAPI, EnvioError, TransporteHTTPS
from tests.sincronizador.doble_softland import ConexionFicticia

TOKEN = "t" * 32


class TransporteFalso:
    """Guarda lo que se envía y responde como la API."""

    def __init__(self, codigo: int = 200, cuerpo: bytes | None = None) -> None:
        self.codigo = codigo
        self.cuerpo = cuerpo
        self.envios: list[tuple[str, dict[str, Any], dict[str, str]]] = []

    def post(self, ruta: str, cuerpo: bytes, encabezados: dict[str, str]) -> tuple[int, bytes]:
        datos = json.loads(cuerpo)
        self.envios.append((ruta, datos, encabezados))
        if self.cuerpo is not None:
            return self.codigo, self.cuerpo
        lista = next(iter(datos.values()))
        return self.codigo, RespuestaSync(
            recibidos=len(lista), inactivados=0
        ).model_dump_json().encode()


def test_envia_en_orden_lo_que_lee_de_softland() -> None:
    conexion = ConexionFicticia()
    transporte = TransporteFalso()
    resultados = sincronizar(conexion, ClienteAPI(transporte, TOKEN), date(2026, 11, 27))

    assert [ruta for ruta, _, _ in transporte.envios] == [
        "/sync/articulos",
        "/sync/centros",
        "/sync/precios",
    ]
    _, articulos, encabezados = transporte.envios[0]
    assert encabezados["Authorization"] == f"Bearer {TOKEN}"
    assert [a["codigo"] for a in articulos["articulos"]] == ["020093", "020215", "000001"]
    assert transporte.envios[1][1]["centros"] == [
        {"codigo": "513-01-2", "descripcion": "CENTRO FICTICIO", "activo": True},
        {"codigo": "100-01-1", "descripcion": "CENTRO QUE NO ACEPTA DATOS", "activo": False},
    ]
    assert transporte.envios[2][1]["precios"] == [
        {
            "articulo": "020093",
            "precio_unitario": 1500,
            "fecha_compra": "2026-10-20",
            "orden_compra": "OC-1",
        },
        {
            "articulo": "020215",
            "precio_unitario": 1000,
            "fecha_compra": "2026-09-01",
            "orden_compra": "OC-2",
        },
    ]
    assert [len(r.descartes) for r in resultados] == [1, 1, 1]
    assert "artículos: 3 recibidos, 0 inactivados, 1 descartados" in resultados[0].resumen()


def test_solo_lee_y_siempre_revierte() -> None:
    conexion = ConexionFicticia()
    sincronizar(conexion, ClienteAPI(TransporteFalso(), TOKEN), date(2026, 11, 27))
    sentencias = [sql for sql, _ in conexion.consultas if not sql.startswith("SET TRANSACTION")]
    assert sentencias == [consultas.ARTICULOS, consultas.CENTROS, consultas.PRECIOS]
    for sql in sentencias:
        lectura.validar_solo_lectura(sql)
    assert conexion.rollbacks == 3


def test_los_precios_se_leen_desde_el_primero_de_enero_del_anio_anterior() -> None:
    conexion = ConexionFicticia()
    sincronizar(conexion, ClienteAPI(TransporteFalso(), TOKEN), date(2026, 11, 27))
    [(_, parametros)] = [c for c in conexion.consultas if c[0] == consultas.PRECIOS]
    assert parametros == (date(2025, 1, 1),)


@pytest.mark.parametrize("tabla", ["ARTICULO", "CENTRO_COSTO"])
def test_catalogo_vacio_no_se_envia(tabla: str) -> None:
    conexion = ConexionFicticia()
    conexion.filas[tabla] = []
    transporte = TransporteFalso()
    with pytest.raises(CatalogoVacioError):
        sincronizar(conexion, ClienteAPI(transporte, TOKEN), date(2026, 11, 27))
    assert transporte.envios == []


def test_la_api_rechaza_el_envio() -> None:
    transporte = TransporteFalso(401, b'{"detail": "Token del sincronizador ausente o no valido."}')
    with pytest.raises(EnvioError, match="La API respondió 401 al enviar articulos: Token"):
        sincronizar(ConexionFicticia(), ClienteAPI(transporte, TOKEN), date(2026, 11, 27))


@pytest.mark.parametrize(
    ("cuerpo", "detalle"),
    [
        (b"<html>error</html>", "<html>error</html>"),
        (b"[1, 2]", "[1, 2]"),
        (b'{"otro": 1}', "{'otro': 1}"),
    ],
)
def test_detalle_de_errores_sin_formato(cuerpo: bytes, detalle: str) -> None:
    with pytest.raises(
        EnvioError, match=re.escape(f"respondió 500 al enviar articulos: {detalle}")
    ):
        sincronizar(
            ConexionFicticia(), ClienteAPI(TransporteFalso(500, cuerpo), TOKEN), date(2026, 1, 1)
        )


ENTORNO = {"CRM_URL_API": "https://crm.example.com", "SYNC_TOKEN": TOKEN}


def test_main_sincroniza_y_cierra_la_conexion(capsys: pytest.CaptureFixture[str]) -> None:
    conexion = ConexionFicticia()
    codigo = main(ENTORNO, lambda _entorno: conexion, TransporteFalso())
    assert codigo == 0
    assert conexion.cerrada
    salida = capsys.readouterr().out
    assert "precios: 2 recibidos" in salida
    assert "Artículo '12345'" in salida


@pytest.mark.parametrize("falta", ["CRM_URL_API", "SYNC_TOKEN"])
def test_main_sin_configuracion(falta: str, capsys: pytest.CaptureFixture[str]) -> None:
    entorno = {k: v for k, v in ENTORNO.items() if k != falta}
    assert main(entorno, lambda _entorno: ConexionFicticia()) == 2
    assert falta in capsys.readouterr().err


def test_main_con_error_devuelve_1(capsys: pytest.CaptureFixture[str]) -> None:
    conexion = ConexionFicticia()
    conexion.filas["ARTICULO"] = []
    assert main(ENTORNO, lambda _entorno: conexion, TransporteFalso()) == 1
    assert "no se completó: Softland no devolvió artículos" in capsys.readouterr().err
    assert conexion.cerrada


@pytest.mark.parametrize("url", ["http://crm.example.com", "ftp://crm.example.com"])
def test_solo_https_salvo_localhost(url: str) -> None:
    with pytest.raises(ValueError, match="https"):
        TransporteHTTPS(url)
    assert main({**ENTORNO, "CRM_URL_API": url}, lambda _entorno: ConexionFicticia()) == 1


def test_main_usa_el_entorno_del_proceso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRM_URL_API", raising=False)
    monkeypatch.delenv("SYNC_TOKEN", raising=False)
    assert main() == 2


class _Manejador(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        largo = int(self.headers["Content-Length"])
        cuerpo = json.loads(self.rfile.read(largo))
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"detail": "no"}')
            return
        respuesta = json.dumps({"recibidos": len(cuerpo["articulos"]), "inactivados": 0})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(respuesta.encode())

    def log_message(self, *_argumentos: Any) -> None:
        """Sin registro en la consola de pruebas."""


@pytest.fixture
def servidor_local() -> Iterator[str]:
    servidor = http.server.HTTPServer(("127.0.0.1", 0), _Manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_address[1]}"
    finally:
        servidor.shutdown()


def test_transporte_http_real_contra_localhost(servidor_local: str) -> None:
    transporte = TransporteHTTPS(servidor_local + "/")
    cuerpo = b'{"articulos": [1, 2]}'
    encabezados = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    assert transporte.post("/sync/articulos", cuerpo, encabezados) == (
        200,
        b'{"recibidos": 2, "inactivados": 0}',
    )
    assert transporte.post("/sync/articulos", cuerpo, {})[0] == 401
