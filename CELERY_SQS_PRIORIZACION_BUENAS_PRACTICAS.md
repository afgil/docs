# Celery + SQS: Priorización con Workers Dedicados (Buenas Prácticas)

**Fecha:** Febrero 2026  
**Contexto:** Tu Pana backend, colas HIGH (Excel/batch), MEDIUM (resto), LOW (opcional).  
**Objetivo:** Tener 1 ECS task para HIGH y 1 ECS task para MEDIUM, ambos activos, con priorización real y coste ~$465/mes.

---

## 1. El problema: Por qué 1 worker con 3 colas NO funciona

### Configuración inicial (problemática)

Un solo worker escuchando todas las colas:

```bash
celery -A backend worker --queues="high,medium,low" --concurrency=2
```

**Problema:** Celery hace **round-robin** entre las colas por defecto (toma 1 task de cada cola en orden). Si MEDIUM tiene **miles de mensajes** y HIGH tiene **pocos pero urgentes**, el worker alterna entre ambas → **HIGH no tiene prioridad real** y puede tardar minutos en ser atendida.

**Ejemplo:**
- HIGH: 5 mensajes (Excel, batch críticos)
- MEDIUM: 3.000 mensajes (logs, sync)
- Worker con concurrency=2: toma 1 de HIGH, 1 de MEDIUM, 1 de HIGH, 1 de MEDIUM... → HIGH debe esperar a que se despachen muchos MEDIUM.

**Síntoma:** Excel se queda "Cargando 0 de 1 documentos..." porque la task está en la cola HIGH pero el worker está ocupado con MEDIUM.

---

## 2. Solución: Workers dedicados por nivel de prioridad

### Patrón recomendado (industry standard)

**Colas separadas + Workers dedicados:**

- **Cola HIGH** → **Worker HIGH** (consume solo HIGH)
- **Cola MEDIUM** → **Worker MEDIUM** (consume solo MEDIUM, y LOW si existe)
- **Cola LOW** (opcional) → Worker MEDIUM o worker LOW dedicado

**Ventajas:**
1. **Priorización real:** HIGH nunca espera a que MEDIUM termine.
2. **Isolation:** Si MEDIUM se satura (miles de mensajes), HIGH sigue funcionando.
3. **Escalado independiente:** Puedes escalar HIGH y MEDIUM por separado según carga.
4. **Observability:** Métricas por cola (queue length, processing time) son más claras.

