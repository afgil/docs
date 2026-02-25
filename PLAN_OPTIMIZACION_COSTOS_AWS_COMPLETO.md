# Plan Completo de Optimización de Costos AWS - Tu Pana

**Fecha:** Febrero 2026  
**Fuente datos:** CloudWatch (últimos 7 días), AWS CLI, Datadog APM  
**Región:** us-east-1  
**Última actualización:** Config conservadora aplicada por lentitud (App 2×4vCPU/8GB, High 2vCPU/4GB, Medium 4vCPU/8GB; coste ~$753)

---

## 0. Costes proyectados hoy (referencia deploy_production.sh)

**Configuración CONSERVADORA aplicada (por lentitud detectada en endpoints; workers HIGH y MEDIUM activos):**

| Servicio ECS | Config en deploy | vCPU | RAM | Tasks | Coste Fargate estimado/mes (us-east-1) |
|--------------|------------------|------|-----|-------|----------------------------------------|
| **pana-backend-service** (App) | 4096 / 8192 | 4 | 8 GB | 2 | ~\$288 |
| **pana-backend-celery-high** | 2048 / 4096 | 2 | 4 GB | 1 | ~\$72 |
| **pana-backend-celery-medium** | 4096 / 8192 | 4 | 8 GB | 1 | ~\$144 |
| **pana-backend-celery-beat** | 2048 / 4096 | 2 | 4 GB | 1 | ~\$72 |
| **Subtotal ECS Prod** | | | | | **~\$576** |

*Fargate us-east-1: ~\$0.04048/vCPU-hora, ~\$0.004445/GB-hora; 730 h/mes.*

| Otros (fijos) | Estimado/mes |
|---------------|--------------|
| RDS Prod + Staging | ~\$77 |
| ALB, CloudWatch, S3, Lambda, ECR, SQS, CloudFront, Data Transfer | ~\$100 |
| **Subtotal otros** | **~\$177** |

**Total deploy_production.sh (prod + fijos): ~\$753/mes.** Staging (si aplica) +~\$54.

**Por qué conservadora:** Se detectó lentitud con config optimizada (App 2vCPU); se subió a 4 vCPU/8 GB. Endpoints lentos:
- `GET /api/master-entities/{id}/customers-configuration/` (AVG 10s, MAX 123s)
- `GET /api/master-entities/{id}/customers/` (AVG 12s)

**Si la lentitud persiste:** El problema es N+1 queries o queries sin índices (no recursos). Ver sección 13 para optimización por endpoint.

**Arquitectura:** 
- **3 colas SQS separadas** (high, medium, low): patrón recomendado para priorización con SQS (no tiene prioridad nativa).
- **2 workers ECS dedicados** (celery-high solo HIGH, celery-medium solo MEDIUM+LOW): garantiza priorización real.
- **Concurrency:** HIGH=2, MEDIUM=2.
- Ver análisis completo en `docs/CELERY_SQS_PRIORIZACION_BUENAS_PRACTICAS.md`.

---

## 1. Coste actual (post-optimizaciones)

| Servicio | Configuración actual | Costo estimado/mes |
|----------|----------------------|--------------------|
| **App Prod** | 2 × 2 vCPU / 4 GB (pana-backend-app) | ~$144 |
| **Celery (unificado)** | 1 × 2 vCPU / 4 GB (pana-backend-celery-medium:198) | ~$72 |
| **Staging App** | 1 × 1 vCPU / 2 GB (pana-backend-app-staging:163) | ~$36 |
| **Celery Staging** | 1 × 0.5 vCPU / 1 GB (pana-backend-celery-staging:60) | ~$18 |
| **Celery High** | 0 tasks (escalado a 0) | $0 |
| **Celery Beat (prod + staging)** | 2 × 0.25 vCPU / 0.5 GB | ~$18 |
| **RDS Prod** | db.t3.medium | ~$62 |
| **RDS Staging** | db.t3.micro | ~$15 |
| **Otros (ver desglose abajo)** | - | ~$100 |

