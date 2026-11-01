"""PostToolUse: al editar lógica Python, corre las pruebas rápidas y reporta si fallan."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAICES = ("src/crm_compras/", "sincronizador/", "tests/")


def main() -> int:
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    datos = json.load(sys.stdin)
    ruta = (datos.get("tool_input") or {}).get("file_path", "")
    proyecto = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    try:
        relativa = Path(ruta).resolve().relative_to(proyecto).as_posix()
    except ValueError:
        return 0  # fuera del proyecto
    if not relativa.endswith(".py") or not relativa.startswith(RAICES):
        return 0
    uv = shutil.which("uv") or "uv"
    resultado = subprocess.run(  # noqa: S603 - comando fijo, sin entrada del usuario
        [uv, "run", "pytest", "tests/unitarias", "tests/caja_negra", "-q", "-x", "--no-header"],
        cwd=proyecto,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if resultado.returncode in (0, 5):  # 5 = no hay pruebas que correr
        return 0
    salida = (resultado.stdout + resultado.stderr)[-3000:]
    print(f"Las pruebas fallan después de editar {relativa}:\n{salida}", file=sys.stderr)
    return 2  # Claude recibe el error y debe corregirlo


if __name__ == "__main__":
    sys.exit(main())
