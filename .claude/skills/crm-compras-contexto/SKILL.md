---
name: crm-compras-contexto
description: Estado, decisiones y forma de trabajo del proyecto CRM-Compras (compras y presupuesto de una exportadora de flores, con Softland como fuente). Úsala al iniciar o retomar cualquier sesión en este repositorio, antes de continuar una tarea de docs/spec/tareas.md, o cuando haya dudas sobre el entorno, Softland, SonarCloud, los hooks o el MCP.
---

# CRM-Compras: contexto del proyecto

Las reglas del dominio y el stack están en `CLAUDE.md`, y la especificación en `docs/spec/` (requisitos, diseño y tareas) y `docs/calidad/plan-pruebas.md`. Esta skill guarda **lo que no está en esos archivos**: el avance, las decisiones tomadas con el responsable, el entorno y los problemas ya resueltos.

## 1. Forma de trabajo acordada (obligatoria)

- Interfaz, comentarios, documentación, commits y PR en **español**.
- **Una tarea a la vez**: ejecutar, verificar con pruebas y reportar el resultado real antes de pasar a la siguiente. Nunca decir que algo funciona sin haberlo ejecutado.
- Explicar en una línea qué cambió.
- **Una rama por cambio** (`feat/…`, `fix/…`, `docs/…`, `test/…`, `chore/…`), creada desde `main` actualizado.
- **No hacer commit ni push sin que el responsable lo pida.** Cuando lo autoriza: commit, push, PR y esperar el workflow.
- **Ninguna atribución a herramientas de IA** en commits, PR ni código (sin `Co-Authored-By` ni "Generated with").
- Autor de los commits (configurado en el repo local): `clickcultivossayonara`.
- No agregar funciones que no se pidieron. Ser conciso.
- Esperar aprobación entre fases o tareas.

## 2. Avance

| Fase o tarea | Estado | Dónde |
|---|---|---|
| 1. `CLAUDE.md` (producto, reglas D1–D20, tecnología, pruebas) | ✅ | commit inicial en `main` |
| 2. SPEC: 42 requisitos, diseño y tareas | ✅ | PR #1 |
| 3. Calidad: esqueleto, humo, caja negra, SonarCloud y workflow | ✅ | PR #2 |
| Pruebas adicionales (S2 activa, base de I1, marcas, plan) | ✅ | PR #3 |
| 4. Hooks (secretos y pruebas) | ✅ | PR #4 |
| 5. MCP `softland-lectura` | ✅ | PR #5 |
| T1.1 Calendario semanal | ✅ | PR #6 |
| **T1.2 Reparto semanal del presupuesto** | ⏭️ **siguiente** | — |

Los 6 PR están fusionados en `main`, con el workflow y el Quality Gate en verde.

**T1.2:** `dominio/presupuesto.repartir_mes(valor_mes, n_semanas)`. Se usa `divmod` y el residuo va a la última semana; solo se aceptan 4 o 5 semanas y valores ≥ 0. Los casos están en `plan-pruebas.md` §3.2. La propiedad P1 (T1.2p) es **opcional**: preguntar antes de hacerla.

## 3. Decisiones tomadas con el responsable

- **Stack: Python** (FastAPI + Jinja2/HTMX, SQLAlchemy, PostgreSQL en la nube), en lugar de TypeScript, para reutilizar lo hecho en `C:\Apps\Almacen`.
- **Arquitectura:** la web y la API van en la nube. Un sincronizador local lee Softland y envía los datos por HTTPS saliente. El puerto 1433 nunca se expone.
- **Presupuesto:** anual, con un valor por mes, controlado también **por semana**. Va antes de IVA. Lo que sobra se acumula a la semana siguiente. Usar saldo de semanas o meses futuros, o exceder el presupuesto, requiere **aprobación de Gerencia** con justificación.
- **Semanas ISO**, de lunes a domingo. Una semana que cruza dos meses pertenece al **mes de su jueves**. El responsable dijo primero "el mes del lunes", pero el Excel real (agosto a diciembre de 2025: 4, 4, 5, 4, 4) solo coincide con la regla del jueves, y él la aprobó.
- La semana que consume presupuesto es la de la **fecha requerida**.
- **Partida** = rubro × área, es decir, una fila de detalle del Excel. El jefe asigna la partida de cada línea y el sistema sugiere la que se usó antes para el mismo artículo y centro de costo.
- **Bodegas:** 1 = La Unión, 2 = La Ceja, 5 = Prohibidos. Los artículos prohibidos los define cada jefe y van siempre a la bodega 5. Las demás bodegas las asigna Compras al generar el cargador.
- **Cargador:** un solo `.xlsx` consolidado con el formato exacto de la plantilla (Artículo como texto de 6 dígitos, Centro Costo `NNN-NN-N`, fecha `dd/mm/yyyy`). Se genera por lotes y cada línea se exporta una sola vez.
- **Precio** = el de la última compra en Softland, congelado al enviar el pedido. Un artículo sin compras previas no se puede pedir.
- **Unidades con decimales:** KL, CC, MT, GR, GL, LB y LT. Todas las demás (UND, PAR, RLL…) solo aceptan enteros.
- **Sin Docker Desktop**, por su licencia comercial. PostgreSQL de pruebas: el servicio de GitHub Actions; en local es opcional, con `TEST_DATABASE_URL`.
- Se incluyeron **todas** las pruebas adicionales. Cada una se construye junto con la tarea que crea el código que prueba (ver `tareas.md`).

