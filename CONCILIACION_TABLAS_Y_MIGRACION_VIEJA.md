# Conciliación bancaria: tablas y migración de datos vieja → nueva

## Tablas que vinculan la conciliación

### Modelo viejo (movimientos directos)

- **`banking.Movement`**
  - `reconciled` (boolean): indica si el movimiento fue conciliado.
  - `voucher_id`: comprobante contable de la conciliación.
- **`accounting.BankReconciliation`**
  - `movements` (M2M): movimientos bancarios conciliados.
  - `documents` (M2M via BankReconciliationDocument): facturas/documentos conciliados.
  - Antes no tenía `payment_document`; al guardar se marcaba cada `Movement` con `reconciled=True`.

### Modelo nuevo (documento de pago tipo 100)

- **`documents.Document`** (dte_type code 100): documento de pago (uno por movimiento de ingreso, creado desde Fintoc o manual).
- **`documents.DocumentPaymentMetadata`**
  - `document_id` (OneToOne con Document 100).
  - `movement_id` (FK opcional a `banking.Movement`): movimiento origen cuando viene de Fintoc.
  - **`reconciliation_status`**: `unmatched` | `suggested` | `reconciled` | `cleaned`. **Este campo es el que usa la pantalla “movimientos por conciliar”**: se listan Document 100 con `reconciliation_status = 'unmatched'`.
- **`accounting.BankReconciliation`**
  - `payment_document_id` (FK opcional a Document 100): documento de pago asociado (1 pago → N facturas).
  - Sigue existiendo `movements` (M2M). Al guardar una conciliación con `payment_document`, se actualiza `DocumentPaymentMetadata.reconciliation_status = 'reconciled'` para ese documento.

## Qué tabla define “está conciliado” en cada flujo

- **Viejo:** `Movement.reconciled == True`.
- **Nuevo (pantalla conciliación por pagos):** `DocumentPaymentMetadata.reconciliation_status == 'reconciled'` (o `'cleaned'`; lo que no está conciliado es `'unmatched'`).

## Por qué todo aparece como “por conciliar”

Si se crearon Document 100 para movimientos que **ya** estaban conciliados (p. ej. con `ensure_payment_documents_for_income_movements`), esos documentos se crean con `reconciliation_status = 'unmatched'` por defecto. El sistema viejo solo tenía `Movement.reconciled = True`; no se actualizó la metadata del Document 100.

## Migración: vieja → nueva

Script: **`scripts/migrate_reconciled_movements_to_payment_metadata.py`**

Hace:

- Para cada `DocumentPaymentMetadata` con `movement_id` no nulo y cuyo `Movement` tiene `reconciled=True`, pone `reconciliation_status = 'reconciled'`.

Así, los movimientos que ya estaban conciliados en el modelo viejo dejan de aparecer en “movimientos por conciliar”.

**Ejecución:**

```bash
source env/bin/activate
python scripts/migrate_reconciled_movements_to_payment_metadata.py
```

O desde Django shell:

```bash
python manage.py shell < scripts/migrate_reconciled_movements_to_payment_metadata.py
```
