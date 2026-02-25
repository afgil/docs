# Análisis Completo de Optimización de Costos AWS - Tu Pana

**Fecha:** Febrero 2026  
**Región:** us-east-1  
**Infraestructura:** Terraform (pana-backend)

---

## Resumen Ejecutivo

Este documento analiza la infraestructura AWS actual del proyecto Tu Pana (pana-backend) y propone **5 optimizaciones ordenadas de mayor a menor impacto económico**, basadas en la configuración Terraform y las mejores prácticas de AWS Cost Optimization.

---

## Inventario de Servicios AWS Actuales

| Servicio | Configuración Actual | Costo Estimado Mensual |
|----------|---------------------|------------------------|
| **ECS Fargate (App)** | 2 tasks × 4 vCPU, 8GB RAM, 24/7 | ~$290 |
| **ECS Fargate (Celery)** | 4 workers × 0.5 vCPU, 1GB RAM, 24/7 | ~$71 |
| **RDS PostgreSQL** | db.t3.medium, 20GB gp3, Single-AZ | ~$64 |
| **NAT Gateway** | 1 NAT + EIP, 24/7 | ~$33 |
| **ALB** | Application Load Balancer | ~$25-40 |
| **CloudWatch Logs** | 2 log groups, 30 días retención | ~$10-50 |
| **ECR** | Repositorio, lifecycle activo | ~$5-15 |
| **S3** | tupanabucketdata, CloudFront OAI | Variable |
| **CloudFront** | PriceClass_100, cdn.tupana.ai | Variable |
| **SQS** | pana-celery-queue | < $5 |
| **Lambda (Datadog)** | Log forwarder, 1024MB, ARM64 | ~$5-15 |
| **KMS** | Datadog forwarder key | ~$1 |

**Total estimado:** ~$500-600/mes (sin S3/CloudFront según tráfico)

---

## Cómo Verificar en AWS Cost Explorer

1. **AWS Console** → **Billing** → **Cost Explorer**
2. **Granularity:** Monthly
3. **Group by:** Service
4. **Time range:** Last 3 months
5. **Filters:** 
   - Tag `Project` = `pana-backend` (si aplica)
   - O filtrar por región `us-east-1`

### Métricas Clave a Revisar

| Métrica | Ubicación | Qué buscar |
|---------|-----------|------------|
| ECS Fargate vCPU-Hours | Cost Explorer → ECS | Picos vs uso real |
| ECS Fargate GB-Hours | Cost Explorer → ECS | Right-sizing memoria |
| RDS Instance Hours | Cost Explorer → RDS | Uso de db.t3.medium |
| NAT Gateway | Cost Explorer → VPC | Costo fijo + datos |
| CloudWatch Logs | Cost Explorer → CloudWatch | Ingesta y almacenamiento |
| Data Transfer | Cost Explorer → Data Transfer | Salida a internet |

---

## Las 5 Optimizaciones (Mayor a Menor Impacto)

### 1. **ECS Fargate Right-Sizing - App Principal**  
**Impacto estimado: $100-200/mes | Mayor ahorro**

**Problema:** La app Django está configurada con **4 vCPU y 8GB RAM** por task, con **2 tasks** (8 vCPU, 16GB total). AWS Compute Optimizer indica que típicamente hay 30-70% de sobre-dimensionamiento en tareas Fargate.

**Evidencia en Terraform:**
```hcl
# terraform-complete/modules/ecs/main.tf
cpu    = "4096"   # 4 vCPU
memory = "8192"   # 8 GB
desired_count = 2
```

**Acciones recomendadas:**
1. Ir a **AWS Console** → **Compute Optimizer** → **ECS**
2. Revisar recomendaciones de right-sizing para `pana-backend-app`
3. Probar reducir a **2 vCPU / 4GB** por task si Compute Optimizer lo sugiere
4. Mantener 2 tasks para HA, o probar 1 task si el tráfico es bajo

**Terraform (ejemplo de cambio):**
```hcl
cpu    = "2048"   # 2 vCPU
memory = "4096"   # 4 GB
```

**Validación:** Monitorear CPU/Memory en CloudWatch y Datadog durante 1-2 semanas antes de bajar más.

---

### 2. **NAT Gateway → NAT Instance o VPC Endpoints**  
**Impacto estimado: $25-35/mes | Segundo mayor ahorro**

**Problema:** Un NAT Gateway cuesta **~$0.045/hora** ($33/mes) + **$0.045/GB** de datos procesados. Es uno de los costos fijos más altos en muchas cuentas.

**Evidencia en Terraform:**
```hcl
# terraform-complete/modules/network/main.tf
resource "aws_nat_gateway" "main" { ... }
```

**Acciones recomendadas:**
1. **Opción A - VPC Endpoints (recomendado):** Crear Gateway Endpoints para S3 (gratis) y Interface Endpoints para ECR, CloudWatch Logs, Secrets Manager. Reducir tráfico que pasa por NAT.
2. **Opción B - NAT Instance:** Reemplazar NAT Gateway por una instancia t4g.nano (~$3/mes) con NAT AMI. Menos resiliente pero mucho más barato.
3. Revisar en **VPC** → **Flow Logs** o **Cost Explorer** cuántos GB pasan por el NAT.

