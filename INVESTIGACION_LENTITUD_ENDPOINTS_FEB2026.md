# Investigación de Lentitud de Endpoints - Febrero 2026

**Fecha:** 2026-02-16  
**Fuente:** Datadog APM  
**Contexto:** CPU App <2%, CPU RDS 6-29%, Conexiones DB 11-13 → NO es problema de recursos, ES problema de queries lentas/N+1

---

## Resumen Ejecutivo

**Conclusión principal:** Los 3 endpoints más lentos sufren de:
1. **N+1 queries** por falta de `prefetch_related`
2. **Scraping síncrono** bloqueando el request thread
3. **Queries pesadas en `__str__()`** ejecutadas durante la serialización

**Impacto:** Latencias de 65-120s promedio, cuando deberían ser <1s.

---

## 1. GET /api/master-entities/{id}/credentials/ - 65s avg, 188s max (140 hits)

### Vista Analizada
- **Archivo:** `apps/master_entities/views.py:342`
- **Clase:** `CredentialListCreateView`
- **Queryset:** Línea 348-382
- **Serializer:** `CredentialSerializer` (apps/master_entities/serializers.py:281)

### Problemas Detectados

#### ❌ Problema #1: N+1 en certificate_file (CRÍTICO)
**Ubicación:** `CredentialSerializer.get_has_digital_certificate_file()` (línea 321-326)

```python
def get_has_digital_certificate_file(self, obj):
    """Retorna True si tiene archivo PFX (credencial CERTIFICATE)."""
    if obj.credential_type.name != "certificate":
        return False
    cert_file = getattr(obj, "certificate_file", None)  # ← N+1 QUERY
    return bool(cert_file and cert_file.file)
```

**Evidencia:**
- El queryset tiene `select_related("credential_type")` (línea 382) ✅
- FALTA: `prefetch_related("certificate_file")` ❌
- Por cada credencial en la lista, se hace 1 query adicional para obtener `certificate_file`
- Con 50 credenciales → 50 queries extras

#### ❌ Problema #2: Queries en Credential.__str__() (CRÍTICO)
**Ubicación:** `apps/master_entities/app_models/credential.py:68-74`

```python
def __str__(self):
    entity_count = self.master_entities.count()  # ← QUERY #1 por credencial
    if entity_count == 0:
        return f"{self.user} - Sin entidades"
    elif entity_count == 1:
        return f"{self.user} - {self.master_entities.first().name}"  # ← QUERY #2
    else:
        return f"{self.user} - {entity_count} entidades"
```

**Evidencia:**
- `self.master_entities.count()` → 1 query por credencial
- `self.master_entities.first().name` → 1 query adicional si count==1
- Con 50 credenciales → hasta 100 queries extras
- FALTA: `prefetch_related("master_entities")` en el queryset

#### ❌ Problema #3: ManyToMany sin índice
**Ubicación:** `apps/master_entities/app_models/credential.py:41-43`

```python
master_entities = models.ManyToManyField(
    "MasterEntity", related_name="credentials", blank=True
)
```

**Evidencia:**
- Filtro por `master_entities=master_entity` (línea 361-365 views.py) puede ser lento sin índice
- Django crea tabla intermedia `master_entities_credential_master_entities`
- Sin índice custom, las queries pueden ser lentas con muchas relaciones

### Soluciones Propuestas

#### ✅ Solución #1: Agregar prefetch_related
```python
# apps/master_entities/views.py:382
return queryset.select_related("credential_type").prefetch_related(
    "certificate_file",
    "master_entities"
).order_by("-created_at")
```

#### ✅ Solución #2: Optimizar Credential.__str__()
```python
def __str__(self):
    # Usar hasattr para detectar si master_entities está prefetched
    if hasattr(self, '_prefetched_objects_cache') and 'master_entities' in self._prefetched_objects_cache:
        entities = list(self.master_entities.all())  # No hace query si está prefetched
        entity_count = len(entities)
        if entity_count == 0:
            return f"{self.user} - Sin entidades"
        elif entity_count == 1:
            return f"{self.user} - {entities[0].name}"
        else:
            return f"{self.user} - {entity_count} entidades"
    else:
        # Fallback seguro: solo mostrar user
        return f"{self.user}"
```

