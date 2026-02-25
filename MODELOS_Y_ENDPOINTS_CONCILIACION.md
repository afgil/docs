# Modelos y endpoints relacionados con conciliación

Listado de modelos y endpoints del backend (pana-backend) vinculados a la conciliación bancaria y configuración de conciliación automática.

---

## 1. Modelos

### 1.1. App `accounting`

| Modelo | Archivo | Descripción |
|--------|---------|-------------|
| **BankReconciliation** | `apps/accounting/app_models/bank_reconciliation.py` | Conciliación bancaria. Vincula facturas (Document) con movimientos bancarios (Movement), genera comprobante (Voucher). Campos: master_entity, documents (M2M vía BankReconciliationDocument), movements (M2M), voucher, reconciliation_date, amount_reconciled, difference_amount, status (active/reverted), notes, reconciled_by_user_id, category. |
| **BankReconciliationDocument** | `apps/accounting/app_models/bank_reconciliation_document.py` | Tabla intermedia BankReconciliation–Document. Guarda reconciled_amount y mark_as_paid por documento en conciliaciones parciales. |
| **BankReconciliationRecommendation** | `apps/accounting/app_models/bank_reconciliation_recommendation.py` | Recomendaciones de matching documento–movimiento. status (currently_recommended, automatically_applied, manually_applied, not_applied), recommendation_type (perfect_match, unperfect_match, etc.), documents (M2M), movements (M2M). |
| **BankReconciliationHistory** | `apps/accounting/app_models/bank_reconciliation_history.py` | Historial de cambios en conciliaciones (create, update, delete) para auditoría. event_type, bank_reconciliation_id, master_entity, is_automatic, etc. |
| **EntityConciliationConfiguration** | `apps/accounting/app_models/entity_conciliation_configuration.py` | Configuración de conciliación automática por entidad (OneToOne con MasterEntity). auto_reconcile_perfect_matches, auto_reconcile_imperfect_matches, keep_unmatched_amounts_reconcilable. |
| **RecommendationAttemptLog** | `apps/accounting/app_models/recommendation_attempt_log.py` | Log de intentos de generación de recomendaciones. movement, status (success/failed/no_candidates), generation_time_ms, recommendation (FK). |
| **ClientPaymentRut** | `apps/accounting/app_models/client_payment_rut.py` | RUTs desde los que se puede pagar documentos de un cliente (master_entity, client, payer). Usado en lógica de conciliación/recomendaciones. |
| **Voucher** | `apps/accounting/app_models/voucher.py` | Comprobante contable generado al conciliar (referenciado por BankReconciliation y Movement.voucher). |
| **VoucherEntry** | `apps/accounting/app_models/voucher_entry.py` | Líneas del comprobante contable. |
| **MovementCategory** | `apps/accounting/app_models/movement_category.py` | Categoría de movimiento; BankReconciliation puede tener category. |

### 1.2. App `banking`

| Modelo | Archivo | Descripción |
|--------|---------|-------------|
| **Movement** | `apps/banking/app_models/movement.py` | Movimiento bancario (Fintoc). Campos relevantes para conciliación: `reconciled` (Boolean), `voucher` (FK a accounting.Voucher). |

---

## 2. Endpoints

Base URL API: `/api/`.

### 2.1. Accounting – conciliación y configuración

Prefijo: **`api/accounting/`**