**Desglose Otros (estimado us-east-1):**

| Componente | Estimado/mes | Notas |
|------------|--------------|-------|
| **ALB** | ~$22 | Application Load Balancer (LCU + horas) |
| **CloudWatch Logs** | ~$25-40 | logtail 32 GB, ECS logs 30d, datadog forwarders |
| **S3** | ~$5-15 | tupanabucketdata, staging, frontend-images |
| **Lambda** | ~$5-10 | logtail-aws-lambda, datadog-log-forwarder(s) |
| **ECR** | ~$3-5 | Almacenamiento imágenes pana-backend |
| **CloudFront** | ~$5-15 | cdn.tupana.ai, 2 distribuciones |
| **SQS** | ~$1-2 | 6 colas, bajo volumen |
| **Data Transfer** | ~$5-15 | Salida internet |
| **TOTAL ESTIMADO** | | **~$465/mes** |

**Ahorro acumulado respecto al punto de partida (~$1.220): ~$755/mes (~62%).**

---

### Proyección Febrero y Marzo (ceteris paribus)

Asumiendo que no hay cambios en la infraestructura ni en el tráfico:

| Mes | Coste proyectado | Notas |
|-----|------------------|-------|
| **Febrero 2026** | ~\$465 | Config actual aplicada (App 2×2vCPU/4GB, Celery unificado, etc.) |
| **Marzo 2026** | ~\$465 | Mismo que febrero |

**Detalle mensual (ceteris paribus):**

| Servicio | Feb | Mar |
|----------|-----|-----|
| App Prod (2×2vCPU/4GB) | $144 | $144 |
| Celery (unificado) | $72 | $72 |
| Staging App | $36 | $36 |
| Celery Staging | $18 | $18 |
| Celery Beat ×2 | $18 | $18 |
| RDS Prod + Staging | $77 | $77 |
| ALB, CloudWatch, S3, etc. | ~$100 | ~$100 |
| **TOTAL** | **~$465** | **~$465** |

---

## 2. Resumen Ejecutivo (referencia inicial vs objetivo)

| Métrica | Inicial | Actual (post-optim.) | Proyección Feb/Mar |
|---------|--------|----------------------|-------------------|
| **Gasto total estimado** | ~$1.220 | **~$465** | ~$465 (ceteris paribus) |
| **ECS** | ~$992 | **~$288** | ~$288 |
| **RDS** | ~$77 | ~$77 | $0 (mantener) |
| **Otros** | ~$150 | ~$100 | ~$100 |

---

## 3. Análisis ECS - Métricas CloudWatch Reales

### 3.1 App Principal (pana-backend-service)

| Config Actual | CPU Promedio | CPU Máximo | Memoria Promedio | Memoria Máximo |
|---------------|--------------|------------|------------------|----------------|
| 2 tasks × 8 vCPU / 16 GB | **0.2-0.6%** | 23% | **2.8-5.3%** | 5.5% |
| Costo: ~$576/mes | | | | |

**Diagnóstico:** Sobredimensionamiento extremo. La app usa <1% CPU y <6% memoria de lo asignado.

| Propuesta | vCPU | Memory | Costo | Riesgo |
|-----------|------|--------|-------|--------|
| **Conservadora** | 4 vCPU × 2 tasks | 8 GB × 2 | ~$288/mes | Bajo |
| **Recomendada** | 2 vCPU × 2 tasks | 4 GB × 2 | ~$72/mes | Medio (pico 23%) |
| **Mínima** | 1 vCPU × 2 tasks | 2 GB × 2 | ~$36/mes | Alto |

**Recomendación:** Empezar con **4 vCPU / 8 GB × 2 tasks** (~$288), validar 2 semanas, bajar a **2 vCPU / 4 GB** si estable.

