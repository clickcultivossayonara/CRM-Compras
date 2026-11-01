# Tareas — CRM-Compras (MVP)

Una tarea a la vez, en orden. Cada una termina con sus pruebas en verde y el resultado reportado. Las tareas marcadas **(opcional)** son pruebas de propiedad: el responsable del proyecto decide si se ejecutan.

Referencias: [requisitos.md](requisitos.md) · [diseno.md](diseno.md)

## Fase 0 — Base del proyecto
- [ ] **T0.1** Crear el esqueleto: `pyproject.toml` con uv, ruff, mypy strict, pytest y pytest-cov, la estructura de [diseno.md §2](diseno.md#2-módulos), `.env.example` y `.gitignore`. → R6.1
- [ ] **T0.2** Crear Docker Compose con PostgreSQL y la configuración por variables de entorno. → R6.1
- [ ] **T0.3** Configurar SonarCloud y el comando de calidad (fase 3 del plan de trabajo). → todos

## Fase 1 — Dominio (sin I/O)
- [ ] **T1.1** `calendario`: semana ISO, mes según el jueves y semanas de cada mes. Pruebas: 2025-W40 → octubre, años de 53 semanas, 1 de enero en la semana 53 del año anterior. → R1.6, R2.2
- [ ] **T1.2** `presupuesto.repartir_mes`: reparto con residuo en la última semana. → R2.2
  - [ ] **T1.2p** (opcional) Propiedad P1.
- [ ] **T1.3** `presupuesto.saldo` y `disponible`. Pruebas: saldo exacto, saldo cero, acumulado entre meses, consumo futuro que limita el disponible. → R2.1, R2.3, R2.4
  - [ ] **T1.3p** (opcional) Propiedades P2 y P3.
- [ ] **T1.4** `lector_presupuesto`: celdas → partidas, advertencias y errores, con fixtures ficticios que imitan el formato real. → R1.1–R1.6
- [ ] **T1.5** `precios.normalizar`: regla del `020215` (con comentario sin número, con decimales y vacío). → R6.4
- [ ] **T1.6** `pedido.validar_linea` y `validar_pedido`: todos los errores y advertencias de R3.5, más bodega 5 para prohibidos. → R3.5, R3.6, R3.8
- [ ] **T1.7** `pedido` máquina de estados y decisión `enviado` / `pendiente_gerencia`. → R3.9, R3.10, R4.1, R4.2, R4.4
  - [ ] **T1.7p** (opcional) Propiedad P5.
- [ ] **T1.8** `cargador.armar`: hojas por bodega, orden de columnas, bodega faltante → error. → R5.1, R5.2, R5.5
  - [ ] **T1.8p** (opcional) Propiedad P6.
- [ ] **T1.9** (opcional) Propiedad P4 del calendario.

## Fase 2 — Datos y sesión
- [ ] **T2.1** Modelos SQLAlchemy y migración inicial de [diseno.md §3](diseno.md#3-modelo-de-datos-base-propia). → R1, R3, R5, R6.6
- [ ] **T2.2** Auditoría solo de inserción, con un permiso de base de datos que impide UPDATE y DELETE. → R1.9, R4.5, R6.6
- [ ] **T2.3** Inicio de sesión, hash argon2, roles, CSRF y protección de rutas por rol. → R6.1, R2.5
- [ ] **T2.4** Administración: usuarios, asignación de partidas y centros a cada jefe, y unidades con decimales. → R1.10, R6.7

## Fase 3 — Sincronización
- [ ] **T3.1** Endpoints `/sync/*` con token, reemplazo idempotente e inactivación sin borrado. → R6.2, R6.3
- [ ] **T3.2** Sincronizador: consultas de solo lectura (tomadas de Almacen), normalización de precios y envío. Pruebas con un doble de Softland. → R6.2, R6.4
- [ ] **T3.3** Indicador de última sincronización con advertencia a las 24 horas. → R6.5

## Fase 4 — Funciones del MVP
- [ ] **T4.1** Carga de presupuesto: subir el archivo, vista previa, confirmar y recargar sin perder consumo. → R1.1–R1.10
- [ ] **T4.2** Consulta de saldo por partida y semana. → R2.1–R2.5
- [ ] **T4.3** Lista de prohibidos del jefe. → R3.7
- [ ] **T4.4** Pedido: búsqueda de artículos, líneas, sugerencia de partida, validación en vivo y envío. → R3.1–R3.10
- [ ] **T4.5** Bandejas de Gerente y Comprador, con aprobar, rechazar y anular. → R4.1–R4.5
- [ ] **T4.6** Generación del lote y descarga del `.xlsx`, comparada con la plantilla ficticia. → R5.1–R5.5

## Fase 5 — Cierre del MVP
- [ ] **T5.1** Pruebas de humo de punta a punta: login, carga de presupuesto, pedido, aprobación y cargador. → todos
- [ ] **T5.2** Quality Gate de SonarCloud en verde y cobertura ≥ 80 %. → todos

## Pendientes externos (no bloquean el desarrollo)
- [ ] **E1** TI crea un usuario de SQL Server de solo lectura (`db_datareader`) sobre `SAYOERP`. → R6.2
- [ ] **E2** Confirmar las tablas de centros de costo y el campo de artículo activo en Softland. → R6.2
- [ ] **E3** Lista real de unidades que admiten decimales. → R6.7
- [ ] **E4** Versión de Softland y opción de importación automática (fuera del MVP).
