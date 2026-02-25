# Optimización query listado de documentos (documents_v2)

**Fecha:** 2026-02-16  
**Endpoint:** `GET /api/master-entities/{id}/documents_v2/`  
**Vista:** `DocumentManageView.get()` (listado sin `document_id`)

---

## 1. Análisis Datadog (última hora)

Se consultó la API de Datadog Logs (v2) para la última hora con filtro `documents` / `documents_v2`.

### Requests observados (muestra)

- `GET /api/master-entities/615813/documents/?page=1&page_size=25` → 200 (35KB)
- Varios `GET .../documents_v2/` y `.../scheduled-documents/` (OPTIONS, GET, 200/401)

Los logs disponibles en el entorno actual no exponen atributo de duración (`@duration`) en el mensaje; la duración suele verse en **APM Traces** (Trace Explorer en Datadog). Para identificar los requests más lentos por duración se recomienda:

1. En Datadog: **APM → Trace Explorer**
2. Filtro: `service:pana-backend` y `resource_name:*documents_v2*` (o `*documents*`)
3. Ordenar por duración y revisar parámetros en los spans (query params, `master_entity_id`, `page`, `limit`, `ordering`, `document_type`, `dte_type`, `search`, `available_for_cession`).

### Parámetros típicos del listado

| Parámetro               | Uso |
|-------------------------|-----|
| `page`, `limit`         | Paginación (default `limit=100`) |
| `ordering`              | `-date_issued`, `date_issued`, `folio`, `-folio`, `dte_type__code,-date_issued` |
| `document_type`         | `issued` \| `received` |
| `dte_type`, `dte_type__code__in`, `dte_types` | Filtro por tipo(s) DTE |
| `receiver_id`           | Filtro por receptor |
| `search`                | Búsqueda (SmartSearchQueryBuilder) |
| `available_for_cession` | `true` → filtros y anotaciones extra (TraceEvent, DocumentCession) |
| `include_pdf`           | Compatibilidad (sin efecto actual en listado) |
| `folio`                 | Filtro por folio |

---

## 2. Ineficiencias detectadas en código

### 2.1 N+1 en `DocumentCreateSerializer.get_parity()` (crítico)

**Ubicación:** `apps/documents/serializers_refactor.py` – `DocumentCreateSerializer.get_parity()`

Para **cada** documento del listado se ejecutaban:

- `obj.parities_as_source.select_related(...).all()` → 1 query
- `obj.parities_as_target.select_related(...).all()` → 1 query

Con `limit=100` → **200 queries extra** solo por parity.

**Solución aplicada:** En la vista de listado se añadió:

- `Prefetch("parities_as_source", queryset=DocumentParity.objects.select_related("target_document", "target_document__dte_type"))`
- `Prefetch("parities_as_target", queryset=DocumentParity.objects.select_related("source_document", "source_document__dte_type"))`

Así, al serializar, `get_parity()` usa la caché de prefetch y no dispara queries.

### 2.2 N+1 en referencias (`reference_type`)

**Ubicación:** `DocumentReferenceSerializer.to_representation()` usa `instance.reference_type.code`.

El listado hacía `prefetch_related("references")` pero sin `select_related("reference_type")` en el queryset de referencias, por lo que por cada referencia se hacía 1 query al acceder a `reference_type`.

**Solución aplicada:** Prefetch de referencias con:

- `Prefetch("references", queryset=DocumentReference.objects.select_related("reference_type"))`

### 2.3 Otras consideraciones (sin cambio en esta iteración)

- **`total_count = queryset.count()`:** Un `COUNT(*)` sobre el queryset filtrado; en tablas muy grandes puede ser costoso. Opciones futuras: contar solo hasta un tope o usar estimación según necesidad de producto.
- **`available_for_cession == "true"`:**
  - Dos consultas auxiliares (`TraceEvent`, `DocumentCession`) con `values_list(..., flat=True).distinct()` ya están acotadas.
  - `exclude(id__in=rejected_doc_ids)` con listas muy grandes podría sustituirse por subquery si se observa lentitud.
- **Ordenamiento por folio:** El orden `ordering=folio` / `-folio` usa anotaciones con `Case/When` y `regex`; en conjuntos grandes puede ser pesado. Valorar índices o expresiones más simples si se prioriza rendimiento.

---

## 3. Cambios realizados en código

**Archivo:** `apps/documents/app_views/documents.py`

1. Import de `Prefetch` (`django.db.models`) y de `DocumentParity`, `DocumentReference` desde `apps.documents.app_models`.
2. En el listado (rama sin `document_id`), construcción del queryset con:
   - `prefetch_references` = `Prefetch("references", queryset=DocumentReference.objects.select_related("reference_type"))`
   - `prefetch_parities_source` = `Prefetch("parities_as_source", queryset=DocumentParity.objects.select_related("target_document", "target_document__dte_type"))`
   - `prefetch_parities_target` = `Prefetch("parities_as_target", queryset=DocumentParity.objects.select_related("source_document", "source_document__dte_type"))`
   - `prefetch_related(prefetch_references, prefetch_parities_source, prefetch_parities_target, "traces__events")` en lugar de `prefetch_related("references", "traces__events")`.

---

## 4. Impacto esperado

- **Antes:** 1 query principal + 1 prefetch references + 1 prefetch traces__events + **2×N** queries por parity + **M** queries por reference_type (M = total de referencias en la página).
- **Después:** 1 query principal + 4 prefetches (references con reference_type, parities_as_source, parities_as_target, traces__events); sin queries extra en `get_parity()` ni en `DocumentReferenceSerializer.to_representation()` para la página actual.

Reducción fuerte del número de queries en listados típicos (p. ej. 100 documentos con varias referencias y paridades).

---

## 5. Cómo seguir analizando en Datadog

1. **Logs:**  
   `POST https://api.datadoghq.com/api/v2/logs/events/search`  
   Filtro: `service:pana-backend`, query con `*documents*` o `*documents_v2*`, `from`: `now-1h`, `to`: `now`.

2. **APM (recomendado para lentitud):**  
   Trace Explorer → filtro por `service:pana-backend` y por `resource_name` o URL que contenga `documents_v2` → ordenar por duración y revisar parámetros en los spans.

3. **Credenciales:** usar `DD-API-KEY` y `DD-APPLICATION-KEY` (no versionar en código).
