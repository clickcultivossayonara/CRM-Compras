"""Inicio y cierre de sesión, y página de inicio (R6.1)."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from crm_compras.datos.usuarios import UsuarioSesion
from crm_compras.dominio.pedido import Rol
from crm_compras.web.seguridad import (
    CAMPO_CSRF,
    CLAVE_SESION_USUARIO,
    autenticar,
    renovar_csrf,
    repositorio,
    requiere_roles,
    token_csrf,
    verificar_csrf,
)

LARGO_MAXIMO = 128
MENSAJE_FALLIDO = "Usuario o contraseña incorrectos."

plantillas = Jinja2Templates(directory=Path(__file__).parent / "plantillas")
router = APIRouter(dependencies=[Depends(verificar_csrf)])

CualquierRol = Annotated[UsuarioSesion, Depends(requiere_roles(*Rol))]


def _formulario(request: Request, error: str = "", codigo: int = status.HTTP_200_OK) -> Response:
    return plantillas.TemplateResponse(
        request,
        "login.html",
        {"campo_csrf": CAMPO_CSRF, "csrf": token_csrf(request), "error": error},
        status_code=codigo,
    )


@router.get("/login", response_class=HTMLResponse)
def formulario_login(request: Request) -> Response:
    return _formulario(request)


@router.post("/login", response_class=HTMLResponse)
def iniciar_sesion(
    request: Request,
    usuario: Annotated[str, Form(max_length=LARGO_MAXIMO)],
    clave: Annotated[str, Form(max_length=LARGO_MAXIMO)],
) -> Response:
    autenticado = autenticar(repositorio(request), usuario.strip(), clave)
    if autenticado is None:
        return _formulario(request, MENSAJE_FALLIDO, status.HTTP_401_UNAUTHORIZED)
    request.session.clear()
    request.session[CLAVE_SESION_USUARIO] = autenticado.id
    renovar_csrf(request)
    return RedirectResponse("/", status.HTTP_303_SEE_OTHER)


@router.post("/salir")
def cerrar_sesion(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/login", status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
def inicio(request: Request, usuario: CualquierRol) -> Response:
    return plantillas.TemplateResponse(
        request,
        "inicio.html",
        {"usuario": usuario, "campo_csrf": CAMPO_CSRF, "csrf": token_csrf(request)},
    )
