"""Unitarias del MCP de Softland con una conexión simulada (nunca toca Softland real)."""

import asyncio
from collections.abc import Sequence
from typing import Any

import pytest

from mcp_softland import consultas, servidor
from mcp_softland.consultas import ConsultaNoPermitidaError


class CursorFalso:
    def __init__(self, columnas: list[str], filas: list[tuple[Any, ...]]) -> None:
        self.description = [(c,) for c in columnas]
        self._filas = filas
        self.ejecutadas: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, sql: str, *params: Any) -> None:
        self.ejecutadas.append((sql, params))

    def fetchall(self) -> Sequence[Sequence[Any]]:
        return self._filas


class ConexionFalsa:
    def __init__(self, columnas: list[str], filas: list[tuple[Any, ...]] | None = None) -> None:
        self.cursor_falso = CursorFalso(columnas, filas or [])
        self.rollbacks = 0

    def cursor(self) -> CursorFalso:
        return self.cursor_falso

    def rollback(self) -> None:
        self.rollbacks += 1

    @property
    def consulta(self) -> tuple[str, tuple[Any, ...]]:
        return self.cursor_falso.ejecutadas[-1]


# --- Filtro de solo lectura ---------------------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "  select ARTICULO FROM SAYONARA.ARTICULO",
        "WITH x AS (SELECT 1 AS a) SELECT a FROM x",
        "SELECT FECHA_ULT_MODIF FROM T",  # columna que contiene texto parecido, no la palabra
    ],
)
def test_acepta_consultas_de_lectura(sql: str) -> None:
    consultas.validar_solo_lectura(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE SAYONARA.ARTICULO SET ACTIVO='N'",
        "DELETE FROM SAYONARA.ARTICULO",
        "INSERT INTO T VALUES (1)",
        "SELECT 1; DROP TABLE T",
        "SELECT * INTO copia FROM SAYONARA.ARTICULO",
        "EXEC sp_who",
        "select 1 where 1=1 and exists(select 1) ; truncate table x",
        "MERGE T USING S ON 1=1",
        "",
    ],
)
def test_rechaza_cualquier_escritura(sql: str) -> None:
    with pytest.raises(ConsultaNoPermitidaError):
        consultas.validar_solo_lectura(sql)


def test_siempre_hace_rollback_aunque_falle() -> None:
    conexion = ConexionFalsa(["a"])

    def falla(*_: Any) -> None:
        raise RuntimeError("error de red")

    setattr(conexion.cursor_falso, "execute", falla)  # noqa: B010
    with pytest.raises(RuntimeError):
        consultas.ejecutar(conexion, "SELECT 1")
    assert conexion.rollbacks == 1


def test_lee_sin_bloquear_y_devuelve_filas_como_diccionarios() -> None:
    conexion = ConexionFalsa(["CODIGO", "ACTIVO"], [("020093", "S")])
    filas = consultas.ejecutar(conexion, "SELECT CODIGO, ACTIVO FROM T")
    assert conexion.cursor_falso.ejecutadas[0][0].endswith("READ UNCOMMITTED")
    assert filas == [{"codigo": "020093", "activo": "S"}]
    assert conexion.rollbacks == 1


# --- Herramientas -------------------------------------------------------------------------


def test_buscar_articulos_usa_parametros_y_conserva_ceros() -> None:
    conexion = ConexionFalsa(
        ["codigo", "descripcion", "unidad", "activo"], [("020093", "X", "CC", "S")]
    )
    filas = consultas.buscar_articulos(conexion, "0200")
    sql, params = conexion.consulta
    assert "?" in sql and "0200" not in sql
    assert params == ("%0200%", "%0200%")
    assert filas[0]["codigo"] == "020093"


@pytest.mark.parametrize(("pedido", "aplicado"), [(0, 1), (-5, 1), (10, 10), (20, 20), (500, 20)])
def test_el_limite_queda_entre_1_y_20(pedido: int, aplicado: int) -> None:
    conexion = ConexionFalsa(["codigo", "descripcion", "acepta_datos"])
    consultas.buscar_centros_costo(conexion, "513", pedido)
    assert f"TOP {aplicado} " in conexion.consulta[0]


