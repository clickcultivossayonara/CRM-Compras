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
| Skill de contexto | ✅ | PR #7 |
| T1.2 Reparto semanal (`presupuesto.repartir_mes`) + propiedad P1 | ✅ | PR #8 |
| T1.3 Saldo y disponible (`saldos`, `disponibles`, `cabe`) + propiedades P2 y P3 | ✅ | PR #9 |
| T1.4 Lector del Excel (`lector_presupuesto.leer_presupuesto`) | ✅ | PR #10 |
| T1.5 Precios (`precios.normalizar`, regla del `020215`) | ✅ | PR #11 |
| T1.6 Validación de líneas y pedido (`pedido.validar_linea`, `validar_pedido`) | ✅ | PR #12 |
| T1.7 Máquina de estados (`enviar`, `aprobar`, `rechazar`, `anular`, `exportar`) + P5 | ✅ | PR #14 |
| T1.8 Cargador (`cargador.armar_cargador`, `lineas_para_lote`) + P6 | ✅ | PR #15 |
| T1.9 Propiedad P4 del calendario + T1.10 mutación M1 (97,6 %) | ✅ | PR #16 |
| **Fase 1 (dominio) completa. Siguiente: fase 2** (ver `docs/spec/tareas.md`) | ⏭️ **siguiente** | — |

Los 16 PR están fusionados en `main` con el workflow y el Quality Gate en verde (228 pruebas en CI, cobertura del 100 %; SonarCloud en `main`: 0 bugs, 0 vulnerabilidades, 0 code smells, 0 % de duplicación).

**Próxima sesión (fase 2):**
1. **Instalar PostgreSQL en WSL (Ubuntu)**, aprobado por el responsable, para correr en local las pruebas de integración (I1) con `TEST_DATABASE_URL`. Sin Docker. Requiere `sudo` dentro de Ubuntu: la contraseña de Linux la escribe el responsable, nunca se pide en el chat. Usar credenciales de prueba, solo en variables de entorno.
2. **T2.1**: modelos SQLAlchemy y migración inicial de `diseno.md` §3, con I1. Después T2.2 (auditoría solo de inserción), T2.3 (sesión, argon2, roles, CSRF y S1) y T2.4 (administración).

