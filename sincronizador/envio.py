"""Envío a la API por HTTPS saliente (D1: el puerto de SQL Server nunca se expone)."""

import json
import urllib.error
import urllib.request
from typing import Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel

from crm_compras.contrato_sync import RespuestaSync

SEGUNDOS = 120
_HOSTS_LOCALES = frozenset({"localhost", "127.0.0.1"})


class EnvioError(RuntimeError):
    """La API rechazó el envío o no respondió."""


class Transporte(Protocol):
    def post(self, ruta: str, cuerpo: bytes, encabezados: dict[str, str]) -> tuple[int, bytes]:
        """Envía un POST y devuelve el código HTTP y el cuerpo de la respuesta."""
        ...


class TransporteHTTPS:
    """Transporte real con la biblioteca estándar; verifica el certificado del servidor."""

    def __init__(self, url_base: str) -> None:
        partes = urlsplit(url_base)
        if partes.scheme != "https" and partes.hostname not in _HOSTS_LOCALES:
            raise ValueError("La URL de la API debe usar https (solo localhost admite http).")
        self._url_base = url_base.rstrip("/")

    def post(self, ruta: str, cuerpo: bytes, encabezados: dict[str, str]) -> tuple[int, bytes]:
        peticion = urllib.request.Request(  # noqa: S310 - el esquema se valida al crear
            self._url_base + ruta, data=cuerpo, headers=encabezados, method="POST"
        )
        try:
            with urllib.request.urlopen(peticion, timeout=SEGUNDOS) as respuesta:  # noqa: S310
                return int(respuesta.status), bytes(respuesta.read())
        except urllib.error.HTTPError as error:
            return int(error.code), bytes(error.read())


class ClienteAPI:
    def __init__(self, transporte: Transporte, token: str) -> None:
        self._transporte = transporte
        self._token = token

    def enviar(self, tipo: str, envio: BaseModel) -> RespuestaSync:
        codigo, cuerpo = self._transporte.post(
            f"/sync/{tipo}",
            envio.model_dump_json().encode(),
            {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
        )
        if codigo != 200:
            raise EnvioError(f"La API respondió {codigo} al enviar {tipo}: {_detalle(cuerpo)}")
        return RespuestaSync.model_validate_json(cuerpo)


def _detalle(cuerpo: bytes) -> str:
    try:
        datos = json.loads(cuerpo)
    except ValueError:
        return cuerpo[:200].decode(errors="replace")
    return str(datos.get("detail", datos))[:500] if isinstance(datos, dict) else str(datos)[:500]
