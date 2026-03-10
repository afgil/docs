# Creación de asientos contables (AccountingEntry) — Endpoints y estructura REST

## 1. Qué es un asiento

En este proyecto, **asiento contable** = modelo **`AccountingEntry`** (app `accounting`).  
No existe un serializer “por nombre de asiento” ni un recurso llamado “bank reconciliation” como asiento: la conciliación bancaria (`BankReconciliation`) es un recurso que, en ciertos flujos, **dispara la creación** de un `AccountingEntry` (tipo `PAYMENT_RECONCILIATION`).

- **AccountingEntry**: cabecera del asiento (company, entry_type, status, entry_date, idempotency_key, etc.) con líneas en `AccountingLine` y documentos en `AccountingEntryDocument`.
- **Voucher / VoucherEntry**: otro sistema (comprobantes contables); no son `AccountingEntry`.

---

## 2. Tipos de asiento (EntryType) y quién los crea
 
| EntryType | Descripción | Builder (servicio) | Origen (dónde se invoca) |
|-----------|-------------|--------------------|---------------------------|
| `INVOICE_ISSUED` | Ingreso + CxC por factura emitida | `build_invoice_issued_entry` | Señales/documentos (ensure_invoice_issued_entry), no endpoint directo |
| `CREDIT_NOTE_APPLICATION` | NC aplicada a facturas | `build_credit_note_application_entry` | POST accounting-entries (body allocations con role source/target) |
| `PAYMENT_RECONCILIATION` | Pago (doc 100) aplicado a facturas; puede incluir diferencia OtherIncome/OtherExpense | `build_payment_reconciliation_entry` | POST accounting-entries (body allocations con role source/target); BankReconciliation serializer (flujo payment_document + document_reconciliations) |
| `BANK_MOVEMENT_RECEIVED` | Movimiento bancario recibido (Cash Dr, BankMovementPending Cr) | `build_bank_movement_received_entry` | Señal de banking al crear/actualizar movimiento (no endpoint) |
| `PAYMENT_CLEANED` | Limpieza de pago sin conciliar con facturas | `build_cleaned_payment_entry` / `build_bulk_cleaned_payment_single_entry` | BulkCleanPaymentsView; DocumentBatchPatchSerializer (limpieza) |
| `RECEIVABLE_BULK_CLOSE_EXCLUSIONS` | Cierre masivo CxC (marcar facturas pagadas con exclusiones) | `build_bulk_mark_receivable_paid_single_entry` | BulkMarkReceivablesPaidView |
| `MANUAL_ADJUSTMENT` | Ajuste manual (ej. descripción “Limpieza de pago:…”) | Mismo builder que limpieza | Mismo origen que PAYMENT_CLEANED en flujos legacy |
| `BANK_RECONCILIATION` | Legacy (clear pending, credit AR) | (legacy) | Referenciado en queries; no hay builder activo que lo cree en los flujos actuales |

---

## 3. Endpoints actuales que crean o disparan asientos

### 3.1 Creación directa de asientos (recurso `accounting-entries`)

**Base:** `/api/accounting/accounting-entries/`

| Método | Descripción | Body (resumido) | Asiento creado |
|--------|-------------|-----------------|----------------|
| **POST** | Crear asiento de conciliación de pago o aplicación de NC | Ver abajo | PAYMENT_RECONCILIATION o CREDIT_NOTE_APPLICATION |

- **PAYMENT_RECONCILIATION** y **CREDIT_NOTE_APPLICATION:**  
  `company_id`, `allocations` (un ítem con `role: "source"` + uno o más con `role: "target"`, cada uno `document_id` y `amount`), `idempotency_key`, `post` (opcional). *Legacy: se puede aceptar source_document_id + allocations solo targets y normalizar a este formato.*

Serializers: `CreatePaymentReconciliationSerializer`, `CreateCreditNoteApplicationSerializer`.  
**Esquema genérico:** todo en `allocations` con `role: "source"` | `"target"`.

