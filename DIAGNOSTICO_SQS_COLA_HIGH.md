# Diagnóstico: cola SQS HIGH no procesada

## Resumen

Las tareas encoladas en **pana-celery-queue-high** (batch de documentos, Excel, etc.) pueden no procesarse por configuración del worker o del entorno. Este doc describe causas y cómo verificarlas.

---

## 1. Inspeccionar colas SQS (mensajes pendientes)

Desde el backend, con variables de entorno de AWS y SQS cargadas (por ejemplo desde `.env`):

```bash
cd /Users/antoniogil/dev/tupana/pana-backend
source env/bin/activate
# Cargar .env si usas uno (export SQS_QUEUE_HIGH_URL=..., AWS_REGION=..., etc.)
python manage.py inspect_sqs_queues
```

Opcional: muestrear más mensajes para ver tipos de tarea:

```bash
python manage.py inspect_sqs_queues --sample-size=200
```

El comando muestra por cada cola (HIGH, MEDIUM, LOW):

- **Mensajes visibles (pendientes)**: en cola sin consumir.
- **Mensajes en procesamiento**: ya tomados por un worker (hasta visibility timeout).
- Tipos de tarea en la muestra (ej. `process_master_entity_batch_documents`, `process_pending_batch_documents`).

Si **HIGH** tiene muchos mensajes visibles y no bajan, ningún worker está consumiendo esa cola.

---

## 2. Causas por las que HIGH no se procesa

### 2.1 Staging: worker.sh solo consumía la cola por defecto

**Problema:** En staging, `DJANGO_ENV=staging`. En `worker.sh` la lógica de colas prioritarias (HIGH + MEDIUM) solo se aplicaba cuando `DJANGO_ENV=production`. En staging se ejecutaba la rama `else`: "Redis local" y `QUEUES=""`, y Celery se arrancaba **sin** `--queues`. Eso hace que el worker solo consuma la cola por defecto (`pana-celery-queue-medium`). Las tareas enviadas a **pana-celery-queue-high** nunca son consumidas.

**Corrección:** En `worker.sh` se debe tratar staging igual que production cuando existan `SQS_QUEUE_HIGH_URL` y `SQS_QUEUE_MEDIUM_URL`, y arrancar el worker con `--queues="pana-celery-queue-high,pana-celery-queue-medium"` (y LOW si aplica). Así el mismo worker consume HIGH y MEDIUM también en staging.

**Nota:** En staging las tres URLs suelen ser la misma (`STAGING_SQS_QUEUE_URL`). Aunque sea una sola cola física en SQS, Celery necesita que el worker escuche por nombre esas colas; si no se pasa `--queues` con high y medium, la cola HIGH (por nombre) no se atiende.

### 2.2 Producción: dos ECS (celery-high y celery-medium)

**celery-high (worker-high.sh):** Solo consume `pana-celery-queue-high`. Requiere `SQS_QUEUE_HIGH_URL` en el task definition. Si falta, el script sale con error. Revisar logs del servicio ECS `pana-backend-celery-high`.

**celery-medium (worker-medium.sh):** Consume `pana-celery-queue-medium` (y `pana-celery-queue-low` si está configurada). Requiere `SQS_QUEUE_MEDIUM_URL`. Revisar logs del servicio ECS `pana-backend-celery-medium`.

### 2.3 Producción: task definitions sin URLs SQS

Si el deploy no inyecta las URLs SQS en los task definitions:

- **celery-high:** debe tener `SQS_QUEUE_HIGH_URL` y `DJANGO_ENV=production`.
- **celery-medium:** debe tener `SQS_QUEUE_MEDIUM_URL` (y opcionalmente `SQS_QUEUE_LOW_URL`) y `DJANGO_ENV=production`.

Comprobar en la consola ECS los task definitions de `pana-backend-celery-high` y `pana-backend-celery-medium`.

---

## 3. Qué worker corre en cada entorno

| Entorno     | Script / ECS           | Consume HIGH | Consume MEDIUM (+ LOW) |
|------------|------------------------|--------------|-------------------------|
| Staging    | `worker.sh`            | Sí (tras fix)| Sí                      |
| Producción | ECS celery-high → `worker-high.sh`   | Sí (solo HIGH) | No  |
| Producción | ECS celery-medium → `worker-medium.sh` | No  | Sí                      |

Staging usa **una sola** cola SQS (misma URL para HIGH/MEDIUM/LOW); el worker debe escuchar por nombre ambas colas para que HIGH se procese. Producción suele tener URLs distintas para HIGH y MEDIUM; el worker unificado tiene un proceso dedicado a HIGH y otro a MEDIUM.

---

## 4. Probar que HIGH se consume (local, CI o producción)

Comando de prueba que envía **una tarea dummy por cola** (sin efectos secundarios): `test_task_high` → HIGH, `test_task_medium` → MEDIUM. Si ambas responden, el worker unificado está consumiendo HIGH y MEDIUM.

### 4.1 Verificación en producción

En el entorno de producción (con variables de prod: `SQS_QUEUE_HIGH_URL`, `SQS_QUEUE_MEDIUM_URL`, AWS, etc.), ejecutar desde el contenedor donde corre la app (por ejemplo ECS Exec al task de web/app o un one-off):

```bash
python manage.py test_celery_unified
```

Opcional: `--wait=60` si la red es lenta.

- Si ves **✅ HIGH: ok-high** y **✅ MEDIUM: ok-medium**, el worker está procesando la cola HIGH (y MEDIUM).
- Si HIGH falla por timeout o error, revisar que el servicio ECS del worker (worker-unified) esté en ejecución y que en sus logs aparezca el arranque con colas `pana-celery-queue-high,pana-celery-queue-medium`.

### 4.2 Local o CI

```bash
# Con .env de staging/prod cargado (SQS_QUEUE_*)
python manage.py test_celery_unified
```

Para solo verificar en tests unitarios que las tareas de batch están en HIGH:

```bash
DJANGO_ENV=test python manage.py test apps.core.tests.unit.test_celery_unified_queues --keepdb
```

---

## 5. Referencia rápida de tareas en HIGH

- `documents.process_pending_batch_documents`
- `documents.process_master_entity_batch_documents`
- `master_entities.build_ready_excel_documents`
- `master_entities.scrape_excel_receivers`
- `core.test_task_high` (solo pruebas)

Si estas tareas aparecen en `inspect_sqs_queues` como mensajes visibles en la cola HIGH y no disminuyen, confirmar que un worker con `--queues="pana-celery-queue-high"` (o high+medium en staging) esté corriendo y estable.
