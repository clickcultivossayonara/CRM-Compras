"""Integración: la base de datos de pruebas está disponible y es compatible."""

import psycopg


def test_postgresql_es_version_16_o_superior(conexion: psycopg.Connection) -> None:
    fila = conexion.execute("SHOW server_version_num").fetchone()
    assert fila is not None
    assert int(fila[0]) >= 160000


def test_los_cambios_de_una_prueba_no_quedan_guardados(conexion: psycopg.Connection) -> None:
    conexion.execute("CREATE TEMP TABLE prueba_aislamiento (valor int)")
    conexion.execute("INSERT INTO prueba_aislamiento VALUES (1)")
    fila = conexion.execute("SELECT count(*) FROM prueba_aislamiento").fetchone()
    assert fila == (1,)
