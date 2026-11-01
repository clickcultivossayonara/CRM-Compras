# Plan de calidad y pruebas

Deriva de [requisitos.md](../spec/requisitos.md) y [diseno.md](../spec/diseno.md). Cada tarea de [tareas.md](../spec/tareas.md) implementa los casos de su módulo **antes** de darse por terminada.

## 1. Comandos

| Qué | Comando | Tiempo objetivo |
|---|---|---|
| Instalar | `uv sync` | — |
| Humo (un comando) | `uv run pytest tests/humo` | < 1 min |
| Suite completa + cobertura | `uv run pytest --cov --cov-report=xml --junitxml=reports/pytest.xml` | < 3 min |
| Solo unitarias / caja negra | `uv run pytest -m unitaria` · `uv run pytest -m caja_negra` | — |
| Caja negra contra un servidor real | `CRM_URL_BASE=https://… uv run pytest tests/caja_negra` | — |
| Propiedad (opcional) | `uv sync --group propiedad` y luego `uv run pytest -m propiedad` | — |
| Linter y formato | `uv run ruff check . && uv run ruff format --check .` | — |
| Tipos | `uv run mypy` | — |
| SonarCloud | `uv tool run pysonar` (después de la suite completa) | — |

- Cada prueba recibe su marca según la carpeta (`tests/conftest.py`).
- Las pruebas de propiedad no se ejecutan por defecto (`-m 'not propiedad'`).
- La cobertura mínima local es del 80 % (`fail_under`). Si no se alcanza, la suite falla.

## 2. Niveles

| Nivel | Carpeta | Qué valida | Regla |
|---|---|---|---|
| Unitarias | `tests/unitarias/` | Funciones de `dominio/` con casos borde | Sin I/O, sin base de datos, sin red |
| Caja negra | `tests/caja_negra/` | La API por HTTP: estado, cuerpo y archivo descargado | Solo el fixture `cliente`; nunca importa módulos internos |
| Humo | `tests/humo/` | Que la app arranca como proceso real y que los flujos críticos responden | < 1 min |
| Integración | `tests/integracion/` | Repositorios y migraciones contra PostgreSQL | Ver la propuesta I1 |
| Propiedad | `tests/unitarias/` con `@pytest.mark.propiedad` | Invariantes P1 a P6 del diseño | Opcionales |

Los datos de prueba siempre son ficticios, creados con fábricas en `tests/fabricas.py`, y nunca se conectan a Softland.

## 3. Casos de prueba por módulo

Abreviaturas: **PE** = partición de equivalencia · **VL** = valor límite · **INV** = entrada inválida.

### 3.1 Calendario (T1.1 · R1.6, R2.2)
| Tipo | Entrada | Esperado |
|---|---|---|
| PE | 15/10/2025 | semana 2025-W42, octubre |
| VL | 29/09/2025 (lunes de W40) | W40, **octubre** (su jueves es el 02/10) |
| VL | 05/10/2025 (domingo de W40) | W40, octubre |
| VL | 01/01/2027 (viernes) | 2026-W53, diciembre de 2026 |
| VL | 29/12/2025 (lunes) | 2026-W01, enero de 2026 |
| PE | semanas de ago a dic de 2025 | 4, 4, 5, 4, 4 (las del Excel real) |
| VL | año con 53 semanas (2026) | 53 semanas, cada una en un solo mes |

### 3.2 Reparto semanal (T1.2 · R2.2)
| Tipo | Mes, semanas | Esperado |
|---|---|---|
| PE | 400, 4 | [100, 100, 100, 100] |
| VL | 403, 4 | [100, 100, 100, 103] |
| VL | 0, 5 | [0, 0, 0, 0, 0] |
| VL | 3, 5 | [0, 0, 0, 0, 3] |
| INV | −1, 4 | error |
| INV | 400, 0 · 400, 6 | error (solo se aceptan 4 o 5) |

### 3.3 Saldo y disponible (T1.3 · R2.1–R2.4)
| Tipo | Escenario | Esperado |
|---|---|---|
| PE | asignado 100/semana, sin consumo, semana 3 | saldo 300, disponible 300 |
| VL | línea por exactamente el disponible | cabe |
| VL | línea por el disponible + 1 | no cabe → Gerencia |
| VL | disponible 0 y línea de 1 | no cabe |
| PE | lo que sobra de enero se usa en febrero | cabe |
| PE | consumo en la semana 10 que limita una línea en la semana 5 | disponible(5) = min(saldo(5…52)) |
| VL | línea de valor 0 | rechazada antes (cantidad > 0) |
| PE | varias líneas de la misma partida y semana | se suman antes de comparar |