**Ahorro:** $288-504/mes

---

### 3.2 Celery High (pana-backend-celery-high)

| Config Actual | CPU Promedio | CPU Máximo |
|---------------|--------------|------------|
| 1 × 2 vCPU / 4 GB | 0.5% | **54%** |
| Costo: ~$72/mes | | |

**Diagnóstico:** Picos de 54% durante procesamiento. Mantener 2 vCPU para bursts.

**Recomendación:** Mantener 2 vCPU / 4 GB. Opcional probar 1 vCPU / 2 GB con monitoreo (ahorro $36, riesgo medio).

**Ahorro:** $0 (conservador) o $36 (agresivo)

---

### 3.3 Celery Medium (pana-backend-celery-medium)

| Config Actual | CPU Promedio | CPU Máximo |
|---------------|--------------|------------|
| 1 × 4 vCPU / 8 GB | 2.7% | 16% |
| Costo: ~$145/mes | | |

**Diagnóstico:** Claramente sobredimensionado. Máx 16% de 4 vCPU = 0.64 vCPU equivalente.

**Recomendación:** Bajar a **2 vCPU / 4 GB** (~$72/mes).

**Ahorro:** $73/mes

---

### 3.4 Staging App (pana-backend-staging)

| Config Actual | CPU Promedio | CPU Máximo |
|---------------|--------------|------------|
| 1 × 4 vCPU / 8 GB | 0.38% | 4% |
| Costo: ~$145/mes | | |

**Diagnóstico:** Staging con recursos de producción. Uso mínimo.

**Recomendación:** Bajar a **1 vCPU / 2 GB** (~$36/mes). Alternativa: scale-to-zero fuera de horario.

**Ahorro:** $109/mes

---

### 3.5 Celery Staging, Celery Beat

| Servicio | Config | Uso | Acción |
|----------|--------|-----|--------|
| celery-staging | 1 vCPU / 2 GB | OK | Mantener |
| celery-beat × 2 | 0.25 vCPU / 0.5 GB | OK | Mantener |

---

## 4. Análisis RDS - Métricas CloudWatch

### 4.1 Producción (pana-database-migrated)

| Config Actual | CPU Promedio | CPU Máximo | FreeableMemory |
|---------------|--------------|------------|----------------|
| db.t3.medium (2 vCPU, 4 GB) | 6-36% | **99%** | ~2 GB libre |
| Costo: ~$62/mes | | | |

**Diagnóstico:** 
- CPU alcanza 99% en picos → **no bajar** a t3.small (saturaría).
- Memoria: ~2 GB usados de 4 GB. db.t3.small tiene 2 GB total → no cabe.

**Recomendación:** **Mantener db.t3.medium**. No reducir tamaño.

**Ahorro:** $0

---

### 4.2 Staging (pana-backend-staging)

| Config Actual | CPU Promedio | CPU Máximo |
|---------------|--------------|------------|
| db.t3.micro (2 vCPU burstable, 1 GB) | ~5% | ~10% |
| Costo: ~$15/mes | | |

**Recomendación:** Mantener. Ya es la instancia más económica.

---

## 5. Otras Optimizaciones (del análisis anterior)

| # | Acción | Ahorro Est. |
|---|--------|-------------|
| 1 | Retención 7 días en logtail-aws-lambda (32 GB sin límite) | $15-40 |
| 2 | Eliminar colas SQS huérfanas (celery, low, pana-celery-queue) | Operativo |
| 3 | Scale-to-zero staging 12h/día (opcional) | $70-90 |

---

## 6. Plan de Implementación por Fases

### Fase 1 – Rápida (Semana 1) – Sin riesgo