## 4. Softland (solo lectura)

- SQL Server 2019 (versión 15) Standard. Base `SAYOERP`, esquema `SAYONARA`.
- **El usuario disponible es el mismo de Almacen y es `sysadmin`.** El responsable decidió no crear otro. Por eso la solo lectura se garantiza **en el código**:
  - Solo consultas `SELECT` fijas con parámetros.
  - Un filtro que rechaza instrucciones de escritura.
  - `ROLLBACK` al terminar cada consulta.
  - `READ UNCOMMITTED`, para no bloquear el ERP.
  - **Nunca** escribir en Softland ni ejecutar SQL libre.
- Las credenciales son variables de entorno del usuario de Windows: `SOFTLAND_SERVIDOR`, `SOFTLAND_USUARIO`, `SOFTLAND_CLAVE` y `SOFTLAND_BASE`. **Nunca** se imprimen, ni se copian a archivos, ni se ponen en el chat. Se copiaron desde `C:\Apps\Almacen\config.py`, que las tiene en texto plano: no repetir esa práctica.
- Tablas confirmadas:
  - `ARTICULO`: `ARTICULO`, `DESCRIPCION`, `UNIDAD_ALMACEN`, `ACTIVO` (`S`/`N`), `CLASIFICACION_1`, `TIPO`. Hay unos 4.236 artículos.
  - `CENTRO_COSTO`: `CENTRO_COSTO`, `DESCRIPCION`, `ACEPTA_DATOS`.
  - `BODEGA`: `BODEGA`, `NOMBRE`.
  - `ORDEN_COMPRA`, `PROVEEDOR`.
  - `ORDEN_COMPRA_LINEA`: incluye `CENTRO_COSTO`, `BODEGA` y `PRECIO_UNITARIO`. Sirve para sugerir partidas y obtener precios.
- La consulta de precio de última compra está en `C:\Apps\Almacen\app.py` (ruta `consulta_precios`). Incluye la regla del artículo `020215`: su precio se divide por el factor numérico del comentario.
- **MCP `softland-lectura`** (`herramientas/mcp_softland`, registrado en `.mcp.json`) ofrece: `listar_tablas`, `describir_tabla`, `buscar_articulos`, `buscar_centros_costo` y `unidades_de_medida`. No tiene herramienta de precios, por decisión del responsable.

## 5. Entorno local (Windows 11)

- Repositorio: `C:\Users\stecnologia\CRM-Compras`, en GitHub `clickcultivossayonara/CRM-Compras`, que es público.
- **Abrir VS Code en la carpeta del proyecto.** Si Claude Code arranca en `C:\Users\stecnologia`, no carga los hooks ni el MCP del proyecto.
- Python 3.13. Si `uv` no está en el PATH (pasa cuando VS Code no se cerró del todo después de instalarlo), usar la ruta completa:
  `C:\Users\stecnologia\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`
- GitHub CLI: `C:\Program Files\GitHub CLI\gh.exe`. La sesión está iniciada con `clickcultivossayonara`, que es administrador del repositorio.
- No hay Docker.
- Las variables de entorno nuevas solo se ven después de **cerrar VS Code por completo** (Ctrl + Q), no con "Reload Window".