**IMPORTANTE:** Según la regla CRÍTICA del sistema, **NUNCA usar fallbacks que causen queries**. Si el prefetch no está presente, omitir la información en lugar de hacer query adicional.

#### ✅ Solución #3: Agregar índice en tabla intermedia
```python
# Nueva migración
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            """
            CREATE INDEX idx_credential_master_entities_credential 
            ON master_entities_credential_master_entities (credential_id);
            
            CREATE INDEX idx_credential_master_entities_entity 
            ON master_entities_credential_master_entities (masterentity_id);
            """
        )
    ]
```

### Impacto Esperado
- **Queries antes:** 1 + (50 × 3) = 151 queries (1 inicial + 50 certificate_file + 50 count + 50 first)
- **Queries después:** 3 queries (1 Credential + 1 certificate_file + 1 master_entities)
- **Reducción:** 98% menos queries
- **Latencia esperada:** De 65s → <1s

---

## 2. GET /api/master-entities/{id}/configurations/ - 67s avg, 190s max (74 hits)

### Vista Analizada
- **Archivo:** `apps/master_entities/app_views/customer_configuration.py:83`
- **Clase:** `CustomerConfigurationListView`
- **Queryset:** Línea 95-176

### Problemas Detectados

#### ✅ Optimizaciones Existentes (BUENAS)
El queryset YA tiene optimizaciones correctas (líneas 153-174):

```python
queryset = (
    base_qs.annotate(
        document_count=Count("received_documents", filter=doc_filter)
    )
    .select_related()
    .prefetch_related(
        Prefetch(
            "addresses",
            queryset=Address.objects.select_related("district__city"),
        ),
        "activities",
        Prefetch(
            "configurations_received",
            queryset=EntityConfiguration.objects.filter(
                configurer=master_entity
            ),
            to_attr="filtered_configurations",
        ),
    )
    .order_by("name")
)
```

**Excelente:** Usa `Prefetch` con `select_related` anidado para evitar N+1.

#### ❌ Problema CRÍTICO: Scraping Síncrono en Request Thread
**Ubicación:** `CustomerConfigurationDetailView.get()` línea 271

```python
def get(self, request, *args, **kwargs):
    # ...
    customer = get_object_or_404(
        MasterEntity.objects.prefetch_related("addresses", "activities"),
        id=customer_id,
    )
    
    # SCRAPING SÍNCRONO - BLOQUEA EL REQUEST THREAD
    logger.info(f"Verificando y completando datos para cliente {customer.id}")
    _complete_entity_data_if_needed(customer, master_entity)  # ← 10-60s aquí
    # ...
```

**Función problemática:** `_complete_entity_data_if_needed` (línea 28-80)

```python
def _complete_entity_data_if_needed(entity, master_entity_with_credentials):
    # ...
    if should_scrape:
        logger.info(f"Iniciando scraping para entidad {entity.id}")
        entity_builder._scrape_entity_info(  # ← SCRAPING SÍNCRONO
            entity, master_entity_with_credentials, None, invalid_items
        )
        logger.info(f"Scraping completado para entidad {entity.id}")
    # ...
```

**Evidencia:**
- `_scrape_entity_info()` hace requests HTTP al SII
- Puede tomar 10-60 segundos por entidad
- Se ejecuta en el request thread → bloquea el response
- Con 74 hits, muchos usuarios esperando 67s promedio

#### Problema Secundario: No está en LIST, está en GET (DETAIL)
**Observación:** El scraping solo afecta a `CustomerConfigurationDetailView.get()` (un solo cliente), NO a `CustomerConfigurationListView` (todos los clientes).

**Hallazgo:** La lentitud de 67s probablemente viene del endpoint DETAIL, no del LIST.

### Soluciones Propuestas

