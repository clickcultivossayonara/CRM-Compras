"""T2.1 · Partes de la capa de datos que no necesitan una base: URL y SQL de la migración."""

import io
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from crm_compras.datos.conexion import VARIABLE_URL, url_desde_entorno, url_sqlalchemy

RAIZ = Path(__file__).resolve().parents[2]
URL_FICTICIA = "postgresql://usuario@servidor/base"


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        ("postgresql://u@h/b", "postgresql+psycopg://u@h/b"),
        ("postgres://u@h/b", "postgresql+psycopg://u@h/b"),
        ("postgresql+psycopg://u@h/b", "postgresql+psycopg://u@h/b"),
    ],
)
def test_url_con_el_driver_psycopg(url: str, esperado: str) -> None:
    assert url_sqlalchemy(url) == esperado


def test_url_desde_el_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VARIABLE_URL, URL_FICTICIA)
    assert url_desde_entorno() == "postgresql+psycopg://usuario@servidor/base"


def test_sin_url_en_el_entorno_es_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VARIABLE_URL, raising=False)
    with pytest.raises(RuntimeError, match=VARIABLE_URL):
        url_desde_entorno()


def sql_de_migracion(rango: str, *, revertir: bool = False) -> str:
    """SQL que Alembic genera sin conectarse a ninguna base."""
    salida = io.StringIO()
    configuracion = Config(toml_file=str(RAIZ / "pyproject.toml"), output_buffer=salida)
    configuracion.attributes["url"] = URL_FICTICIA
    if revertir:
        command.downgrade(configuracion, rango, sql=True)
    else:
        command.upgrade(configuracion, rango, sql=True)
    return salida.getvalue()


def test_migracion_inicial_crea_tablas_y_unidades() -> None:
    sql = sql_de_migracion("head")
    assert "CREATE TABLE linea" in sql
    assert "uq_linea_pedido_id_articulo_centro_costo" in sql
    assert "INSERT INTO unidad_decimal (unidad) VALUES ('KL')" in sql


def test_migracion_inicial_se_puede_revertir() -> None:
    sql = sql_de_migracion("head:base", revertir=True)
    assert "DROP TABLE linea" in sql
    assert "DROP TABLE usuario" in sql
