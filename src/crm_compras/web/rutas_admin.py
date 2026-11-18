"""Administración: usuarios, asignaciones de cada jefe y unidades con decimales (R1.10, R6.7).

Todas las rutas son solo del Administrador y exigen CSRF en los POST.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from crm_compras.datos import administracion as admin
from crm_compras.datos.modelos import Usuario
from crm_compras.datos.usuarios import UsuarioSesion
from crm_compras.dominio.pedido import Rol
from crm_compras.dominio.usuarios import LARGO_MAXIMO_CLAVE, errores_clave
from crm_compras.web.rutas_sesion import plantillas
from crm_compras.web.seguridad import (
    CAMPO_CSRF,
    cifrar_clave,
    requiere_roles,
    token_csrf,
    verificar_csrf,
)


def sesion_bd(request: Request) -> Iterator[Session]:
    with request.app.state.base.sesion() as sesion:
        yield sesion


router = APIRouter(prefix="/admin", dependencies=[Depends(verificar_csrf)])

Administrador = Annotated[UsuarioSesion, Depends(requiere_roles(Rol.ADMINISTRADOR))]
SesionBD = Annotated[Session, Depends(sesion_bd)]
Texto = Annotated[str, Form(max_length=LARGO_MAXIMO_CLAVE)]


def _pagina(
    request: Request,
    plantilla: str,
    contexto: dict[str, object],
    errores: list[str] | None = None,
) -> Response:
    codigo = status.HTTP_422_UNPROCESSABLE_CONTENT if errores else status.HTTP_200_OK
    return plantillas.TemplateResponse(
        request,
        plantilla,
        {
            **contexto,
            "errores": errores or [],
            "campo_csrf": CAMPO_CSRF,
            "csrf": token_csrf(request),
            "roles": [r.value for r in Rol],
        },
        status_code=codigo,
    )


def _volver(ruta: str) -> RedirectResponse:
    return RedirectResponse(ruta, status.HTTP_303_SEE_OTHER)


def _usuario_o_404(sesion: Session, usuario_id: int) -> Usuario:
    try:
        return admin.obtener_usuario(sesion, usuario_id)
    except admin.NoEncontrado as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


def _pagina_usuario(
    request: Request, sesion: Session, usuario_id: int, errores: list[str] | None = None
) -> Response:
    usuario = _usuario_o_404(sesion, usuario_id)
    partidas, centros = admin.asignaciones(sesion, usuario_id)
    return _pagina(
        request,
        "admin_usuario.html",
        {
            "usuario": usuario,
            "partidas": admin.listar_partidas(sesion),
            "centros": admin.listar_centros(sesion),
            "partidas_asignadas": partidas,
            "centros_asignados": centros,
        },
        errores,
    )


@router.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request, _admin: Administrador, sesion: SesionBD) -> Response:
    return _pagina(request, "admin_usuarios.html", {"usuarios": admin.listar_usuarios(sesion)})


@router.post("/usuarios", response_class=HTMLResponse)
def crear_usuario(
    request: Request,
    editor: Administrador,
    sesion: SesionBD,
    usuario: Texto,
    nombre: Texto,
    rol: Texto,
    clave: Texto,
) -> Response:
    errores = errores_clave(clave)
    if not errores:
        try:
            nuevo = admin.crear_usuario(
                sesion, editor.id, usuario, nombre, rol, cifrar_clave(clave)
            )
        except admin.AdministracionError as error:
            errores = error.problemas
    if errores:
        sesion.rollback()
        return _pagina(
            request, "admin_usuarios.html", {"usuarios": admin.listar_usuarios(sesion)}, errores
        )
    sesion.commit()
    return _volver(f"/admin/usuarios/{nuevo.id}")


@router.get("/usuarios/{usuario_id}", response_class=HTMLResponse)
def usuario(request: Request, usuario_id: int, _admin: Administrador, sesion: SesionBD) -> Response:
    return _pagina_usuario(request, sesion, usuario_id)


@router.post("/usuarios/{usuario_id}", response_class=HTMLResponse)
def actualizar_usuario(
    request: Request,
    usuario_id: int,
    editor: Administrador,
    sesion: SesionBD,
    nombre: Texto,
    rol: Texto,
    activo: Annotated[bool, Form()] = False,
) -> Response:
    _usuario_o_404(sesion, usuario_id)
    try:
        admin.actualizar_usuario(sesion, editor.id, usuario_id, nombre, rol, activo)
    except admin.AdministracionError as error:
        sesion.rollback()
        return _pagina_usuario(request, sesion, usuario_id, error.problemas)
    sesion.commit()
    return _volver(f"/admin/usuarios/{usuario_id}")


@router.post("/usuarios/{usuario_id}/clave", response_class=HTMLResponse)
def cambiar_clave(
    request: Request, usuario_id: int, editor: Administrador, sesion: SesionBD, clave: Texto
) -> Response:
    _usuario_o_404(sesion, usuario_id)
    if errores := errores_clave(clave):
        return _pagina_usuario(request, sesion, usuario_id, errores)
    admin.cambiar_clave(sesion, editor.id, usuario_id, cifrar_clave(clave))
    sesion.commit()
    return _volver(f"/admin/usuarios/{usuario_id}")


@router.post("/usuarios/{usuario_id}/asignaciones", response_class=HTMLResponse)
def asignar(
    request: Request,
    usuario_id: int,
    editor: Administrador,
    sesion: SesionBD,
    partidas: Annotated[list[int] | None, Form()] = None,
    centros: Annotated[list[str] | None, Form()] = None,
) -> Response:
    _usuario_o_404(sesion, usuario_id)
    try:
        admin.asignar(sesion, editor.id, usuario_id, partidas or [], centros or [])
    except admin.AdministracionError as error:
        sesion.rollback()
        return _pagina_usuario(request, sesion, usuario_id, error.problemas)
    sesion.commit()
    return _volver(f"/admin/usuarios/{usuario_id}")


@router.get("/unidades", response_class=HTMLResponse)
def unidades(request: Request, _admin: Administrador, sesion: SesionBD) -> Response:
    return _pagina(request, "admin_unidades.html", {"unidades": admin.listar_unidades(sesion)})


@router.post("/unidades", response_class=HTMLResponse)
def agregar_unidad(
    request: Request, editor: Administrador, sesion: SesionBD, unidad: Texto
) -> Response:
    try:
        admin.agregar_unidad(sesion, editor.id, unidad)
    except admin.AdministracionError as error:
        sesion.rollback()
        return _pagina(
            request,
            "admin_unidades.html",
            {"unidades": admin.listar_unidades(sesion)},
            error.problemas,
        )
    sesion.commit()
    return _volver("/admin/unidades")


@router.post("/unidades/{unidad}/quitar")
def quitar_unidad(unidad: str, editor: Administrador, sesion: SesionBD) -> Response:
    try:
        admin.quitar_unidad(sesion, editor.id, unidad)
    except admin.NoEncontrado as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    sesion.commit()
    return _volver("/admin/unidades")
