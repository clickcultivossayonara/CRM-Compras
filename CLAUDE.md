# CRM-Compras

## 1. Producto

Sistema web para el área de compras de una empresa exportadora de flores (Antioquia, Colombia). Reemplaza los cargadores en Excel que cada jefe envía por correo y la digitación manual en Softland.

Los jefes hacen sus pedidos en la web, con códigos, centros de costo y precios reales tomados de Softland, y ven su presupuesto. Compras consolida los pedidos y descarga un cargador único, ya validado, con el formato que Softland importa.

### Flujo
1. El jefe crea el pedido en la web. El sistema valida cada línea contra los datos de Softland y contra su presupuesto.
2. El jefe envía el pedido. Si supera el presupuesto, se requiere aprobación de Gerencia.
3. Compras revisa y aprueba.
4. Compras consolida los pedidos aprobados y descarga el cargador para importarlo en Softland.

### Roles
- **Jefe de área**: ve el presupuesto de sus centros de costo, define sus artículos prohibidos y crea pedidos.
- **Comprador**: revisa, aprueba o rechaza pedidos y genera el cargador consolidado.
- **Gerente**: aprueba o rechaza los pedidos que superan el presupuesto.
- **Administrador**: gestiona usuarios y carga el presupuesto desde Excel.

### Fuentes de datos
- **Softland** (SQL Server, base `sayoerp`, red local): catálogo de artículos, descripciones, centros de costo y precio de última compra. **Solo lectura.**
- **Presupuesto**: no está en Softland. Se carga desde un Excel anual con valores por **rubro** (por ejemplo, Abonos y fertilizantes) × **área** (por ejemplo, Pompón o La Ceja) × **mes**, y con el número de semanas de cada mes.
- **Base propia de la aplicación**: pedidos, presupuesto cargado, asignaciones de artículo a rubro y de centro de costo a área, artículos prohibidos, usuarios y auditoría.

### Reglas del dominio (nunca se rompen)
1. **Softland es de solo lectura.** El sistema nunca escribe, modifica ni borra datos en `sayoerp`.
2. **Moneda**: todo valor está en pesos colombianos (COP) como **entero**. Nunca se usa `float` para dinero.
3. **Zona horaria**: fechas y periodos se calculan en `America/Bogota`.
4. **Valor de una línea** = cantidad × precio de última compra en Softland, **antes de IVA**. El precio se congela al enviar el pedido. Un artículo sin compras previas en Softland no tiene precio; la línea se marca con error y no se puede enviar.
5. **Presupuesto anual por mes y semana**: el Excel trae el valor de cada mes y su número de semanas (4 o 5). El valor semanal es el valor del mes dividido entre sus semanas, en pesos enteros; el residuo del redondeo se suma a la última semana del mes. Lo que no se gasta en una semana se acumula a la siguiente. Saldo acumulado en la semana *s* = suma de lo asignado hasta *s* − suma de lo consumido hasta *s*. Lo disponible para un pedido de la semana *s* es el menor saldo acumulado desde *s* hasta el fin del año, para no dejar en negativo semanas posteriores que ya tienen consumo. La semana que consume presupuesto es la de la **fecha requerida** de la línea (no la de envío). Las semanas son ISO, de lunes a domingo; una semana que cruza dos meses pertenece al mes en que cae su **jueves** (así se cuentan en el Excel de presupuesto).
6. **Carga del presupuesto**: solo se importan las filas de detalle (rubro × área) y las columnas con mes como encabezado. Las filas de totales y las columnas sin encabezado se ignoran y se reportan como advertencia. Los valores con decimales se redondean a pesos enteros.
7. **Partida presupuestal**: cada fila de detalle del Excel es una partida (rubro × área). El jefe asigna cada línea del pedido a una de sus partidas. El sistema sugiere la partida usada antes para el mismo artículo y centro de costo, pero no la impone. Una línea sin partida no se puede enviar.
8. **Compromiso**: un pedido compromete presupuesto al salir de `borrador` (a `enviado` o `pendiente_gerencia`). Lo libera si se `rechaza` o se `anula`.
9. **Exceso de presupuesto**: un pedido que supera el saldo disponible, o que usa saldo de semanas o meses futuros, no sigue sin la aprobación de un Gerente, que debe dejar una justificación.
10. **Catálogo real**: un pedido solo admite artículos cuyo código exista y esté activo en Softland. No se permiten artículos en texto libre.
11. **Centro de costo válido**: cada línea lleva un centro de costo que existe en Softland y que está asignado al jefe.
12. **Descripción**: la descripción del artículo y la del centro de costo se toman siempre de Softland. Nunca se escriben a mano.
13. **Cantidades**: siempre mayores a cero y coherentes con la unidad de medida del artículo en Softland.
14. **Bodegas**: 1 = La Unión, 2 = La Ceja, 5 = Prohibidos. Cada jefe define su lista de artículos prohibidos, y una línea con un artículo prohibido va siempre a la **bodega 5**. Para las demás líneas, Compras define la bodega al generar el cargador.
15. **Duplicados**: el mismo artículo con el mismo centro de costo no puede repetirse en un pedido. Si ya se pidió en otro pedido de la misma semana, se advierte al usuario sin bloquear.
16. **Estados del pedido**: `borrador → enviado`, o `borrador → pendiente_gerencia` si excede lo disponible. `pendiente_gerencia → enviado | rechazado` (Gerente). `enviado → aprobado | rechazado` (Comprador). `aprobado → exportado` (al generar el cargador). Desde `pendiente_gerencia`, `enviado` o `aprobado` se puede pasar a `anulado`. Rechazar o anular exige motivo. Solo se edita en `borrador`.
17. **Cargador para Softland**: se genera un solo archivo `.xlsx` consolidado con las columnas exactas de la plantilla, sin cambiar sus formatos (ver abajo). Solo incluye líneas de pedidos aprobados, y cada línea se exporta una sola vez.
18. **Visibilidad**: un jefe solo ve y modifica los pedidos y el presupuesto de sus centros de costo.
19. **Auditoría**: todo cambio de estado, presupuesto, prohibidos o usuarios registra usuario, fecha y valores anterior y nuevo. La auditoría no se borra.
20. **Datos reales**: nunca se suben al repositorio datos reales de la empresa, proveedores, precios ni personas. Solo datos ficticios.