| Tarea | Comando / Acción | Ahorro |
|-------|------------------|--------|
| Retención CloudWatch logtail | `aws logs put-retention-policy --log-group-name /aws/lambda/logtail-aws-lambda --retention-in-days 7` | ~$25 |
| Eliminar cola SQS `celery` | AWS Console SQS → Eliminar (tras validar 0 mensajes) | - |
| Eliminar cola SQS `pana-celery-queue-low` | Idem | - |
| Eliminar cola SQS `pana-celery-queue` | Solo si prod usa solo high+medium | - |

---

### Fase 2 – ECS Celery y Staging (Semana 2)

| Tarea | Cambio | Antes | Después | Ahorro |
|-------|--------|-------|---------|--------|
| Celery Medium | Task definition | 4 vCPU / 8 GB | 2 vCPU / 4 GB | $73/mes |
| Staging App | Task definition | 4 vCPU / 8 GB | 1 vCPU / 2 GB | $109/mes |

**Pasos:**
1. Crear nueva revisión de task definition con CPU/memory reducidos.
2. Actualizar servicio ECS: `aws ecs update-service --cluster pana-backend-cluster --service pana-backend-celery-medium --task-definition pana-backend-celery-medium --force-new-deployment`
3. Monitorear 24-48h en CloudWatch/Datadog.
4. Repetir para staging.

---

### Fase 3 – App Principal (Semana 3-4)

| Tarea | Cambio | Antes | Después | Ahorro |
|-------|--------|-------|---------|--------|
| App Prod | Task definition | 8 vCPU / 16 GB × 2 | 4 vCPU / 8 GB × 2 | $288/mes |

**Pasos:**
1. Crear task definition `pana-backend-app` con 4096 CPU, 8192 memory.
2. Actualizar `pana-backend-service` para usar la nueva revisión.
3. Monitorear 1-2 semanas (picos de carga, scraping).
4. Si estable, evaluar bajar a 2 vCPU / 4 GB (+$216/mes ahorro).

---

### Fase 4 – Opcional (Mes 2)

| Tarea | Descripción | Ahorro |
|-------|-------------|--------|
| Scale-to-zero staging | EventBridge + Lambda para desiredCount=0 20:00-08:00 | $70-90 |
| Celery High 1 vCPU | Probar con monitoreo cercano | $36 |
| Compute Savings Plans | 1 año para ECS Fargate | 20-30% adicional |

---

## 7. Tabla de Costos – Antes y Después

**Estado actual (post-optimizaciones aplicadas):**

| Servicio | Config actual (post-optim.) | Costo actual |
|----------|-----------------------------|--------------|
| **App Prod** | 2×2vCPU/4GB | $144 |
| **Celery (unificado)** | 1×2vCPU/4GB (high=0) | $72 |
| **Staging App** | 1×1vCPU/2GB | $36 |
| **Celery Staging** | 1×0.5vCPU/1GB | $18 |
| **Celery Beat ×2** | 2×0.25vCPU/0.5GB | $18 |
| **RDS Prod** | db.t3.medium | $62 |
| **RDS Staging** | db.t3.micro | $15 |
| **CloudWatch, ALB, S3, etc.** | - | ~$100 |
| **TOTAL** | | **~$465** |

**Referencia inicial → actual:** ~$1.220 → ~$465 (**~$755 ahorro**).

Opcionales para seguir bajando: Fase 3 agresiva (App 2×2vCPU/4GB), scale-to-zero staging, retención CloudWatch 7d → total podría acercarse a **~$460–580**.

---

## 8. Comandos de Referencia

### Ver CPU RDS
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=pana-database-migrated \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:00Z) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:00Z) \
  --period 3600 --statistics Average Maximum
```

### Ver CPU ECS
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=pana-backend-service Name=ClusterName,Value=pana-backend-cluster \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:00Z) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:00Z) \
  --period 3600 --statistics Average Maximum
```

### Actualizar task definition (ejemplo Celery Medium)
Editar en ECS Console o via `aws ecs register-task-definition` con `cpu: 2048`, `memory: 4096` para los contenedores. Luego:
```bash
aws ecs update-service --cluster pana-backend-cluster \
  --service pana-backend-celery-medium --force-new-deployment
```

