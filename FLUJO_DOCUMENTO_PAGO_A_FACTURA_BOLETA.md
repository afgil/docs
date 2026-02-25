# Flujo: Orden → Documento de Pago (100) → Factura/Boleta (33/39) → Emisión

## Resumen

Este documento describe el flujo completo desde una orden externa (ej. Shopify) hasta la emisión de una factura o boleta en Tu Pana, pasando por el documento de pago (tipo 100) y el clonador.

---

## 1. Documento creado en la prueba

### Documento de Pago (ID: 1176202)

| Campo | Valor |
|-------|-------|
| **Tipo** | 100 (Documento de Pago) |
| **Estado** | draft |
| **Fecha** | 2026-02-06 |
| **Monto total** | $119.000 |
| **Emisor** | 77.203.450-4 |
| **Receptor** | 12.345.678-5 (JULIO CESAR VIDAL TUREUNA) |

**Detalles:**

- Producto Test: 1 x $100.000 = $100.000
- Neto: $100.000 | IVA 19%: $19.000 | Total: $119.000

---

## 2. Payload original (orden raw del webhook)

El endpoint POST /v1/documents/payments acepta la **orden raw** del webhook `orders/paid` de Shopify. El backend transforma y construye los detalles.

```json
{
  "order": {
    "id": 12345,
    "order_number": 1001,
    "total_price": "119000",
    "currency": "CLP",
    "taxes_included": true,
    "note_attributes": [
      { "name": "tipo_documento", "value": "factura" },
      { "name": "tupana.rut", "value": "12345678-5" },
      { "name": "tupana.business_name", "value": "Cliente Payment Test" },
      { "name": "tupana.address", "value": "Av Test 123" },
      { "name": "tupana.city", "value": "Santiago" },
      { "name": "tupana.comuna", "value": "Las Condes" }
    ],
    "line_items": [
      {
        "title": "Producto Test",
        "quantity": 1,
        "total": "119000",
        "tax_lines": [{ "price": "19000" }]
      }
    ],
    "shipping_lines": [{ "price": "3500" }]
  },
  "shop": "test-shop.myshopify.com",
  "emitter_rut": "77.203.450-4"
}
```

**Delivery:** Se obtiene de `shipping_lines[].price`. El backend lo agrega como línea "Envío" con conversión a neto si `taxes_included=true`.

**taxes_included:** Si `true`, los montos de `line_items` y `shipping_lines` se convierten a neto (resta `tax_lines` o divide por 1.19). El backend construye los detalles con montos netos.

---

## 3. Clonación

El clonador `PaymentDocumentToInvoiceCloner` copia el documento 100 a un borrador 33 o 39.

### Clonado a Factura (33) – ID: 1176203

| Campo | Valor |
|-------|-------|
| Tipo | 33 (Factura Electrónica) |
| Estado | draft |
| Monto | $119.000 |
| Detalles | Idénticos al documento 100 |

### Clonado a Boleta (39) – ID: 1176204

| Campo | Valor |
|-------|-------|
| Tipo | 39 (Boleta Electrónica) |
| Estado | draft |
| Monto | $119.000 |
| Detalles | Idénticos al documento 100 |

**Conclusión:** El clonador preserva montos, líneas y datos de emisor/receptor. Solo cambia el tipo de documento (33 vs 39).

---

## 4. ¿Llega como factura o boleta?

Depende de `document_type` en el payload original:

| document_type | Target al clonar | Descripción |
|---------------|------------------|-------------|
| `"invoice"` | 33 (Factura) | Cliente con RUT, requiere factura |
| `"receipt"` | 39 (Boleta) | Consumidor final o sin RUT |

**En Shopify** (`buildPaymentPayload`):

- `tipo_documento: "factura"` o `tupana.document_type: "invoice"` → `document_type: "invoice"`
- `tipo_documento: "boleta"` o `same_as_shipping` → `document_type: "receipt"`
- Si hay RUT y no se especifica → factura por defecto

**Frontend actual:** La página Pagos Externos usa `targetTypeCode: '33'` fijo. Debería tomar `document_type` de `order_json` para elegir 33 o 39.

---

## 5. ¿Funcionará la emisión después del clonador?

Sí. El flujo es:

1. **Clonar** → Crea documento DRAFT 33 o 39 con los mismos datos que el 100.
2. **Multi-invoice wizard** → Carga el borrador clonado.
3. **Emitir** → El usuario revisa y emite; el documento pasa a estado emitido con folio SII.

El documento clonado tiene:

- Header, Issuer, Receiver, Details, Total
- Montos correctos (neto, IVA, total)
- Estado DRAFT listo para emisión

**Requisitos para emitir:**

- Credenciales SII configuradas para el emisor
- Receptor con RUT válido (factura) o 66666666-6 (boleta consumidor final)
- Folio disponible en el libro del emisor

---

## 6. Comparación: Orden vs Documento final

### Caso A: Orden Shopify con factura (RUT cliente)

| Etapa | Tipo | Receptor | Monto |
|-------|------|----------|-------|
| Orden Shopify | - | RUT en note_attributes / billing | total_price |
| Doc. Pago (100) | 100 | Mismo RUT, razón social | Mismo monto (neto+IVA) |
| Clonado | 33 | Idéntico | Idéntico |
| Emitido | 33 | Idéntico | Idéntico + folio SII |

**Flujo de datos:** Orden → Payment API → Doc 100 → Cloner → Draft 33 → Emisión → Factura final.

### Caso B: Orden Shopify con boleta (consumidor final)

| Etapa | Tipo | Receptor | Monto |
|-------|------|----------|-------|
| Orden Shopify | - | 66666666-6, "Consumidor final" | total_price |
| Doc. Pago (100) | 100 | 66666666-6 | Mismo monto |
| Clonado | 39 | Idéntico | Idéntico |
| Emitido | 39 | Idéntico | Idéntico + folio SII |

### Caso C: Test script (payload directo)

| Etapa | Tipo | Receptor | Monto |
|-------|------|----------|-------|
| Payload API | document_type: "invoice" | 12345678-5 | 100000 neto + 19% IVA |
| Doc. Pago (100) | 100 | 12.345.678-5 | $119.000 |
| Clonado | 33 o 39 | Idéntico | $119.000 |
| Emitido | 33 o 39 | Idéntico | $119.000 + folio |

---

## 7. Diferencias entre casos

| Aspecto | Factura (33) | Boleta (39) |
|---------|--------------|-------------|
| Receptor | RUT obligatorio (no 66666666-6) | Puede ser consumidor final |
| Uso | Cliente con RUT (empresa/persona) | Venta a consumidor final |
| Origen en Shopify | `tipo_documento: factura` + RUT | `tipo_documento: boleta` o sin RUT |
| document_type | `"invoice"` | `"receipt"` |
| Target clonador | 33 (o 34 si exento) | 39 (o 41 si exento) |

---

## 8. Recomendaciones

1. **Frontend:** Usar `order_json.document_type` para elegir `targetTypeCode` (33 vs 39) en lugar de hardcodear 33.
2. **Paridad:** El clonador crea `DocumentParity` entre el 100 y el documento emitido para trazabilidad.
3. **Emisión:** El documento clonado está listo para emitir; el wizard solo debe cargarlo y permitir la emisión.
4. **IVA exento:** Si `iva_amount = 0`, usar 34 (factura exenta) o 41 (boleta exenta) en lugar de 33/39.
