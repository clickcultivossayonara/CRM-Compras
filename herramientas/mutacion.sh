#!/usr/bin/env bash
# Pruebas de mutación (M1) sobre src/crm_compras/dominio/ con un umbral mínimo de mutantes
# eliminados. mutmut no corre en Windows: ejecutar en Linux o WSL desde la raíz del repositorio,
# por ejemplo: wsl -d Ubuntu -- bash herramientas/mutacion.sh
# El proyecto se copia a una carpeta de Linux porque en /mnt/c mutmut no puede copiar fechas.
set -uo pipefail

UMBRAL="${UMBRAL_MUTACION:-80}"
origen="$(pwd)"
destino="${DESTINO_MUTACION:-$HOME/crm-compras-mutacion}"
export PATH="$HOME/.local/bin:$PATH"
export UV_LINK_MODE=copy

rm -rf "$destino"
mkdir -p "$destino"
tar -C "$origen" \
    --exclude=.venv --exclude=.git --exclude=mutants --exclude=__pycache__ \
    --exclude=.mypy_cache --exclude=.ruff_cache --exclude=.pytest_cache --exclude=reports \
    -cf - . | tar -C "$destino" -xf -
cd "$destino" || exit 1

# Sin --no-build uv podría ejecutar scripts de instalación. El proyecto no se instala:
# mutmut lo carga desde su copia en mutants/src.
uv sync --frozen --no-build --no-install-project --group mutacion -q || exit 1
uv run --no-sync --no-build mutmut run > mutmut.log 2>&1 || { tail -20 mutmut.log; exit 1; }
uv run --no-sync --no-build mutmut results
uv run --no-sync --no-build mutmut export-cicd-stats > /dev/null || exit 1

uv run --no-sync --no-build python - "$UMBRAL" <<'PY'
import json
import sys

umbral = float(sys.argv[1])
datos = json.load(open("mutants/mutmut-cicd-stats.json", encoding="utf-8"))
eliminados = datos["killed"]
total = datos["total"]
puntaje = 100 * eliminados / total if total else 0.0
print(f"Mutantes eliminados: {eliminados} de {total} ({puntaje:.1f} %). Umbral: {umbral:.0f} %.")
sys.exit(0 if puntaje >= umbral else 1)
PY