| Método | Ruta | Vista / ViewSet | Descripción |
|--------|------|------------------|-------------|
| GET    | `bank-reconciliations/` | BankReconciliationViewSet | Lista conciliaciones (filtros: status, reconciliation_date, reconciled_by_user_id). |
| POST   | `bank-reconciliations/` | BankReconciliationViewSet | Crear conciliación. |
| GET    | `bank-reconciliations/<id>/` | BankReconciliationViewSet | Detalle conciliación. |
| PUT/PATCH | `bank-reconciliations/<id>/` | BankReconciliationViewSet | Actualizar conciliación. |
| DELETE | `bank-reconciliations/<id>/` | BankReconciliationViewSet | Eliminar (revertir) conciliación. |
| GET    | `bank-reconciliations/pending/` | BankReconciliationViewSet (action) | Pendientes. |
| GET    | `bank-reconciliations/reconciled/` | BankReconciliationViewSet (action) | Conciliadas. |
| GET    | `bank-reconciliations/suggestions/` | BankReconciliationViewSet (action) | Sugerencias de conciliación. |
| GET    | `bank-reconciliations/suggestions_summary/` | BankReconciliationViewSet (action) | Resumen de sugerencias. |
| POST   | `bank-reconciliations/<id>/revert/` | BankReconciliationViewSet (action) | Revertir conciliación. |
| GET    | `bank-reconciliations/summary/` | BankReconciliationViewSet (action) | Resumen. |
| GET    | `bank-reconciliations/receivable_documents/` | BankReconciliationViewSet (action) | Documentos por cobrar. |
| POST   | `bank-reconciliations/bulk_reconcile/` | BankReconciliationViewSet (action) | Conciliación masiva. |
| GET    | `bank-reconciliations/recommendations_by_movements/` | BankReconciliationViewSet (action) | Recomendaciones por movimientos. |
| GET    | `bank-reconciliations/recommendations_grouped_by_rut/` | BankReconciliationViewSet (action) | Recomendaciones agrupadas por RUT. |
| GET    | `bank-reconciliations/history/` | BankReconciliationViewSet (action) | Historial de conciliaciones. |
| POST   | `reconcile/` | reconcile_invoice_with_movement | Concilia una factura con un movimiento (crea voucher, marca factura pagada y movimiento reconciliado). |
| POST   | `reconcile/bulk/` | bulk_reconcile | Conciliación en lote. |
| GET    | `master-entities/<int:master_entity_id>/conciliation-configuration/` | EntityConciliationConfigurationViewSet | Obtener configuración de conciliación de la entidad. |
| PUT    | `master-entities/<int:master_entity_id>/conciliation-configuration/` | EntityConciliationConfigurationViewSet | Actualizar configuración de conciliación. |
| GET    | `master-entities/<int:master_entity_id>/bank-reconciliations/export-excel/` | BankReconciliationExcelExportView | Exportar conciliaciones a Excel. |

### 2.2. Banking – movimientos (filtro conciliado)

Prefijo: **`api/banking/`**

| Método | Ruta | Vista | Descripción |
|--------|------|-------|-------------|
| GET    | `master-entities/<int:master_entity_id>/movements/` | MovementListView | Lista movimientos. Query param **`reconciled`** (true/false) para filtrar por conciliado. |
| GET    | `master-entities/<int:master_entity_id>/movements/export-excel/` | MovementExcelExportView | Exportar movimientos a Excel; acepta filtro **`reconciled`**. |

### 2.3. Master entities – configuración de entidad (incluye conciliación)

Prefijo: **`api/`** (master_entities.urls)

| Método | Ruta | Vista | Descripción |
|--------|------|-------|-------------|
| GET    | `master-entities/<int:pk>/configurations/` | MasterEntityConfigurationView | Obtiene configuración de la entidad; incluye bloque **conciliation** (auto_reconcile_perfect_matches, auto_reconcile_imperfect_matches, keep_unmatched_amounts_reconcilable). |
| PUT/PATCH | `master-entities/<int:pk>/configurations/` | MasterEntityConfigurationView | Actualiza configuración; se puede enviar **conciliation** en el body para actualizar EntityConciliationConfiguration. |

---

## 3. Servicios y tareas relacionadas

| Ubicación | Nombre | Descripción |
|-----------|--------|-------------|
| `apps/accounting/services/` | ReconciliationRecommendationService | Generación de recomendaciones de conciliación. |
| `apps/accounting/services/` | ReconciliationRecommendationTaskService | Tarea de recomendaciones. |
| `apps/accounting/services/` | ReconciliationSqlService | Lógica SQL para conciliación. |
| `apps/banking/services/` | ReconciliationSuggestionsService | Sugerencias de conciliación (usado en BankReconciliationViewSet). |
| `apps/banking/tasks.py` | link_unreconciled_movements_by_tax_id_number | Tarea Celery: vincula movimientos no conciliados por RUT. |
| `apps/banking/management/commands/` | link_unreconciled_movements_by_tax_id_number | Comando management equivalente. |
| `apps/banking/management/commands/` | generate_reconciliation_recommendations_sql | Genera recomendaciones de conciliación vía SQL. |

---

## 4. Tests relacionados

- `apps.accounting.tests.unit.test_reconciliation_views`
- `apps.accounting.tests.unit.test_auto_reconciliation_configuration`
- `apps.accounting.tests.unit.test_partial_reconciliation`
- `apps.accounting.tests.unit.test_reconciliation_recommendation_service`
- `apps.accounting.tests.unit.test_reconciliation_recommendation_task_service`
- `apps.accounting.tests.unit.test_reconciliation_sql_service`
- `apps.accounting.tests.unit.test_reconciliation_with_credit_debit_notes`
- `apps.accounting.tests.integration.test_reconciliation_edit_delete`
- `apps.accounting.tests.test_bank_reconciliation_views`
- `apps.banking.tests.unit.test_movement_reconciled_filter`
- `apps.banking.tests.unit.test_link_unreconciled_movements_command`
