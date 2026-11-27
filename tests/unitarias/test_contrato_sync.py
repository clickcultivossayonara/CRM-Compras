"""T3.1 · Contrato del sincronizador: lo que la API acepta y lo que rechaza (diseño §5)."""

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from crm_compras.contrato_sync import EnvioArticulos, EnvioCentros, EnvioPrecios
from tests.fabricas import ANCHO_COMPLETO, otros_digitos


def articulo(**cambios: Any) -> dict[str, Any]:
    return {
        "codigo": "020093",
        "descripcion": "ARTICULO FICTICIO",
        "unidad": "CC",
        "activo": True,
        **cambios,
    }


def centro(**cambios: Any) -> dict[str, Any]:
    return {"codigo": "513-01-2", "descripcion": "CENTRO FICTICIO", "activo": True, **cambios}


def precio(**cambios: Any) -> dict[str, Any]:
    return {
        "articulo": "020093",
        "precio_unitario": 1500,
        "fecha_compra": "2026-10-20",
        "orden_compra": "OC-1",
        **cambios,
    }


def test_envios_validos() -> None:
    assert (
        EnvioArticulos.model_validate({"articulos": [articulo()]}).articulos[0].codigo == "020093"
    )
    assert EnvioCentros.model_validate({"centros": [centro()]}).centros[0].activo is True
    leido = EnvioPrecios.model_validate({"precios": [precio()]}).precios[0]
    assert (leido.precio_unitario, leido.fecha_compra) == (1500, date(2026, 10, 20))


def test_envios_vacios_son_validos() -> None:
    assert EnvioArticulos.model_validate({"articulos": []}).articulos == []


@pytest.mark.parametrize(
    "cambios",
    [
        {"codigo": "20093"},
        {"codigo": "0200930"},
        {"codigo": "02009A"},
        {"codigo": otros_digitos("020093", ANCHO_COMPLETO)},
        {"descripcion": ""},
        {"unidad": ""},
        {"unidad": "X" * 11},
        {"activo": "si"},
        {"sobrante": 1},
    ],
)
def test_articulo_invalido(cambios: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        EnvioArticulos.model_validate({"articulos": [articulo(**cambios)]})


@pytest.mark.parametrize("codigo", ["51301-2", "513-1-2", "513-01-22", "ABC-01-2"])
def test_centro_invalido(codigo: str) -> None:
    with pytest.raises(ValidationError):
        EnvioCentros.model_validate({"centros": [centro(codigo=codigo)]})


@pytest.mark.parametrize(
    "cambios",
    [
        {"precio_unitario": -1},
        {"precio_unitario": 1500.5},
        {"precio_unitario": "1500"},
        {"fecha_compra": "20/10/2026"},
        {"orden_compra": ""},
        {"articulo": "20093"},
    ],
)
def test_precio_invalido(cambios: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        EnvioPrecios.model_validate({"precios": [precio(**cambios)]})


def test_precio_cero_es_valido() -> None:
    assert EnvioPrecios.model_validate({"precios": [precio(precio_unitario=0)]}).precios


@pytest.mark.parametrize(
    ("modelo", "cuerpo", "mensaje"),
    [
        (
            EnvioArticulos,
            {"articulos": [articulo(), articulo()]},
            "Artículos repetidos en el envío: 020093",
        ),
        (
            EnvioCentros,
            {"centros": [centro(), centro()]},
            "Centros de costo repetidos en el envío: 513-01-2",
        ),
        (
            EnvioPrecios,
            {"precios": [precio(), precio()]},
            "Precios de artículos repetidos en el envío: 020093",
        ),
    ],
)
def test_codigos_repetidos(modelo: Any, cuerpo: dict[str, Any], mensaje: str) -> None:
    with pytest.raises(ValidationError, match=mensaje):
        modelo.model_validate(cuerpo)


def test_falta_la_lista() -> None:
    with pytest.raises(ValidationError):
        EnvioArticulos.model_validate({"centros": []})