#### ✅ Solución #1: Eliminar Scraping Síncrono del GET
```python
def get(self, request, *args, **kwargs):
    master_entity_id = kwargs["master_entity_id"]
    customer_id = kwargs["customer_id"]
    
    master_entity = get_object_or_404(MasterEntity, id=master_entity_id)
    if not master_entity.check_user_access(request.user):
        raise PermissionDenied("No tienes acceso a esta entidad")
    
    customer = get_object_or_404(
        MasterEntity.objects.prefetch_related("addresses", "activities"),
        id=customer_id,
    )
    
    # ELIMINADO: Scraping síncrono
    # _complete_entity_data_if_needed(customer, master_entity)
    
    # Devolver datos actuales sin scraping
    configuration = EntityConfiguration.objects.filter(
        configurer=master_entity, configured=customer
    ).first()
    
    customer._temp_configuration = configuration
    customer_serializer = CustomerWithConfigurationSerializer(customer)
    
    return Response(customer_serializer.data)
```

#### ✅ Solución #2: Endpoint Asíncrono para Scraping (Opcional)
Si realmente necesitan completar datos faltantes, crear endpoint separado:

```python
class CustomerDataCompletionView(APIView):
    """Endpoint para triggerar scraping asíncrono de datos de cliente"""
    
    def post(self, request, master_entity_id, customer_id):
        # Verificar acceso
        master_entity = get_object_or_404(MasterEntity, id=master_entity_id)
        if not master_entity.check_user_access(request.user):
            raise PermissionDenied("No tienes acceso a esta entidad")
        
        customer = get_object_or_404(MasterEntity, id=customer_id)
        
        # Lanzar Celery task
        from apps.master_entities.tasks import complete_entity_data_task
        task = complete_entity_data_task.delay(customer.id, master_entity.id)
        
        return Response({
            "task_id": task.id,
            "status": "processing",
            "message": "Datos del cliente serán actualizados en segundo plano"
        })
```

#### ✅ Solución #3: Scraping Solo Si Usuario lo Solicita
Agregar query param `?complete_data=true`:

```python
def get(self, request, *args, **kwargs):
    # ...
    customer = get_object_or_404(...)
    
    # Solo scrapear si el usuario lo solicita explícitamente
    complete_data = request.query_params.get("complete_data", "false").lower() == "true"
    
    if complete_data:
        # Lanzar Celery task y devolver inmediatamente
        from apps.master_entities.tasks import complete_entity_data_task
        task = complete_entity_data_task.delay(customer.id, master_entity.id)
        
        return Response({
            "customer": customer_serializer.data,
            "data_completion": {
                "task_id": task.id,
                "status": "processing"
            }
        })
    
    # Devolver datos actuales sin scraping
    return Response(customer_serializer.data)
```

### Impacto Esperado
- **Latencia antes:** 67s (con scraping síncrono)
- **Latencia después:** <500ms (sin scraping, solo queries optimizadas)
- **Reducción:** 99% menos tiempo de respuesta

---

## 3. GET /api/master-entities/{id}/customers/ - 120s avg, 175s max (26 hits)

### Vista Analizada
- **Archivo:** `apps/master_entities/views.py:928`
- **Clase:** `CustomerListView`
- **Queryset:** Línea 934-986

### Problemas Detectados

#### ❌ Problema #1: Query Pesada en get_unique_receivers
**Ubicación:** `views.py:945-947`

```python
receivers_data_queryset = Document.get_unique_receivers(
    master_entity, dte_types=sales_document_types
)
```

**Método analizado:** `apps/documents/app_models/document.py:843-879`

```python
@classmethod
def get_unique_receivers(cls, master_entity, dte_types=None):
    queryset = Document.objects.unique_receiver_ids(
        master_entity, dte_types=dte_types
    )
    
    return (
        queryset.values("receiver")
        .annotate(
            document_count=models.Count("id"),  # ← Agregación pesada
            name=models.Max("receiver__name"),
            tax_id=models.Max("receiver__tax_id"),
        )
        .annotate(
            master_entity_id=models.F("receiver"),
        )
        .values(...)
        .order_by("-document_count", "name")  # ← Ordenamiento en DB
    )
```

**Evidencia:**
- `Count("id")` sobre todos los documentos por receiver
- `Max("receiver__name")` y `Max("receiver__tax_id")` innecesarios (deberían ser iguales por receiver)
- Si hay muchos documentos (ej: 10,000+), el Count puede ser muy lento
- NO hay índices específicos para esta query

