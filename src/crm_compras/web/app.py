"""Punto de entrada de la aplicación web."""

from fastapi import FastAPI


def crear_app() -> FastAPI:
    app = FastAPI(title="CRM-Compras")

    @app.get("/salud")
    def salud() -> dict[str, str]:
        return {"estado": "ok"}

    return app


app = crear_app()
