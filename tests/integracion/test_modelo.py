"""T2.1 · I1: migración inicial y restricciones del modelo contra PostgreSQL real.

Datos ficticios. Cada inserción inválida va en un punto de guardado para no abortar la prueba.
"""

from datetime import date
from decimal import Decimal

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import errors
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crm_compras.datos.conexion import url_sqlalchemy
from crm_compras.datos.modelos import Base, Linea
from tests.integracion.conftest import url_pruebas

TABLAS = {
    "anio_presupuesto",
    "articulo",
    "asignacion_mensual",
    "auditoria",
    "centro_costo",
    "jefe_centro",
    "jefe_partida",
    "linea",
    "lote",
    "partida",
    "pedido",
    "precio",
    "prohibido",
    "sincronizacion",
    "unidad_decimal",
    "usuario",
}


@pytest.fixture
def base(conexion: psycopg.Connection) -> dict[str, int]:
    """Usuario, catálogo, presupuesto y un pedido ficticios para colgar las líneas."""

    def uno(sql: str, *params: object) -> int:
        fila = conexion.execute(sql, params).fetchone()
        assert fila is not None
        return int(fila[0])

    jefe = uno(
        "INSERT INTO usuario (usuario, nombre, hash_clave, rol) "
        "VALUES ('jefe.prueba', 'Jefe Ficticio', 'x', 'jefe') RETURNING id"
    )
    conexion.execute(
        "INSERT INTO articulo VALUES ('020093', 'ARTICULO FICTICIO', 'UND', true, now())"
    )
    conexion.execute("INSERT INTO centro_costo VALUES ('513-01-2', 'CENTRO FICTICIO', true, now())")
    conexion.execute(
        "INSERT INTO anio_presupuesto (anio, cargado_por, archivo) VALUES (2026, %s, 'f.xlsx')",
        (jefe,),
    )
    partida = uno(
        "INSERT INTO partida (anio, rubro, area) VALUES (2026, 'RUBRO', 'AREA') RETURNING id"
    )
    pedido = uno("INSERT INTO pedido (jefe_id) VALUES (%s) RETURNING id", jefe)
    return {"jefe": jefe, "partida": partida, "pedido": pedido}


def insertar_linea(conexion: psycopg.Connection, base: dict[str, int], **cambios: object) -> None:
    columnas: dict[str, object] = {
        "pedido_id": base["pedido"],
        "articulo": "020093",
        "centro_costo": "513-01-2",
        "partida_id": base["partida"],
        "cantidad": Decimal(4),
        "fecha_requerida": date(2026, 11, 20),
        **cambios,
    }
    marcadores = ", ".join(["%s"] * len(columnas))
    conexion.execute(
        f"INSERT INTO linea ({', '.join(columnas)}) VALUES ({marcadores})",  # noqa: S608
        tuple(columnas.values()),
    )


def rechaza(
    conexion: psycopg.Connection, error: type[Exception], sql: str, *params: object
) -> None:
    with pytest.raises(error), conexion.transaction():
        conexion.execute(sql, params)


def test_la_migracion_crea_todas_las_tablas(conexion: psycopg.Connection) -> None:
    filas = conexion.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    assert {f[0] for f in filas} == TABLAS | {"alembic_version"}


def test_modelos_y_migracion_coinciden(alembic_pruebas: Config) -> None:
    command.check(alembic_pruebas)


def test_unidades_con_decimales_iniciales(conexion: psycopg.Connection) -> None:
    filas = conexion.execute("SELECT unidad FROM unidad_decimal ORDER BY unidad").fetchall()
    assert [f[0] for f in filas] == ["CC", "GL", "GR", "KL", "LB", "LT", "MT"]


@pytest.mark.parametrize(
    ("sql", "params"),
    [
        ("INSERT INTO articulo VALUES (%s, 'X', 'UND', true, now())", ("20093",)),
        ("INSERT INTO articulo VALUES (%s, 'X', 'UND', true, now())", ("02009A",)),
        ("INSERT INTO centro_costo VALUES (%s, 'X', true, now())", ("51301-2",)),
        (
            "INSERT INTO usuario (usuario, nombre, hash_clave, rol) VALUES ('u', 'U', 'x', %s)",
            ("invitado",),
        ),
        ("INSERT INTO sincronizacion (tipo, registros) VALUES (%s, 1)", ("bodegas",)),
        ("INSERT INTO sincronizacion (tipo, registros) VALUES ('precios', %s)", (-1,)),
    ],
)
def test_formatos_y_valores_invalidos(
    conexion: psycopg.Connection, sql: str, params: tuple[object, ...]
) -> None:
    rechaza(conexion, errors.CheckViolation, sql, *params)