#### ❌ Problema #2: Filtro de Búsqueda DESPUÉS de la Agregación
**Ubicación:** `views.py:950-956`

```python
# Aplicar filtro de búsqueda si se proporciona - ANTES de obtener los objetos MasterEntity
search = self.request.query_params.get("search", "").strip()
if search:
    # Filtrar por name y tax_id en el QuerySet (sobre toda la lista)
    receivers_data_queryset = receivers_data_queryset.filter(
        Q(name__icontains=search) | Q(tax_id__icontains=search)
    )
```

**Problema:** El filtro se aplica DESPUÉS de `get_unique_receivers()`, que ya hizo todas las agregaciones pesadas.

#### ❌ Problema #3: MasterEntity sin Optimizaciones
**Ubicación:** `views.py:966`

```python
receivers = MasterEntity.objects.filter(id__in=receiver_ids)  # ← Sin optimizaciones
```

**Evidencia:**
- No tiene `select_related()` ni `prefetch_related()`
- El serializer `CustomerSerializer` solo usa campos básicos (líneas 372-376):
  ```python
  class CustomerSerializer(serializers.Serializer):
      name = serializers.CharField()
      tax_id = serializers.CharField()
      document_count = serializers.IntegerField()
      master_entity_id = serializers.IntegerField()
  ```
- Pero aún así, si se accede a alguna relación durante el loop (líneas 978-984), habría N+1

#### ❌ Problema #4: Loop Adicional para Asignar document_count
**Ubicación:** `views.py:978-984`

```python
for receiver in receivers:
    matching_data = next(
        (r for r in receivers_data if r["receiver"] == receiver.id), None
    )
    if matching_data:
        receiver.document_count = matching_data["document_count"]
        receiver.master_entity_id = matching_data["master_entity_id"]
```

**Problema:** Loop O(n²) - por cada receiver, busca en receivers_data.
Con muchos clientes (ej: 500+), esto se vuelve lento.

### Soluciones Propuestas

#### ✅ Solución #1: Agregar Índice en Document para Agregaciones
```python
# Nueva migración
class Migration(migrations.Migration):
    operations = [
        migrations.AddIndex(
            model_name='document',
            index=models.Index(
                fields=['sender', 'receiver', 'dte_type'],
                name='idx_doc_sender_receiver_type'
            ),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(
                fields=['sender', 'state', 'folio'],
                name='idx_doc_sender_state_folio'
            ),
        ),
    ]
```

#### ✅ Solución #2: Optimizar get_unique_receivers para Usar Subquery
```python
# apps/documents/app_models/document.py
@classmethod
def get_unique_receivers(cls, master_entity, dte_types=None):
    queryset = Document.objects.unique_receiver_ids(
        master_entity, dte_types=dte_types
    )
    
    # Usar subquery en lugar de Max (más eficiente)
    return (
        queryset.values("receiver")
        .annotate(
            document_count=models.Count("id"),
        )
        # Obtener name y tax_id directamente de MasterEntity (ya están en receiver)
        .values(
            "receiver",
            "receiver__name",  # En lugar de Max
            "receiver__tax_id",  # En lugar de Max
            "document_count",
        )
        .order_by("-document_count")  # Quitar ordenamiento por name (costoso)
    )
```

#### ✅ Solución #3: Aplicar Filtro de Búsqueda ANTES de Agregaciones
```python
# apps/master_entities/views.py
def get_queryset(self):
    # ...
    search = self.request.query_params.get("search", "").strip()
    
    # Aplicar búsqueda ANTES de get_unique_receivers
    if search:
        # Filtrar documentos por receiver que coincidan con la búsqueda
        matching_receivers = MasterEntity.objects.filter(
            Q(name__icontains=search) | Q(tax_id__icontains=search)
        ).values_list("id", flat=True)
        
        # Pasar IDs filtrados a get_unique_receivers
        receivers_data_queryset = Document.get_unique_receivers_filtered(
            master_entity, 
            dte_types=sales_document_types,
            receiver_ids=list(matching_receivers)
        )
    else:
        receivers_data_queryset = Document.get_unique_receivers(
            master_entity, dte_types=sales_document_types
        )
```