**Fuentes:**
- [Celery Priority Queues Best Practices](https://moldstud.com/articles/p-ultimate-guide-to-efficient-task-management-demystifying-celery-prioritization-strategies) (mejora hasta 35% en latencia y 40% en wait time con priorización explícita)
- [AWS SQS Priority Pattern](https://www.pulumi.com/answers/sqs-priority-queuing-in-aws/) (múltiples colas es el patrón estándar para priorización en SQS)
- [StackOverflow: Celery Multiple Queues](https://stackoverflow.com/questions/46204888/prioritizing-queues-among-multiple-queues-in-celery) (workers dedicados por cola)

---

## 3. Arquitectura actual (Tu Pana)

### 3 colas en SQS

| Cola | Routing keys | Uso |
|------|--------------|-----|
| **pana-celery-queue-high** | `high_priority_task`, `batch_issue_task`, `excel_process_task` | Excel, batch de emisión, crítico |
| **pana-celery-queue-medium** | `default`, la mayoría de tasks | Webhooks, sync, emails, reportes |
| **pana-celery-queue-low** (opcional) | `low_priority_task` | Tareas diferibles (limpieza, logs) |

### Workers

| Worker | Archivo | Colas consumidas | Concurrency |
|--------|---------|------------------|-------------|
| **celery-high** | `worker-high.sh` | `pana-celery-queue-high` | 2 |
| **celery-medium** | `worker-medium.sh` | `pana-celery-queue-medium`, `pana-celery-queue-low` | 2 |

### ¿Por qué funciona?

- **worker-high** SOLO consume HIGH: si hay mensaje en HIGH, lo procesa inmediatamente (no espera a MEDIUM).
- **worker-medium** SOLO consume MEDIUM y LOW: no toca HIGH, así no compite.
- **Isolation:** Si MEDIUM tiene 5.000 mensajes, HIGH sigue vacío y se atiende en segundos.

---

## 4. Benchmarks y buenas prácticas (research)

### 4.1 Múltiples colas separadas vs cola única con prioridad

| Enfoque | Ventajas | Desventajas | Recomendación |
|---------|----------|-------------|---------------|
| **Colas separadas** (high, medium, low) | ✅ Priorización real garantizada<br>✅ Escalado independiente<br>✅ Métricas por cola<br>✅ SQS no requiere config especial | ❌ Más colas (coste marginal)<br>❌ Más workers (más recursos) | **Recomendado** para SQS |
| **Cola única con prioridad** | ✅ Solo 1 cola<br>✅ Solo 1 worker | ❌ SQS no tiene prioridad nativa<br>❌ Celery + SQS no soporta `queue_order_strategy: priority`<br>❌ Round-robin → sin prioridad real | **No funciona** con SQS |

**Conclusión:** Para SQS, **colas separadas + workers dedicados** es el único patrón que garantiza priorización.

### 4.2 ¿Cuántos workers por cola?

**Regla general:**
- **HIGH:** 1-2 workers con concurrency=1 o 2 (suficiente si el volumen es bajo pero la urgencia alta).
- **MEDIUM:** N workers según volumen; empezar con 1 worker concurrency=2 y escalar si se acumula.
- **LOW:** Compartir con MEDIUM o tener worker dedicado solo si volumen de LOW es muy alto.

**Tu caso (Tu Pana):**
- **HIGH:** Bajo volumen (Excel, batch: decenas/día), urgencia alta → **1 worker, concurrency=1 o 2**.
- **MEDIUM:** Medio volumen (webhooks, sync: cientos/día) → **1 worker, concurrency=2**.
- **LOW:** Muy bajo volumen → **compartir con worker MEDIUM** (mismo worker consume medium,low).

### 4.3 Concurrency por worker

**Concurrency = número de procesos paralelos del worker.**

- **CPU-bound tasks** (Excel parsing, PDF generation): concurrency=1 o 2 (más no mejora; GIL de Python).
- **I/O-bound tasks** (scraping, HTTP, DB queries): concurrency=4-8 (más threads esperan I/O en paralelo).

**Recomendación Tu Pana:**
- **worker-high (Excel, batch):** concurrency=1 (Excel es CPU-bound y pesado; 1 task a la vez es suficiente).
- **worker-medium (webhooks, sync):** concurrency=2 (mix de I/O y CPU).

### 4.4 Recursos por worker (vCPU y memoria)

| Worker | Carga | vCPU recomendado | Memoria recomendada |
|--------|-------|------------------|---------------------|
| **HIGH** (Excel, batch) | CPU-bound, 1 task a la vez | **1 vCPU** (burst OK con Fargate) | **2 GB** (Excel puede usar ~1 GB) |
| **MEDIUM** (webhooks, sync) | I/O-bound, concurrency=2 | **2 vCPU** | **4 GB** |
| **Beat** (scheduler) | Mínimo | **0.5-1 vCPU** | **1-2 GB** |

---

## 5. Solución para Tu Pana: 2 workers activos con coste ~$465/mes

### 5.1 Configuración propuesta (colas ECS separadas, ambos activos)

| Servicio ECS | Config | vCPU | RAM | Tasks | Coste/mes |
|--------------|--------|------|-----|-------|-----------|
| **App** | 2048 / 4096 | 2 | 4 GB | 2 | ~$144 |
| **celery-high** | 1024 / 2048 | 1 | 2 GB | 1 | ~$36 |
| **celery-medium** | 2048 / 4096 | 2 | 4 GB | 1 | ~$72 |
| **celery-beat** | 1024 / 2048 | 1 | 2 GB | 1 | ~$36 |
| **Subtotal ECS** | | | | | **$288** |
| RDS + otros | | | | | $177 |
| **TOTAL** | | | | | **~$465** |

### 5.2 Por qué esta config funciona

1. **Priorización real:**
   - Worker HIGH consume **solo** `pana-celery-queue-high` → si hay Excel/batch, lo procesa inmediatamente.
   - Worker MEDIUM consume **solo** `pana-celery-queue-medium,pana-celery-queue-low` → nunca toca HIGH.

2. **Recursos ajustados:**
   - HIGH: 1 vCPU con concurrency=1 (Excel CPU-bound, 1 task a la vez).
   - MEDIUM: 2 vCPU con concurrency=2 (webhooks I/O-bound, 2 tasks en paralelo).
   - Beat: 1 vCPU (scheduler, uso mínimo).

3. **Isolation:**
   - Si MEDIUM se satura (3.000 mensajes), HIGH sigue vacío y responde en segundos.

4. **Coste:**
   - HIGH 1vCPU/2GB = $36, MEDIUM 2vCPU/4GB = $72, Beat 1vCPU/2GB = $36.
   - App 2×2vCPU/4GB = $144.
   - Total $288 ECS + $177 otros = **$465**.

### 5.3 Cambios en deploy_production.sh

```bash
# App: 2 vCPU / 4 GB × 2 tasks
generate_django_task_definition \
    "pana-backend-app" \
    "2048" \
    "4096" \
    "/ecs/pana-backend" \
    "true"

# Celery High: 1 vCPU / 2 GB × 1 task (solo HIGH)
generate_celery_task_definition \
    "pana-backend-celery-high" \
    "pana-backend-celery-high" \
    "./worker-high.sh" \
    "1024" \
    "2048" \
    "/ecs/pana-backend-celery-high"

# Celery Medium: 2 vCPU / 4 GB × 1 task (MEDIUM + LOW)
generate_celery_task_definition \
    "pana-backend-celery-medium" \
    "pana-backend-celery-medium" \
    "./worker-medium.sh" \
    "2048" \
    "4096" \
    "/ecs/pana-backend-celery-medium"

# Beat: 1 vCPU / 2 GB × 1 task
generate_celery_task_definition \
    "pana-backend-celery-beat" \
    "pana-backend-celery-beat" \
    "./worker-beat.sh" \
    "1024" \
    "2048" \
    "/ecs/pana-backend-celery-beat"

# Update: Celery High con desired-count 1 (antes 0)
aws ecs update-service \
    --cluster pana-backend-cluster \
    --service $CELERY_HIGH_SERVICE_NAME \
    --task-definition $CELERY_HIGH_TASK_ARN \
    --desired-count 1 \
    --region $AWS_REGION
```

### 5.4 Cambios en worker-high.sh

**Reducir concurrency de 2 a 1** (Excel es CPU-bound y pesado; 1 task a la vez es suficiente):

```bash
celery -A backend worker \
  --loglevel=info \
  --concurrency=1 \
  --queues="$QUEUES" \
  --hostname="high@%h"
```

---

## 6. Alternativa: Si el volumen de HIGH es muy alto

Si HIGH recibe **cientos** de Excel/batch por día (no es el caso hoy), escalar:

- **celery-high:** 2 tasks × 1 vCPU = $72 (en lugar de $36).
- Total: $288 + $36 = $324 ECS. Con otros $177 = **$501/mes**.

O aumentar concurrency=2 en HIGH pero mantener 1 vCPU (para tareas I/O como webhooks previos al Excel).

---

## 7. Monitoreo y validación

Tras desplegar, monitorear en CloudWatch y Datadog:

| Métrica | Umbral | Acción si se excede |
|---------|--------|---------------------|
| **CPU High** | > 80% sostenido | Subir a 2 vCPU o reducir concurrency |
| **Memoria High** | > 80% | Subir a 4 GB |
| **Queue length HIGH** | > 10 mensajes > 5 min | Aumentar concurrency o tasks |
| **CPU Medium** | > 80% sostenido | Subir a 4 vCPU o añadir 2da task |
| **Queue length MEDIUM** | > 100 mensajes > 10 min | Escalar Medium horizontalmente |

**Dashboard recomendado:**
- CloudWatch: `ApproximateNumberOfMessagesVisible` por cola (high, medium, low).
- Datadog APM: latencia de tasks por routing key (high vs medium).
- ECS: CPU/Memory utilization por servicio.

---

## 8. Respuesta a "¿Deberíamos tener solo 1 cola con prioridad?"

### NO con SQS

**Razón:** SQS **no tiene prioridad nativa** a nivel mensaje. Las alternativas son:

1. **Colas separadas** (lo que usas hoy) → ✅ Funciona perfecto
2. **Cola única con "prioridad simulada"** (delay messages, visibilityTimeout tricks) → ❌ Complejo y frágil
3. **Celery `queue_order_strategy: 'priority'`** → ❌ Solo funciona con Redis como broker, **no con SQS**

**Conclusión:** Para SQS, **colas separadas + workers dedicados es la única solución confiable** para priorización.

### Alternativa: Redis como broker (si quisieras cambiar)

Si usaras **Redis** en lugar de SQS:
- Podrías tener 1 cola con prioridad interna (message priority 0-10).
- Celery con `queue_order_strategy: 'priority'` procesaría mensajes de mayor prioridad primero.

**Pero:**
- Redis requiere ElastiCache (~$50-100/mes mínimo).
- Más complejo de mantener (persistencia, failover).
- SQS es más simple y serverless.

**Recomendación:** Mantener SQS con colas separadas; es más simple y confiable.

---

## 9. Resumen ejecutivo

### ✅ Lo que debes hacer

- **Mantener 3 colas separadas** (high, medium, low) en SQS.
- **2 workers ECS dedicados:**
  - **celery-high:** 1 task, 1 vCPU / 2 GB, concurrency=1, solo HIGH.
  - **celery-medium:** 1 task, 2 vCPU / 4 GB, concurrency=2, solo MEDIUM+LOW.
- **desired-count=1 en ambos** (no high=0).

### ✅ Coste total: ~$465/mes

- App $144 + Celery High $36 + Celery Medium $72 + Beat $36 + RDS $77 + Otros $100 = **$465**.

### ✅ Garantiza priorización real

- HIGH se procesa inmediatamente (worker dedicado).
- MEDIUM no bloquea HIGH.
- Si HIGH se satura, escalar solo HIGH (añadir 2da task o subir a 2 vCPU).

---

## 10. Checklist de implementación

- [ ] Aplicar cambios en `deploy_production.sh`:
  - App 2048/4096
  - Celery High 1024/2048, desired-count=1
  - Celery Medium 2048/4096, desired-count=1
  - Beat 1024/2048
- [ ] `worker-high.sh`: reducir concurrency=2 a concurrency=1
- [ ] Desplegar y monitorear CPU/memoria en CloudWatch
- [ ] Validar queue length HIGH se mantiene ~0 (sin acumulación)
- [ ] Validar Excel/batch se procesan en <30s desde que el usuario lo dispara
- [ ] Ajustar si CPU High > 80% (subir a 2 vCPU o concurrency=2 si es I/O)

---

## 11. FAQs

### ¿Por qué no poner HIGH en 0 tasks?

Si HIGH está en 0, **no hay worker** para procesar Excel/batch → el usuario ve "Cargando 0 de 1..." indefinidamente. Necesitas **al menos 1 task** en HIGH para que funcione.

### ¿Por qué HIGH solo 1 vCPU si Excel es pesado?

Excel es CPU-bound pero **procesa 1 task a la vez** (concurrency=1). Con Fargate, 1 vCPU puede burst hasta 100% → suficiente para 1 Excel pesado. Si el volumen de Excel sube (varios usuarios en paralelo), escalar a 2 vCPU o 2 tasks.

### ¿Por qué no 1 solo worker con `--queues="high,medium,low"`?

Porque Celery hace **round-robin** sin prioridad real → HIGH espera a MEDIUM. Solo con Redis (no SQS) puedes usar `queue_order_strategy: 'priority'` para que revise high primero.

### ¿Cuándo usar LOW?

Si tienes tareas **muy diferibles** (limpieza de S3, logs antiguos, reportes no urgentes) que pueden esperar horas/días. Si no, LOW es opcional y puedes tener solo HIGH y MEDIUM.

---

## 12. Referencias

- [Celery Priority Strategies](https://moldstud.com/articles/p-ultimate-guide-to-efficient-task-management-demystifying-celery-prioritization-strategies)
- [SQS Priority Pattern (Pulumi)](https://www.pulumi.com/answers/sqs-priority-queuing-in-aws/)
- [Celery Docs: SQS Broker](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/sqs.html)
- [StackOverflow: Multiple Queue Prioritization](https://stackoverflow.com/questions/46204888/prioritizing-queues-among-multiple-queues-in-celery)
- [AWS SQS Priority Queue Samples (GitHub)](https://github.com/aws-samples/sqs-priority-queues)
