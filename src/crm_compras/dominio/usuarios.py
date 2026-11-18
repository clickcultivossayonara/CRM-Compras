"""Reglas de la administración de usuarios y de unidades con decimales (R1.10, R6.1, R6.7)."""

import re

from crm_compras.dominio.pedido import Rol

LARGO_MINIMO_CLAVE = 12
LARGO_MAXIMO_CLAVE = 128
LARGO_MAXIMO_NOMBRE = 120

# Minúsculas, dígitos, punto, guion y guion bajo; de 3 a 50 caracteres (solo ASCII).
_USUARIO = re.compile(r"[a-z0-9][a-z0-9._-]{2,49}")
_UNIDAD = re.compile(r"[A-Z]{1,10}")


def normalizar_usuario(usuario: str) -> str:
    return usuario.strip().lower()


def normalizar_unidad(unidad: str) -> str:
    return unidad.strip().upper()


def errores_usuario(usuario: str, nombre: str, rol: str) -> list[str]:
    errores = []
    if not _USUARIO.fullmatch(usuario):
        errores.append(
            "El usuario debe tener de 3 a 50 caracteres: minúsculas, dígitos, punto o guion."
        )
    if not nombre.strip():
        errores.append("El nombre es obligatorio.")
    elif len(nombre.strip()) > LARGO_MAXIMO_NOMBRE:
        errores.append(f"El nombre admite máximo {LARGO_MAXIMO_NOMBRE} caracteres.")
    if rol not in {r.value for r in Rol}:
        errores.append(f"El rol {rol!r} no existe.")
    return errores


def errores_clave(clave: str) -> list[str]:
    if len(clave) < LARGO_MINIMO_CLAVE:
        return [f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres."]
    if len(clave) > LARGO_MAXIMO_CLAVE:
        return [f"La contraseña admite máximo {LARGO_MAXIMO_CLAVE} caracteres."]
    return []


def errores_unidad(unidad: str) -> list[str]:
    if not _UNIDAD.fullmatch(unidad):
        return ["La unidad debe tener de 1 a 10 letras, como en Softland (por ejemplo, KL)."]
    return []


def errores_autoedicion(
    editor_id: int, usuario_id: int, rol_nuevo: Rol, activo_nuevo: bool
) -> list[str]:
    """Un administrador no puede quitarse su rol ni desactivarse: dejaría el sistema sin acceso."""
    if editor_id != usuario_id:
        return []
    errores = []
    if rol_nuevo is not Rol.ADMINISTRADOR:
        errores.append("No puede quitarse a sí mismo el rol de administrador.")
    if not activo_nuevo:
        errores.append("No puede desactivar su propio usuario.")
    return errores
