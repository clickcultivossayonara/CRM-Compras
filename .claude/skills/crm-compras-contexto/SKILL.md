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
| Skill: cierre de la fase 1 y Archify como trabajo futuro (F1) | ✅ | PR #17 |
| T2.1 Modelos SQLAlchemy y migración inicial (Alembic) + I1 | ✅ | PR #18 |
| T2.2 Auditoría solo de inserción (trigger) | ✅ | PR #19 |
| T2.3 Sesión, argon2, CSRF, roles por ruta + S1 | ✅ | PR #20 |
| T2.4 Administración (usuarios, asignaciones, unidades) + `crear_administrador` | ✅ | PR #21 |
| T3.1 API del sincronizador `/sync/*` (token, upsert, inactivación) | ✅ | PR #22 |
| T3.2 Sincronizador local (`sincronizador/`) + C1 + X1 | ✅ | PR #24 |
| T3.3 Indicador de la última sincronización (aviso a las 24 h) | ✅ | PR #25 |
| **Fase 3 (sincronización) completa. Siguiente: fase 4, T4.1** | ⏭️ **siguiente** | — |

Los 25 PR están fusionados en `main` con el workflow y el Quality Gate en verde (489 pruebas en CI con PostgreSQL 16, cobertura del 100 %; mutación del dominio 97,6 %).

**Cómo quedó la fase 3:**
- **API** (`web/rutas_sync.py`): `POST /sync/{articulos|centros|precios}` con `Authorization: Bearer ${SYNC_TOKEN}`. Contrato Pydantic compartido en `crm_compras/contrato_sync.py`. Artículos y centros con upsert e inactivación por `sincronizado_en < ahora`; precios se reemplazan (`inactivados` = retirados) y exigen que el artículo exista. Listas de códigos con `= ANY(:codigos)`. Rutas en S1 como `CON_TOKEN`.
- **Sincronizador** (`sincronizador/`, `uv run python -m sincronizador`): `lectura.py` (solo lectura, compartida con el MCP), `consultas.py` (última compra con cualquier proveedor desde el 1 de enero del año anterior), `preparar.py` (descarta y reporta filas inválidas), `envio.py` (solo HTTPS, `Transporte` inyectable), `__main__.py` (no envía catálogos vacíos; salida 0, 1 o 2). Variables: `SOFTLAND_*`, `CRM_URL_API`, `SYNC_TOKEN`. Doble de Softland en `tests/sincronizador/doble_softland.py`.
- **X1 real (27/11/2026):** 4.238 artículos (7 descartados por código que no tiene 6 dígitos), 171 centros (1 descartado), 2.115 precios (5 descartados). Se sugirió al responsable revisar esos códigos en Softland.
- **Frescura:** `dominio/sincronizacion.evaluar` (la más vieja de los 3 tipos; aviso si falta uno o > 24 h); `RepositorioSincronizacion` inyectado en `crear_app(sincronizaciones=...)`; en pruebas sin base, fixture `sincronizaciones` (doble en memoria).

**Próxima sesión (fase 4, funciones del MVP)**, en orden de `tareas.md`:
1. **T4.1** carga del presupuesto: subir el `.xlsx` (openpyxl con fórmulas → `lector_presupuesto.leer_presupuesto`), vista previa, confirmar y recargar sin perder consumo; R1: carga < 5 s.
2. **T4.2** saldo por partida y semana (`presupuesto.saldos`, `disponibles`).
3. **T4.3** prohibidos del jefe.
4. **T4.4** pedido (búsqueda, líneas, sugerencia de partida, validación en vivo con HTMX, envío) + I2 (bloqueo de fila, sin sobregiro) + R1 (búsqueda < 300 ms con 20.000 artículos).
5. **T4.5** bandejas de Gerente y Comprador.
6. **T4.6** lote y descarga del cargador `.xlsx` + C2 (golden file).
Toda ruta nueva va en la matriz S1.

