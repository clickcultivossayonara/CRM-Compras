"""T3.1 · Caja negra de /sync/* (R6.2, R6.3). Plan de pruebas §3.8.

Con la app sobre PostgreSQL en una transacción que se revierte. Datos ficticios.
"""

from typing import Any

import httpx2
import pytest
from sqlalchemy import select

from crm_compras.datos.conexion import BaseDatos
from crm_compras.datos.modelos import Articulo, CentroCosto, Precio, Sincronizacion


def articulo(codigo: str, activo: bool = True) -> dict[str, Any]:
    return {
        "codigo": codigo,
        "descripcion": f"ARTICULO {codigo}",
        "unidad": "UND",
        "activo": activo,
    }


def centro(codigo: str) -> dict[str, Any]:
    return {"codigo": codigo, "descripcion": f"CENTRO {codigo}", "activo": True}


def precio(codigo: str, valor: int = 1000) -> dict[str, Any]:
    return {
        "articulo": codigo,
        "precio_unitario": valor,
        "fecha_compra": "2026-10-20",
        "orden_compra": "OC-1",
    }


@pytest.fixture
def enviar(cliente_bd: httpx2.Client, token_sync: str) -> Any:
    def _enviar(tipo: str, cuerpo: object) -> httpx2.Response:
        return cliente_bd.post(
            f"/sync/{tipo}", json=cuerpo, headers={"Authorization": f"Bearer {token_sync}"}
        )

    return _enviar


@pytest.mark.parametrize("tipo", ["articulos", "centros", "precios"])
@pytest.mark.parametrize(
    "encabezados",
    [
        {},
        {"Authorization": "Bearer token-equivocado"},
        {"Authorization": ""},
        {"Authorization": "Basic dXN1YXJpbzpjbGF2ZQ=="},
    ],
)
def test_sin_token_valido_es_401(
    cliente_bd: httpx2.Client, tipo: str, encabezados: dict[str, str]
) -> None:
    respuesta = cliente_bd.post(f"/sync/{tipo}", json={tipo: []}, headers=encabezados)
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_el_token_se_revisa_antes_que_el_cuerpo(cliente_bd: httpx2.Client) -> None:
    assert cliente_bd.post("/sync/articulos", content=b"no es json").status_code == 401


@pytest.mark.parametrize(
    ("tipo", "cuerpo"),
    [
        ("articulos", None),
        ("articulos", {"articulos": [articulo("20093")]}),
        ("articulos", {"articulos": [articulo("020093"), articulo("020093")]}),
        ("centros", {"centros": [centro("51301-2")]}),
        ("precios", {"precios": [{**precio("020093"), "precio_unitario": 10.5}]}),
        ("precios", {"articulos": []}),
    ],
)
def test_cuerpo_invalido_es_422_y_no_cambia_nada(
    enviar: Any, bd: BaseDatos, tipo: str, cuerpo: object
) -> None:
    assert enviar(tipo, cuerpo).status_code == 422
    with bd.sesion() as sesion:
        assert sesion.scalars(select(Sincronizacion)).first() is None


def test_articulos_recibidos_y_registro(enviar: Any, bd: BaseDatos) -> None:
    respuesta = enviar("articulos", {"articulos": [articulo("020093"), articulo("000001")]})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"recibidos": 2, "inactivados": 0}
    with bd.sesion() as sesion:
        guardado = sesion.get(Articulo, "020093")
        assert guardado is not None
        assert (guardado.descripcion, guardado.unidad, guardado.activo) == (
            "ARTICULO 020093",
            "UND",
            True,
        )
        [registro] = sesion.scalars(select(Sincronizacion)).all()
        assert (registro.tipo, registro.registros) == ("articulos", 2)


def test_enviar_dos_veces_lo_mismo_da_el_mismo_resultado(enviar: Any, bd: BaseDatos) -> None:
    cuerpo = {"articulos": [articulo("020093"), articulo("000001", activo=False)]}
    primera = enviar("articulos", cuerpo).json()
    segunda = enviar("articulos", cuerpo).json()
    assert primera == segunda == {"recibidos": 2, "inactivados": 0}
    with bd.sesion() as sesion:
        estados = {a.codigo: a.activo for a in sesion.scalars(select(Articulo))}
    assert estados == {"020093": True, "000001": False}


