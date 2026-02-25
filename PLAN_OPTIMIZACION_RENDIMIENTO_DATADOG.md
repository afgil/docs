# Plan de Optimización de Rendimiento (Datadog APM)

**Fecha:** Febrero 2026  
**Fuente:** Datadog API Spans, 21.000 spans (última semana)  
**Servicio:** pana-backend  
**Scripts:** `scripts/fetch_datadog_spans_all.sh`, `scripts/analisis_datadog_apm.sh`

---

## 1. Top por impacto (hits × avg_duration)

| hits | avg ms | max ms | impact | resource |
|------|--------|--------|--------|----------|
| **568** | **9022** | **48029** | 5.124.528 | **GET /v1/documents/{num}** |
| 340 | 2901 | 20993 | 986.207 | GET /api/master-entities/{num}/configurations/ |
| **317** | **2570** | **27363** | 814.576 | **GET /api/auth/profile/** |
| 363 | 2131 | 21020 | 773.416 | GET /api/master-entities/{num}/credentials/ |
| 106 | 4348 | 22286 | 460.939 | GET /api/master-entities/{num}/customers/ |
| 220 | 1583 | 16800 | 348.153 | GET /api/master-entities/{num}/documents/ |
| 174 | 1742 | 15040 | 303.123 | GET /api/master-entities/{num}/sii-company-credentials/ |
| 147 | 1967 | 20487 | 289.159 | GET /api/master-entities/{num}/customers-configuration/{num} |
| 474 | 521 | 3494 | 246.873 | GET /api/documents/batch/{guid}/ |
| 1029 | 148 | 4274 | 152.756 | GET /v1/documents |
| 1032 | 147 | 3623 | 151.260 | GET /v1/master-entities |

---

## 2. Top por hits (más llamados)

| hits | resource |
|------|----------|
| 1032 | GET /v1/master-entities |
| 1029 | GET /v1/documents |
| 786 | GET /api/activities/ |
| 568 | GET /v1/documents/{num} |
| 474 | POST /api/banking/fintoc/webhook/ |
| 474 | GET /api/documents/batch/{guid}/ |
| 441 | GET /api/searchs/history/ |
| 363 | GET /api/master-entities/{num}/credentials/ |
| 340 | GET /api/master-entities/{num}/configurations/ |
| 317 | GET /api/auth/profile/ |
| 310 | POST /api/auth/track-session/ |

---

## 3. Top por latencia máxima (p95 proxy)

| hits | max ms | resource |
|------|--------|----------|
| 568 | **48029** | GET /v1/documents/{num} |
| 317 | **27363** | GET /api/auth/profile/ |
| 363 | 21020 | GET credentials |
| 340 | 20993 | GET configurations |
| 106 | 22286 | GET customers |
| 220 | 16800 | GET documents |
| 118 | 10440 | GET /api/v1/dashboard/summary/ |

---

## 4. Prioridad de optimización

### Crítico (impacto + latencia)

1. **GET /v1/documents/{num}** – 568 hits, avg 9 s, max 48 s. Impacto máximo.
2. **GET /api/auth/profile/** – 317 hits, avg 2.5 s, max 27 s. Llamado en cada sesión.
3. **GET /api/master-entities/{num}/configurations/** – 340 hits, avg 2.9 s.
4. **GET /api/master-entities/{num}/credentials/** – 363 hits, avg 2.1 s.

### Alto (muchos hits, latencia moderada)

5. **GET /v1/documents** y **GET /v1/master-entities** – ~1.030 hits cada uno, avg ~147 ms.
6. **GET /api/master-entities/{num}/documents/** – 220 hits, avg 1.6 s.
7. **GET /api/master-entities/{num}/sii-company-credentials/** – 174 hits, avg 1.7 s.
8. **GET /api/documents/batch/{guid}/** – 474 hits, avg 521 ms.

### Medio

9. **GET /api/v1/dashboard/summary/** – 118 hits, max 10 s.
10. **POST /api/banking/fintoc/webhook/** – 474 hits, max 7 s.

---

## 5. Plan de actuación

| Problema | Acción |
|----------|--------|
| **N+1** | Revisar QuerySets: `select_related()`, `prefetch_related()` en listados y serializers. |
| **Queries lentas** | Índices en modelos; `only()`/`defer()`; agregaciones en DB. |
| **auth/profile** | Caché Redis (perfil por user_id); revisar queries asociadas. |
| **v1/documents/{num}** | Trace Explorer → identificar span DB; optimizar serializer/queryset. |
| **configurations / credentials** | Evitar N+1; prefetch relacionadas; evaluar caché. |
| **Endpoints muy llamados** | Paginación; caché idempotente; límite de página. |

---

## 6. Candidatos por código

| Área | Archivo / vista | Traces asociados |
|------|------------------|------------------|
| Auth | `auth_views` | GET /api/auth/profile/ |
| Documentos | `document_filters`, `document_views` | GET /v1/documents, GET /v1/documents/{num} |
| Master entities | `master_entity_views` | /configurations, /credentials, /documents, /customers |
| Batches | `batch_views` | GET /api/documents/batch/{guid}/ |
| Dashboard | `dashboard` | GET /api/v1/dashboard/summary/ |

---

## 7. Requests a documents: qué argumentos más afectan

Investigación en código (vistas, serializers, `DocumentXMLPDFService`) para los endpoints que aparecen en el top de impacto.

### 7.1 GET /v1/documents/{document_id}/ (mayor impacto: 568 hits, avg 9 s, max 48 s)

**Vista:** `DocumentDetailAPIView` (`apps/documents/app_views/document_detail_view.py`).  
**Argumentos (query params) que disparan trabajo costoso:**

| Query param | Efecto | Coste relativo |
|-------------|--------|-----------------|
| **`pdf_file=true`** | El serializer devuelve el PDF en **base64** (`get_preview_pdf()` + codificación). Sin este param se usan URLs presignadas. | **Muy alto** (generar PDF + base64 en respuesta). |
| **`file_type=PDF`** | `DocumentXMLPDFService.process_xml_and_pdf(process_pdf=True)` → `document.get_or_scrape_pdf()` (S3 o scrape SII). | **Alto** (I/O PDF, posible scrape). |
| **`file_type=XML`** | Se procesa solo XML → `get_or_scrape_xml()`. | **Alto** (scrape/consulta XML). |
| **`folio`** (cualquier valor) | Se procesan **XML y PDF**: `process_xml=True`, `process_pdf=True`. | **Muy alto** (ambos flujos). |
| **`include_pdf=true`** | `should_process_pdf` → True → se ejecuta `get_or_scrape_pdf()`. | **Alto**. |
| *(sin params)* | Por defecto la vista procesa **PDF** (`should_process_pdf` devuelve True). XML se procesa salvo que `file_type=PDF` o `pdf_file=true`. | **Alto** (siempre PDF; a veces también XML). |

**Conclusión:** Las peticiones que más daño hacen son las que piden **PDF embebido** (`pdf_file=true`) o **folio** (XML+PDF). Las que solo piden metadatos sin `file_type`/`folio`/`include_pdf` igualmente ejecutan `process_xml_and_pdf` con PDF (y a veces XML).

**Recomendación:** En Trace Explorer / Datadog, filtrar por `GET /v1/documents/` y agrupar o segmentar por **query string** (o por `resource_name` si incluye query) para ver % de requests con `pdf_file=true`, `folio`, `file_type=PDF`, etc. Priorizar: evitar `pdf_file=true` en listados o detalles que no necesiten PDF inline; usar `file_type=XML` solo cuando haga falta XML; y/o hacer el procesamiento de PDF/XML bajo demanda (endpoint separado o param explícito) en lugar de por defecto.

---

### 7.2 GET /v1/documents (listado; 1029 hits, avg 148 ms)

**Vista:** `DocumentListCreateView`. Menor impacto que el detalle; los picos (max 4274 ms) suelen venir de **paginación grande** o **filtros** que disparan muchas queries. Revisar en traces: filtros por `master_entity`, `date`, `dte_type`, `page_size`.

---

### 7.3 GET /api/documents/batch/{guid}/ (474 hits, avg 521 ms, max 3494 ms)

**Vista:** `batch_views` (detalle de batch). El argumento es el **guid** del batch. La latencia depende del tamaño del batch (número de documentos) y del serializer que carga relaciones. Revisar N+1 en documentos del batch y uso de `select_related`/`prefetch_related`.

---

### 7.4 GET /api/master-entities/{id}/documents/ (220 hits, avg 1,6 s, max 16,8 s)

**Argumento de ruta:** `master_entity_id`. Los query params típicos (filtros por fecha, tipo DTE, estado, búsqueda) pueden provocar queries pesadas o N+1. Revisar en Datadog los spans de DB para este endpoint y comprobar si hay prefetch de `details`, `references`, `sender`, `receiver`.

---

### 7.5 Argumentos más usados según Datadog (master_entity_id en span, excluido al agregar)

Para ver **desde Datadog** qué argumentos (query params) se usan más y más impactan, **sin segmentar por empresa**:

1. **Tag en el span:** En `apps/core/utils/datadog/span_modifier.py` se setea el tag `http.query_params` con el query string **completo** (incluye `master_entity_id` para trazabilidad por empresa en Datadog). Solo se excluyen params sensibles (password, token, etc.).

2. **Script de análisis:** Ejecutar desde el backend:
   ```bash
   # Con archivo JSON de spans (si tienes fetch_datadog_spans_all.sh)
   python scripts/analisis_datadog_documentos_argumentos.py --file scripts/datadog_spans_all.json

   # Consultando la API de Datadog (últimos 7 días)
   DD_API_KEY=xxx DD_APP_KEY=xxx python scripts/analisis_datadog_documentos_argumentos.py --api --pages 10
   ```
   El script filtra spans de endpoints de documentos, normaliza el resource (reemplaza IDs por `{num}`/`{guid}`), agrupa por (resource pattern, query params) y muestra **top por impacto** (hits × avg_duration) y **top por hits**. Al agregar, **excluye** `master_entity_id`, `entity_id`, `company_id` para no segmentar por empresa (pero esos params SÍ están en el span de Datadog para filtrar/debuggear).

3. **Si aún no hay tag en los datos:** Tras desplegar el cambio del span_modifier, los nuevos spans tendrán `http.query_params`. Vuelve a ejecutar el script con `--api` o con un JSON reciente para ver qué argumentos afectan más en producción.

---

## 8. Uso de scripts

```bash
# Obtener todos los spans (última semana, máx 50 páginas)
./scripts/fetch_datadog_spans_all.sh 7 scripts/datadog_spans_all.json 50

# Analizar agregados (top recursos por impacto)
jq -r '.data[] | select(.attributes.resource_name | test("^GET /api|^POST /api|^GET /v1|^POST /v1")) | [.attributes.resource_name, ((.attributes.custom.duration//0)/1000000)] | @tsv' scripts/datadog_spans_all.json | awk -F'\t' '{r=$1;d=$2+0;c[r]++;s[r]+=d;if(d>m[r])m[r]=d}END{for(r in c)printf "%d\t%.0f\t%.0f\t%s\n",c[r],s[r]/c[r],m[r],r}' | sort -t$'\t' -k2 -nr

# Argumentos más usados en endpoints de documentos (excl. master_entity_id)
python scripts/analisis_datadog_documentos_argumentos.py --file scripts/datadog_spans_all.json
# o contra la API:
python scripts/analisis_datadog_documentos_argumentos.py --api --pages 10
```