### 3.4 Lector del Excel (T1.4 · R1.1–R1.6)
| Tipo | Entrada | Esperado |
|---|---|---|
| PE | formato válido (fixture ficticio igual al real) | partidas correctas, sin errores |
| PE | fila numérica fuera de rangos (POLIETILENO) | partida con área `GENERAL` |
| PE | fila de total general y filas de rubro | ignoradas |
| PE | columnas G a R con datos y sin encabezado | ignoradas, con advertencia |
| VL | 65040809,987 | 65040810 |
| VL | 0,5 · 1,5 | 1 · 2 (ROUND_HALF_UP) |
| VL | celda vacía | 0 |
| INV | valor negativo · texto en una celda de valor | error con fila y columna |
| INV | sin fila de meses · sin fila "Semanas" | error |
| INV | semanas de octubre = 4 | error "octubre debe tener 5 semanas" |
| INV | rubro y área repetidos | error |

### 3.5 Validación de líneas y pedido (T1.6 · R3.5, R3.6, R3.8)
| Tipo | Entrada | Esperado |
|---|---|---|
| PE | línea completa y válida | sin errores, valor = cantidad × precio |
| INV | código inexistente · inactivo | error |
| PE/VL | código `020093` (cero a la izquierda) | aceptado y conservado como texto |
| INV | código `20093` · `0200930` · `02009A` | error de formato |
| INV | centro de costo ajeno · inexistente | error |
| INV | partida ausente · ajena | error |
| VL | cantidad 0 · −1 | error |
| VL | cantidad 1 · 0,01 en una unidad decimal | aceptada |
| INV | cantidad 1,5 en una unidad entera | error |
| INV | artículo sin precio | error |
| VL | fecha requerida = hoy · ayer | aceptada · error |
| INV | fecha en un año sin presupuesto | error |
| INV | mismo artículo y centro de costo dos veces en el pedido | error |
| PE | mismo artículo y centro de costo en otro pedido de la misma semana | **advertencia** que no bloquea |
| PE | artículo prohibido del jefe | bodega 5 |
| PE | varios errores en una línea | se reportan todos juntos |
| VL | cantidad × precio grande (10⁶ × 10⁷) | entero exacto, sin pérdida |

### 3.6 Estados del pedido (T1.7 · R3.9, R3.10, R4)
| Tipo | Transición | Esperado |
|---|---|---|
| PE | borrador → enviar (cabe) | enviado, precio congelado |
| PE | borrador → enviar (excede) | pendiente_gerencia |
| PE | pendiente_gerencia → aprobar con justificación | enviado |
| INV | pendiente_gerencia → aprobar sin justificación | error |
| PE | enviado → aprobar (Comprador) · rechazar con motivo | aprobado · rechazado |
| INV | rechazar o anular sin motivo | error |
| INV | aprobado → editar · rechazado → enviar · exportado → anular | `TransicionInvalida` |
| PE | anular desde pendiente_gerencia, enviado o aprobado | anulado, presupuesto liberado |

### 3.7 Cargador (T1.8, T4.6 · R5)
| Tipo | Entrada | Esperado |
|---|---|---|
| PE | líneas de las bodegas 1, 2 y 5 | 3 hojas: `La Union`, `La Ceja`, `Prohibidos` |
| PE | solo bodega 5 | 1 hoja |
| PE | columnas y formatos | idénticos a la plantilla ficticia (A y C como texto, F como `dd/mm/yyyy`) |
| INV | línea sin bodega | error, no se genera el archivo |
| INV | línea ya exportada | no se incluye en otro lote |
| PE | volver a descargar el lote | archivo con el mismo contenido |

### 3.8 Caja negra de la API (T2–T4)
| Tipo | Caso | Esperado |
|---|---|---|
| PE | cada rol en sus rutas | 200 |
| INV | Jefe en una ruta de Gerente o Comprador · sin sesión | 403 · redirige al login |
| INV | Jefe consulta un pedido de otro jefe | 404 (no revela que existe) |
| INV | formulario sin token CSRF | 403 |
| INV | `/sync/*` sin token · con token errado · con JSON inválido | 401 · 401 · 422 |
| PE | `/sync/*` enviado dos veces con el mismo cuerpo | mismo resultado (idempotente) |
| INV | subir un archivo que no es `.xlsx` · `.xlsx` de más de 5 MB | 422 |

