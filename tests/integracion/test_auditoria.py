"""T2.2 · I1: la auditoría solo admite inserciones, también para el dueño de la tabla (D19).

Todo ocurre en una transacción que se revierte: la auditoría no se puede limpiar con DELETE.
"""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import psycopg
import pytest
from alembic.config import Config
from psycopg import errors
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from crm_compras.datos.auditoria import registrar
from crm_compras.datos.conexion import url_sqlalchemy
from crm_compras.datos.modelos import Auditoria
from tests.base_pruebas import url_pruebas

MENSAJE = "solo admite inserciones"


@pytest.fixture
def conexion_orm(alembic_pruebas: Config) -> Iterator[Connection]:
    motor = create_engine(url_sqlalchemy(url_pruebas()))
    with motor.connect() as conexion:
        transaccion = conexion.begin()
        yield conexion
        transaccion.rollback()
    motor.dispose()


@pytest.fixture
def con_registro(conexion: psycopg.Connection) -> psycopg.Connection:
    conexion.execute(
        "INSERT INTO auditoria (entidad, entidad_id, accion, despues) "
        "VALUES ('pedido', '1', 'enviar', '{\"estado\": \"enviado\"}')"
    )
    return conexion


def test_registrar_guarda_valores_exactos(conexion_orm: Connection) -> None:
    sesion = Session(bind=conexion_orm, join_transaction_mode="create_savepoint")
    registrar(
        sesion,
        usuario_id=None,
        entidad="presupuesto",
        entidad_id=2026,
        accion="cargar",
        antes={"total": Decimal("1000.50")},
        despues={"total": Decimal("2000"), "archivo_del": date(2026, 1, 15)},
    )
    sesion.flush()
    guardado = sesion.scalars(select(Auditoria)).one()
    assert (guardado.entidad, guardado.entidad_id, guardado.accion) == (
        "presupuesto",
        "2026",
        "cargar",
    )
    assert guardado.antes == {"total": "1000.50"}
    assert guardado.despues == {"total": "2000", "archivo_del": "2026-01-15"}
    assert guardado.fecha is not None


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE auditoria SET accion = 'otra'",
        "DELETE FROM auditoria",
        "TRUNCATE auditoria",
    ],
)
def test_la_auditoria_no_se_modifica_ni_se_borra(
    con_registro: psycopg.Connection, sql: str
) -> None:
    with pytest.raises(errors.InsufficientPrivilege, match=MENSAJE), con_registro.transaction():
        con_registro.execute(sql)
    fila = con_registro.execute("SELECT count(*), min(accion) FROM auditoria").fetchone()
    assert fila == (1, "enviar")


def test_el_dueno_de_la_tabla_tampoco_puede_modificarla(
    con_registro: psycopg.Connection,
) -> None:
    dueno = con_registro.execute(
        "SELECT tableowner FROM pg_tables WHERE tablename = 'auditoria'"
    ).fetchone()
    actual = con_registro.execute("SELECT current_user").fetchone()
    assert dueno == actual
    with pytest.raises(errors.InsufficientPrivilege), con_registro.transaction():
        con_registro.execute("DELETE FROM auditoria")