@pytest.mark.parametrize(
    ("texto", "patron"),
    [("50%", "%50[%]%"), ("A_B", "%A[_]B%"), ("[x]", "%[[]x]%"), ("  pompon ", "%pompon%")],
)
def test_los_comodines_del_usuario_se_buscan_literales(texto: str, patron: str) -> None:
    conexion = ConexionFalsa(["codigo", "descripcion", "unidad", "activo"])
    consultas.buscar_articulos(conexion, texto)
    assert conexion.consulta[1][0] == patron


def test_texto_demasiado_largo_se_rechaza() -> None:
    with pytest.raises(ConsultaNoPermitidaError):
        consultas.buscar_articulos(ConexionFalsa(["a"]), "x" * 51)


def test_texto_de_50_caracteres_se_acepta() -> None:
    consultas.buscar_articulos(ConexionFalsa(["codigo"]), "x" * 50)


@pytest.mark.parametrize("tabla", ["ARTICULO; DROP TABLE X", "ART ICULO", "dbo.ARTICULO", "A'"])
def test_describir_tabla_rechaza_nombres_invalidos(tabla: str) -> None:
    with pytest.raises(ConsultaNoPermitidaError):
        consultas.describir_tabla(ConexionFalsa(["columna"]), tabla)


def test_describir_tabla_solo_en_el_esquema_sayonara() -> None:
    conexion = ConexionFalsa(["columna", "tipo", "admite_nulos", "largo"])
    consultas.describir_tabla(conexion, "centro_costo")
    assert conexion.consulta[1] == ("SAYONARA", "CENTRO_COSTO")


def test_listar_tablas_y_unidades() -> None:
    conexion = ConexionFalsa(["TABLE_NAME"], [("ARTICULO",), ("BODEGA",)])
    assert consultas.listar_tablas(conexion, "art") == ["ARTICULO", "BODEGA"]
    assert conexion.consulta[1] == ("SAYONARA", "%ART%")
    unidades = ConexionFalsa(["unidad", "articulos"], [("UND", 10)])
    assert consultas.unidades_de_medida(unidades) == [{"unidad": "UND", "articulos": 10}]


# --- Servidor -----------------------------------------------------------------------------


def test_cadena_de_conexion_exige_las_tres_variables() -> None:
    with pytest.raises(RuntimeError, match="SOFTLAND_CLAVE"):
        servidor.cadena_conexion({"SOFTLAND_SERVIDOR": "s", "SOFTLAND_USUARIO": "u"})


def test_cadena_de_conexion_usa_base_por_defecto_e_intencion_de_lectura() -> None:
    cadena = servidor.cadena_conexion(
        {"SOFTLAND_SERVIDOR": "srv", "SOFTLAND_USUARIO": "u", "SOFTLAND_CLAVE": "c"}
    )
    assert "DATABASE=SAYOERP;" in cadena
    assert "ApplicationIntent=ReadOnly;" in cadena


def test_todas_las_herramientas_se_declaran_de_solo_lectura() -> None:
    herramientas = asyncio.run(servidor.servidor.list_tools())
    nombres = {h.name for h in herramientas}
    assert nombres == {
        "listar_tablas",
        "describir_tabla",
        "buscar_articulos",
        "buscar_centros_costo",
        "unidades_de_medida",
    }
    for h in herramientas:
        assert h.annotations is not None
        assert h.annotations.read_only_hint is True
        assert h.annotations.destructive_hint is False


def test_las_herramientas_cierran_la_conexion(monkeypatch: pytest.MonkeyPatch) -> None:
    cerradas: list[bool] = []

    class ConexionCerrable(ConexionFalsa):
        def close(self) -> None:
            cerradas.append(True)

    respuestas = iter([[("KG", 3)], [], [], [], []])

    def conectar() -> ConexionCerrable:
        return ConexionCerrable(["unidad", "articulos"], next(respuestas))

    monkeypatch.setattr(servidor, "_conectar", conectar)
    assert servidor.unidades_de_medida() == [{"unidad": "KG", "articulos": 3}]
    assert servidor.listar_tablas("x") == []
    assert servidor.describir_tabla("ARTICULO") == []
    assert servidor.buscar_articulos("x") == []
    assert servidor.buscar_centros_costo("x") == []
    assert len(cerradas) == 5
