"""T2.1 y T2.2 · Capa de datos sin base: URL, valores de auditoría y SQL de las migraciones."""

import io
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from crm_compras.datos.auditoria import a_json
from crm_compras.datos.conexion import VARIABLE_URL, url_desde_entorno, url_sqlalchemy
from crm_compras.dominio.pedido import Estado

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
    assert "CREATE TRIGGER auditoria_sin_cambios BEFORE UPDATE OR DELETE ON auditoria" in sql
    assert "CREATE TRIGGER auditoria_sin_truncate BEFORE TRUNCATE ON auditoria" in sql


def test_migraciones_se_pueden_revertir() -> None:
    sql = sql_de_migracion("head:base", revertir=True)
    assert "DROP TRIGGER auditoria_sin_cambios ON auditoria" in sql
    assert "DROP FUNCTION auditoria_solo_insercion()" in sql
    assert "DROP TABLE linea" in sql
    assert "DROP TABLE usuario" in sql


def test_auditoria_convierte_valores_sin_perder_precision() -> None:
    valores = {
        "valor": Decimal("65040809.987"),
        "fecha": date(2026, 11, 20),
        "momento": datetime(2026, 11, 18, 15, 30, tzinfo=UTC),
        "estado": Estado.ENVIADO,
        "lista": [1, "dos"],
        "vacio": None,
    }
    assert a_json(valores) == {
        "valor": "65040809.987",
        "fecha": "2026-11-20",
        "momento": "2026-11-18T15:30:00+00:00",
        "estado": "enviado",
        "lista": [1, "dos"],
        "vacio": None,
    }
    assert a_json(None) is None


def test_auditoria_rechaza_valores_que_no_sabe_guardar() -> None:
    with pytest.raises(TypeError, match="set"):
        a_json({"conjunto": {1, 2}})
