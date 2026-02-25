# Análisis AWS - Costos Reales y Optimizaciones de Infraestructura

**Fecha:** Febrero 2026  
**Método:** Consulta directa vía AWS CLI (cuenta 390402567331)  
**Nota:** El IAM user `celery-worker` no tiene permisos de Cost Explorer; los costos se estiman con precios públicos AWS us-east-1.

---

## Inventario Real de Recursos

### ECS Fargate (cluster: pana-backend-cluster)

| Servicio | Desired | Running | CPU | Memory | Costo Est. Mes |
|----------|---------|---------|-----|--------|----------------|
| **pana-backend-service** (prod) | 2 | 2 | 8192 (8 vCPU) | 16384 (16 GB) | ~$576 |
| **pana-backend-celery-high** | 1 | 1 | 2048 (2 vCPU) | 4096 (4 GB) | ~$72 |
| **pana-backend-celery-medium** | 1 | 1 | 4096 (4 vCPU) | 8192 (8 GB) | ~$145 |
| **pana-backend-celery** | 0 | 0 | 2048 | 4096 | $0 |
| **pana-backend-staging** | 1 | 1 | 4096 (4 vCPU) | 8192 (8 GB) | ~$145 |
| **pana-backend-celery-staging** | 1 | 1 | 1024 (1 vCPU) | 2048 (2 GB) | ~$36 |
| **pana-backend-celery-beat** (prod) | 1 | 1 | 256 | 512 | ~$9 |
| **pana-backend-celery-beat-staging** | 1 | 1 | 256 | 512 | ~$9 |

**Total ECS estimado: ~$992/mes**

### Colas SQS (6 colas)

| Cola | Mensajes | En vuelo | Estado | Uso en código |
|------|----------|----------|--------|---------------|
| **pana-celery-queue-high** | 0 | 1 | Activa | ✅ settings.py |
| **pana-celery-queue-medium** | 0 | 252 | Activa | ✅ settings.py (default) |
| **pana-celery-queue-staging** | 0 | 0 | Activa | Staging |
| **pana-celery-queue** | 0 | 0 | Fallback | settings.py (si no high/medium) |
| **pana-celery-queue-low** | 0 | 0 | **Sin referencias** | ❌ Orphaned |
| **celery** | 0 | 0 | **Legacy** | ❌ Orphaned |

### RDS

| Instancia | Clase | Storage | Multi-AZ | Costo Est. |
|-----------|-------|---------|----------|------------|
| pana-database-migrated (prod) | db.t3.medium | 30 GB | No | ~$62 |
| pana-backend-staging | db.t3.micro | 40 GB | No | ~$15 |

**Total RDS: ~$77/mes**

### CloudWatch Logs

| Log Group | Retención | Almacenado | Nota |
|-----------|-----------|------------|------|
| /aws/lambda/logtail-aws-lambda | **null (∞)** | **32.2 GB** | ⚠️ Sin retención, coste alto |
| /aws/lambda/datadog-log-forwarder | null | 122 MB | - |
| /aws/lambda/datadog-log-forwarder-staging | null | 131 MB | - |
| /ecs/pana-backend-celery-medium | 30 días | 5.3 GB | - |
| /ecs/pana-backend-celery-high | 30 días | 2.3 GB | - |
| /ecs/pana-backend | 30 días | 1.1 GB | - |
| /ecs/pana-backend-staging | 7 días | 42 MB | OK |

### Otros

- **ALB:** pana-backend-alb (internet-facing)
- **CloudFront:** 2 distribuciones (una: cdn.tupana.ai)
- **S3:** 7 buckets (tupanabucketdata, tupanabucketdata-staging, pana-frontend-images, etc.)
- **ECR:** 1 repo (pana-backend)
- **Lambda:** datadog-log-forwarder, datadog-log-forwarder-staging, logtail-aws-lambda
- **NAT Gateway:** No hay NAT disponibles (posible uso de público en subnets)

---

## Optimizaciones Prioritarias

### 1. Consolidar colas SQS (eliminar colas huérfanas)

**Problema:** 6 colas cuando solo 3 se usan activamente (high, medium, staging).  
**Colas candidatas a eliminar:**
- `celery` – sin referencias en código
- `pana-celery-queue-low` – sin referencias en settings.py
- `pana-celery-queue` – fallback si no hay high/medium; si prod usa high+medium, queda redundante

