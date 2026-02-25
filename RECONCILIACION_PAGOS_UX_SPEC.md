# Especificación UX: Pantalla de Conciliación por Pagos (Payments Reconciliation)

**Producto:** Tu Pana (Chile)  
**Alcance:** Pantalla que vincula movimientos bancarios / documentos de pago con facturas por cobrar.  
**Objetivo:** Conciliación lo más rápida posible con visibilidad total (nunca ocultar datos) y guía clara mediante sugerencias y filtros.

---

## 1. Arquitectura de información de la pantalla

### 1.1. Regla de oro

- **Siempre se muestran las dos listas:** (A) Movimientos / Pagos (Documento 100) y (B) Facturas por cobrar.
- **Al seleccionar un movimiento:** se conectan de inmediato los “rayos” (Lightning) con las facturas sugeridas, o se indica “Sin coincidencias”; la lista de facturas **nunca se oculta**.
- **Tras conectar los rayos (con animación):** se reordena la vista de facturas: la(s) factura(s) sugerida(s) aparecen primero; el resto mantiene un orden lógico (p. ej. fecha, cliente), pero la sugerencia sale de ese orden para quedar arriba.

### 1.2. Estructura en zonas

| Zona | Contenido | Comportamiento |
|------|-----------|----------------|
| **Header** | Título “Conciliación por pagos”, entidad, **Total pendiente** (monto total por cobrar), acciones globales (Limpiar masivo, Configuración). | Fijo; el total pendiente se actualiza al cargar/conciliar. |
| **Barra de resumen (debajo del header)** | Métricas en una línea: “X movimientos por conciliar · Y facturas por conciliar · $Z monto total”. | Solo lectura; refuerza visibilidad. |
| **Columna izquierda** | Lista/tabla de **Movimientos** (pagos, Doc 100): búsqueda, filtros (chips), ordenación, filas con estados (selected, matched, etc.). | Siempre visible; ancho fijo o mínimo (ej. 420px). |
| **Columna derecha** | Lista de **Facturas por cobrar**: total pendiente arriba, búsqueda/filtros, ordenación, filas con estados. Sugerencias reordenadas arriba al seleccionar movimiento. | Siempre visible; resto del ancho. |
| **Panel de Match (central o inline)** | Aparece cuando hay movimiento y/o factura(s) seleccionados: detalle del movimiento, factura(s) elegida(s), diferencia, comisiones si aplican, confianza sugerida, acciones (Conciliar, Limpiar, etc.). | Inline en la columna derecha (debajo del detalle del pago) o como barra fija entre columnas. |
| **Rayos (Lightning)** | Líneas animadas que unen el movimiento seleccionado con la(s) factura(s) conectada(s). | Se dibujan al conectar; animación suave. |
| **Estados vacíos** | Sin movimientos, sin facturas, sin coincidencias, sin selección. | Mensajes y CTAs claros (ver microcopy). |

### 1.3. Flujo de datos por defecto

- **Carga inicial:** Se muestran todos los movimientos (pagos) según filtros; y **todas** las facturas “por cobrar” (unpaid) con el **total pendiente** destacado arriba de la lista de facturas.
- **Al seleccionar un movimiento:** Se calculan sugerencias (recomendaciones); se conectan los rayos a las mejores candidatas (máx. 2 si aplica); la lista de facturas se reordena con sugeridas arriba; si no hay candidatas, se muestra “Sin coincidencias” pero la lista de facturas sigue visible (sin ocultar filas).

---

## 2. Componentes de UI y estados

### 2.1. Header

- **Título:** “Conciliación por pagos”
- **Subtítulo:** “Selecciona un pago (Doc 100) y asígnalo a facturas o márcalo como limpio.”
- **Total pendiente:** Número destacado (ej. “$2.450.000 por cobrar”) o integrado en la barra de resumen.
- **Acciones:** “Limpiar masivo”, “Configuración” (autoconciliación).

### 2.2. Búsqueda global y chips de filtro

- **Búsqueda:** Un campo por columna (o uno global que filtre ambas listas según contexto). Placeholder: “Buscar por RUT, razón social, glosa, monto”.
- **Chips (Movimientos):** Estado (Todos, Pendientes, Conciliados, Limpios), “Sin rayo” (sin sugerencias), “Sin RUT”.
- **Chips (Facturas):** Opcional: “Solo sugeridas” / “Todas” (toggle Suggested view, ver sección 6).
- Comportamiento: no ocultar datos; solo filtrar/ordenar. Siempre existe la opción “Ver todas”.

