# Requisitos — CRM-Compras (MVP)

Las reglas del dominio están en [CLAUDE.md](../../CLAUDE.md#reglas-del-dominio-nunca-se-rompen) y aquí se citan como **D1…D20**. Cada requisito tiene un identificador (R*n*.*m*) que se enlaza desde [tareas.md](tareas.md).

## Alcance

**Incluido en el MVP**
1. Cargar el presupuesto anual desde Excel.
2. Consultar el saldo por semana.
3. Crear y validar pedidos con datos de Softland.
4. Aprobar pedidos: Comprador y, cuando hay exceso, Gerente.
5. Descargar el cargador consolidado para Softland.

Además, como soporte: inicio de sesión con roles, sincronización de datos de Softland y auditoría.

**Fuera del MVP**
- Escribir en Softland, incluida la importación automática.
- Integrar `C:\Apps\Almacen`.
- Cotizaciones y gestión de proveedores.
- Aplicación móvil.
- Importar los cargadores Excel que hoy hacen los jefes.
- Notificaciones por correo.
- Reportes y tableros fuera de la consulta de saldo.

---

## R1. Carga del presupuesto

Como **Administrador**, quiero subir el Excel de presupuesto del año para que el sistema controle el gasto.

- [ ] **R1.1** El sistema acepta un `.xlsx` con el formato de `Presupuestos Compras.xlsx`: una fila con los meses como encabezado, una fila "Semanas" y filas de rubro y área. (D6)
- [ ] **R1.2** Una fila con fórmula `SUM(Bx:By)` es un **rubro**, y las filas de su rango son sus **áreas**. Cada par rubro × área es una **partida**. (D6, D7)
- [ ] **R1.3** Una fila con valores que no pertenece a ningún rango es una partida con el área `GENERAL` (por ejemplo, POLIETILENO). Se ignoran la fila del total general y las filas de rubro.
- [ ] **R1.4** Solo se leen las columnas con mes como encabezado. Las columnas con datos y sin encabezado se ignoran y se reportan como advertencia. (D6)
- [ ] **R1.5** Los valores se redondean a pesos enteros con redondeo hacia arriba en la mitad (`ROUND_HALF_UP`). Una celda vacía es 0. Un valor negativo o no numérico es un error con su fila y columna. (D2, D6)
- [ ] **R1.6** El número de semanas de cada mes debe coincidir con el calendario ISO, contando cada semana en el mes de su jueves. Si no coincide, la carga se rechaza indicando el mes. (D5)
- [ ] **R1.7** Antes de confirmar, el sistema muestra una vista previa con las partidas, el total por mes, las advertencias y los errores. Si hay errores, no se puede confirmar.
- [ ] **R1.8** Al recargar el mismo año se reemplazan los valores asignados sin perder lo ya consumido. Si una partida con consumo desaparece del archivo, la carga se rechaza.
- [ ] **R1.9** Cada carga queda en la auditoría: usuario, fecha, archivo y totales anteriores y nuevos. (D19)
- [ ] **R1.10** El Administrador asigna a cada jefe sus partidas y sus centros de costo. (D18)

## R2. Consulta de saldo

Como **Jefe de área**, quiero ver cuánto presupuesto tengo por semana para pedir sin pasarme.

- [ ] **R2.1** Para cada partida del jefe, el sistema muestra por semana: lo asignado, lo consumido, el saldo acumulado y lo disponible. (D5)
- [ ] **R2.2** El valor semanal es el valor del mes dividido entre sus semanas, y el residuo del redondeo se suma a la última semana. (D5)
- [ ] **R2.3** Lo consumido suma las líneas de pedidos en `pendiente_gerencia`, `enviado`, `aprobado` y `exportado`, en la semana de su fecha requerida. (D5, D8)
- [ ] **R2.4** Lo disponible en la semana *s* es el menor saldo acumulado entre *s* y el fin del año. (D5)
- [ ] **R2.5** El jefe solo ve sus partidas. El Comprador, el Gerente y el Administrador ven todas. (D18)

## R3. Pedidos

Como **Jefe de área**, quiero armar un pedido con datos reales para que llegue sin errores a Compras.

- [ ] **R3.1** El jefe busca artículos por código o por descripción entre los artículos **activos** sincronizados desde Softland. No se aceptan artículos en texto libre. (D10)
- [ ] **R3.2** Cada línea tiene: artículo, centro de costo (solo los del jefe), partida (solo las del jefe), cantidad, fecha requerida y comentario opcional. (D11, D7)
- [ ] **R3.3** La descripción del artículo, la descripción del centro de costo, la unidad y el precio se toman de Softland y no se pueden editar. (D12, D4)
- [ ] **R3.4** El sistema sugiere la partida usada en la última línea con el mismo artículo y centro de costo. (D7)
- [ ] **R3.5** El sistema valida cada línea y muestra todos los problemas a la vez:
  - **Errores (bloquean el envío)**: código inexistente o inactivo; centro de costo inexistente o ajeno; partida faltante o ajena; cantidad ≤ 0; cantidad con decimales en una unidad que exige entero; artículo sin precio; fecha requerida anterior a hoy o fuera de un año con presupuesto cargado; artículo y centro de costo repetidos en el mismo pedido. (D4, D10, D11, D13, D15)
  - **Advertencias (no bloquean)**: el mismo artículo y centro de costo ya está en otro pedido de la misma semana. (D15)
- [ ] **R3.6** Si el artículo está en la lista de prohibidos del jefe, la línea se marca con la bodega 5. (D14)
- [ ] **R3.7** El jefe mantiene su lista de artículos prohibidos (agregar y quitar). (D14, D19)
- [ ] **R3.8** El valor de la línea es la cantidad × el precio, antes de IVA, en pesos enteros. (D2, D4)
- [ ] **R3.9** Al enviar, el precio se congela. Si alguna partida excede lo disponible en la semana de la línea, el pedido pasa a `pendiente_gerencia`; si no, a `enviado`. (D4, D8, D9, D16)
- [ ] **R3.10** El pedido solo se edita en `borrador`. El jefe puede anular su pedido en `pendiente_gerencia`, `enviado` o `aprobado`, con motivo, y así se libera el presupuesto. (D8, D16)

## R4. Aprobación

Como **Comprador** y como **Gerente**, quiero revisar los pedidos para controlar lo que se compra.

- [ ] **R4.1** El Gerente ve los pedidos en `pendiente_gerencia` con el exceso por partida y semana. Los aprueba con justificación obligatoria (pasan a `enviado`) o los rechaza con motivo. (D9, D16)
- [ ] **R4.2** El Comprador ve los pedidos en `enviado` y los aprueba o los rechaza con motivo. (D16)
- [ ] **R4.3** Al aprobar, el sistema vuelve a validar. Si un artículo quedó inactivo después del envío, el pedido no se aprueba y se muestra el motivo. (D10)
- [ ] **R4.4** Rechazar o anular libera el presupuesto comprometido. (D8)
- [ ] **R4.5** Cada transición de estado queda en la auditoría. (D19)

## R5. Cargador consolidado

Como **Comprador**, quiero descargar un solo archivo validado para importarlo en Softland sin digitar.

- [ ] **R5.1** El Comprador selecciona pedidos `aprobado` y asigna la bodega (1 o 2) a las líneas que no son prohibidas. Las líneas prohibidas quedan fijas en la bodega 5. (D14)
- [ ] **R5.2** El sistema genera un `.xlsx` con una hoja por bodega (`La Union`, `La Ceja`, `Prohibidos`) y con las columnas y formatos exactos de la plantilla. Hay una fila por línea, en el orden de la plantilla. (D17)
- [ ] **R5.3** El código del artículo y el centro de costo se escriben como texto. Los ceros a la izquierda se conservan y la fecha va con formato `dd/mm/yyyy`. (D17)
- [ ] **R5.4** Cada generación crea un **lote** con su número. Las líneas incluidas pasan a `exportado` y no pueden entrar en otro lote. El mismo lote se puede volver a descargar idéntico. (D16, D17)
- [ ] **R5.5** Si una línea seleccionada no tiene bodega, no se genera el archivo y se indica qué falta.

## R6. Soporte

- [ ] **R6.1 Sesión y roles**: ingreso con usuario y contraseña (hash argon2). Los roles son Jefe, Comprador, Gerente y Administrador, y cada ruta verifica el rol.
- [ ] **R6.2 Sincronización**: el sincronizador local lee de Softland, solo con `SELECT`, los artículos (código, descripción, unidad, activo), los centros de costo (código, descripción, activo) y el último precio de compra, y los envía a la API con un token. (D1)
- [ ] **R6.3** Un artículo o centro de costo que ya no viene en la sincronización queda inactivo. Nunca se borra.
- [ ] **R6.4** El precio del artículo `020215` se divide por el factor numérico de su comentario, como en Almacen. (D4)
- [ ] **R6.5** La pantalla muestra la fecha de la última sincronización. Si tiene más de 24 horas, se muestra una advertencia.
- [ ] **R6.6 Auditoría**: registro que solo admite inserciones, consultable por el Administrador. (D19)
- [ ] **R6.7** Las unidades que admiten decimales están en una lista que mantiene el Administrador. La lista inicial es KL, CC, MT, GR, GL, LB y LT; cualquier otra unidad exige cantidades enteras. (D13)