### Formato del cargador (plantilla de importación a Softland)
| Columna | Formato |
|---|---|
| Artículo | texto, 6 dígitos con ceros a la izquierda (`020093`) |
| Descripción | texto, la de Softland |
| Centro Costo | texto `NNN-NN-N` (`513-01-2`) |
| Descripción Centro de Costo | texto, la de Softland |
| Cantidad | número |
| Fecha Requerida | fecha `dd/mm/yyyy` |
| Comentario | texto opcional |

El nombre de la hoja corresponde a la bodega (por ejemplo, `Prohibidos` para la bodega 5). Compras define la bodega antes de descargar.

### Proyecto relacionado: `C:\Apps\Almacen`
Aplicación Flask existente (Python + pyodbc) que ya consulta Softland (esquema `SAYONARA` en `SAYOERP`) y escribe en una base propia (`INNOVACIONTIC`, esquema `Almacen`). Sirve como referencia de las tablas y consultas reales: `ARTICULO`, `ORDEN_COMPRA`, `ORDEN_COMPRA_LINEA` y `PROVEEDOR`. Su consulta de precio de última compra se reutiliza, incluida la regla del artículo `020215`: su precio se divide por el factor que viene en el comentario. Más adelante se podría integrar a este proyecto. **No se copian sus prácticas de seguridad**: tiene credenciales en el código y contraseñas en texto plano.

### Supuestos por confirmar
- Versión de Softland y si permite una importación automática, además de la plantilla manual.

## 2. Tecnología

### Arquitectura
- **Web + API en la nube.** Usan su propia base de datos (PostgreSQL).
- **Sincronizador local**: un servicio pequeño instalado en la red de la empresa. Lee Softland con un usuario de solo lectura y envía catálogo, centros de costo y precios a la API por HTTPS saliente. SQL Server (puerto 1433) **nunca** se expone a internet.

