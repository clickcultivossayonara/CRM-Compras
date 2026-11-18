"""T2.4 · Administración por HTTP: usuarios, asignaciones y unidades (R1.10, R6.1, R6.7, D19).

Usa la app sobre PostgreSQL en una transacción que se revierte. Datos ficticios.
"""

from datetime import UTC, datetime

import httpx2
import pytest
from sqlalchemy import select

from crm_compras.datos.conexion import BaseDatos
from crm_compras.datos.modelos import AnioPresupuesto, Auditoria, CentroCosto, Partida
from tests.conftest import Cuenta, Entrar, csrf_de
from tests.fabricas import clave_aleatoria

CLAVE_CORTA = "x" * 5


@pytest.fixture
def admin(cliente_bd: httpx2.Client, entrar_bd: Entrar) -> httpx2.Client:
    """Cliente con la sesión del administrador ficticio."""
    entrar_bd(cliente_bd, "administrador")
    return cliente_bd


def enviar(cliente: httpx2.Client, ruta: str, **datos: object) -> httpx2.Response:
    token = csrf_de(cliente.get("/").text)
    return cliente.post(ruta, data={"csrf_token": token, **datos}, follow_redirects=False)


def ingresa(cliente: httpx2.Client, usuario: str, clave: str) -> bool:
    cliente.cookies.clear()
    token = csrf_de(cliente.get("/login").text)
    respuesta = cliente.post(
        "/login",
        data={"usuario": usuario, "clave": clave, "csrf_token": token},
        follow_redirects=False,
    )
    return respuesta.status_code == 303


def auditoria(bd: BaseDatos, accion: str) -> list[Auditoria]:
    with bd.sesion() as sesion:
        return list(sesion.scalars(select(Auditoria).where(Auditoria.accion == accion)))


def test_crear_un_usuario_que_luego_ingresa(admin: httpx2.Client, bd: BaseDatos) -> None:
    clave = clave_aleatoria()
    respuesta = enviar(
        admin,
        "/admin/usuarios",
        usuario=" Nuevo.Jefe ",
        nombre="Jefe Nuevo",
        rol="jefe",
        clave=clave,
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"].startswith("/admin/usuarios/")
    assert "nuevo.jefe" in admin.get("/admin/usuarios").text

    [registro] = auditoria(bd, "crear")
    assert registro.despues == {
        "usuario": "nuevo.jefe",
        "nombre": "Jefe Nuevo",
        "rol": "jefe",
        "activo": True,
    }
    assert ingresa(admin, "nuevo.jefe", clave)


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ({"usuario": "jefe.1", "rol": "jefe"}, "El usuario jefe.1 ya existe."),
        ({"usuario": "x", "rol": "jefe"}, "El usuario debe tener de 3 a 50 caracteres"),
        ({"usuario": "otro.usuario", "rol": "dueño"}, "El rol &#39;dueño&#39; no existe."),
        (
            {"usuario": "otro.usuario", "rol": "jefe", "clave": CLAVE_CORTA},
            "al menos 12 caracteres",
        ),
    ],
)
def test_crear_usuario_invalido(
    admin: httpx2.Client, bd: BaseDatos, datos: dict[str, str], mensaje: str
) -> None:
    completos = {"nombre": "Nombre Ficticio", "clave": clave_aleatoria(), **datos}
    respuesta = enviar(admin, "/admin/usuarios", **completos)
    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert auditoria(bd, "crear") == []


def test_editar_y_desactivar_un_usuario(
    admin: httpx2.Client, bd: BaseDatos, cuentas_bd: dict[str, Cuenta]
) -> None:
    jefe, clave = cuentas_bd["jefe"]
    ruta = f"/admin/usuarios/{jefe.id}"
    respuesta = enviar(admin, ruta, nombre="Jefe Renombrado", rol="comprador")
    assert respuesta.status_code == 303
    pagina = admin.get(ruta).text
    assert 'value="Jefe Renombrado"' in pagina
    assert '<option value="comprador" selected>' in pagina

    [registro] = auditoria(bd, "actualizar")
    assert registro.antes is not None
    assert registro.despues is not None
    assert (registro.antes["activo"], registro.despues["activo"]) == (True, False)
    assert registro.despues["rol"] == "comprador"
    assert not ingresa(admin, jefe.usuario, clave)