### 3.2 Conciliaciones bancarias (recurso `bank-reconciliations`) — crean asiento como efecto

**Base:** `/api/accounting/bank-reconciliations/`

| Método | Acción | Efecto en asientos |
|--------|--------|--------------------|
| **POST** (create) | Crear conciliación | Si flujo es documento de pago + `document_reconciliations`: internamente llama a `build_payment_reconciliation_entry` + `post_entry` → crea **PAYMENT_RECONCILIATION**. |
| **POST** `.../bulk_reconcile/` | Conciliación masiva | Con `document_reconciliations` (y movimientos): crea conciliaciones; en el flujo con documento de pago se crean asientos **PAYMENT_RECONCILIATION**. |

No hay endpoint “crear asiento por nombre”: se crea el recurso conciliación y el asiento es un efecto secundario.

### 3.3 Limpieza de pagos y cierre masivo CxC

Estos asientos **no** se crean con `POST /api/accounting/accounting-entries/` (no usan `allocations` ni `lines` en ese recurso). Tienen endpoints propios con payload distinto:

| Endpoint | Método | Body (resumido) | Asiento(s) |
|----------|--------|-----------------|------------|
| `/api/accounting/master-entities/<id>/bulk-clean-payments/` | POST | accounting_plan_account_id, date_to, exclude_document_ids, single_entry, clean_note, payment_source | PAYMENT_CLEANED / MANUAL_ADJUSTMENT (vía DocumentBatchPatchSerializer) |
| `/api/accounting/master-entities/<id>/bulk-mark-receivables-paid/` | POST | exclude_document_ids, date_to | RECEIVABLE_BULK_CLOSE_EXCLUSIONS (un asiento por lote) |

Al hacer **GET** de un asiento de tipo PAYMENT_CLEANED o RECEIVABLE_BULK_CLOSE_EXCLUSIONS, la respuesta incluye `allocations` (derivado de entry_documents + lines) con el mismo formato que el resto, para consistencia.

### 3.4 Endpoints legacy (Voucher, no AccountingEntry)

| Endpoint | Método | Qué crea |
|----------|--------|----------|
| `/api/accounting/reconcile/` | POST | Voucher + VoucherEntry (comprobante), no AccountingEntry |
| `/api/accounting/reconcile/bulk/` | POST | Varios Voucher + VoucherEntry, no AccountingEntry |

### 3.5 Otros recursos que no son “crear asiento”

- **GET** `/api/accounting/documents/<document_id>/accounting-entries/`: lista asientos que afectan a un documento.
- **GET/PATCH** `/api/accounting/accounting-entries/<id>/`: leer/actualizar asiento existente.
- **Vouchers:** `POST /api/accounting/vouchers/`, `POST /api/accounting/voucher-entries/`, etc.: crean `Voucher`/`VoucherEntry`, no `AccountingEntry`.

---

## 4. Propuesta de estructura REST unificada para creación de asientos

Objetivo: **un solo recurso “asientos”** con creación por **tipo de asiento** explícito y payloads claros, en lugar de deducir el tipo por el body.

### 4.1 Recurso principal: asientos

- **Colección:** `GET /api/accounting/accounting-entries/` (ya existe; filtros por company_id, entry_type, status, fechas).
- **Detalle:** `GET /api/accounting/accounting-entries/<id>/` (ya existe).
- **Creación:** un único `POST /api/accounting/accounting-entries/` con cuerpo que siempre incluya el tipo.

### 4.2 Formato de creación propuesto (REST unificado)

**POST** `/api/accounting/accounting-entries/`

- **Cabecera común (todas las creaciones):**
  - `company_id` (requerido)
  - `idempotency_key` (requerido)
  - `post` (opcional, default true): si se debe pasar el asiento a POSTED tras crearlo.