### Stack
- **Python 3.12 o superior** (desarrollo en 3.13) con tipado completo. `mypy --strict` debe pasar.
- **Gestión de dependencias**: `uv` (`pyproject.toml` + `uv.lock`).
- **API y web**: FastAPI + Jinja2 + HTMX, servidas desde el mismo proceso, sin un frontend separado.
- **Datos**: SQLAlchemy 2 + Alembic (migraciones) sobre PostgreSQL. Pydantic v2 para validar las entradas.
- **Sincronizador**: Python + `pyodbc` (ODBC Driver 17/18 for SQL Server), solo con consultas `SELECT`.
- **Excel**: `openpyxl`, para leer el presupuesto y generar el cargador.
- **Autenticación**: usuario y contraseña con hash `argon2-cffi`, sesión firmada con una clave tomada de una variable de entorno, y roles desde la base de datos.
- **Local**: Docker Compose para PostgreSQL.

### Estructura
```
src/crm_compras/dominio/     # reglas puras, sin I/O (presupuesto, pedido, validaciones, cargador)
src/crm_compras/datos/       # modelos SQLAlchemy y repositorios
src/crm_compras/web/         # rutas FastAPI y plantillas Jinja2
sincronizador/               # servicio local de lectura de Softland
tests/unitarias|caja_negra|humo|integracion
```

### Estilo y convenciones
- Interfaz, mensajes de error, comentarios y documentación en **español**.
- Dominio en español (`Pedido`, `CentroCosto`, `saldo_disponible`). Términos técnicos estándar en inglés (`router`, `repository`).
- Dinero como `int` (pesos). Nunca `float`; si hace falta un cálculo intermedio, se usa `Decimal` y se redondea con `ROUND_HALF_UP`.
- La lógica de negocio va en `dominio/`. Las rutas y el sincronizador no repiten reglas.
- `ruff` para linter y formato. Sin `Any` innecesario y sin código comentado.
- Las consultas SQL siempre llevan parámetros (`?`). Nunca se arman concatenando texto del usuario.
- Secretos solo en variables de entorno (`.env` no se versiona; se versiona `.env.example`). Nunca se escriben IP, usuarios ni contraseñas de Softland en el código.

### Git
- Una rama por cambio (`feat/…`, `fix/…`, `docs/…`, `test/…`).
- No hacer commit ni push sin autorización explícita.
- No agregar atribuciones a herramientas de IA en commits ni en código.

## 3. Pruebas y calidad

- **Framework**: pytest + pytest-cov. Las pruebas de caja negra y de humo usan `httpx2` solo por HTTP (fixture `cliente`; con `CRM_URL_BASE` apuntan a un servidor real). Detalle de casos y comandos en [docs/calidad/plan-pruebas.md](docs/calidad/plan-pruebas.md).
- **Unitarias**: cada regla del dominio tiene pruebas con casos borde: saldo exacto, saldo en cero, acumulado entre semanas y meses, mes de 4 y de 5 semanas, residuo del redondeo, cantidad cero o negativa, código inexistente o inactivo, centro de costo ajeno, duplicados, prohibidos a bodega 5, códigos con ceros a la izquierda.
- **Caja negra**: validan la API solo por entradas y salidas (partición de equivalencia, valores límite, entradas inválidas).
- **Humo**: `uv run pytest tests/humo` verifica en menos de 1 minuto que la app arranca y que los flujos críticos responden.
- **Softland en pruebas**: nunca se conecta a `sayoerp` real. Se usa un doble de prueba con datos ficticios.
- **Cobertura mínima**: 80 % en `src/crm_compras`.
- **Análisis estático**: SonarCloud/SonarQube. El Quality Gate exige cero bugs y cero vulnerabilidades nuevas, cobertura ≥ 80 % y duplicación ≤ 3 %, hotspots revisados al 100 %. Se ejecuta con `uv tool run pysonar`, con credenciales solo en variables de entorno.
- **Pruebas de propiedad** (Hypothesis): son opcionales y el responsable del proyecto decide si se ejecutan.
- Ninguna tarea se da por terminada sin correr sus pruebas y reportar el resultado real.
- Los datos de prueba son ficticios y se generan con fábricas (factories).
