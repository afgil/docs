# Emails duplicados: Resumen semanal de facturas recibidas

## Síntoma

Los clientes reciben **dos** emails del resumen semanal de facturas recibidas:

- Uno con remitente **<dev@send.tupana.ai>** (entorno dev/staging)
- Otro con remitente **<notifications@send.tupana.ai>** (producción)

## ¿Hay dos tasks de facturas recibidas?

**No.** En código solo existe **una** task que envía este resumen:

- **Task:** `documents.send_weekly_received_invoices_summary`
- **Archivo:** `apps/documents/tasks/weekly_summary.py`
- **Flujo:** Task → `WeeklySummaryService.send_weekly()` → `ReceivedInvoiceWeeklySummaryService.send_weekly_summaries()` → por cada empresa con facturas se llama a `EmailService.send_received_invoices_summary_email()`

La migración `apps/scrapers/migrations/0006_create_weekly_received_documents_periodic_task.py` crea otra periodic task, pero es **diferente**: `scrapers.scrape_received_documents_new_clients_weekly` (scraping de documentos recibidos para clientes nuevos), **no** el envío del resumen por email.

## Por qué salen dos remitentes (dev vs notifications)

El remitente del email se define en `apps/core/utils/email_service.py` en `send_received_invoices_summary_email()`:

```python
from_email = (
    "notifications@send.tupana.ai"
    if not settings.DEBUG
    else "dev@send.tupana.ai"
)
```

- **<notifications@send.tupana.ai>** → cuando `DEBUG=False` (producción)
- **<dev@send.tupana.ai>** → cuando `DEBUG=True` (staging/dev)

Si el usuario recibe los dos, significa que **la misma task se está ejecutando en dos entornos** (uno con DEBUG=True y otro con DEBUG=False) y ambos envían al mismo destinatario.

## Causa más probable

1. **Staging y producción** tienen la **misma** periodic task `documents.send_weekly_received_invoices_summary` habilitada (p. ej. “Weekly Received Invoices Summary”).
2. La task se programa a la **misma hora** (o muy próxima) en ambos (p. ej. lunes 14:30 Chile).
3. Staging (DEBUG=True) envía con **dev@** y producción (DEBUG=False) con **notifications@**.
4. Los clientes están en la misma base de datos (o staging usa datos de prod), así que reciben los dos correos.

O bien:

- En la **misma** base de datos (prod) hay **dos** registros en `django_celery_beat.PeriodicTask` con `task = "documents.send_weekly_received_invoices_summary"` (por ejemplo creados con nombres distintos). Beat dispara la task dos veces; si además hay workers de staging y prod consumiendo la misma cola, uno podría ejecutar con DEBUG=True y otro con DEBUG=False, generando los dos remitentes.

## Cómo verificar en producción

En la base de datos de **producción** (o donde corra Beat):

```sql
SELECT id, name, task, enabled, crontab_id, last_run_at
FROM django_celery_beat_periodictask
WHERE task = 'documents.send_weekly_received_invoices_summary';
```

O desde Django shell:

```python
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.filter(task="documents.send_weekly_received_invoices_summary")
for t in tasks:
    print(t.id, t.name, t.enabled, t.crontab, t.last_run_at)
```

- Si hay **más de un registro** con esa task → hay periodic tasks duplicadas; eso puede causar dos ejecuciones y, con workers de dos entornos, los dos remitentes.

## Qué hacer (solución)

1. **Dejar una sola ejecución del resumen**
   - En la BD donde corre Celery Beat (prod), debe haber **solo una** `PeriodicTask` con `task = "documents.send_weekly_received_invoices_summary"` y **enabled=True**.
   - Si hay varias, deshabilitar o borrar las sobrantes (por ejemplo desde Django Admin o con el comando que usa `task_path` para borrar).

2. **Evitar que staging envíe a clientes reales**
   - Opción A: En **staging**, deshabilitar la periodic task “Weekly Received Invoices Summary” (o la que apunte a `documents.send_weekly_received_invoices_summary`).
   - Opción B: Si staging y prod comparten la misma tabla `PeriodicTask`, que **solo en producción** esté habilitada esa task; en staging dejarla `enabled=False`.
   - Así solo un entorno (prod) envía el resumen y los usuarios solo reciben el de **<notifications@send.tupana.ai>**.

3. **Comando para (re)configurar la task**
   - La task se crea/actualiza con:
     `python manage.py setup_received_invoices_weekly_summary_task`
   - Para eliminar la task periódica:
     `python manage.py setup_received_invoices_weekly_summary_task --delete`
   - El comando busca por `task=task_path`; si existen varias con el mismo path, el `--delete` puede fallar por múltiples resultados (habría que borrar duplicados a mano o por script).

## Resumen

| Pregunta | Respuesta |
|----------|-----------|
| ¿Hay dos tasks de código para facturas recibidas? | No, solo una: `documents.send_weekly_received_invoices_summary`. |
| ¿Por qué un email sale de dev y otro de notifications? | El remitente depende de `DEBUG`; los dos correos indican que la misma task se ejecuta en un entorno con DEBUG=True y otro con DEBUG=False. |
| Causa más probable | Misma periodic task habilitada en staging y prod (o dos registros PeriodicTask con la misma task en la misma BD), ejecutándose a la misma hora. |
| Acción | Una sola periodic task habilitada para este resumen; deshabilitar en staging (o el entorno no prod) para que solo prod envíe con notifications@. |