- **Regla: todo asiento debe tener documento.**  
  Cada asiento creado por API debe estar respaldado por al menos un documento. **Buena práctica:** justificar **por línea** (cada línea con su `document_id`), de modo que cada movimiento quede trazable a un documento concreto; evita un solo documento “paraguas” para todo el asiento y mejora auditoría. Según el tipo: el documento viene en el payload (p. ej. el ítem con `role: "source"` en `allocations`) o se envía explícito; en asientos tipo journal, **cada línea debe traer `document_id`** (ver DOCUMENT_SUPPORTED_JOURNAL). Si falta el documento requerido para el tipo o para alguna línea, la creación falla (validación).

- **Tipo de asiento:** campo `entry_type` con uno de:
  - `PAYMENT_RECONCILIATION`
  - `CREDIT_NOTE_APPLICATION`
  - `DOCUMENT_SUPPORTED_JOURNAL` (otros ingresos, otros gastos, capital, etc.; ver abajo)
  - (Opcional a futuro: `INVOICE_ISSUED`, `PAYMENT_CLEANED`, etc., si se exponen por API.)

- **Esquema genérico: todo en `allocations`.**  
  Pago aplicado a facturas y NC aplicada a facturas son el mismo concepto: un documento origen se asigna a uno o más documentos destino con un monto cada uno. En lugar de un campo aparte para el origen, **todo va en un solo array** con rol:
  - **`allocations`**: array de `{ "document_id": int, "amount": str|number, "role": "source" | "target" }`.
    - **Un único ítem con `role: "source"`**: el documento origen (pago doc 100 o NC). El `amount` en el source es el monto total de ese documento aplicado (opcional para validación: suma de targets ≤ source).
    - **El resto con `role: "target"`** (o sin `role`, que se interpreta como target): facturas a las que se aplica, cada una con su monto.
  - Así no hace falta `source_document_id`: el origen es el ítem en `allocations` con `role: "source"`. Un solo contrato, un solo array.

- **Payload por tipo:**

  - **PAYMENT_RECONCILIATION**
    - `allocations`: un ítem con `role: "source"` (documento de pago, ej. doc 100) + uno o más ítems con `role: "target"` (facturas y montos).

  - **CREDIT_NOTE_APPLICATION**
    - `allocations`: un ítem con `role: "source"` (documento NC) + uno o más ítems con `role: "target"` (facturas y montos). Mismo formato que pago.

  - **DOCUMENT_SUPPORTED_JOURNAL** (asiento con líneas libres: otros ingresos, otros gastos, capital, ingresos, gastos)
    - **Justificación por línea (buena práctica):** cada línea debe traer su propio `document_id` para justificar ese movimiento. Así se evita un solo documento para todo el asiento y se mejora trazabilidad y auditoría.
    - `document_id`: int (opcional a nivel asiento). Si todo el asiento se respalda por un único documento, puede enviarse aquí además de en cada línea; el backend puede usarlo para `AccountingEntryDocument` (SOURCE) y/o `original_document`. No sustituye el `document_id` por línea.
    - `entry_date`: string (fecha ISO, requerido).
    - `description`: string (opcional).
    - `lines`: array de líneas contables (mínimo 2; débitos totales = créditos totales). Cada ítem:
      - `account_code`: string (código de cuenta en el plan, ej. `OtherIncome`, `OtherExpense`, `Revenue`, `Capital`, o el `code` de `ChartOfAccounts`).
      - `debit_amount`: string|number (decimal, ≥ 0). Una línea tiene solo débito o solo crédito.
      - `credit_amount`: string|number (decimal, ≥ 0).
      - `document_id`: int (**requerido por línea**). Documento que justifica esta línea (`AccountingLine.document`). Permite que cada movimiento tenga su propio respaldo (recibo, factura, comprobante, etc.). **Si el documento no existe** en el sistema (no creado o no pertenece a la company), el backend no crea el asiento y responde con error (p. ej. `document_not_found`), indicando el `document_id` o el índice de línea en el detail.
    - Cuentas típicas: otros ingresos (`OtherIncome`), otros gastos (`OtherExpense`), ingresos (`Revenue`), gastos (cuenta tipo expense), patrimonio/capital (`Equity`/código de cuenta tipo EQUITY), activo, pasivo. El backend validará que los `account_code` existan en el plan de cuentas de la company (o cuenta estándar).

