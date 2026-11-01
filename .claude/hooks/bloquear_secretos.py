"""PreToolUse: bloquea escrituras que contengan secretos o datos reales de la empresa."""

import json
import re
import sys
from pathlib import PurePath

PATRONES = [
    (
        r"\b(sq[a-z]{1,3}_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})",
        "token de servicio",
    ),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "llave privada"),
    (r"(?i)\bPWD=[^;{}\s]{3,};", "contraseña en cadena de conexión"),
    (
        r"(?i)\b(password|passwd|pwd|clave|contrase[ñn]a|secret_key|token)\s*[:=]\s*['\"][^'\"\s]{4,}['\"]",
        "credencial escrita en el código",
    ),
    (
        r"\b(10\.\d{1,3}|192\.168|172\.(1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b",
        "IP de la red interna",
    ),
]
# Correos reales: solo se revisan en código y pruebas; se permiten dominios de ejemplo.
CORREO = r"[A-Za-z0-9._%+-]+@(?!(example|ejemplo)\.)[A-Za-z0-9-]+\.[A-Za-z.]{2,}"


def negar(motivo: str) -> None:
    razon = f"Bloqueado: {motivo}. Usa variables de entorno o datos ficticios."
    salida = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": razon,
        }
    }
    print(json.dumps(salida, ensure_ascii=False))


def main() -> int:
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    entrada = json.load(sys.stdin).get("tool_input") or {}
    ruta = entrada.get("file_path", "")
    texto = "\n".join(str(entrada.get(k, "")) for k in ("content", "new_string"))
    partes = PurePath(ruta.replace("\\", "/")).parts
    if PurePath(ruta).name == ".env":
        negar("el archivo .env no se edita desde aquí")
        return 0
    if ".claude" in partes and "hooks" in partes:
        return 0  # este mismo script contiene los patrones
    for patron, nombre in PATRONES:
        if re.search(patron, texto):
            negar(f"{nombre} en {PurePath(ruta).name}")
            return 0
    es_codigo = any(p in ("src", "tests", "sincronizador") for p in partes)
    if es_codigo and re.search(CORREO, texto):
        negar(f"correo que parece real en {PurePath(ruta).name}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