### 2.3. Tabla izquierda (Movimientos)

**Columnas (ordenables):**

- Checkbox (limpieza masiva / multi-select)
- Icono rayo (conectar a facturas)
- RUT pagador
- Razón social
- Monto
- Fecha
- Glosa / descripción
- Origen (Shopify, Fintoc, Manual)
- Estado (Pendiente, Conciliado, Limpio)

**Estados de fila:**

- **Default:** Fondo neutro.
- **Selected:** Fondo verde suave, borde izquierdo verde; rayo activo si hay facturas conectadas.
- **Matched:** Indicador “Conciliado” (chip/badge).
- **Partially matched:** (Futuro) Badge “Pago parcial”.
- **Conflict:** (Futuro) Borde o icono de advertencia si hay diferencia o duplicado.
- **Limpio:** Badge “Limpio”; no conciliable.

### 2.4. Tabla derecha (Facturas)

**Contenido arriba de la tabla:**

- **Total pendiente:** “Total por cobrar: $X” (suma de facturas mostradas o del contexto actual).

**Columnas (ordenables):**

- Doc # / Folio
- Cliente (RUT / Razón social)
- Monto
- Fecha emisión
- Estado (Por cobrar, Parcial, etc.)
- Acción (Conciliar)

**Estados de fila:**

- **Default:** Fondo neutro.
- **Suggested (candidata):** Borde o fondo sutil distinto; badge “Sugerida” o score.
- **Connected (conectada por rayo):** Borde verde, anillo verde; “Conectada”.
- **Selected:** Resaltado para multi-select si aplica.
- **Already reconciled:** Deshabilitada o oculta según filtro; tooltip “Ya conciliada”.

### 2.5. Panel de Match (central / inline)

Visible cuando hay movimiento seleccionado (y opcionalmente factura(s) elegida(s)).

**Contenido:**

- **Movimiento:** Monto, fecha, RUT, razón social, glosa (expandible).
- **Factura(s) seleccionada(s):** Hasta 2; monto cada una y total.
- **Diferencia:** Monto (movimiento − facturas). Si calza: “Calza perfecto”.
- **Comisiones / retenciones:** (Si el movimiento incluye gastos bancarios) Línea opcional “Incluye comisión: $X”.
- **Confianza sugerida:** Score (ej. 85/100) o etiquetas (“Mismo monto”, “Mismo cliente”, “Fecha cercana”, “Pago parcial”).
- **Acciones:** Conciliar, Limpiar (marcar no relacionado), Rechazar sugerencia, Ver movimientos.

Si no hay facturas conectadas: mensaje “Selecciona una o dos facturas para conciliar” o “Sin coincidencias para este pago”.

---

## 3. Lógica de sugerencias (UX, sin código)

### 3.1. Reglas de ranking (prioridad)

1. **Mismo monto** (exacto o dentro de tolerancia): mayor peso.
2. **Mismo cliente (RUT):** alto peso.
3. **Fecha cercana** (emisión factura vs fecha movimiento): peso medio.
4. **Monto parcial:** si el movimiento es menor que la factura, candidato a “Pago parcial”.
5. **Combinación:** mismo RUT + monto cercano + fecha cercana → muy alta confianza.

### 3.2. Comunicación visual de confianza

- **Score numérico:** “85/100” en badge junto al candidato.
- **Etiquetas (tags):** “Mismo monto”, “Mismo cliente”, “Fecha cercana”, “Pago parcial”, “Múltiples facturas”.
- **Orden:** Las sugerencias aparecen **arriba** de la lista de facturas (fuera del orden lógico); el resto ordenado por fecha o cliente.
- **Rayos:** Solo se dibujan hacia las facturas que el sistema sugiere (o que el usuario ha conectado); refuerzan “estas son las que calzan”.

### 3.3. Sin coincidencias

- No ocultar la lista de facturas.
- Mensaje claro: “No hay coincidencias sugeridas para este pago. Revisa todas las facturas más abajo o márcalo como limpio.”
- Acciones: “Limpiar pago”, “Ver movimientos”, o elegir manualmente una factura de la lista.

---

## 4. Acciones y atajos de teclado

### 4.1. Acciones principales