Ejemplo unificado (todo en `allocations`, un ítem `role: "source"` y el resto `role: "target"`):

```json
{
  "company_id": 1,
  "idempotency_key": "unique-key-123",
  "post": true,
  "entry_type": "PAYMENT_RECONCILIATION",
  "allocations": [
    { "document_id": 100, "amount": "80000", "role": "source" },
    { "document_id": 201, "amount": "50000", "role": "target" },
    { "document_id": 202, "amount": "30000", "role": "target" }
  ]
}
```

```json
{
  "company_id": 1,
  "idempotency_key": "nc-app-456",
  "post": true,
  "entry_type": "CREDIT_NOTE_APPLICATION",
  "allocations": [
    { "document_id": 50, "amount": "20000", "role": "source" },
    { "document_id": 201, "amount": "20000", "role": "target" }
  ]
}
```
*(Mismo esquema: un solo array; el origen es el ítem con `role: "source"`. Si se omite `role` en un ítem, se asume `"target"`.)*

**Compatibilidad legacy:** El backend puede aceptar el formato anterior con `source_document_id` + `allocations` (solo targets) y convertirlo a este formato (armar un ítem source + allocations).

Ejemplo **DOCUMENT_SUPPORTED_JOURNAL** (justificación por línea: cada línea con su `document_id`):

```json
{
  "company_id": 1,
  "idempotency_key": "journal-otros-ingresos-001",
  "post": true,
  "entry_type": "DOCUMENT_SUPPORTED_JOURNAL",
  "document_id": 300,
  "entry_date": "2025-02-26",
  "description": "Otros ingresos por intereses",
  "lines": [
    { "account_code": "Cash", "debit_amount": "10000", "credit_amount": "0", "document_id": 300 },
    { "account_code": "OtherIncome", "debit_amount": "0", "credit_amount": "10000", "document_id": 300 }
  ]
}
```
*(Un solo recibo (300) justifica ambas líneas.)*

```json
{
  "company_id": 1,
  "idempotency_key": "journal-capital-002",
  "post": true,
  "entry_type": "DOCUMENT_SUPPORTED_JOURNAL",
  "entry_date": "2025-02-26",
  "description": "Aporte de capital",
  "lines": [
    { "account_code": "Cash", "debit_amount": "500000", "credit_amount": "0", "document_id": 301 },
    { "account_code": "Capital", "debit_amount": "0", "credit_amount": "500000", "document_id": 301 }
  ]
}
```
*(Comprobante 301 justifica ambas partidas.)*

Cuando un mismo asiento agrupa movimientos con **distintos respaldos**, cada línea lleva su propio `document_id`:
```json
{
  "company_id": 1,
  "idempotency_key": "journal-multi-003",
  "post": true,
  "entry_type": "DOCUMENT_SUPPORTED_JOURNAL",
  "entry_date": "2025-02-26",
  "description": "Varios ingresos y gastos",
  "lines": [
    { "account_code": "Cash", "debit_amount": "10000", "credit_amount": "0", "document_id": 310 },
    { "account_code": "OtherIncome", "debit_amount": "0", "credit_amount": "10000", "document_id": 310 },
    { "account_code": "OtherExpense", "debit_amount": "5000", "credit_amount": "0", "document_id": 311 },
    { "account_code": "Cash", "debit_amount": "0", "credit_amount": "5000", "document_id": 311 }
  ]
}
```
*(Líneas 1 y 2 justificadas por doc 310; líneas 3 y 4 por doc 311. Débitos totales = créditos totales.)*