**Cómo quedó la capa de datos y la web (fase 2):**
- `datos/conexion.BaseDatos(url=None, conexion=None)`: reparte sesiones con `.sesion()`; el motor se crea al primer uso desde `DATABASE_URL`. Con `conexion`, los `commit` son puntos de guardado (lo usan las pruebas).
- `datos/modelos.py`: 16 tablas; dinero en `BIGINT`; restricciones con nombre (formatos de código, estados, roles, meses, semanas, bodegas, D15). Migraciones en `datos/migraciones/versions/`, Alembic configurado en `pyproject.toml` (sin `alembic.ini`): `uv run alembic upgrade head`, `uv run alembic revision --autogenerate -m "…"`. Las listas iniciales se escriben fijas en la migración, no importadas del dominio.
- `datos/auditoria.registrar(sesion, usuario_id=, entidad=, entidad_id=, accion=, antes=, despues=)`: única forma de auditar; un trigger rechaza UPDATE, DELETE y TRUNCATE incluso al dueño de la tabla.
- `datos/administracion.py`: operaciones de administración con `AdministracionError(problemas)` y `NoEncontrado`; reciben claves ya cifradas.
- `web/app.crear_app(configuracion=None, usuarios=None, base=None)`; se arranca con `uvicorn --factory crm_compras.web.app:crear_app`. `web/seguridad`: `cifrar_clave`, `autenticar`, `verificar_csrf` (router), `requiere_roles(...)`, `SinSesion` → 303 al login. Plantillas Jinja2 en `web/plantillas/` (`_errores.html` para listar errores).
- Rutas: `web/rutas_sesion.py` (login, salir, inicio) y `web/rutas_admin.py` (`/admin/...`). **Toda ruta nueva va en la matriz S1** (`tests/caja_negra/test_autorizacion.py`) o la prueba falla; la matriz lee las rutas del esquema OpenAPI, así que **ninguna ruta usa `include_in_schema=False`**.
- Pruebas: `tests/base_pruebas.py` (URL, Alembic), fixtures en `tests/conftest.py`: `cliente`/`entrar` (app en memoria, sin base), `bd`, `cuentas_bd`, `cliente_bd`, `entrar_bd` (app sobre PostgreSQL en una transacción revertida; la auditoría no se puede borrar). Claves de prueba con `clave_aleatoria()`: el hook de secretos bloquea `clave="..."` de 4 o más caracteres.

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
- **Administración (T2.4), decidido por defecto e informado:** los usuarios nunca se borran, solo se desactivan; un administrador no puede quitarse su rol ni desactivarse; contraseñas de 12 a 128 caracteres; solo a un Jefe se le asignan partidas y centros. La sesión dura 8 horas.

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
- **PostgreSQL 18.6 en WSL (Ubuntu 26.04)**, instalado por el responsable; arranca solo con WSL (systemd). Base de pruebas `crm_pruebas`, usuario `pruebas` (mismas credenciales de prueba que CI). `TEST_DATABASE_URL` está guardada como variable de entorno del usuario de Windows, con `127.0.0.1`: **nunca `localhost`**, porque WSL no reenvía IPv6 y la conexión se queda colgada.
- La contraseña de Linux (`sudo`) la escribe el responsable; si la olvida: `wsl -d Ubuntu -u root` y `passwd stecnologia`.
- **WSL se apaga solo** unos segundos después del último comando, aunque PostgreSQL sea un servicio, y después de reiniciar el equipo no arranca hasta que algo lo llame. Si las pruebas con base se cuelgan o dan `ConnectionTimeout`: dejar en segundo plano `wsl.exe -d Ubuntu --exec sleep infinity` (Bash con `run_in_background`) o pedir al responsable que deje una ventana de Ubuntu abierta, y comprobar con `systemctl is-active postgresql`.
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
- En GitHub: el secreto `SONAR_TOKEN` y las variables `SONAR_ORGANIZATION` y `SONAR_PROJECT_KEY`. El token solo permite analizar; no sirve para administrar el proyecto. El 18/11/2026 el anterior dejó de ser válido ("The provided token is invalid") y el responsable generó uno nuevo **sin vencimiento** y lo actualizó en GitHub. Si vuelve a fallar: el responsable lo regenera en sonarcloud.io → My Account → Security y lo guarda en el repositorio → Settings → Secrets and variables → Actions → `SONAR_TOKEN`; luego `gh run rerun <id>`. Claude no tiene acceso a SonarCloud y el token nunca pasa por el chat.
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
- **Alembic sin `alembic.ini`:** con la configuración en `pyproject.toml`, `config.get_main_option(...)` busca el `.ini` y falla. El URL se pasa en `config.attributes["url"]` y, si no viene, se toma de `DATABASE_URL`.
- **FastAPI 0.162** agrupa los routers incluidos en un `_IncludedRouter` y ya no los expone en `app.routes`: para listar rutas se usa `app.openapi()["paths"]`.
- **`uv add`** reinstala el entorno sin los grupos opcionales: después correr `uv sync --group propiedad` o mypy no encuentra Hypothesis.
- **Las pruebas con base no pueden limpiar con `DELETE`** (la auditoría lo impide): todo va en una transacción revertida (`bd`). El humo deja su usuario guardado en la base de pruebas; no asumir que la tabla `usuario` está vacía.
- **Los `ERROR` del contenedor de PostgreSQL al final del log de CI** (violaciones de restricciones) son de las pruebas que intentan guardar datos inválidos a propósito; no son fallas.

## 10. Pendientes

- **Fase 4** (T4.1 a T4.6) y luego la fase 5. Ver `docs/spec/tareas.md`.
- **Datos de Softland por revisar** (responsable): 7 artículos y 1 centro de costo con código mal formado no llegan a la app.
- **E4:** versión de Softland y si permite importación automática (fuera del MVP).
- **F1, trabajo futuro (al terminar las 5 fases, pedido por el responsable):** diagrama interactivo de la arquitectura con **Archify** (`https://github.com/tt-a1i/archify`, skill para agentes, Apache-2.0). Revisar su código y fijar la versión antes de instalarla; sin datos reales, IP ni credenciales en el diagrama. Ver `tareas.md` → "Trabajo futuro". No adelantarlo antes de cerrar la fase 5.
- Las pruebas adicionales que esperan su tarea: I2 (T4.4), C2 (T4.6), R1 (T4.1 y T4.4), y E1, A1 y S3 (fase 5). Ya hechas: M1 (T1.10), I1 (T2.1), S1 (T2.3, crece con cada ruta), C1 y X1 (T3.2).
