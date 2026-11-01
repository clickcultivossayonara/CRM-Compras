# Diseño — CRM-Compras (MVP)

Este diseño cubre [requisitos.md](requisitos.md). Las reglas D1…D20 están en [CLAUDE.md](../../CLAUDE.md).

## 1. Arquitectura

```
 Red de la empresa                         Nube
┌──────────────────────────┐   HTTPS   ┌─────────────────────────────────┐
│ SQL Server (SAYOERP)     │  saliente │ App FastAPI (web + API)         │
│   ▲ solo SELECT          │ ────────► │   /sync/*  (token)              │
│ Sincronizador (pyodbc)   │           │   páginas Jinja2 + HTMX         │
└──────────────────────────┘           │         │                       │
                                       │   PostgreSQL (base propia)      │
                                       └─────────────────────────────────┘
```

- La nube nunca inicia conexiones hacia la red de la empresa. (D1)
- El sincronizador se ejecuta de forma programada, cada hora en horario laboral, y bajo demanda.

## 2. Módulos

| Módulo | Responsabilidad | I/O |
|---|---|---|
| `dominio/calendario.py` | Semana ISO de una fecha, mes de la semana según su jueves y semanas de cada mes | no |
| `dominio/presupuesto.py` | Repartir el mes en semanas, saldo acumulado y disponible | no |
| `dominio/lector_presupuesto.py` | Convertir las celdas del Excel en partidas, advertencias y errores | recibe celdas, no archivos |
| `dominio/pedido.py` | Entidades, validación de líneas y máquina de estados | no |
| `dominio/precios.py` | Normalizar precios (regla del `020215`) | no |
| `dominio/cargador.py` | Armar las filas y hojas del cargador desde las líneas | no |
| `datos/` | Modelos SQLAlchemy, repositorios y migraciones Alembic | sí |
| `web/` | Rutas, sesión, permisos y plantillas | sí |
| `sincronizador/` | Consultas a Softland y envío a la API | sí |

`openpyxl` solo se usa en `web/` (lectura y escritura del archivo). El dominio recibe y devuelve estructuras de Python, así se prueba sin archivos.

## 3. Modelo de datos (base propia)

```
usuario(id, usuario, nombre, hash_clave, rol, activo)
articulo(codigo PK, descripcion, unidad, activo, sincronizado_en)
centro_costo(codigo PK, descripcion, activo, sincronizado_en)
precio(articulo PK→articulo, precio_unitario int, fecha_compra, orden_compra)
unidad_decimal(unidad PK)
anio_presupuesto(anio PK, cargado_por, cargado_en, archivo)
partida(id, anio, rubro, area, UNIQUE(anio, rubro, area))
asignacion_mensual(partida_id, mes, valor int, semanas int)
jefe_partida(usuario_id, partida_id)
jefe_centro(usuario_id, centro_codigo)
prohibido(usuario_id, articulo_codigo)
pedido(id, jefe_id, estado, creado_en, enviado_en, justificacion_gerencia, motivo)
linea(id, pedido_id, articulo, centro_costo, partida_id, cantidad Numeric(12,2),
      fecha_requerida, comentario, precio_congelado int NULL, valor int NULL,
      bodega int NULL, lote_id NULL)
lote(id, generado_por, generado_en)
auditoria(id, usuario_id, fecha, entidad, entidad_id, accion, antes jsonb, despues jsonb)
sincronizacion(id, tipo, recibido_en, registros)
```

- El dinero siempre se guarda como `int`. La cantidad se guarda como `Numeric`, porque algunas unidades admiten decimales. (D2, D13)
- `auditoria` no tiene permisos de UPDATE ni DELETE para el usuario de la aplicación. (D19)

## 4. Algoritmos

### 4.1 Calendario (D5)
- `semana_de(fecha)` devuelve `(anio_iso, semana_iso)`.
- `mes_de_semana(anio_iso, semana)` devuelve el mes de su jueves.
- `semanas_del_mes(anio, mes)` devuelve las semanas ISO cuyo jueves cae en ese mes.

Ejemplo: la semana 2025-W40 va del 29/09 al 05/10. Su jueves es el 02/10, así que pertenece a octubre.

### 4.2 Reparto semanal (D5)
```
base, residuo = divmod(valor_mes, n_semanas)
semanas = [base] * n_semanas;  semanas[-1] += residuo
```
Invariante: la suma de las semanas es igual al valor del mes.

### 4.3 Saldo y disponible (D5, D9)
Para una partida, con *A(w)* = asignado y *C(w)* = consumido en la semana *w*:
```
saldo(s)      = Σ_{w≤s} A(w) − Σ_{w≤s} C(w)
disponible(s) = min_{t ≥ s} saldo(t)
```
Una línea de valor *v* en la semana *s* cabe si `v ≤ disponible(s)`. Así se usa lo acumulado de semanas anteriores (D5) sin dejar en negativo semanas posteriores que ya tienen consumo. Si no cabe, el pedido va a Gerencia (D9).

