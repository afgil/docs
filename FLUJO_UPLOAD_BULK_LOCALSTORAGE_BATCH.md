# Flujo: Upload → localStorage → Batch (emisión masiva)

Documentos del upload → `bulk_invoice_documents` → firma → `POST /documents/batch/`. Claves: ver `BULK_EXCEL_LOCALSTORAGE_KEYS.md`.

---

## 1. Upload

- **Origen:** `ExcelUpload.tsx` → `handlePreview()`.
- **Endpoint:** `POST /api/master-entities/{id}/documents/upload-v4/`.
- **Respuesta:** `{ success, documents_created, documents: [...], message, past_emission_dates_count?, ... }`.

Tras éxito: `navigate('/platform/bulk-invoice-preview', { state: { documents, documentsCreated, message, past_emission_dates_count } })`. No se escribe en localStorage.

---

## 2. localStorage (preview)

- **Componente:** `BulkInvoiceDraft.tsx` en `/platform/bulk-invoice-preview`.
- Lee `location.state?.documents`, procesa con `UploadToStorageTransformer.transform(...)` y guarda en `BulkExcelStorageKeys.BULK_DOCUMENTS`.
- Se actualiza también al guardar un documento (modal), al guardado masivo y al eliminar.

---

## 3. Continuar a emisión

- Usuario clic en «Continuar a emisión» → `handleContinueToEmission()` lee `BulkExcelStorageKeys.BULK_DOCUMENTS` y navega a `/platform/bulk-invoice-signature` con `state: { documents, documentsCount, useInvoiceSignature: true }`.

---

## 4. Envío al batch

- En `BulkInvoiceCreation.handleSignAndIssue()`: documentos desde `location.state?.documents` o, si faltan, desde `BulkExcelStorageKeys.BULK_DOCUMENTS`. Se filtran con `isDocumentComplete`, se convierten con `new StorageToBatchTransformer().transform(validDocuments)` y se envía `POST /documents/batch/` con `{ documents, state: "issued", from_excel: true }`. Con `batch_id` se guardan `bulkBatchData` y `currentBatchState` y se navega a `processing/{batch_id}`.