### 4.3 Ventajas

- Un solo endpoint de creación de asientos.
- Tipo de asiento explícito (`entry_type`), sin depender del “nombre” del serializer.
- Misma URL para listar y crear; filtros por `entry_type` ya existen.
- Posibilidad de extender con más tipos (PAYMENT_CLEANED, INVOICE_ISSUED, etc.) añadiendo campos en el body y validación por `entry_type`.

### 4.4 Qué no cambia con esta propuesta

- **BankReconciliation:** sigue siendo un recurso distinto (conciliación bancaria); puede seguir creando asientos internamente cuando el flujo sea “documento de pago + document_reconciliations”.
- **Bulk “bulk-clean-payments” y “bulk-mark-receivables-paid”:** pueden seguir como acciones por entidad; internamente siguen usando los mismos builders.
- **Señales (ej. BANK_MOVEMENT_RECEIVED):** siguen creando asientos por evento, no por API.

### 4.5 Pasos sugeridos para implementar

1. Introducir en el **serializer de creación** un campo `entry_type` (opcional al inicio para compatibilidad).
2. Si viene `entry_type`, validar y mapear a uno de los flujos existentes (`allocations` con exactamente un `role: "source"` y al menos un target para pago o NC). Aceptar formato legacy (source_document_id + allocations solo targets) y normalizar a allocations con roles.
3. Documentar en OpenAPI/Postman los dos formatos (con y sin `entry_type`).
4. A medio plazo: exigir `entry_type` y deprecar la creación sin tipo.
5. Si más adelante se exponen más tipos por API (ej. limpieza de pago, asiento por factura emitida), añadir casos en el mismo `POST accounting-entries` según `entry_type`.

---

## 5. Resumen