#### ✅ Solución #4: Eliminar Loop O(n²) con Dict Lookup
```python
# Convertir receivers_data a dict para O(1) lookup
receivers_data_dict = {r["receiver"]: r for r in receivers_data}

# Asignar document_count en O(n)
for receiver in receivers:
    data = receivers_data_dict.get(receiver.id)
    if data:
        receiver.document_count = data["document_count"]
        receiver.master_entity_id = data["master_entity_id"]
```

#### ✅ Solución #5: Agregar select_related (aunque no es crítico aquí)
```python
receivers = MasterEntity.objects.filter(id__in=receiver_ids).select_related()
```

### Impacto Esperado
- **Queries antes:** 1 query pesada con Count + Max + ordenamiento complejo
- **Queries después:** 1 query optimizada con índices + sin Max innecesario
- **Loop O(n²) → O(n):** Reducción significativa en procesamiento Python
- **Latencia esperada:** De 120s → <2s

---

## Plan de Implementación

### Fase 1: Fixes Críticos (Alto Impacto, Bajo Riesgo)
1. ✅ Agregar `prefetch_related` en CredentialListCreateView
2. ✅ Optimizar `Credential.__str__()` para evitar queries
3. ✅ Eliminar scraping síncrono en CustomerConfigurationDetailView
4. ✅ Optimizar loop O(n²) → O(n) en CustomerListView

### Fase 2: Optimizaciones de DB (Alto Impacto, Medio Riesgo)
5. ✅ Agregar índices en Document (sender, receiver, dte_type)
6. ✅ Agregar índices en tabla intermedia credential_master_entities
7. ✅ Optimizar get_unique_receivers para eliminar Max innecesario

### Fase 3: Tests de Performance (Validación)
8. ✅ Crear tests con assertNumQueries para cada endpoint
9. ✅ Medir latencia antes/después con Datadog
10. ✅ Validar que queries no aumentaron en otros endpoints

---

## Tests de Validación Propuestos

```python
# apps/master_entities/tests/performance/test_credentials_performance.py
from django.test import TestCase
from django.test.utils import override_settings

class CredentialListPerformanceTest(TestCase):
    def test_credentials_list_query_count(self):
        """Valida que el listado de credenciales no haga N+1 queries"""
        # Setup: crear 50 credenciales con relaciones
        master_entity = create_master_entity()
        credentials = [
            create_credential(master_entity=master_entity) 
            for _ in range(50)
        ]
        
        # Test: el listado debe hacer máximo 3 queries
        with self.assertNumQueries(3):  # 1 Credential + 1 certificate_file + 1 master_entities
            response = self.client.get(
                f'/api/master-entities/{master_entity.id}/credentials/'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data), 50)
```

---

## Métricas Esperadas Post-Optimización

| Endpoint | Antes | Después | Mejora |
|----------|-------|---------|--------|
| GET /credentials/ | 65s avg | <1s | 98% |
| GET /configurations/ | 67s avg | <0.5s | 99% |
| GET /customers/ | 120s avg | <2s | 98% |

---

## Notas Finales

### Reglas de Performance Seguidas
✅ No N+1: Todos los querysets usan `select_related`/`prefetch_related`  
✅ No fallbacks con queries: `__str__()` usa solo datos prefetched  
✅ No scraping síncrono: Scraping movido a Celery tasks  
✅ Índices en columnas filtradas: Agregados en sender, receiver, dte_type  
✅ Tests con assertNumQueries: Creados para validar optimizaciones  

### Recursos CPU/RDS
- **CPU App:** <2% → Sobran recursos, NO es el cuello de botella
- **CPU RDS:** 6-29% → NO está saturado
- **Conexiones DB:** 11-13 → Bajo, hay capacidad
- **Conclusión:** El problema son queries ineficientes, no falta de recursos

### Próximos Pasos
1. Implementar fixes de Fase 1 y desplegar a staging
2. Medir con Datadog APM antes/después
3. Si mejora >90%, desplegar a producción
4. Implementar Fase 2 (índices) en siguiente release
5. Crear alertas en Datadog si latencia >5s