**Cálculo:** Si pasan ~100GB/mes por NAT: $33 + $4.50 = $37.50. Con VPC Endpoints para S3/ECR, puede bajar a ~$5-10.

---

### 3. **Reducir Workers Celery y/o Usar Fargate Spot**  
**Impacto estimado: $20-45/mes | Tercer mayor ahorro**

**Problema:** 4 workers Celery con Selenium corriendo 24/7. Cada worker tiene 0.5 vCPU + 1GB + contenedor Selenium (1GB). Si la carga de tareas no justifica 4 workers, es desperdicio.

**Evidencia en Terraform:**
```hcl
# terraform.tfvars
celery_worker_count = 4
celery_task_cpu     = 512
celery_task_memory  = 1024
```

**Acciones recomendadas:**
1. Revisar métricas de SQS: mensajes en cola, mensajes procesados/hora.
2. Si la cola suele estar vacía, reducir a **2 workers** (ahorro ~$35/mes).
3. Evaluar **Fargate Spot** para Celery (hasta 70% descuento). Las tareas async toleran interrupciones mejor que la API.
4. Considerar **scaling basado en SQS**: 0 workers cuando no hay mensajes, escalar a N cuando hay carga.

---

### 4. **CloudWatch Logs - Retención y Filtrado**  
**Impacto estimado: $10-30/mes | Cuarto mayor ahorro**

**Problema:** Retención de 30 días en 2+ log groups (`/ecs/pana-backend`, `/ecs/pana-backend-celery`). Los logs se ingieren a Datadog vía Lambda Forwarder, por lo que CloudWatch actúa como buffer. 30 días puede ser excesivo.

**Evidencia en Terraform:**
```hcl
# modules/ecs/main.tf
retention_in_days = 30
```

**Acciones recomendadas:**
1. Reducir retención a **7 días** para logs de ECS (Datadog ya los tiene).
2. Crear **Subscription Filters** para enviar solo logs de ERROR/WARN a un segundo destino si se necesita auditoría larga.
3. Revisar en **CloudWatch** → **Log groups** el volumen de ingestión (GB/mes).
4. Evaluar si Datadog Lambda Forwarder puede usar un filter pattern más estricto para reducir invocaciones.

**Terraform:**
```hcl
retention_in_days = 7
```

---

### 5. **RDS Right-Sizing y Reserved Capacity**  
**Impacto estimado: $15-25/mes | Quinto mayor ahorro**

**Problema:** db.t3.medium (~$62/mes) puede estar sobre-dimensionado. Además, no hay uso de Reserved Instances o Savings Plans para RDS.

**Evidencia en Terraform:**
```hcl
# terraform.tfvars
rds_instance_class = "db.t3.medium"
rds_allocated_storage = 20
```

**Acciones recomendadas:**
1. Ir a **Compute Optimizer** → **RDS** para ver recomendaciones.
2. Si el CPU promedio es < 30%, probar **db.t3.small** (ahorro ~$30/mes).
3. Considerar **RDS Reserved Instance** (1 año) para 30-40% descuento.
4. Revisar **Performance Insights** (si está habilitado) para confirmar que no hay cuellos de botella.
5. `log_statement = "all"` y `log_min_duration_statement = 1000` generan muchos logs; evaluar si es necesario en producción.

---

## Otras Optimizaciones Menores

| Optimización | Ahorro Est. | Esfuerzo |
|--------------|-------------|----------|
| Compute Savings Plans (1 año) para ECS | 20-30% sobre Fargate | Bajo |
| S3 Lifecycle → Glacier para archivos antiguos | Variable según uso | Bajo |
| CloudFront PriceClass_200 → 100 (ya está en 100) | N/A | - |
| ECR: mantener solo 3 imágenes (ya configurado) | Mantener | - |
| Revisar snapshots RDS no usados | $5-20 | Bajo |

---

## Plan de Acción Sugerido

1. **Semana 1:** Habilitar AWS Compute Optimizer y revisar recomendaciones ECS/RDS.
2. **Semana 2:** Implementar right-sizing ECS (empezar por 1 task con recursos reducidos en staging).
3. **Semana 3:** Evaluar VPC Endpoints para S3/ECR y reducir NAT usage.
4. **Semana 4:** Reducir retención CloudWatch a 7 días y revisar Celery worker count.
5. **Mes 2:** Evaluar Reserved Instances o Savings Plans según compromiso a largo plazo.

---

## Referencias

- [AWS Cost Optimization - ECS Fargate](https://docs.aws.amazon.com/prescriptive-guidance/latest/optimize-costs-microsoft-workloads/optimizer-ecs-fargate.html)
- [Cost Optimization Checklist - ECS Fargate](https://aws.amazon.com/blogs/containers/cost-optimization-checklist-for-ecs-fargate/)
- [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/)
- [VPC Endpoints Pricing](https://aws.amazon.com/privatelink/pricing/)
