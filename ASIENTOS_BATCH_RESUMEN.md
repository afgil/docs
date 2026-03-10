# Resumen: Todo llama a accounting entries batch

## Objetivo

Unificar todos los flujos de creación de asientos de limpieza/conciliación para que pasen por el **endpoint batch** `POST /accounting/accounting-entries/batch/` (o por la misma lógica compartida en backend).

## Cambios realizados

### 1. Frontend: `cleanPaymentDocuments`

- **Antes:** Llamaba N veces a `POST /accounting/accounting-entries/` (un asiento por pago) o una vez con un asiento de muchas líneas si `singleEntry`.
- **Ahora:** Construye un array `entries` (1 o N elementos, mismo formato DOCUMENT_SUPPORTED_JOURNAL) y llama **una sola vez** a `createAccountingEntriesBatch` → `POST /accounting/accounting-entries/batch/`.
- **Archivo:** `pana-frontend/src/services/reconciliationService.ts`.
- **Respuesta:** Sigue devolviendo `{ updated_ids, failed? }`; si el batch devuelve `errors`, se mapean a `failed`.

### 2. Backend: `BulkCleanPaymentsView` (limpieza masiva de movimientos por conciliar)

- **Antes:** Solo obtenía IDs con `get_payment_document_ids_to_reconcile` y aplicaba el patch de documentos (reconciliation_status=CLEANED). No creaba asientos.
- **Ahora:**
  1. Obtiene **(document_id, pending_amount)** con `AccountingManager.get_payment_document_ids_and_amounts_to_reconcile` (nuevo método).
  2. Arma la lista de asientos DOCUMENT_SUPPORTED_JOURNAL (un asiento con muchas líneas si `single_entry`, o un asiento por documento).
  3. Valida con `BatchCreateAccountingEntrySerializer` y procesa con **`process_batch_entries`** (misma lógica que el endpoint batch).
  4. Parchea solo los documentos cuyos asientos se crearon/omitieron por idempotencia.
- **Archivos:** `apps/accounting/app_views/accounting_summary_views.py`, `apps/accounting/managers/accounting_manager.py` (nuevo método), `apps/accounting/services/accounting_entry_batch_service.py` (nuevo).

### 3. Backend: `BulkMarkReceivablesPaidView` (marcar CxC como pagadas)

- **Antes:** Llamaba directamente a `AccountingEntryBuilder.build_bulk_mark_receivable_paid_single_entry` y `AccountingEntryPoster.post_entry`.
- **Ahora:** Arma un único ítem de batch con `entry_type: "RECEIVABLE_BULK_CLOSE_EXCLUSIONS"` y `document_ids`, valida con `BatchCreateAccountingEntrySerializer` y llama a **`process_batch_entries`**. Luego sincroniza estado de cobranza como antes.
- **Archivo:** `apps/accounting/app_views/accounting_summary_views.py`.

### 4. API batch: soporte para RECEIVABLE_BULK_CLOSE_EXCLUSIONS

- **CreateAccountingEntrySerializer:** Se agregó `ENTRY_TYPE_RECEIVABLE_BULK_CLOSE_EXCLUSIONS` y campo `document_ids` (lista de IDs de facturas). Validación: `document_ids` obligatorio y no vacío para este tipo.
- **AccountingEntryBuilder.build_from_generic_payload:** Se agregó rama para `RECEIVABLE_BULK_CLOSE_EXCLUSIONS` que delega en `build_bulk_mark_receivable_paid_single_entry`.
- **Archivos:** `apps/accounting/app_serializers/accounting_entry_serializer.py`, `apps/accounting/services/accounting_entry_service.py`.

### 5. Servicio compartido `process_batch_entries`

- **Nuevo:** `apps/accounting/services/accounting_entry_batch_service.py` con `process_batch_entries(entries_data, user, post_after=True)`.
- Hace el mismo bucle que la vista batch: por cada entry, resuelve company, comprueba acceso, `build_from_generic_payload`, opcionalmente post, y retorna `(created_list, skipped_list, errors_list)`.
- **AccountingEntryBatchCreateView** ahora solo valida el body y llama a `process_batch_entries` en lugar de duplicar la lógica.

### 6. Manager: `get_payment_document_ids_and_amounts_to_reconcile`

- **Nuevo:** En `AccountingManager`. Devuelve lista de `(document_id, pending_amount)` para documentos tipo 100 por conciliar, con el mismo criterio que `get_payment_document_ids_to_reconcile` y montos desde saldo en cuenta BankMovementPending.

## Tests añadidos/actualizados

### Frontend (`pana-frontend/src/services/__tests__/reconciliationService.accounting.test.ts`)

- **cleanPaymentDocuments:**
  - Test actualizado: verifica que se llama a `POST /accounting/accounting-entries/batch/` con `post: true` y `entries` (un entry con varias líneas cuando `singleEntry` y varios documentos).
  - Test nuevo: cuando no es `singleEntry`, verifica que se envían varios entries en el batch con `idempotency_key` `cleaned_payment_<docId>`.

### Backend

- **Unit (`apps/accounting/tests/unit/test_generic_accounting_entry_create.py`):**
  - `test_receivable_bulk_close_exclusions_valid`: serializer acepta payload con `entry_type: RECEIVABLE_BULK_CLOSE_EXCLUSIONS` y `document_ids`.
  - `test_receivable_bulk_close_exclusions_empty_document_ids_invalid`: `document_ids` vacío es inválido.

- **Integración (`apps/accounting/tests/integration/test_accounting_entry_api.py`):**
  - **AccountingEntryBatchAPITest.test_batch_document_supported_journal_like_front_clean_payments:** Simula la llamada del front al batch con un entry DOCUMENT_SUPPORTED_JOURNAL (mismo formato que `cleanPaymentDocuments`). Comprueba 200, `created`/`skipped`/`errors`, y que el asiento creado es DOCUMENT_SUPPORTED_JOURNAL y POSTED.

## Cómo testear

- **Backend (batch + serializer + integración batch):**
  ```bash
  DJANGO_ENV=test python manage.py test apps.accounting.tests.unit.test_generic_accounting_entry_create apps.accounting.tests.integration.test_accounting_entry_api --keepdb
  ```
- **Frontend (reconciliationService accounting):**
  ```bash
  npm test -- --run src/services/__tests__/reconciliationService.accounting.test.ts
  ```

## Resumen de flujos

| Flujo | Quién llama | Cómo llega al batch |
|-------|-------------|----------------------|
| Limpieza de uno/varios pagos (modal) | Front | `cleanPaymentDocuments` → `createAccountingEntriesBatch` → `POST .../batch/` |
| Limpieza masiva de movimientos por conciliar | Front → Backend | Front llama `POST .../bulk-clean-payments/`; backend arma entries y usa `process_batch_entries` (misma lógica que el batch) y luego patch de documentos |
| Marcar CxC como pagadas (masivo) | Front → Backend | Front llama `POST .../bulk-mark-receivables-paid/`; backend arma 1 entry RECEIVABLE_BULK_CLOSE_EXCLUSIONS y usa `process_batch_entries` |

En todos los casos la creación de asientos pasa por la misma lógica (batch): ya sea por llamada directa del front al endpoint batch, o por uso interno de `process_batch_entries` en las vistas de bulk.
