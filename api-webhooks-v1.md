# API de Webhooks v1

## Descripción General

La API de Webhooks permite gestionar webhooks para notificaciones de eventos de documentos. Esta API es específica por empresa, utilizando automáticamente la empresa del usuario autenticado.

## Endpoint Base

```
POST /api/v1/webhooks/
GET  /api/v1/webhooks/
```

## Autenticación

Requiere autenticación JWT. El usuario debe tener acceso a al menos una empresa.

## Listar Webhooks (GET)

Obtiene todos los webhooks configurados para la empresa del usuario.

### Respuesta Exitosa (200)

```json
[
  {
    "id": 1,
    "url": "https://mi-sistema.com/webhook",
    "events": ["document.issued", "document.delivered"],
    "events_display": ["Emitido", "Entregado"],
    "secret": "mi-clave-secreta",
    "is_active": true,
    "last_status_code": 200,
    "last_sent_at": "2025-01-13T10:30:00Z",
    "success_rate": 95.5,
    "last_delivery": {
      "id": 123,
      "event": "document.issued",
      "is_success": true,
      "status_code": 200,
      "sent_at": "2025-01-13T10:30:00Z",
      "document_id": 456
    },
    "created_at": "2025-01-01T09:00:00Z",
    "updated_at": "2025-01-13T10:30:00Z"
  }
]
```

### Respuesta cuando no hay webhooks (200)

```json
[]
```

### Errores

- **401 Unauthorized**: Usuario no autenticado
- **403 Forbidden**: Usuario sin acceso a entidades

## Crear Webhook (POST)

Crea un nuevo webhook para la empresa del usuario.

### Parámetros de Entrada

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `master_entity_id` | integer | Sí | ID de la entidad maestra para la cual se crea el webhook |
| `url` | string | Sí | URL del endpoint que recibirá las notificaciones |
| `events` | array | Sí | Lista de eventos a notificar. Ver [Eventos Disponibles](#eventos-disponibles) |
| `secret` | string | No | Clave secreta para verificar la autenticidad de las notificaciones |
| `is_active` | boolean | No | Si el webhook está activo (default: true) |

### Ejemplo de Request

```json
{
  "master_entity_id": 123,
  "url": "https://mi-sistema.com/webhook/callback",
  "events": ["document.issued", "document.delivered", "document.rejected"],
  "secret": "mi-clave-secreta-super-segura",
  "is_active": true
}
```

### Respuesta Exitosa (201)

```json
{
  "id": 1,
  "url": "https://mi-sistema.com/webhook/callback",
  "events": ["document.issued", "document.delivered", "document.rejected"],
  "events_display": ["Emitido", "Entregado", "Rechazado SII"],
  "secret": "mi-clave-secreta-super-segura",
  "is_active": true,
  "last_status_code": null,
  "last_sent_at": null,
  "success_rate": 0,
  "last_delivery": null,
  "created_at": "2025-01-13T11:00:00Z",
  "updated_at": "2025-01-13T11:00:00Z"
}
```

### Validaciones

- **URL**: Debe ser una URL válida y única para la empresa
- **Events**: Debe contener al menos un evento válido
- **Secret**: Máximo 255 caracteres

### Errores

- **400 Bad Request**: Datos inválidos

  ```json
  {
    "url": ["Este campo es requerido."],
    "events": ["Debe seleccionar al menos un evento."]
  }
  ```

- **401 Unauthorized**: Usuario no autenticado

- **403 Forbidden**: Usuario sin acceso a entidades

## Eventos Disponibles

| Evento | Descripción |
|--------|-------------|
| `document.issued` | Documento emitido correctamente |
| `document.delivered` | PDF/XML enviado al cliente |
| `document.rejected` | Documento rechazado por el SII |
| `document.paid` | Documento conciliado/pagado |
| `document.cancelled` | Documento anulado o nota de crédito |

## Formato de Notificaciones

Cuando ocurre un evento, se envía una petición POST a la URL configurada con el siguiente formato:

### Headers

```
Content-Type: application/json
User-Agent: Pana-Webhooks/1.0
X-Webhook-Signature: sha256=abc123... (si se configura secret)
X-Webhook-Event: document.issued
X-Webhook-Delivery: 12345
```

### Body

```json
{
  "event": "document.issued",
  "timestamp": "2025-01-13T10:30:00Z",
  "delivery_id": "12345",
  "data": {
    "document_id": 456,
    "folio": "12345",
    "document_type": "33",
    "amount": 2380.00,
    "sender_rut": "76543210-9",
    "receiver_rut": "12345678-9",
    "issue_date": "2025-01-13",
    "xml_file": "https://s3.amazonaws.com/bucket/xml-file-url?signature=...",
    "pdf_file": "https://s3.amazonaws.com/bucket/pdf-file-url?signature=..."
  }
}
```

## Verificación de Seguridad

Si se configura un `secret`, las notificaciones incluyen una firma HMAC-SHA256 en el header `X-Webhook-Signature`.

Para verificar la autenticidad:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

## Consideraciones de Uso

1. **URLs Únicas**: Cada empresa puede tener múltiples webhooks, pero las URLs deben ser únicas por empresa.

2. **Tasa de Éxito**: El sistema calcula automáticamente la tasa de éxito de entregas para cada webhook.

3. **Reintentos**: El sistema reintenta automáticamente las entregas fallidas según una política configurada.

4. **Timeout**: Las notificaciones tienen un timeout de 30 segundos.

5. **Orden**: Los webhooks se procesan en orden de creación.

## Ejemplos de Uso

### Crear Webhook con cURL

```bash
curl -X POST "https://api.pana.cl/api/v1/webhooks/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "master_entity_id": 123,
    "url": "https://mi-app.com/webhooks/pana",
    "events": ["document.issued", "document.rejected"],
    "secret": "my-webhook-secret"
  }'
```

### Listar Webhooks con cURL

```bash
curl -X GET "https://api.pana.cl/api/v1/webhooks/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Notas de Implementación

- El sistema automáticamente asocia el webhook con la primera empresa accesible del usuario.
- Los webhooks se procesan de forma asíncrona para no bloquear operaciones críticas.
- Se mantiene un historial completo de todas las entregas (éxitosas y fallidas).
- Las URLs duplicadas están permitidas entre diferentes empresas pero no dentro de la misma empresa.