- **Confirmar match (Conciliar):** Une movimiento con una o dos facturas; marca factura(s) como pagada(s) y movimiento como conciliado.
- **Dividir movimiento en varias facturas:** Permite asignar partes del monto del movimiento a distintas facturas (split).
- **Pago parcial en una factura:** Un movimiento con monto menor al de la factura; se registra monto conciliado y saldo pendiente.
- **Marcar como “No relacionado” / “Limpio”:** El pago no corresponde a facturas (comisión, traspaso, etc.); no se oculta, queda con estado “Limpio”.
- **Deshacer / Historial:** (Futuro) Deshacer última conciliación; historial de conciliaciones para auditoría.

### 4.2. Atajos propuestos (español + tecla)

- **Conciliar:** `Ctrl/Cmd + Enter` cuando el panel de Match está activo.
- **Limpiar pago:** `Ctrl/Cmd + L` con movimiento seleccionado.
- **Siguiente movimiento (Tinder):** `→` o `Enter` en modo Tinder.
- **Cancelar selección:** `Esc`.

---

## 5. Operaciones en lote (batch)

### 5.1. Multi-select movimientos

- Checkbox en cada fila de movimientos.
- “Seleccionar todos los mostrados” en el modal de Limpiar masivo.
- **Flujo:** Usuario filtra (ej. por fecha), selecciona varios movimientos, abre “Limpiar masivo” y marca categoría/nota; confirma. No se mezcla con conciliación en esta versión (solo limpieza).

### 5.2. Multi-select facturas para un movimiento

- Un movimiento puede conciliarse con **varias facturas** (hasta 2 en la UI actual; lógica de “split” puede extender).
- Usuario selecciona movimiento; el sistema sugiere 1–2 facturas; el usuario puede cambiar la selección (quitar/añadir) y luego Conciliar.

### 5.3. Confirmación masiva de sugerencias (alta confianza)

- (Futuro) Toggle “Sugerencias de alta confianza”: lista de pares movimiento–factura(s) con score > umbral.
- Botón “Conciliar todas las sugerencias mostradas” con confirmación; el usuario puede revisar y ejecutar en lote.

---

## 6. Ordenación y filtros (manteniendo “mostrar todo”)

### 6.1. Ordenación por defecto

- **Movimientos:** Por defecto por fecha (más reciente primero); el usuario puede cambiar por RUT, razón social, monto, glosa, estado.
- **Facturas:** Por defecto por fecha de emisión o por cliente. **Al seleccionar un movimiento:** las facturas **sugeridas** se reordenan para aparecer **arriba** (fuera de ese orden); el resto mantiene el orden lógico elegido.

### 6.2. Toggle “Vista sugerida” (Suggested view)

- **Off (default):** Se muestran **todas** las facturas por cobrar; las sugeridas aparecen arriba pero el resto sigue visible.
- **On:** Opcionalmente filtrar la lista para mostrar **solo** candidatas sugeridas para el movimiento seleccionado.
- **Escapa:** Siempre un enlace o botón “Ver todas las facturas” para volver a la vista completa sin ocultar datos.

### 6.3. Filtros

- No eliminar filas de forma irreversible; solo filtrar. “Limpiar filtros” restaura la vista completa.

---

## 7. Microcopy (español)

### 7.1. Títulos de sección

- **Conciliación por pagos**
- **Movimientos (Documento 100)** / **Pagos**
- **Facturas por cobrar**
- **Total por cobrar**
- **Candidatos a conciliar**
- **Todas las facturas**
- **Limpiar pagos** (modal)
- **Configuración de autoconciliación**

### 7.2. Botones

- **Conciliar** – Confirmar match
- **Limpiar** – Marcar pago como no relacionado (comisión/traspaso)
- **Reabrir** – Volver a dejar el pago como conciliable
- **Limpiar masivo** – Abrir modal de limpieza en lote
- **Configuración** – Abrir configuración de autoconciliación
- **Ver movimientos** – Ir a movimientos bancarios
- **Rechazar** – No volver a mostrar esta sugerencia
- **Cargar más facturas**
- **Marcar como limpios (N)** – En modal bulk
- **Cancelar** / **Cerrar**

### 7.3. Tooltips

- **Diferencia:** “Diferencia entre el monto del movimiento y el total de las facturas seleccionadas.”
- **Confianza:** “Qué tan probable es que este movimiento corresponda a esta factura (monto, cliente, fecha).”
- **Pago parcial:** “El monto del movimiento no cubre el total de la factura; se registrará como pago parcial.”
- **Rayo (conectar):** “Incluir este movimiento en la conciliación con las facturas seleccionadas.”

### 7.4. Estados vacíos