---

## 9. Checklist Pre-Implementación

- [ ] Backup RDS reciente
- [ ] Alarmas CloudWatch para CPUUtilization > 80% en ECS y RDS
- [ ] Ventana de cambio en horario de baja carga
- [ ] Validar que colas SQS a eliminar no tienen consumers activos
- [ ] Comunicar al equipo antes de cambios en App prod (Fase 3)

---

## 10. Riesgos y Mitigación

| Riesgo | Mitigación |
|--------|------------|
| App se satura con 4 vCPU | Rollback a task def anterior en ECS (1 clic) |
| Pico de carga inesperado | Alarmas → escala manual o reconsiderar 8 vCPU |
| RDS picos 99% | No reducir RDS; evaluar índices/optimización de queries |
| Staging demasiado lenta | Subir a 2 vCPU / 4 GB ($72) |

---

## 11. Procesos que más memoria consumen (ECS)

Métricas CloudWatch (últimos 3 días) y asignación por contenedor:

| Servicio | Memoria asignada | Uso real (avg / max) | Contenedores que más asignan |
|----------|------------------|------------------------|------------------------------|
| **pana-backend-service** | 8 GB × 2 tasks | 3.8% / 5.9% (~300–470 MB por task) | django-app 5.5 GB, datadog-agent 1 GB, selenium 512 MB |
| **pana-backend-celery-medium** | 4 GB × 1 task | 8.2% / 10.8% (~330–430 MB) | celery 768 MB, selenium 512 MB |
| **pana-backend-staging** | 2 GB × 1 task | 6.4% / 21% (~130–420 MB) | django 1 GB, selenium 512 MB, datadog 512 MB |
| **pana-backend-celery-staging** | 2 GB × 1 task | **23.9%** / 24% (~480 MB) | celery 768 MB, selenium 512 MB |

**Procesos que más memoria consumen (por asignación en task definition):**

1. **django-app (prod):** 5.632 MB asignados por contenedor. Uso real ~5% → gran margen para bajar (p. ej. 2–3 GB).
2. **datadog-agent:** 1.024 MB en cada task de app (prod y staging). Fijo; no se puede bajar desde ECS sin quitar el agente.
3. **selenium-chrome:** 512 MB en app y celery. Uso típico estable; necesario para scraping.
4. **Celery (worker):** 768 MB en celery-medium/celery-staging. Uso real ~8–24%; se podría probar 512 MB en staging.

**Conclusión:** El mayor “consumidor” asignado es **django-app** (5.5 GB con uso real bajo). **datadog-agent** suma 1 GB por task de app. Reducir memoria de django-app en la task definition (p. ej. a 2–3 GB) y mantener datadog/selenium permite más ahorro sin tocar observabilidad ni scraping.

---

## 12. Cambios ya aplicados (Celery unificado + App Prod 2vCPU)

- **App Prod 2×2vCPU/4GB:** `deploy_lean.sh` genera task `pana-backend-app` con 2048 CPU / 4096 MB cuando se despliega producción. Django 1280/3072, selenium 512/512, datadog 256/512. **Ahorro:** ~$144/mes.
- **Worker unificado:** Un solo servicio (`pana-backend-celery-medium`) consume **high** y **medium** en orden de prioridad (`worker.sh` con `QUEUES=high,medium`).
- **celery-high:** `desiredCount=0` (escalado a 0).
- **celery-medium:** Task definition con **2 vCPU / 4 GB** y `./worker.sh` (antes 4 vCPU / 8 GB y `worker-medium.sh`).

**Ahorro Celery:** ~\$145/mes (eliminado celery-high \$72 + reducción celery-medium 4→2 vCPU ~\$73).

**Más reducciones ECS posibles:**