def test_guardar_sin_cambios_no_audita(
    admin: httpx2.Client, bd: BaseDatos, cuentas_bd: dict[str, Cuenta]
) -> None:
    jefe = cuentas_bd["jefe"][0]
    enviar(admin, f"/admin/usuarios/{jefe.id}", nombre=jefe.nombre, rol="jefe", activo="true")
    assert auditoria(bd, "actualizar") == []


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        (
            {"rol": "jefe", "activo": "true"},
            "No puede quitarse a sí mismo el rol de administrador.",
        ),
        ({"rol": "administrador"}, "No puede desactivar su propio usuario."),
    ],
)
def test_el_administrador_no_se_quita_el_acceso(
    admin: httpx2.Client, cuentas_bd: dict[str, Cuenta], cambios: dict[str, str], mensaje: str
) -> None:
    yo = cuentas_bd["administrador"][0]
    respuesta = enviar(admin, f"/admin/usuarios/{yo.id}", nombre=yo.nombre, **cambios)
    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert admin.get("/admin/usuarios").status_code == 200


def test_editar_con_datos_invalidos(admin: httpx2.Client, cuentas_bd: dict[str, Cuenta]) -> None:
    jefe = cuentas_bd["jefe"][0]
    respuesta = enviar(admin, f"/admin/usuarios/{jefe.id}", nombre="  ", rol="jefe")
    assert respuesta.status_code == 422
    assert "El nombre es obligatorio." in respuesta.text


def test_restablecer_la_clave(
    admin: httpx2.Client, bd: BaseDatos, cuentas_bd: dict[str, Cuenta]
) -> None:
    jefe, anterior = cuentas_bd["jefe"]
    nueva = clave_aleatoria()
    assert enviar(admin, f"/admin/usuarios/{jefe.id}/clave", clave=nueva).status_code == 303
    [registro] = auditoria(bd, "cambiar_clave")
    assert (registro.antes, registro.despues) == (None, None)
    assert not ingresa(admin, jefe.usuario, anterior)
    assert ingresa(admin, jefe.usuario, nueva)


def test_clave_corta_no_se_acepta(admin: httpx2.Client, cuentas_bd: dict[str, Cuenta]) -> None:
    jefe = cuentas_bd["jefe"][0]
    respuesta = enviar(admin, f"/admin/usuarios/{jefe.id}/clave", clave=CLAVE_CORTA)
    assert respuesta.status_code == 422
    assert "al menos 12 caracteres" in respuesta.text


@pytest.mark.parametrize("sufijo", ["", "/clave", "/asignaciones"])
def test_usuario_inexistente(admin: httpx2.Client, sufijo: str) -> None:
    ruta = f"/admin/usuarios/9999{sufijo}"
    if not sufijo:
        assert admin.get(ruta).status_code == 404
    datos = {"nombre": "X", "rol": "jefe", "clave": clave_aleatoria()}
    assert enviar(admin, ruta, **datos).status_code == 404


@pytest.fixture
def catalogo(bd: BaseDatos, cuentas_bd: dict[str, Cuenta]) -> tuple[list[int], list[str]]:
    """Dos partidas y dos centros de costo ficticios."""
    with bd.sesion() as sesion:
        administrador = cuentas_bd["administrador"][0].id
        sesion.add(AnioPresupuesto(anio=2026, cargado_por=administrador, archivo="f.xlsx"))
        partidas = [Partida(anio=2026, rubro="RUBRO", area=area) for area in ("AREA A", "AREA B")]
        ahora = datetime.now(UTC)
        centros = [
            CentroCosto(codigo=c, descripcion=f"CENTRO {c}", activo=True, sincronizado_en=ahora)
            for c in ("100-01-1", "200-02-2")
        ]
        sesion.add_all([*partidas, *centros])
        sesion.commit()
        return [p.id for p in partidas], [c.codigo for c in centros]