Varias líneas de la misma partida en un pedido se evalúan juntas: se suman por semana y se recalcula.

### 4.4 Lectura del Excel (R1)
1. Se busca la fila cuyas celdas tienen nombres de meses (ENERO…DICIEMBRE). Esa fila define las columnas válidas.
2. La fila con "Semanas" en la columna A da el número de semanas por mes. Se valida con 4.1.
3. Una fila con fórmula `SUM(Bx:By)` es un rubro y su rango define sus áreas.
4. Una fila numérica fuera de todo rango es una partida con área `GENERAL`.
5. Los nombres se normalizan: sin espacios sobrantes, en mayúsculas y conservando las tildes.

### 4.5 Máquina de estados (D16)
```
borrador ──enviar──► enviado ──aprobar(Comprador)──► aprobado ──exportar──► exportado
    │                   │  └─rechazar──► rechazado
    └─enviar(excede)─► pendiente_gerencia ──aprobar(Gerente, justificación)──► enviado
                         └─rechazar──► rechazado
pendiente_gerencia | enviado | aprobado ──anular(motivo)──► anulado
```
Cualquier otra transición genera `TransicionInvalida`.

## 5. Contrato del sincronizador (R6.2)

`POST /sync/{articulos|centros|precios}` con el encabezado `Authorization: Bearer ${SYNC_TOKEN}`. El cuerpo es la lista completa, se reemplaza el contenido anterior y la operación es idempotente.

```json
{"articulos": [{"codigo": "020093", "descripcion": "...", "unidad": "CC", "activo": true}]}
{"centros":   [{"codigo": "513-01-2", "descripcion": "...", "activo": true}]}
{"precios":   [{"articulo": "020093", "precio_unitario": 123, "fecha_compra": "2026-10-20", "orden_compra": "OC-1"}]}
```

- La respuesta es `200 {"recibidos": n, "inactivados": m}`.
- Un código que no cumple el formato rechaza todo el envío con `422`.
- Las consultas de Softland salen de `C:\Apps\Almacen\app.py`. El precio es el de la compra más reciente del artículo con cualquier proveedor, redondeado a pesos enteros.

## 6. Cargador (R5)
- `armar_cargador(lineas) -> dict[nombre_hoja, list[fila]]`, con las filas en el orden de la plantilla.
- Al escribir el archivo: las columnas A y C son texto (`number_format = '@'`) y la F es fecha con formato `dd/mm/yyyy`.
- Una prueba compara el archivo generado con la plantilla `Bodega 5.xlsx`, usando una versión ficticia en `tests/fixtures/`.

## 7. Seguridad
- Secretos por variables de entorno: `DATABASE_URL`, `SECRET_KEY`, `SYNC_TOKEN`, `SOFTLAND_SERVIDOR`, `SOFTLAND_BASE`, `SOFTLAND_USUARIO`, `SOFTLAND_CLAVE`.
- Formularios con protección CSRF. Cookies `HttpOnly`, `Secure` y `SameSite=Lax`.
- El usuario de SQL Server disponible es el mismo de Almacen y tiene permisos de **sysadmin** (decisión del responsable: no se crea otro). Por eso la solo lectura se garantiza en el código: solo `SELECT` fijos con parámetros, filtro que rechaza instrucciones de escritura, `ROLLBACK` al terminar y `READ UNCOMMITTED` para no bloquear el ERP.
- Tablas confirmadas en Softland: `SAYONARA.ARTICULO` (`ACTIVO` = `S`/`N`, `UNIDAD_ALMACEN`), `SAYONARA.CENTRO_COSTO` (`CENTRO_COSTO`, `DESCRIPCION`, `ACEPTA_DATOS`), `SAYONARA.BODEGA` y `SAYONARA.ORDEN_COMPRA_LINEA` (incluye `CENTRO_COSTO`, útil para sugerir partidas).

## 8. Propiedades para pruebas de propiedad (opcionales)
- **P1** La suma del reparto semanal es igual al valor del mes, y ninguna semana es negativa.
- **P2** `disponible(s) ≤ saldo(s)`, y `disponible` nunca aumenta al agregar consumo.
- **P3** Si toda línea aceptada cumple `v ≤ disponible(s)`, ningún `saldo(t)` queda negativo.
- **P4** Cada año ISO tiene 52 o 53 semanas, y cada semana pertenece a un solo mes.
- **P5** Cualquier secuencia de transiciones válidas termina en un estado del diagrama, y las inválidas siempre fallan.
- **P6** Los códigos del cargador conservan su texto exacto (ceros a la izquierda) para cualquier código de 6 dígitos.
