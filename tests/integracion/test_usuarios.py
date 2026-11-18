"""T2.3 · I1: el repositorio SQL de usuarios lee lo que hay en PostgreSQL."""

import psycopg

from crm_compras.datos.conexion import BaseDatos
from crm_compras.datos.usuarios import RepositorioUsuariosSQL
from crm_compras.dominio.pedido import Rol
from tests.base_pruebas import url_pruebas


def test_busca_usuarios_por_nombre_y_por_id(conexion: psycopg.Connection) -> None:
    fila = conexion.execute(
        "INSERT INTO usuario (usuario, nombre, hash_clave, rol, activo) "
        "VALUES ('gerente.sql', 'Gerente Ficticio', 'hash', 'gerente', false) RETURNING id"
    ).fetchone()
    assert fila is not None
    conexion.commit()
    try:
        repositorio = RepositorioUsuariosSQL(BaseDatos(url_pruebas()))
        por_nombre = repositorio.por_usuario("gerente.sql")
        assert por_nombre is not None
        assert (por_nombre.nombre, por_nombre.rol, por_nombre.activo) == (
            "Gerente Ficticio",
            Rol.GERENTE,
            False,
        )
        assert repositorio.por_id(fila[0]) == por_nombre
        assert repositorio.por_usuario("no.existe") is None
        assert repositorio.por_id(-1) is None
    finally:
        conexion.execute("DELETE FROM usuario WHERE usuario = 'gerente.sql'")
        conexion.commit()