def test_lo_que_no_llega_queda_inactivo_sin_borrarse_y_vuelve_si_llega(
    enviar: Any, bd: BaseDatos
) -> None:
    enviar("articulos", {"articulos": [articulo("020093"), articulo("000001")]})
    respuesta = enviar("articulos", {"articulos": [articulo("020093")]})
    assert respuesta.json() == {"recibidos": 1, "inactivados": 1}
    with bd.sesion() as sesion:
        ausente = sesion.get(Articulo, "000001")
        assert ausente is not None
        assert ausente.activo is False

    assert enviar("articulos", {"articulos": [articulo("020093")]}).json()["inactivados"] == 0
    enviar("articulos", {"articulos": [articulo("020093"), articulo("000001")]})
    with bd.sesion() as sesion:
        assert sesion.get(Articulo, "000001").activo is True  # type: ignore[union-attr]


def test_cambios_de_descripcion_se_actualizan(enviar: Any, bd: BaseDatos) -> None:
    enviar("articulos", {"articulos": [articulo("020093")]})
    nuevo = {**articulo("020093"), "descripcion": "NUEVA DESCRIPCION", "unidad": "LT"}
    enviar("articulos", {"articulos": [nuevo]})
    with bd.sesion() as sesion:
        guardado = sesion.get(Articulo, "020093")
        assert guardado is not None
        assert (guardado.descripcion, guardado.unidad) == ("NUEVA DESCRIPCION", "LT")


def test_centros_de_costo(enviar: Any, bd: BaseDatos) -> None:
    enviar("centros", {"centros": [centro("513-01-2"), centro("100-01-1")]})
    respuesta = enviar("centros", {"centros": [centro("513-01-2")]})
    assert respuesta.json() == {"recibidos": 1, "inactivados": 1}
    with bd.sesion() as sesion:
        estados = {c.codigo: c.activo for c in sesion.scalars(select(CentroCosto))}
    assert estados == {"513-01-2": True, "100-01-1": False}


def test_precios_se_reemplazan(enviar: Any, bd: BaseDatos) -> None:
    enviar("articulos", {"articulos": [articulo("020093"), articulo("000001")]})
    assert enviar("precios", {"precios": [precio("020093"), precio("000001")]}).json() == {
        "recibidos": 2,
        "inactivados": 0,
    }
    respuesta = enviar("precios", {"precios": [precio("020093", valor=2500)]})
    assert respuesta.json() == {"recibidos": 1, "inactivados": 1}
    with bd.sesion() as sesion:
        precios = {p.articulo: p.precio_unitario for p in sesion.scalars(select(Precio))}
    assert precios == {"020093": 2500}


def test_precio_de_un_articulo_desconocido_rechaza_todo(enviar: Any, bd: BaseDatos) -> None:
    enviar("articulos", {"articulos": [articulo("020093")]})
    respuesta = enviar("precios", {"precios": [precio("020093"), precio("999999")]})
    assert respuesta.status_code == 422
    assert "999999" in respuesta.json()["detail"]
    with bd.sesion() as sesion:
        assert sesion.scalars(select(Precio)).first() is None


def test_un_envio_vacio_inactiva_todo_el_catalogo(enviar: Any) -> None:
    enviar("articulos", {"articulos": [articulo("020093"), articulo("000001")]})
    assert enviar("articulos", {"articulos": []}).json() == {"recibidos": 0, "inactivados": 2}


def test_el_inicio_refleja_una_sincronizacion_completa(
    enviar: Any, cliente_bd: httpx2.Client, entrar_bd: Any
) -> None:
    enviar("articulos", {"articulos": [articulo("020093")]})
    enviar("centros", {"centros": [centro("513-01-2")]})
    entrar_bd(cliente_bd, "jefe")
    assert "tienen más de 24 horas sin actualizarse" in cliente_bd.get("/").text
    enviar("precios", {"precios": [precio("020093")]})
    pagina = cliente_bd.get("/").text
    assert "Última sincronización con Softland: " in pagina
    assert "todavía no se ha completado" not in pagina
    assert "tienen más de 24 horas sin actualizarse" not in pagina