| Acción | Ahorro est. | Notas |
|--------|-------------|--------|
| Reducir memoria django-app (prod) de 5.5 GB a 3 GB | Permite bajar task a 4 GB total → ~\$50/mes | Validar con picos de carga |
| Celery Beat: 2 vCPU/4 GB → 0.25 vCPU/512 MB | ~\$15/mes | Beat es solo scheduler |
| Evaluar quitar datadog-agent de tasks y usar solo API/Lambda | ~\$0 directo, libera 1 GB por task | Menos memoria por task |

---

## 13. Datadog APM – Análisis de rendimiento y plan de optimización

### 13.1 Cómo analizar traces en Datadog

- **APM → Services → `pana-backend`**  
  Ver latencia (p50, p75, p95, p99), throughput (req/s) y errores por endpoint.

- **APM → Services → pana-backend → Resources**  
  Lista de recursos (endpoints/operaciones) ordenables por:
  - **Latency** (avg, p95): identificar los más lentos.
  - **Throughput** (hits): identificar los más repetidos.

- **Prioridad de optimización:**  
  Combinar **alto throughput** y **alta latencia** → mayor impacto (tiempo total consumido = throughput × latencia).  
  También priorizar endpoints con **p95 o p99 altos** (experiencia usuario y riesgo de timeouts).

- **Trace Explorer**  
  Filtrar por `service:pana-backend`, ordenar por duration; abrir traces individuales para ver spans (DB, HTTP, etc.) y detectar N+1 o queries lentas.

### 13.2 Resultados del análisis Datadog APM (ejecutado)

**Fuente:** API Spans 21.000 spans (última semana). Scripts: `scripts/fetch_datadog_spans_all.sh`, `scripts/analisis_datadog_apm.sh`. Ver `docs/PLAN_OPTIMIZACION_RENDIMIENTO_DATADOG.md`.

**Top por impacto (hits × avg_duration):**

| hits | avg ms | max ms | impact | resource |
|------|--------|--------|--------|----------|
| 60 | 146 | 734 | 8761 | **GET /v1/master-entities** |
| 60 | 130 | 634 | 7772 | **GET /v1/documents** |
| 2 | 2903 | 3089 | 5806 | POST /api/master-entities/{num}/addresses/sync/ |
| 1 | 5619 | 5619 | 5619 | **GET /v1/documents/{num}** (5.6 s) |
| 2 | 1378 | 1383 | 2756 | GET /api/credentials/415/sii-companies/ |
| 13 | 121 | 389 | 1579 | POST /api/emails/batch-render/ |
| 1 | 1395 | 1395 | 1395 | POST /api/emails/batch/ |
| 1 | 1174 | 1174 | 1174 | POST /api/ads/track-conversion/ |
| 1 | 1106 | 1106 | 1106 | POST /api/master-entities/{num}/documents/{num}/traces/refresh/ |
| 3 | 310 | 411 | 929 | GET /api/master-entities/{num}/customers-configuration/ |
| 17 | 51 | 710 | 874 | POST /api/banking/fintoc/webhook/ |
| 5 | 162 | 178 | 811 | GET /api/master-entities/{num}/documents/ |
| 16 | 38 | 58 | 601 | GET /api/master-entities/{num}/configurations/ |
| 2 | 290 | 299 | 579 | GET /api/master-entities/{num}/collection/clients/ |
| 1 | 550 | 550 | 550 | POST /v1/documents/payments |

**Top por latencia máxima (p95 proxy):**

| hits | max ms | resource |
|------|--------|----------|
| 1 | **5619** | GET /v1/documents/{num} |
| 2 | **3089** | POST /api/master-entities/{num}/addresses/sync/ |
| 1 | 1395 | POST /api/emails/batch/ |
| 2 | 1383 | GET /api/credentials/415/sii-companies/ |
| 1 | 1174 | POST /api/ads/track-conversion/ |
| 1 | 1106 | POST traces/refresh |
| 60 | 734 | GET /v1/master-entities |
| 17 | 710 | POST /api/banking/fintoc/webhook/ |
| 60 | 634 | GET /v1/documents |