def test_asignar_partidas_y_centros_a_un_jefe(
    admin: httpx2.Client,
    bd: BaseDatos,
    cuentas_bd: dict[str, Cuenta],
    catalogo: tuple[list[int], list[str]],
) -> None:
    partidas, centros = catalogo
    jefe = cuentas_bd["jefe"][0]
    ruta = f"/admin/usuarios/{jefe.id}"
    respuesta = enviar(admin, f"{ruta}/asignaciones", partidas=[partidas[0]], centros=centros)
    assert respuesta.status_code == 303
    pagina = admin.get(ruta).text
    assert f'name="partidas" value="{partidas[0]}" checked' in pagina
    assert f'name="partidas" value="{partidas[1]}" >' in pagina
    assert 'name="centros" value="200-02-2" checked' in pagina

    [registro] = auditoria(bd, "asignar")
    assert registro.despues == {"partidas": [partidas[0]], "centros": centros}

    # Repetir lo mismo no audita de nuevo; quitar todo sí.
    enviar(admin, f"{ruta}/asignaciones", partidas=[partidas[0]], centros=centros)
    assert len(auditoria(bd, "asignar")) == 1
    enviar(admin, f"{ruta}/asignaciones")
    assert len(auditoria(bd, "asignar")) == 2
    assert "checked" not in admin.get(ruta).text.split("<legend>Partidas</legend>")[-1]


@pytest.mark.parametrize(
    ("cuenta", "datos", "mensaje"),
    [
        ("comprador", None, "Solo a un jefe se le asignan"),
        ("jefe", {"partidas": "9999"}, "No existen las partidas [9999]."),
        ("jefe", {"centros": "999-99-9"}, "No existen los centros de costo [&#39;999-99-9&#39;]."),
    ],
)
def test_asignaciones_invalidas(
    admin: httpx2.Client,
    cuentas_bd: dict[str, Cuenta],
    catalogo: tuple[list[int], list[str]],
    cuenta: str,
    datos: dict[str, str] | None,
    mensaje: str,
) -> None:
    usuario_id = cuentas_bd[cuenta][0].id
    datos = datos or {"partidas": str(catalogo[0][0])}
    respuesta = enviar(admin, f"/admin/usuarios/{usuario_id}/asignaciones", **datos)
    assert respuesta.status_code == 422
    assert mensaje in respuesta.text


def test_agregar_y_quitar_unidades(admin: httpx2.Client, bd: BaseDatos) -> None:
    assert enviar(admin, "/admin/unidades", unidad=" kg ").status_code == 303
    assert "KG" in admin.get("/admin/unidades").text
    assert enviar(admin, "/admin/unidades/KL/quitar").status_code == 303
    assert "/admin/unidades/KL/quitar" not in admin.get("/admin/unidades").text
    assert [r.entidad_id for r in auditoria(bd, "agregar")] == ["KG"]
    assert [r.antes for r in auditoria(bd, "quitar")] == [{"unidad": "KL"}]


@pytest.mark.parametrize(
    ("unidad", "mensaje"),
    [("LT", "La unidad LT ya admite decimales."), ("K1", "de 1 a 10 letras")],
)
def test_unidad_invalida(admin: httpx2.Client, unidad: str, mensaje: str) -> None:
    respuesta = enviar(admin, "/admin/unidades", unidad=unidad)
    assert respuesta.status_code == 422
    assert mensaje in respuesta.text


def test_quitar_una_unidad_que_no_esta(admin: httpx2.Client) -> None:
    assert enviar(admin, "/admin/unidades/UND/quitar").status_code == 404


def test_el_inicio_del_administrador_enlaza_la_administracion(admin: httpx2.Client) -> None:
    pagina = admin.get("/").text
    assert 'href="/admin/usuarios"' in pagina
    assert 'href="/admin/unidades"' in pagina