## 6. Comandos

```
uv sync                                   # instala dev + softland (default-groups)
uv run pytest tests/humo                  # humo (< 1 min)
uv run pytest --cov --cov-report=xml --junitxml=reports/pytest.xml   # suite + cobertura (≥ 80 %)
uv run ruff check . && uv run ruff format --check .
uv run mypy                               # estricto: src, herramientas, tests
uv export --frozen --no-emit-project -o reports/requisitos-auditoria.txt
uv tool run pip-audit -r reports/requisitos-auditoria.txt --disable-pip --require-hashes --strict
```

Verificación completa antes de cada commit: ruff, formato, mypy, la suite con cobertura y la auditoría. Antes de subir, buscar secretos en los archivos cambiados (IP internas, `PWD=`, tokens `sq*_`/`gh*_`).

## 7. CI y SonarCloud

- Workflow `.github/workflows/calidad.yml`: corre en cada push a `main` y en cada PR. Pasos: linter, tipos, pip-audit, humo, suite con PostgreSQL 16 como servicio, y SonarCloud con `uv tool run pysonar`.
- SonarCloud: organización `clickcultivossayonara`, proyecto `clickcultivossayonara_CRM-Compras`. Usa el Quality Gate "Sonar way" y el código nuevo se mide a **30 días**.
- En GitHub: el secreto `SONAR_TOKEN` y las variables `SONAR_ORGANIZATION` y `SONAR_PROJECT_KEY`. El token solo permite analizar; no sirve para administrar el proyecto. El responsable decidió no regenerarlo.
- Para revisar un PR: `gh run list --branch <rama>`, luego `gh run view <id> --log | grep "QUALITY GATE"`.

## 8. Hooks del proyecto (`.claude/settings.json`)

- **PreToolUse `Write|Edit`** → `bloquear_secretos.py`. Bloquea tokens, llaves privadas, `PWD=`, credenciales escritas en el código, IP internas, el archivo `.env` y correos reales en `src`, `tests` y `sincronizador`. Tiene `onFailure: block`.
- **PostToolUse `Write|Edit`** → `ejecutar_pruebas.py`. Corre las pruebas unitarias y de caja negra al editar `.py` en `src/`, `sincronizador/` o `tests/`. Si fallan, devuelve exit 2 con el error.
- Si un hook bloquea algo legítimo, no hay que saltarlo: se ajusta el patrón y se prueba con casos.

## 9. Problemas ya resueltos (no repetir)

- **MCP SDK 2.x:** `FastMCP` ya no existe; ahora es `from mcp.server.mcpserver import MCPServer`, y `ToolAnnotations` está en `mcp.types` (campos `read_only_hint`, `destructive_hint`…).
- **Starlette TestClient** pide `httpx2`, no `httpx`. Las pruebas usan `httpx2`.
- **pyodbc** trae `pyodbc.pyi` sin `py.typed`, así que en mypy tiene una excepción con `ignore_missing_imports`.
- **Hooks en Windows:** reconfigurar stdin, stdout y stderr a UTF-8; si no, las tildes del mensaje se corrompen.
- **Tokens de SonarCloud:** tienen el prefijo `sqco_`, de 4 letras. Patrón: `sq[a-z]{1,3}_`.
- **Primer análisis de una rama en SonarCloud:** el Quality Gate puede quedar en `NONE`, porque no hay línea base, y el escáner lo marca como falla. Basta con volver a ejecutarlo.
- **Bash con heredocs** que contienen comillas simples a veces falla con "unexpected EOF". En ese caso, escribir el archivo con la herramienta Write.
- **`python -I`** no agrega la carpeta del script al `sys.path`. Para el MCP se usa `python -m mcp_softland.servidor`, con el paquete registrado en `pyproject.toml`.
- Los avisos `LF will be replaced by CRLF` son normales en Windows: el repositorio guarda LF.

## 10. Pendientes

- **T1.2 en adelante** (fase 1 del dominio). Ver `docs/spec/tareas.md`.
- **E4:** versión de Softland y si permite importación automática (fuera del MVP).
- Las pruebas adicionales que esperan su tarea: I2 (T4.4), C1 y X1 (T3.2), C2 (T4.6), S1 (T2.3), R1 (T4.1 y T4.4), M1 (T1.10), y E1, A1 y S3 (fase 5).