**Prioridad de optimización (alto impacto + alta latencia):**

1. **GET /v1/documents** y **GET /v1/master-entities** – Más repetidos y lentos (avg 130–146 ms, max 634–734 ms).
2. **GET /v1/documents/{num}** – 5.6 s en un trace; crítico si es frecuente.
3. **POST /api/master-entities/{num}/addresses/sync/** – 2.9 s avg.
4. **GET /api/credentials/{num}/sii-companies/** – 1.4 s.
5. **POST /api/emails/batch-render/** – 121 ms avg, 389 ms max; 13 hits.
6. **POST /api/banking/fintoc/webhook/** – Max 710 ms; 17 hits.

**Candidatos por código (alineados con traces):**

| Área | Archivo / vista | Traces asociados |
|------|------------------|------------------|
| Documentos | `document_filters.py`, listados | GET /v1/documents, GET /v1/documents/{num} |
| Master entities | `master_entity_views` | GET /v1/master-entities, /configurations, /documents |
| Batches | `batch_views.py` | GET /api/documents/batch/{guid}/, POST batch |
| Emails | `emails` | POST batch-render, POST batch |

### 13.3 Plan de actuación por tipo de problema

| Problema | Acción |
|----------|--------|
| **N+1 (muchas queries por request)** | Revisar QuerySets: `select_related()`, `prefetch_related()` en listados y serializers; tests de número de queries. |
| **Queries lentas (spans DB > ~500 ms)** | Revisar índices en modelos usados en filtros/orden; considerar `only()`/`defer()` o agregaciones en DB. |
| **Endpoints muy llamados y algo lentos** | Paginación estricta, límite de página; caché (Redis) para respuestas idempotentes si aplica. |
| **Reportes / agregaciones pesadas** | Agregar en DB donde sea posible; caché por rango de fechas; jobs asíncronos para reportes grandes. |

### 13.4 Checklist de revisión por endpoint lento

1. En Trace Explorer: abrir un trace del endpoint y revisar duración por span (DB vs HTTP vs lógica).
2. Si el tiempo está en DB: ver lista de queries en el span; identificar repetidas (N+1) o una sola muy lenta.
3. En código: localizar la vista/serializer y el QuerySet; añadir `select_related`/`prefetch_related` o índices según el caso.
4. Añadir o ejecutar test que verifique número de queries (evitar regresiones N+1).
5. Volver a desplegar y comparar latencia en Datadog (misma ventana de tiempo).

### 13.5 Datos agregados desde la API (opcional)

La API de Datadog permite consultar métricas de APM. Para tener una tabla “top endpoints lentos / más repetidos” en este doc o en un dashboard interno:

- **Métricas útiles:** `trace.asgi.request.duration` (por `resource_name` o `http.route`), `trace.asgi.request.hits`.
- **Uso:** Query por servicio `pana-backend` y agrupar por `resource_name`; ordenar por avg duration y por hits; exportar a CSV o documentar en este plan.
- Si la API no devuelve agregados por resource con el plan actual, usar **APM → Resources** en la UI y anotar manualmente los top 5–10 cada trimestre.

### 13.6 Resumen

- **Coste actual infra:** ~\$465/mes (sección 1 y 7).  
- **Rendimiento:** Análisis ejecutado vía `scripts/analisis_datadog_apm.sh`; resultados en 13.2.  
- **Siguientes pasos concretos:**
  1. Optimizar **GET /v1/documents** y **GET /v1/master-entities** (N+1, select_related, índices).
  2. Investigar **GET /v1/documents/{num}** (trace 5.6 s) en Trace Explorer.
  3. Revisar **POST /api/master-entities/{num}/addresses/sync/** (~3 s).
  4. Para cada endpoint, aplicar checklist 13.4 y plan 13.3.
