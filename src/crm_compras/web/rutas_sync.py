"""API del sincronizador local (diseño §5, R6.2, R6.3).

No usa sesión ni CSRF: cada envío lleva ``Authorization: Bearer <SYNC_TOKEN>``. El token se
revisa antes que el cuerpo, así un envío sin token nunca llega a validarse.
"""

import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from crm_compras.contrato_sync import EnvioArticulos, EnvioCentros, EnvioPrecios, RespuestaSync
from crm_compras.datos import sincronizacion
from crm_compras.web.dependencias import SesionBD

_portador = HTTPBearer(auto_error=False)


def verificar_token(
    request: Request,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_portador)],
) -> None:
    esperado: str | None = request.app.state.token_sync
    recibido = credenciales.credentials if credenciales else ""
    if not esperado or not secrets.compare_digest(esperado.encode(), recibido.encode()):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token del sincronizador ausente o no válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


router = APIRouter(prefix="/sync", tags=["sincronización"], dependencies=[Depends(verificar_token)])


def _ahora() -> datetime:
    return datetime.now(UTC)


@router.post("/articulos")
def recibir_articulos(envio: EnvioArticulos, sesion: SesionBD) -> RespuestaSync:
    recibidos, inactivados = sincronizacion.sincronizar_articulos(sesion, envio.articulos, _ahora())
    sesion.commit()
    return RespuestaSync(recibidos=recibidos, inactivados=inactivados)


@router.post("/centros")
def recibir_centros(envio: EnvioCentros, sesion: SesionBD) -> RespuestaSync:
    recibidos, inactivados = sincronizacion.sincronizar_centros(sesion, envio.centros, _ahora())
    sesion.commit()
    return RespuestaSync(recibidos=recibidos, inactivados=inactivados)


@router.post("/precios")
def recibir_precios(envio: EnvioPrecios, sesion: SesionBD) -> RespuestaSync:
    try:
        recibidos, retirados = sincronizacion.sincronizar_precios(sesion, envio.precios)
    except sincronizacion.PreciosSinArticulo as error:
        sesion.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    sesion.commit()
    return RespuestaSync(recibidos=recibidos, inactivados=retirados)
