# Análisis de costos AWS - Febrero 2026

**Cuenta:** 390402567331  
**Región:** us-east-1  
**Fuente:** AWS Cost Explorer vía CLI

---

## Resumen de costes reales

| Período | Total (USD) | Notas |
|---------|-------------|--------|
| **Enero 2026** | **568,38** | Completo |
| **Febrero 2026** (1–23) | **899,88** | Estimado → ~1.170 USD proyectado mes completo |

---

## Desglose por servicio (Enero 2026)

| Servicio | Coste (USD) | % del total |
|----------|-------------|-------------|
| **Amazon Elastic Container Service (ECS)** | 274,57 | 48,3 % |
| **Amazon Relational Database Service (RDS)** | 81,18 | 14,3 % |
| **AmazonCloudWatch** | 49,72 | 8,7 % |
| **Amazon Virtual Private Cloud (NAT, etc.)** | 42,23 | 7,4 % |
| **Amazon EC2 Container Registry (ECR)** | 16,94 | 3,0 % |
| **EC2 - Other (incl. ALB)** | 6,96 | 1,2 % |
| **Amazon Elastic Load Balancing** | 0,22 | - |
| **AWS Lambda** | 2,59 | 0,5 % |
| **Amazon Route 53** | 1,10 | 0,2 % |
| **Amazon Simple Queue Service (SQS)** | 0,97 | 0,2 % |
| **Amazon Simple Storage Service (S3)** | 0,60 | 0,1 % |
| **Otros (Secrets Manager, Cost Explorer, etc.)** | < 1 | - |

---

## Desglose Febrero 2026 (parcial, estimado)

Los costes de febrero son más altos; ECS aparece con ~632 USD en el período 1–23 feb (vs 274 en todo enero). Posibles causas: más tasks, más horas de ejecución o cambio de configuración (deploy con más CPU/RAM). Conviene revisar en Cost Explorer por día y por recurso (cluster/servicio ECS).

| Servicio | Coste período 1–23 feb (USD) |
|----------|------------------------------|
| **Amazon Elastic Container Service** | 632,84 |
| **Tax** | 143,67 |
| **Amazon Relational Database Service** | 47,98 |
| **Amazon Virtual Private Cloud** | 40,08 |
| **AmazonCloudWatch** | 13,02 |
| **EC2 - Other** | 9,89 |
| **Amazon EC2 Container Registry** | 10,28 |
| **Otros** | < 5 |

---

## Cómo configurar las API keys AWS en el backend

Para que los scripts y la CLI usen tus credenciales sin hardcodearlas en código:

1. **Abre el archivo `.env`** en la raíz del backend:
   ```bash
   # Ruta típica
   /Users/antoniogil/dev/tupana/pana-backend/.env
   ```

2. **Añade o actualiza estas líneas** (sustituye por tus valores reales):
   ```bash
   AWS_ACCESS_KEY_ID=tu_access_key
   AWS_SECRET_ACCESS_KEY=tu_secret_key
   AWS_REGION=us-east-1
   ```

3. **No subas `.env` a git.** El archivo debe estar en `.gitignore`.

4. **Ejecutar análisis de costos** usando ese `.env`:
   ```bash
   cd /Users/antoniogil/dev/tupana/pana-backend
   ./scripts/aws_cost_analysis.sh
   ```

5. **Rotar credenciales:** Si las keys se han expuesto (por ejemplo en un chat o log), créalas de nuevo en IAM y actualiza `.env`. Las keys que compartiste en texto plano conviene rotarlas por seguridad.

---

## Propuestas para bajar costos (ordenadas por impacto)

### 1. ECS Fargate – Right-sizing (mayor impacto)

- **Situación:** ECS es ~48 % del gasto (Enero) y en Febrero sube mucho. Suele haber sobredimensionamiento en CPU/RAM por task.
- **Acciones:**
  - Revisar en **AWS Compute Optimizer** las recomendaciones para los servicios ECS del cluster.
  - Reducir CPU/memoria por task según recomendación (por ejemplo de 4 vCPU/8 GB a 2 vCPU/4 GB por task) y mantener 2 tasks para HA.
  - Validar en staging primero; luego producción.
- **Ahorro estimado:** 100–250 USD/mes según configuración actual (ver `docs/PLAN_OPTIMIZACION_COSTOS_AWS_COMPLETO.md`).

### 2. VPC – NAT Gateway

- **Situación:** VPC ~42 USD/mes (NAT Gateway + datos).
- **Acciones:**
  - Usar **VPC Endpoints** (Gateway para S3, Interface para ECR, CloudWatch Logs) para reducir tráfico por NAT.
  - O evaluar sustituir NAT Gateway por **NAT Instance** (t4g.nano) si se acepta menos resiliencia.
- **Ahorro estimado:** 25–35 USD/mes.

### 3. CloudWatch Logs

- **Situación:** ~50 USD/mes en Enero.
- **Acciones:**
  - Bajar retención de log groups de ECS a **7 días** (Datadog ya conserva los datos).
  - Revisar volumen de ingesta y filtros de suscripción.
- **Ahorro estimado:** 10–30 USD/mes.

### 4. RDS

- **Situación:** ~81 USD/mes (Enero). No reducir instancia sin revisar picos de CPU (en docs se indica que hubo picos 99 %).
- **Acciones:**
  - Mantener tamaño actual; usar **RDS Reserved Instance** (1 año) para 30–40 % de descuento.
  - Optimizar queries e índices para reducir picos antes de plantear cambio de clase.
- **Ahorro estimado:** 15–25 USD/mes con Reserved.

### 5. ECR

- **Situación:** ~17 USD/mes.
- **Acciones:**
  - Lifecycle policy: mantener solo las últimas N imágenes (p. ej. 3–5).
  - Limpiar imágenes antiguas manualmente si hace falta.
- **Ahorro estimado:** 5–10 USD/mes.

### 6. Celery workers

- **Situación:** Parte del coste ECS.
- **Acciones:**
  - Revisar número de workers y colas SQS; reducir workers si la cola suele estar vacía.
  - Evaluar **Fargate Spot** para workers (hasta ~70 % descuento, aceptando posibles interrupciones).
- **Ahorro estimado:** 20–45 USD/mes según recorte de workers.

---

## Comando de referencia para análisis local

Configura las variables en `.env` y ejecuta:

```bash
cd /Users/antoniogil/dev/tupana/pana-backend
./scripts/aws_cost_analysis.sh
```

Para usar la CLI manualmente (con variables ya cargadas desde `.env`):

```bash
set -a && source .env && set +a
aws ce get-cost-and-usage --time-period Start=2026-01-01,End=2026-02-23 --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE --output table
```

---

## Referencias

- `docs/ANALISIS_OPTIMIZACION_COSTOS_AWS.md` – Análisis inicial de optimización.
- `docs/PLAN_OPTIMIZACION_COSTOS_AWS_COMPLETO.md` – Plan detallado con fases y comandos ECS/RDS.
- `.cursor/rules/awsconfig.mdc` – Uso de variables AWS desde `.env` en el proyecto.