**Cómo quedó el dominio hecho (para usarlo en las tareas siguientes):**
- `presupuesto`: las semanas de una partida van en listas; la posición *i* es la semana *i* + 1 del año ISO. `cabe(asignado, consumido, lineas)` recibe las líneas como pares `(posición de semana, valor)`, las suma por semana y responde si caben sin Gerencia.
- `lector_presupuesto.leer_presupuesto(filas, anio)`: recibe las filas como las da openpyxl **con fórmulas** (`iter_rows(values_only=True)` sin `data_only`); devuelve `Lectura` con `semanas`, `partidas` (`PartidaLeida`: rubro, área, fila, valores por mes), `advertencias` y `errores`. Probado en local contra el Excel real: 66 partidas, 0 errores.
- `precios.normalizar(articulo, precio_unitario: Decimal, comentario)` → `int | None`.
- `pedido`: `LineaPedido` (articulo, centro_costo, partida_id, cantidad `Decimal`, fecha_requerida, comentario), `ContextoValidacion` (hoy, articulos, precios, centros, centros y partidas del jefe con su año, años con presupuesto, prohibidos, otros_pedidos) y `LineaValidada` (errores, advertencias, valor, bodega). `anio_presupuesto(fecha)` = año del mes del jueves de su semana. `valor_linea(cantidad, precio)` con `ROUND_HALF_UP`. `UNIDADES_DECIMALES` y `BODEGA_PROHIBIDOS` son constantes del módulo.
- `pedido` (estados): `Estado` y `Rol` (`StrEnum` con los valores de la base). `enviar(estado, lineas_validadas, saldos: {partida_id: SaldoPartida})` → `ENVIADO` o `PENDIENTE_GERENCIA`; `partidas_que_exceden` para mostrar el exceso al Gerente; `aprobar(estado, rol, justificacion)`, `rechazar(estado, rol, motivo)`, `anular(estado, motivo)`, `exportar(estado)`, `verificar_editable(estado)`, `compromete_presupuesto(estado)`. Errores de flujo: `TransicionInvalida` (con `noqa: N818`, nombre del diseño); datos faltantes: `ValueError`.
- `cargador`: `LineaCargador` (con `prohibido`, `bodega` y `lote_id`), `armar_cargador(lineas)` → `{nombre_hoja: [filas]}` ordenado por bodega y por `linea_id`; `CargadorError.problemas`; `ENCABEZADOS` y `HOJAS` (`La Union`, `La Ceja`, `Prohibidos`) tomados de la plantilla real `Bodega 5.xlsx`. Escribir el `.xlsx` y compararlo con una plantilla ficticia es de T4.6 (C2).
- `tests/fabricas.py`: fábricas compartidas (por ahora, `otros_digitos` para dígitos no ASCII).
- Las pruebas de propiedad importan Hypothesis **dentro** de la prueba, para que la suite corra sin el grupo `propiedad`. CI instala ese grupo para que mypy las revise.

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
- **Pruebas de propiedad:** el responsable aprobó hacerlas (P1, P2 y P3 hechas). Igual preguntar antes de cada una, porque son opcionales.
- **Excel de presupuesto (T1.4):** un rubro dentro de otro (CULTIVOS (CAMPO) dentro de HERRAMIENTAS) da partidas con **área compuesta**: `HERRAMIENTAS / CULTIVOS (CAMPO) - LA CEJA`. Una fila con nombre y sin valores (PROYECTOS) se **ignora con advertencia**. Los rubros pueden usar `SUM(Bx:By)` o `+Bx+By`. El total general (MATERIA PRIMA, fila 7) se reconoce por estructura, no por el nombre. El año lo indica el Administrador al cargar.
- **Precio del `020215` (T1.5):** si el factor del comentario es 0 o está mal formado, el artículo queda **sin precio** (la línea se bloquea). En Almacen esos casos dan error o NULL. Se le informó al responsable; puede pedir usar el precio sin dividir.
- **Validación de líneas (T1.6):** además de R3.5 se agregaron, informando al responsable: máximo **2 decimales** en unidades decimales (la base usa `Numeric(12,2)`) y la **partida debe ser del mismo año** que la fecha requerida. Una cantidad `NaN` o `Infinity` también es error (lo encontró M1).
- **Códigos:** solo dígitos ASCII (`[0-9]`, nunca `\d`, que acepta dígitos de otros alfabetos).
- **Mutación (M1):** umbral del **80 %** de mutantes eliminados, acordado con el responsable. Se corre en **WSL** (el responsable instaló Ubuntu; usuario `stecnologia`).

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
uv sync --group propiedad && uv run pytest -m propiedad   # P1 a P6 (opcionales)
wsl -d Ubuntu -- bash herramientas/mutacion.sh       # M1, umbral 80 %, solo en WSL
```

Las pruebas de propiedad importan Hypothesis dentro de la prueba; CI instala el grupo `propiedad` para mypy y pip-audit (`uv export ... --group propiedad`).

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
- **Fusionar PR:** el clasificador de permisos de Claude Code bloquea `gh pr merge` ("fusión sin revisión"). No intentar saltarlo: el responsable fusiona desde GitHub y avisa. Después: `git switch main && git pull --ff-only` y nueva rama.
- **ruff RUF001/002/003** rechaza `×`, `–` y `−` en textos, docstrings y comentarios. Usar `/`, "a" o `-`.
- **openpyxl** no está en las dependencias todavía (llega con `web/`). Para inspeccionar el Excel real en local: `uv run --with openpyxl python -I script.py`, con el script en el scratchpad, sin imprimir montos y sin copiar datos al repositorio. El Excel real está en `C:\Users\stecnologia\Downloads\Presupuestos Compras.xlsx`. La consola muestra `�` en las tildes, pero los datos están bien.
- **Esperar el workflow de un PR:** `Monitor` con un bucle sobre `gh run list --branch <rama> --json status,conclusion` y luego `gh run view <id> --log | grep "QUALITY GATE"`.
- **WSL desde Claude Code:** `wsl -d Ubuntu -- bash -c '...'` desde PowerShell parte el comando por espacios. Escribir un script `.sh` en el scratchpad y lanzarlo con `Start-Process wsl.exe -ArgumentList '-d','Ubuntu','--','bash','"/mnt/c/..."'` y tiempo límite. Si Ubuntu no responde ni a `id`, falta la configuración inicial del usuario.
- **mutmut 3:** no corre en Windows; en `/mnt/c` falla al copiar fechas, por eso `herramientas/mutacion.sh` copia el proyecto a `~/crm-compras-mutacion`. Muta el paquete completo con `do_not_mutate` fuera de `dominio/`, porque `tests/conftest.py` importa la app. uv en WSL: `~/.local/bin/uv`. Las pruebas de propiedad no corren bajo mutmut.
- **ruff format** convierte los escapes `\uXXXX` en el carácter literal, y RUF001 lo rechaza: generar esos textos con `chr()`.
- **SonarCloud y uv en scripts:** `uv sync` o `uv run` sin `--no-build` en un `.sh` es una vulnerabilidad nueva ("Omitting --no-build…") y tumba el Quality Gate de seguridad. En scripts usar `uv sync --frozen --no-build` y `uv run --no-sync --no-build`.
- **Ver por qué falla el Quality Gate:** `Invoke-RestMethod "https://sonarcloud.io/api/qualitygates/project_status?projectKey=clickcultivossayonara_CRM-Compras&pullRequest=<n>"` (el proyecto es público).

## 10. Pendientes

- **PostgreSQL en WSL** y luego **fase 2** (T2.1 a T2.4). Ver `docs/spec/tareas.md`.
- **E4:** versión de Softland y si permite importación automática (fuera del MVP).
- Las pruebas adicionales que esperan su tarea: I2 (T4.4), C1 y X1 (T3.2), C2 (T4.6), S1 (T2.3), R1 (T4.1 y T4.4), y E1, A1 y S3 (fase 5). M1 ya está hecha (T1.10).