**Acción:**
1. Confirmar que ninguna tarea periódica de Django Celery Beat usa `pana-celery-queue` o `celery`.
2. Migrar tareas de `pana-celery-queue-low` a `pana-celery-queue-medium` (o eliminarla si está vacía).
3. Eliminar las colas no usadas en AWS Console → SQS.

**Ahorro:** Bajo en dinero, mejora en simplicidad y menos confusión operativa.

---

### 2. Right-sizing app principal (mayor impacto en coste)

**Problema:** App con **8 vCPU y 16 GB por task**, 2 tasks = 16 vCPU, 32 GB total. Suele ser excesivo para una API Django.

**Acción:**
1. Revisar CPU/memoria en CloudWatch o Datadog (p95, p99).
2. Probar en staging: 4 vCPU + 8 GB.
3. Si estabilidad OK, bajar prod a 4 vCPU + 8 GB (o 2 vCPU + 4 GB si la carga es baja).

**Ahorro estimado:** $280–400/mes (reducción ~50 % del coste de la app).

---

### 3. Consolidar workers Celery prod (high + medium)

**Problema:** Dos servicios Celery (high y medium) con tamaños distintos.  
- High: 2 vCPU / 4 GB  
- Medium: 4 vCPU / 8 GB  

Ambos corren 24/7; medium tiene 252 mensajes en vuelo (activa).

**Opciones:**
- **A)** Un solo worker más grande consumiendo de ambas colas (menos complejidad).
- **B)** Mantener separación pero evaluar si high necesita 2 vCPU/4 GB o puede ser más pequeño.

**Acción:** Evaluar en Datadog/CloudWatch uso real de CPU/RAM de celery-high vs celery-medium. Si high está poco cargada, reducir a 1 vCPU / 2 GB.

**Ahorro estimado:** $20–50/mes si se baja el tamaño de celery-high.

---

### 4. CloudWatch: retención en logtail-aws-lambda

**Problema:** `/aws/lambda/logtail-aws-lambda` tiene **32.2 GB** y retención `null` (ilimitada). Aumenta el coste de almacenamiento.

**Acción:**
```bash
aws logs put-retention-policy \
  --log-group-name /aws/lambda/logtail-aws-lambda \
  --retention-in-days 7
```

**Ahorro estimado:** $15–40/mes según volumen de ingesta.

---

### 5. Staging: scale-to-zero fuera de horario

**Problema:** Staging corre 24/7: app (4 vCPU / 8 GB) + celery + beat ≈ $190/mes.

**Acción:**
1. EventBridge + Lambda para poner `desiredCount = 0` fuera de horario (p. ej. 20:00–08:00).
2. O usar AWS Instance Scheduler / scripts similares.

**Ahorro estimado:** ~$90–120/mes si se apaga ~12 h/día.

---

## Resumen de costes estimados

| Componente | Costo Est. Mes |
|------------|----------------|
| ECS Fargate | ~$992 |
| RDS | ~$77 |
| ALB | ~$30 |
| CloudWatch | ~$50–100 |
| S3, CloudFront, Lambda, ECR | Variable |
| **Total aproximado** | **~$1,200–1,300** |

---

## Plan de acción recomendado

| # | Acción | Esfuerzo | Ahorro Est. |
|---|--------|----------|-------------|
| 1 | Poner retención 7 días en logtail-aws-lambda | Bajo | $15–40 |
| 2 | Eliminar colas SQS no usadas | Bajo | Operativo |
| 3 | Right-sizing app (8→4 vCPU, 16→8 GB) | Medio | $280–400 |
| 4 | Reducir celery-high si está infrautilizado | Medio | $20–50 |
| 5 | Scale-to-zero staging fuera de horario | Medio | $90–120 |

**Ahorro total potencial: ~$400–600/mes**

---

## Comandos útiles para validar

```bash
# Ver uso de colas
aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/390402567331/pana-celery-queue-low \
  --attribute-names ApproximateNumberOfMessages

# Ver métricas ECS (requiere CloudWatch)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=pana-backend-service Name=ClusterName,Value=pana-backend-cluster \
  --start-time 2025-02-01T00:00:00Z --end-time 2025-02-15T23:59:59Z \
  --period 3600 --statistics Average
```

---

## Seguridad

Las credenciales compartidas deben rotarse tras este análisis. El usuario `celery-worker` no tiene acceso a Cost Explorer; para ver costos reales usa un usuario/rol con permisos de billing.
