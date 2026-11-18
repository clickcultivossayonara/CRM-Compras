"""Punto de entrada de la aplicación web.

Se arranca con ``uvicorn --factory crm_compras.web.app:crear_app``: la configuración y la base
se leen de variables de entorno al crear la app, no al importar el módulo.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from crm_compras.datos.usuarios import RepositorioUsuarios, RepositorioUsuariosSQL
from crm_compras.web import rutas_sesion
from crm_compras.web.configuracion import Configuracion
from crm_compras.web.seguridad import SinSesion

COOKIE_SESION = "crm_sesion"


def _redirigir_al_login(_request: Request, _error: Exception) -> RedirectResponse:
    return RedirectResponse("/login", status.HTTP_303_SEE_OTHER)


def crear_app(
    configuracion: Configuracion | None = None, usuarios: RepositorioUsuarios | None = None
) -> FastAPI:
    configuracion = configuracion or Configuracion.desde_entorno()
    app = FastAPI(title="CRM-Compras")
    app.state.usuarios = usuarios or RepositorioUsuariosSQL()
    app.add_middleware(
        SessionMiddleware,
        secret_key=configuracion.clave_secreta,
        session_cookie=COOKIE_SESION,
        max_age=configuracion.duracion_sesion,
        same_site="lax",
        https_only=configuracion.cookies_seguras,
    )
    app.add_exception_handler(SinSesion, _redirigir_al_login)
    app.include_router(rutas_sesion.router)

    @app.get("/salud")
    def salud() -> dict[str, str]:
        return {"estado": "ok"}

    return app
