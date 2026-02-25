# Optimización de endpoints de emisiones masivas (batch)

Resumen de optimizaciones aplicadas a los endpoints asociados a emisiones masivas de documentos.

## Endpoints afectados

- **GET/POST/PATCH/DELETE** `v1/documents/batch/`, `v1/documents/batch/<uuid>/`
- **GET** `v1/documents/batch/<uuid>/clients/`
- **PATCH** `v1/documents/batch` (edición masiva de `payment_status` / `reconciliation_status`)

## Cambios realizados

### 1. DELETE batch: eliminación de DocumentIssueTry sin N+1

**Antes:** Por cada `BatchDocument` del batch se ejecutaba una query para contar y otra para eliminar los `DocumentIssueTry` asociados (2N queries).

**Después:** Una sola query para contar y una para eliminar todos los `DocumentIssueTry` del batch:

- `DocumentIssueTry.objects.filter(batch_document__batch_id=batch.id).count()`
- `DocumentIssueTry.objects.filter(batch_document__batch_id=batch.id).delete()`

**Archivo:** `apps/documents/app_views/batch_views.py` (método `delete`).

### 2. PATCH masivo (payment_status / reconciliation_status): una query para documentos

**Antes:** Por cada `id` en `ids` se hacía `Document.objects.filter(pk=doc_id).select_related(...).first()` (N queries).

**Después:** Una sola query para todos los documentos y un diccionario en memoria:

- `Document.objects.filter(pk__in=ids).select_related("document_total", "dte_type", "payment_metadata", "sender")`
- `documents_by_id = {doc.id: doc for doc in documents_qs}`
- En el bucle se usa `documents_by_id.get(doc_id)`.

`user_entity_ids` ya se calculaba una sola vez para usuarios no staff.

**Archivo:** `apps/documents/app_serializers/document_batch_patch_serializer.py` (método `save`).

### 3. GET batch clients: comprobar existencia sin cargar el batch

**Antes:** `DocumentBatch.objects.get(id=batch_id)` cargaba el objeto completo solo para comprobar existencia.

**Después:** `DocumentBatch.objects.filter(id=batch_id).exists()` y, si no existe, se lanza `DocumentBatch.DoesNotExist` (misma excepción que antes para el `except`).

**Archivo:** `apps/documents/app_views/batch_views.py` (método `get_clients`).

## Optimizaciones ya presentes

- **Listado de batches:** `DocumentBatchListSerializer.setup_eager_loading()` aplica `select_related("created_by")`, `Prefetch("batch_documents", ...)` y anotaciones para evitar N+1 en la lista.
- **Detalle de batch:** `DocumentBatchDetailSerializer.setup_eager_loading()` aplica prefetch de `batch_documents` con `document` (dte_type, sender, receiver, export_details, details).
- **Document.by_ids:** El queryset usado en respuestas de batch ya usa `select_related` y `prefetch_related` para documentos por IDs.

### 4. Índices en DocumentBatch (modelo Django)

**Definidos en el modelo** con `Meta.indexes` (sin SQL en migraciones):

- `docbatch_status_idx`: `status` (filtros por estado).
- `docbatch_created_idx`: `-created_at` (orden por defecto del listado).
- `docbatch_status_created_idx`: `(status, -created_at)` (filtro por estado + orden por fecha).

**Archivo:** `apps/documents/app_models/batch_models.py` (clase `DocumentBatch`, `Meta.indexes`).  
**Migración:** `apps/documents/migrations/0151_add_document_batch_indexes.py` (generada con `makemigrations`).

## Posibles mejoras futuras

- En PATCH masivo, reducir múltiples `DocumentStatus.objects.get_or_create(document=document)` mediante una carga previa de `DocumentStatus` por `document_id` y creación en lote de los faltantes (requiere revisar bien el flujo y tests).