@pytest.mark.parametrize(
    ("mes", "valor", "semanas"),
    [(13, 100, 4), (0, 100, 4), (1, -1, 4), (1, 100, 3), (1, 100, 6)],
)
def test_asignacion_mensual_invalida(
    conexion: psycopg.Connection, base: dict[str, int], mes: int, valor: int, semanas: int
) -> None:
    rechaza(
        conexion,
        errors.CheckViolation,
        "INSERT INTO asignacion_mensual VALUES (%s, %s, %s, %s)",
        base["partida"],
        mes,
        valor,
        semanas,
    )


def test_estado_de_pedido_invalido(conexion: psycopg.Connection, base: dict[str, int]) -> None:
    rechaza(
        conexion,
        errors.CheckViolation,
        "UPDATE pedido SET estado = 'pagado' WHERE id = %s",
        base["pedido"],
    )


@pytest.mark.parametrize(
    "cambios",
    [
        {"cantidad": Decimal(0)},
        {"cantidad": Decimal(-1)},
        {"bodega": 3},
        {"valor": -1},
        {"precio_congelado": -1},
    ],
)
def test_linea_invalida(
    conexion: psycopg.Connection, base: dict[str, int], cambios: dict[str, object]
) -> None:
    with pytest.raises(errors.CheckViolation), conexion.transaction():
        insertar_linea(conexion, base, **cambios)


def test_articulo_y_centro_repetidos_en_un_pedido(
    conexion: psycopg.Connection, base: dict[str, int]
) -> None:
    insertar_linea(conexion, base)
    with pytest.raises(errors.UniqueViolation), conexion.transaction():
        insertar_linea(conexion, base, cantidad=Decimal(1))


def test_linea_con_articulo_inexistente(conexion: psycopg.Connection, base: dict[str, int]) -> None:
    with pytest.raises(errors.ForeignKeyViolation), conexion.transaction():
        insertar_linea(conexion, base, articulo="999999")


def test_partida_repetida(conexion: psycopg.Connection, base: dict[str, int]) -> None:
    rechaza(
        conexion,
        errors.UniqueViolation,
        "INSERT INTO partida (anio, rubro, area) VALUES (2026, 'RUBRO', 'AREA')",
    )


def test_bodegas_validas_y_valor_grande_exacto(
    conexion: psycopg.Connection, base: dict[str, int]
) -> None:
    insertar_linea(conexion, base, bodega=5, valor=10**13, cantidad=Decimal("2.50"))
    fila = conexion.execute("SELECT valor, cantidad, comentario FROM linea").fetchone()
    assert fila == (10**13, Decimal("2.50"), "")


def test_los_modelos_leen_lo_guardado(conexion: psycopg.Connection, base: dict[str, int]) -> None:
    insertar_linea(conexion, base, bodega=5)
    conexion.commit()
    try:
        motor = create_engine(url_sqlalchemy(url_pruebas()))
        with Session(motor) as sesion:
            linea = sesion.scalars(select(Linea)).one()
            assert (linea.articulo, linea.cantidad, linea.bodega) == ("020093", Decimal(4), 5)
        motor.dispose()
    finally:
        for tabla in ("linea", "pedido", "partida", "anio_presupuesto", "centro_costo"):
            conexion.execute(f"DELETE FROM {tabla}")  # noqa: S608
        conexion.execute("DELETE FROM articulo")
        conexion.execute("DELETE FROM usuario")
        conexion.commit()


def test_la_migracion_se_revierte_y_se_vuelve_a_aplicar(alembic_pruebas: Config) -> None:
    command.downgrade(alembic_pruebas, "base")
    with psycopg.connect(url_pruebas(), connect_timeout=10) as conn:
        filas = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
    assert {f[0] for f in filas} == {"alembic_version"}
    command.upgrade(alembic_pruebas, "head")
    assert set(Base.metadata.tables) == TABLAS
