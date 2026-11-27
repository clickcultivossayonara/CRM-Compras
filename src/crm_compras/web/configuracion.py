"""Configuración de la web, leída de variables de entorno (los secretos nunca van en el código)."""

import os
from dataclasses import dataclass

LARGO_MINIMO_CLAVE = 32
OCHO_HORAS = 8 * 60 * 60


@dataclass(frozen=True)
class Configuracion:
    clave_secreta: str
    """Firma la cookie de sesión (SECRET_KEY)."""
    cookies_seguras: bool = True
    """Cookie solo por HTTPS; se apaga únicamente para pruebas locales por HTTP."""
    duracion_sesion: int = OCHO_HORAS
    token_sync: str | None = None
    """Token del sincronizador (SYNC_TOKEN). Sin él, /sync/* rechaza todo envío."""

    def __post_init__(self) -> None:
        if len(self.clave_secreta) < LARGO_MINIMO_CLAVE:
            raise ValueError(f"SECRET_KEY debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
        if self.token_sync is not None and len(self.token_sync) < LARGO_MINIMO_CLAVE:
            raise ValueError(f"SYNC_TOKEN debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")

    @classmethod
    def desde_entorno(cls) -> "Configuracion":
        return cls(
            clave_secreta=os.environ.get("SECRET_KEY", ""),
            cookies_seguras=os.environ.get("CRM_COOKIES_SEGURAS", "1") != "0",
            token_sync=os.environ.get("SYNC_TOKEN") or None,
        )