### 3.9 Humo (crece con cada fase)
- [x] La app arranca como proceso y `/salud` responde.
- [x] `/openapi.json` carga.
- [ ] Inicio de sesión (T2.3).
- [ ] Vista previa de la carga de presupuesto (T4.1).
- [ ] Crear y enviar un pedido (T4.4).
- [ ] Aprobar un pedido (T4.5).
- [ ] Descargar el cargador (T4.6).

## 4. SonarCloud / SonarQube

**Configuración:** [`sonar-project.properties`](../../sonar-project.properties). No contiene claves: todo lo propio de la cuenta se lee de variables de entorno.

**Quality Gate:** se crea en SonarCloud (*Quality Gates → Create*) con estas condiciones sobre el **código nuevo**, y se asigna al proyecto:

| Métrica | Condición |
|---|---|
| Bugs nuevos | = 0 (calificación de confiabilidad A) |
| Vulnerabilidades nuevas | = 0 (calificación de seguridad A) |
| Security Hotspots revisados | 100 % |
| Cobertura | ≥ 80 % |
| Líneas duplicadas | ≤ 3 % |
| Calificación de mantenibilidad | A |

**Ejecución** (PowerShell, después de correr la suite completa):
```powershell
$env:SONAR_TOKEN = "<tu token>"            # en SonarCloud: My Account → Security
$env:SONAR_ORGANIZATION = "<tu organización>"
$env:SONAR_PROJECT_KEY = "<clave del proyecto>"
uv run pytest --cov --cov-report=xml --junitxml=reports/pytest.xml
uv tool run pysonar
```
Con `sonar.qualitygate.wait=true`, el comando falla si el Quality Gate no pasa.

## 5. Pruebas adicionales propuestas (tú decides)

| Id | Prueba | Justificación |
|---|---|---|
| I1 | **Integración con PostgreSQL** (Testcontainers o un contenedor de Compose) | Las migraciones, restricciones e índices solo se validan contra una base real. Requiere Docker. |
| I2 | **Concurrencia del presupuesto** | Dos jefes que envían al mismo tiempo contra la misma partida no deben sobregirarla. Necesita un bloqueo de fila y una prueba con envíos simultáneos. |
| C1 | **Contrato del sincronizador** | El sincronizador (en la red de la empresa) y la API (en la nube) se despliegan por separado. Un esquema compartido y probado en ambos lados evita romper la sincronización. |
| C2 | **Regresión del cargador contra la plantilla** (golden file) | Si Softland rechaza el archivo, el flujo completo falla. Comparar celda a celda contra la plantilla protege el formato. |
| S1 | **Matriz de autorización por rol** | Un error de permisos expone el presupuesto o los pedidos de otras áreas. Se prueba cada ruta con cada rol. |
| S2 | **Auditoría de dependencias** (`pip-audit`) | Detecta librerías con vulnerabilidades conocidas. Tarda segundos. |
| S3 | **Análisis dinámico básico** (OWASP ZAP baseline) | Revisa cabeceras, cookies y errores comunes de la app desplegada en la nube. |
| R1 | **Rendimiento de búsqueda y carga** | La búsqueda de artículos debe responder en menos de 300 ms con unos 20.000 artículos, y la carga del presupuesto en menos de 5 s. Es lo que los jefes más usan. |
| A1 | **Accesibilidad** (axe con Playwright) | Formularios usables con teclado y lector de pantalla. Bajo costo si se hace desde el inicio. |
| E1 | **De punta a punta en el navegador** (Playwright) | HTMX mueve lógica a la interfaz. Confirma que la validación en vivo y la descarga funcionan en un navegador real. |
| M1 | **Mutación** (mutmut sobre `dominio/`) | Verifica que las pruebas de dinero y presupuesto detectan cambios en la lógica, no solo que la recorren. |
| X1 | **Verificación manual de consultas contra Softland** (marca `softland`, solo con el usuario de lectura) | Las tablas y columnas reales de Softland no están documentadas. Una prueba opcional confirma que las consultas siguen funcionando. |
