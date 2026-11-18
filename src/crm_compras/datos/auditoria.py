"""Registro de auditoría (D19). La tabla solo admite inserciones (ver la migración)."""

import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from crm_compras.datos.modelos import Auditoria


def a_json(valores: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Valores listos para JSONB: Decimal como texto exacto y fechas en ISO 8601.

    Los estados y roles son StrEnum, así que JSON ya los guarda como texto.
    """
    if valores is None:
        return None
    convertido: dict[str, Any] = json.loads(json.dumps(valores, default=_valor_json))
    return convertido


def _valor_json(valor: object) -> str:
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    raise TypeError(f"No se puede auditar un valor de tipo {type(valor).__name__}.")


def registrar(
    sesion: Session,
    *,
    usuario_id: int | None,
    entidad: str,
    entidad_id: object,
    accion: str,
    antes: Mapping[str, Any] | None = None,
    despues: Mapping[str, Any] | None = None,
) -> Auditoria:
    """Agrega un registro a la sesión; se guarda con el mismo commit del cambio auditado."""
    registro = Auditoria(
        usuario_id=usuario_id,
        entidad=entidad,
        entidad_id=str(entidad_id),
        accion=accion,
        antes=a_json(antes),
        despues=a_json(despues),
    )
    sesion.add(registro)
    return registro
