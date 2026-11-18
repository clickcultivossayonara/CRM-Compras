"""Crea el primer administrador (o uno de rescate). La contraseña se pide sin mostrarla.

Uso: ``DATABASE_URL=... uv run python -m crm_compras.crear_administrador <usuario> "<nombre>"``
"""

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from crm_compras.datos import administracion as admin
from crm_compras.datos.conexion import BaseDatos
from crm_compras.dominio.pedido import Rol
from crm_compras.dominio.usuarios import errores_clave
from crm_compras.web.seguridad import cifrar_clave


def main(
    argumentos: Sequence[str] | None = None,
    base: BaseDatos | None = None,
    pedir_clave: Callable[[str], str] = getpass.getpass,
) -> int:
    lector = argparse.ArgumentParser(description="Crea un usuario administrador.")
    lector.add_argument("usuario")
    lector.add_argument("nombre")
    opciones = lector.parse_args(argumentos)

    clave = pedir_clave("Contraseña: ")
    errores = errores_clave(clave)
    if not errores and pedir_clave("Repita la contraseña: ") != clave:
        errores = ["Las contraseñas no coinciden."]
    if errores:
        print("\n".join(errores), file=sys.stderr)
        return 1

    with (base or BaseDatos()).sesion() as sesion:
        try:
            nuevo = admin.crear_usuario(
                sesion,
                None,
                opciones.usuario,
                opciones.nombre,
                Rol.ADMINISTRADOR.value,
                cifrar_clave(clave),
            )
        except admin.AdministracionError as error:
            print("\n".join(error.problemas), file=sys.stderr)
            return 1
        sesion.commit()
        print(f"Administrador {nuevo.usuario} creado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
