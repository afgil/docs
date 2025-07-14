---
title: "Batch Documents"
sidebar_position: 3
---

# Batch Documents

Batch Documents – Create up to 100 documents in one call.

## Endpoint

```bash
POST /documents/batch
```

## Description

This endpoint allows you to create multiple documents in a single API call, making it more 
efficient than sending individual requests to the single-document endpoint.

You can include up to 100 documents per request.

For your convenience, an optional idempotency safeguard is available to prevent duplicate 
submissions.

## Headers

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Idempotency-Key | string | No | Prevents duplicate batches (≤ 256 chars, expires after 24 h). |

## Body parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| documents | array | Yes | Up to 100 items. Each item must follow the Documents object schema. |

## Documents object schema

Every element inside the `documents[]` array follows the same schema as the payload accepted by 
the single-document endpoint.

### Top-level fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| folio | integer | No | Sequential number; optional (auto-assigned). |
| date_issued | string (YYYY-MM-DD) | Yes | Invoice date. |
| header | object | Yes | See Header subsection. |
| document_issuer | object | Yes | See Document Issuer subsection. |
| document_receiver | object | No | Required for invoices, optional for receipts. |
| details | array | Yes* | Can be empty; see Detail item subsection. |
| references | array | No | See Reference item subsection. |
| dte_type | object | Yes | Contains the document type code (33, 39, etc). |
| json_param | object | No | Arbitrary JSON stored verbatim. |

### Header

| Field | Type | Required |
|-------|------|----------|
| purchase_transaction_type | integer | Yes |
| sale_transaction_type | integer | Yes |
| payment_method | string | Yes |
| due_date | string | Yes |

### Document Issuer

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| rut | string | Yes | Formatted e.g. 76.543.210-K. |
| business_name | string | Yes | |
| phone_number | string | No | |
| email | string | No | |
| business_activity | string | No | |
| activity_code | int | No | |
| sii_branch_code | string | No | |
| address | string | No | |
| district | string | No | |
| city | string | No | |

### Document Receiver (optional)

Same fields as Document Issuer plus optional contact.

### Document Total

| Field | Type | Required |
|-------|------|----------|
| net_amount | decimal | Yes |
| iva_rate | decimal | Yes |
| iva_amount | decimal | Yes |
| total_amount | decimal | Yes |

### Detail item

| Field | Type | Required |
|-------|------|----------|
| line_number | int | Yes |
| item_name | string | Yes |
| item_description | string | No |
| quantity | number | Yes |
| unit_price | decimal | Yes |
| discount_percent | decimal | No |
| item_total | decimal | Yes |
| item_code | string | No |
| unit | string | No |
| other_tax | decimal | No |
| item_type_code | int | No |

### Reference item

| Field | Type | Required |
|-------|------|----------|
| reference_type | int | Yes |
| reference_folio | int | Yes |
| reference_date | string | Yes |
| reference_reason | string | No |
| dte_type_code | string | Yes |

## Full example object

```json
{
  "date_issued": "2025-06-09",
  "header": { "purchase_transaction_type": 1, "sale_transaction_type": 1, "payment_method": "EF", "due_date": "2025-07-09" },
  "document_issuer": { "rut": "76.543.210-K", "business_name": "Mi Empresa SpA", "phone_number": "+56 2 1234567", "email": "ventas@miempresa.cl", "business_activity": "Wholesale", "activity_code": 47190, "sii_branch_code": "123", "address": "Av. Siempre Viva 123", "district": "Santiago", "city": "Santiago" },
  "document_receiver": { "rut": "12.345.678-9", "business_name": "Cliente Ejemplo Ltda.", "business_activity": "Consulting", "contact": "Juan Pérez", "address": "Camino del Cliente 456", "district": "Providencia", "city": "Santiago" },
  "details": [ { "line_number": 1, "item_name": "Servicio X", "item_description": "Descripción", "quantity": 1, "unit_price": 1000.00, "discount_percent": 0, "item_total": 1000.00, "item_code": "SVC-001", "unit": "UN", "other_tax": 0, "item_type_code": 1 } ],
  "references": [ { "reference_type": 33, "reference_folio": 9876, "reference_date": "2025-05-31", "reference_reason": "Anula folio 9876", "dte_type_code": "33" } ],
  "dte_type": { "code": "33" },
  "json_param": { "customField": "valor" }
}
```

## Example request

```bash
curl -X POST https://api.tupana.cl/documents/batch \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: 8d0e9fe8-3cd2-4a46-a180" \
     -d @payload.json
```

## Success response (201)

```json
{
  "batch_id": "16b84fbf-f771-44ef-a5e5-9fd2d3d25b8d",
  "documents": [
    { "index": 0, "document_id": 2451, "status": "created" },
    { "index": 1, "errors": { "folio": ["missing"] }, "status": "invalid" }
  ]
}
```

## Error codes

| Code | Meaning |
|------|---------|
| 413 | More than 100 documents in the array |
| 422 | Malformed body or validation failure | 