- **No existe** un serializer “por nombre de asiento” ni “bank reconciliation” como recurso de asiento; el asiento es siempre **AccountingEntry**.
- La **creación de asientos** hoy se hace por:
  - **POST /api/accounting/accounting-entries/** (solo PAYMENT_RECONCILIATION y CREDIT_NOTE_APPLICATION, tipo implícito por el body),
  - flujos de **bank-reconciliations** (crean PAYMENT_RECONCILIATION como efecto),
  - **bulk-clean-payments** y **bulk-mark-receivables-paid** (otros tipos),
  - y **señales** (BANK_MOVEMENT_RECEIVED, etc.).
- La **propuesta REST** es unificar la creación en **POST /api/accounting/accounting-entries/** con un campo **`entry_type`** explícito y payloads diferenciados por tipo, manteniendo el resto de recursos (bank-reconciliations, bulk, señales) como están.

---

## 6. Propuesta: endpoint batch para recibir asientos

Objetivo: permitir crear **varios asientos en una sola petición**, con tipo explícito por ítem y respuesta que indique éxito/error por ítem.

### 6.1 Endpoint

| Método | URL | Descripción |
|--------|-----|-------------|
| **POST** | `/api/accounting/accounting-entries/batch/` | Crear múltiples asientos en una sola petición |

- Recurso anidado bajo la colección de asientos (`/accounting-entries/`) con acción `batch`, coherente con REST (la colección es `accounting-entries`, el batch es una operación sobre esa colección).

### 6.2 Body del request

**Cabecera común del batch (opcional):**

- `post` (boolean, opcional, default `true`): si los asientos creados deben pasarse a estado POSTED.

**Array de ítems:** cada ítem tiene la misma estructura que el POST simple (sección 4.2), con `entry_type` explícito.

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `entries` | array | sí | Lista de asientos a crear (máximo N, ej. 50 por petición). |
| `post` | boolean | no | Default `true`. Aplica a todos los ítems del batch. |

**Cada elemento de `entries`:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `company_id` | int | sí | Empresa. |
| `idempotency_key` | string | sí | Clave única por asiento (evita duplicados dentro del batch y entre peticiones). |
| `entry_type` | string | sí | `PAYMENT_RECONCILIATION` \| `CREDIT_NOTE_APPLICATION` \| `DOCUMENT_SUPPORTED_JOURNAL`. |
| `post` | boolean | no | Si se omite, usa el `post` del batch. |
| **PAYMENT_RECONCILIATION** / **CREDIT_NOTE_APPLICATION** (todo en allocations) | | | |
| `allocations` | array | condicional | `[{ "document_id": int, "amount": str\|number, "role": "source" \| "target" }]`. Exactamente un ítem con `role: "source"`, el resto `role: "target"` (u omitir role = target). |
| **DOCUMENT_SUPPORTED_JOURNAL** | | | |
| `document_id` | int | no | Opcional a nivel asiento (documento principal si todo el asiento es un solo doc). No sustituye el document_id por línea. |
| `entry_date` | string | condicional | Fecha del asiento (ISO). Requerido para DOCUMENT_SUPPORTED_JOURNAL. |
| `description` | string | no | Descripción opcional. |
| `lines` | array | condicional | `[{ "account_code", "debit_amount", "credit_amount", "document_id" }]`. **Cada línea debe traer `document_id`** (justificación por línea). Débitos totales = créditos totales. |

### 6.3 Ejemplo de body (batch)

```json
{
  "post": true,
  "entries": [
    {
      "company_id": 1,
      "idempotency_key": "payment-recon-001",
      "entry_type": "PAYMENT_RECONCILIATION",
      "allocations": [
        { "document_id": 100, "amount": "80000", "role": "source" },
        { "document_id": 201, "amount": "50000", "role": "target" },
        { "document_id": 202, "amount": "30000", "role": "target" }
      ]
    },
    {
      "company_id": 1,
      "idempotency_key": "nc-app-002",
      "entry_type": "CREDIT_NOTE_APPLICATION",
      "allocations": [
        { "document_id": 50, "amount": "20000", "role": "source" },
        { "document_id": 201, "amount": "20000", "role": "target" }
      ]
    },
    {
      "company_id": 1,
      "idempotency_key": "journal-otros-ingresos-003",
      "entry_type": "DOCUMENT_SUPPORTED_JOURNAL",
      "entry_date": "2025-02-26",
      "description": "Otros ingresos",
      "lines": [
        { "account_code": "Cash", "debit_amount": "10000", "credit_amount": "0", "document_id": 300 },
        { "account_code": "OtherIncome", "debit_amount": "0", "credit_amount": "10000", "document_id": 300 }
      ]
    }
  ]
}
```

### 6.4 Respuesta

- **HTTP 207 Multi-Status** (o **200 OK** con cuerpo estructurado): resultado por ítem.
- Cada ítem en la respuesta debe poder identificarse por índice y/o por `idempotency_key`.

**Estructura de respuesta propuesta:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `created` | array | Ítems creados: `{ "index": int, "idempotency_key": string, "accounting_entry_id": int }`. |
| `skipped` | array | Ítems omitidos por idempotencia: `{ "index": int, "idempotency_key": string, "accounting_entry_id": int }`. |
| `errors` | array | Ítems con error: `{ "index": int, "idempotency_key": string, "error_code": string, "detail": string }`. |

Si **todos** fallan por validación (body mal formado), responder **400** con lista de errores. Si el batch es válido pero algunos ítems fallan (ej. documento inexistente), **207** con `errors` poblado.

Ejemplo **207**:

```json
{
  "created": [
    { "index": 0, "idempotency_key": "payment-recon-001", "accounting_entry_id": 301 }
  ],
  "skipped": [],
  "errors": [
    {
      "index": 1,
      "idempotency_key": "nc-app-002",
      "error_code": "credit_note_not_found",
      "detail": "Credit note with id 50 not found."
    }
  ]
}
```

### 6.5 Reglas de negocio

- **Idempotencia:** si un ítem tiene `idempotency_key` ya usada para esa company, no crear otro asiento; devolverlo en `skipped` con el `accounting_entry_id` existente.
- **Orden:** procesar ítems en orden; si se usa transacción, definir si es “todo o nada” o “por ítem” (recomendación: **por ítem**, para que un fallo no invalide el resto).
- **Límite:** limitar el tamaño del batch (ej. máx. 50 asientos por petición) y responder **400** si se supera.
- **Validación:** validar por ítem; campos requeridos según `entry_type` como en el POST simple.

### 6.5.1 Entry sin documento requerido

Si una entry **no trae el documento (o lista de aplicaciones) requerido** para su `entry_type`, se trata como **error de validación de ese ítem** y no se crea asiento. El ítem va en **`errors`** con un `error_code` y `detail` claros.

| entry_type | Qué se considera “sin document” | error_code sugerido | Comportamiento |
|------------|---------------------------------|---------------------|----------------|
| **PAYMENT_RECONCILIATION** | `allocations` ausente/vacío, o no hay exactamente un ítem con `role: "source"`, o no hay al menos un target | `missing_allocations`, `invalid_allocations` (e.g. zero_or_multiple_sources) | No crear asiento; devolver en `errors`. |
| **CREDIT_NOTE_APPLICATION** | Igual que arriba (mismo esquema) | `missing_allocations`, `invalid_allocations` | No crear asiento; devolver en `errors`. |
| **DOCUMENT_SUPPORTED_JOURNAL** | Falta `document_id` en alguna línea, o `lines` ausente/vacío / desbalance (débitos ≠ créditos) / cuenta inexistente, o **document_id de una línea no existe** en el sistema | `missing_line_document`, `missing_lines`, `lines_not_balanced`, `unknown_account_code`, `document_not_found` | No crear asiento; devolver en `errors` (incl. document_id o índice de línea en detail). |

- **Regla general:** todo asiento debe tener documento (implícito o explícito según el tipo). Si falta el documento requerido para ese tipo, el ítem va en `errors`.

### 6.5.2 Documento asociado a una línea no existe

Si en **DOCUMENT_SUPPORTED_JOURNAL** una línea trae un `document_id` que **no existe** en el sistema (no está creado o no pertenece a la company), el backend **no crea** el asiento y devuelve ese ítem en **`errors`** con un código claro (p. ej. `document_not_found` o `line_document_not_found`), indicando en el `detail` el `document_id` (y opcionalmente el índice de línea) para que el cliente pueda corregir.  
Lo mismo aplica si en **allocations** (pago o NC) algún `document_id` (source o target) no existe: error de validación para ese ítem del batch, con `document_not_found` y detalle del id en cuestión.
- **Respuesta:** igual que para cualquier otro fallo de ítem: **207** con ese ítem en `errors`; el resto del batch se procesa normal.
- **No se crea** asiento para esa entry; no se usa `skipped` (reservado para idempotencia).

Ejemplo de ítem en `errors` por documento faltante:

```json
{
  "index": 2,
  "idempotency_key": "payment-recon-003",
  "error_code": "missing_allocations",
  "detail": "At least one allocation (document_id + amount) is required."
}
```

### 6.6 Resumen del endpoint batch

| Aspecto | Valor |
|---------|--------|
| **URL** | `POST /api/accounting/accounting-entries/batch/` |
| **Body** | `{ "post": boolean?, "entries": [ { company_id, idempotency_key, entry_type, ...payload por tipo } ] }` |
| **Respuesta éxito (parcial/total)** | **207** con `created`, `skipped`, `errors` |
| **Respuesta error (batch inválido)** | **400** con mensajes de validación |
| **Idempotencia** | Por `idempotency_key` por ítem; duplicados → `skipped` |
| **Límite** | Máx. N ítems por petición (ej. 50) |
