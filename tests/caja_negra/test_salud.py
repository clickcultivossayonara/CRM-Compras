"""Caja negra de /salud: solo entradas y salidas HTTP."""

import httpx2
import pytest


def test_get_salud_devuelve_ok(cliente: httpx2.Client) -> None:
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("application/json")
    assert respuesta.json() == {"estado": "ok"}


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE"])
def test_metodos_no_permitidos_en_salud(cliente: httpx2.Client, metodo: str) -> None:
    assert cliente.request(metodo, "/salud").status_code == 405


@pytest.mark.parametrize("ruta", ["/no-existe", "/salud/extra", "/SALUD"])
def test_rutas_inexistentes_devuelven_404(cliente: httpx2.Client, ruta: str) -> None:
    assert cliente.get(ruta).status_code == 404
