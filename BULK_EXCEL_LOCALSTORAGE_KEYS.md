# Claves localStorage – flujo Excel / emisión masiva

Lista ordenada de las variables de localStorage usadas en el flujo de carga Excel → previsualización → firma → batch. Las no usadas fueron eliminadas.

## Claves (orden)

| Clave | Constante | Dónde se usa |
|-------|-----------|--------------|
| `bulk_invoice_documents` | `BulkExcelStorageKeys.BULK_DOCUMENTS` | **SET:** BulkInvoiceDraft (al cargar desde upload, al guardar uno, al guardar masivo, al eliminar), GoogleSheetsImportHandlers. **GET:** BulkInvoiceDraft (Continuar a emisión, bulk save), BulkInvoiceCreation (handleSignAndIssue, conteo en firma), Header (handleContinueToEmission). |
| `bulkBatchData` | `BulkExcelStorageKeys.BULK_BATCH_DATA` | **SET:** BulkInvoiceCreation (tras crear el batch). **GET:** BulkInvoiceDraft (confirmDelete, para sincronizar), EditInvoiceModal (tras editar un documento). |
| `currentBatchState` | `BulkExcelStorageKeys.CURRENT_BATCH_STATE` | **SET:** BulkInvoiceCreation, processing.tsx, sign-certificate.tsx. **GET:** sign.tsx, processing.tsx. **REMOVE:** Platform, multi-invoice-wizard, BatchDocumentsPage, PurchaseOrderWizard. |
| `invoiceMultiDraft` | `BulkExcelStorageKeys.INVOICE_MULTI_DRAFT` | **SET:** BulkInvoiceDraft (al eliminar), EditInvoiceModal, multi-invoice-wizard. **GET:** BulkInvoiceDraft (confirmDelete), EditInvoiceModal, multi-invoice-wizard. **REMOVE:** DocumentsHeader, Platform, multi-invoice-wizard. |

## Claves eliminadas (no se leían)

- `bulkInvoicePreviewState` – solo se hacía `removeItem`, nunca `getItem`.
- `bulkInvoiceProcessedDocuments` – solo `setItem` y `removeItem`, nunca `getItem`.
- `bulk_invoice_documents_timestamp` – solo `setItem` en GoogleSheetsImportHandlers, nunca `getItem`.

## Transformaciones

- **Upload response → localStorage:** `UploadToStorageTransformer.transform(data.documents)` → se guarda en `BULK_DOCUMENTS`.
- **localStorage → request batch:** se lee `BULK_DOCUMENTS`, se filtran documentos completos con `isDocumentComplete`, luego `StorageToBatchTransformer.transform(validDocuments)` → body de `POST /documents/batch/`.

## Emisión y atrás

- **Emisión:** En firma se obtienen documentos de `location.state.documents` o de `BULK_DOCUMENTS`, se filtran, se transforman con `StorageToBatchTransformer` y se envía `POST /documents/batch/`.
- **Atrás:** `handleBack` en BulkInvoiceCreation: desde `bulk-invoice-signature` → `bulk-invoice-preview`, desde `bulk-invoice-preview` → `bulk-invoice-excel`. No se borran claves al volver; los datos siguen en `BULK_DOCUMENTS` para poder continuar a emisión de nuevo.