- **Sin movimientos:** “No hay pagos para mostrar. Conecta tu banco o crea pagos manuales para verlos aquí.” + CTA “Ir a movimientos”.
- **Sin facturas:** “No hay facturas por cobrar para mostrar.”
- **Sin coincidencias:** “No hay coincidencias sugeridas para este pago. Revisa todas las facturas más abajo o márcalo como limpio.”
- **Sin selección (panel derecho):** “Selecciona un pago para ver recomendaciones y facturas a conciliar.”

### 7.5. Mensajes de advertencia / conflicto

- **Monto no calza:** “Diferencia: $X. Verifica que el movimiento corresponda a las facturas seleccionadas.”
- **Factura ya conciliada:** “Esta factura ya fue conciliada con otro movimiento.”
- **Movimiento duplicado:** “Este movimiento podría estar duplicado. Revisa antes de conciliar.”
- **Pago parcial:** “Se registrará un pago parcial de $X; saldo pendiente $Y.”

---

## 8. Casos borde

| Caso | Comportamiento UX |
|------|-------------------|
| **Un movimiento, varias facturas (mismo cliente)** | Sugerir hasta 2 facturas cuyo total calce (o cercano); usuario puede conectar 1 o 2; panel de Match muestra total y diferencia. |
| **Una factura pagada por varios movimientos** | (Futuro) Permitir conciliar varios movimientos contra una factura (pagos parciales sucesivos); total conciliado ≤ monto factura. |
| **Movimiento con comisión/retención** | En panel de Match: línea “Incluye comisión/retención: $X”; diferencia puede ser explicada; opción “Conciliar solo monto neto” si aplica. |
| **Movimiento duplicado** | Advertencia si el monto+fecha+RUT coinciden con otro ya conciliado; no bloquear, sugerir revisar. |
| **Factura ya conciliada** | No mostrarla en “por cobrar” o mostrarla deshabilitada con tooltip “Ya conciliada”; no permitir doble conciliación. |
| **Diferencia de monto** | Mostrar diferencia en el panel; permitir conciliar igual con advertencia o bloquear según configuración. |

---

## 9. Formato de salida: flujos resumidos

### 9.1. Happy path (flujo principal)

1. Usuario entra a Conciliación por pagos; ve movimientos a la izquierda y facturas a la derecha con **total pendiente** arriba.
2. Hace clic en un **movimiento** (pago).
3. El sistema **conecta los rayos** a las 1–2 facturas sugeridas (animación) y **reordena** la lista de facturas con esas arriba; si no hay sugerencias, muestra “Sin coincidencias” y deja todas las facturas visibles.
4. Usuario revisa el **panel de Match** (monto, diferencia, confianza); puede cambiar la factura conectada haciendo clic en otra.
5. Si calza (o acepta diferencia), pulsa **Conciliar**; el movimiento pasa a “Conciliado” y la factura deja de estar “por cobrar”.
6. El total pendiente y los contadores se actualizan; puede seguir con el siguiente movimiento.

### 9.2. Flujo alternativo: usuario elige factura primero

1. Usuario explora la lista de **facturas** (derecha) y hace clic en una.
2. El sistema podría (futuro) resaltar o filtrar **movimientos sugeridos** para esa factura en la columna izquierda.
3. Usuario selecciona un movimiento de la izquierda; se conectan los rayos y se muestra el panel de Match; confirma Conciliar.

### 9.3. Flujo alternativo: marcar como limpio

1. Usuario selecciona un movimiento que no corresponde a facturas (ej. comisión bancaria).
2. Ve “Sin coincidencias” o no elige ninguna factura; en el panel de Match pulsa **Limpiar**.
3. El pago queda como “Limpio”; desaparece de “pendientes” en filtros; puede reabrirse si fue error.

---

## 10. Resumen de principios

- **Visibilidad total:** Ambas listas (movimientos y facturas) siempre visibles; no ocultar filas por defecto.
- **Guía sin imponer:** Sugerencias y rayos orientan; el usuario puede ignorar y elegir cualquier factura o marcar como limpio.
- **Reordenar, no ocultar:** Al seleccionar movimiento, las facturas sugeridas suben arriba; el resto sigue visible en orden lógico.
- **Rayos inmediatos:** Al apretar un movimiento, los rayos se conectan de inmediato a las sugerencias (o se muestra “Sin coincidencias”).
- **Nombres en inglés para entidades:** Movement, Invoice, Reconcile, Match, Confidence, Suggested view.
- **Simple y rápido:** Priorizar 80/20; sin nuevos módulos fuera de esta pantalla.
