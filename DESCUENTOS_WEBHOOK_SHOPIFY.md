# Descuentos en el Webhook Shopify orders/paid

## Cómo vienen los descuentos en el webhook

El webhook `orders/paid` de Shopify envía la orden completa. Los descuentos pueden aparecer en varios niveles:

### 1. A nivel de `line_items` (por línea)

Cada `line_item` puede incluir:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `price` | string | Precio unitario **antes** de descuentos |
| `total` | string | Total del ítem **después** de descuentos (ya aplicados) |
| `total_discount` | string | Monto total del descuento asignado a esta línea |
| `discount_allocations` | array | Asignación de descuentos por aplicación |

**Ejemplo de `line_item` con descuento:**

```json
{
  "id": 123456,
  "title": "Producto A",
  "quantity": 2,
  "price": "10000",
  "total": "18000",
  "total_discount": "2000",
  "tax_lines": [...],
  "discount_allocations": [
    {
      "amount": "2000",
      "discount_application_index": 0,
      "amount_set": { "shop_money": {...}, "presentment_money": {...} }
    }
  ]
}
```

- `price`: 10.000 × 2 = 20.000 (antes de descuento)
- `total`: 18.000 (después de descuento)
- `total_discount`: 2.000

### 2. A nivel de orden

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `total_price` | string | Total de la orden (después de todos los descuentos) |
| `total_discounts` | string | Descuento total de la orden |
| `discount_codes` | array | Códigos aplicados: `[{ "code": "VERANO10", "amount": "2000", "type": "percentage" }]` |
| `discount_applications` | array | Aplicaciones de descuento (orden-level o line-level) |

**Ejemplo de `discount_applications`:**

```json
{
  "discount_applications": [
    {
      "target_type": "line_item",
      "type": "discount_code",
      "value": "10.0",
      "value_type": "percentage",
      "allocation_method": "across",
      "code": "VERANO10",
      "title": "Descuento 10%"
    }
  ]
}
```

### 3. Tipos de descuento en Shopify

- **Por porcentaje**: `value_type: "percentage"`, `value: "10.0"` → 10%
- **Por monto fijo**: `value_type: "fixed_amount"`, `value: "5000"` → $5.000
- **Descuento por línea**: `target_type: "line_item"` (se reparte entre líneas)
- **Descuento por orden**: `target_type: "shipping"` o a nivel de orden

### 4. ¿Hay descuentos globales y descuentos por producto?

**Sí.** Shopify distingue por `target_type` y `target_selection`:

| target_type   | target_selection | Descripción                                      |
|---------------|------------------|--------------------------------------------------|
| `line_item`   | `all`            | Descuento global: aplica a todas las líneas      |
| `line_item`   | `entitled`       | Solo a productos que cumplan criterios           |
| `line_item`   | `explicit`       | Solo a productos elegidos explícitamente         |
| `shipping_line` | `all`          | Descuento sobre el envío                          |

- **Global**: `target_type: "line_item"` + `target_selection: "all"` → se reparte entre todas las líneas según `discount_allocations`.
- **Por producto**: `target_selection: "entitled"` o `"explicit"` → solo ciertas líneas reciben descuento.

En ambos casos, el monto asignado a cada línea viene en `line_item.discount_allocations` y el total descontado en `line_item.total_discount`.

### 4.1. ¿Puede existir un descuento global que NO se reparta entre las líneas?

**Depende del target:**

- **Descuentos sobre productos** (`target_type: "line_item"`): **No.** Shopify siempre reparte el descuento entre las líneas. La suma de `discount_allocations` de todas las líneas = descuento total del orden. No hay descuento "flotante" a nivel orden que no aparezca en alguna línea.

- **Descuentos sobre envío** (`target_type: "shipping_line"`): **Sí.** El descuento aplica directamente al costo de envío y **no** aparece en `line_items.discount_allocations`. Solo afecta a `shipping_lines` y a `order.total_price`.

Para un descuento tipo "envío gratis" o "10% en envío", el monto descontado no estará en las líneas de producto; hay que leerlo de `shipping_lines` o de `total_discounts` y restar la parte que ya viene en las líneas.

### 5. ¿Los descuentos se aplican antes o después del IVA?

**Antes del IVA.** En Shopify el orden es:

1. Subtotal de productos (antes de descuento)
2. Se aplican descuentos → subtotal descontado
3. Se calcula IVA sobre el subtotal descontado
4. Total final = subtotal descontado + IVA

Por eso `line_item.total` ya incluye el descuento aplicado, y `tax_lines` contiene el IVA calculado sobre ese total (descontado). Para obtener el neto: si `taxes_included`, restar `tax_lines` del total o dividir por 1.19.

---

## Estado actual en Tupana

### Transformer (`shopify_order_to_payment_payload`)

El transformer usa `total` cuando está disponible. Si `total` coincide con `price*qty` pero hay `total_discount` o `discount_allocations`, resta el descuento para obtener el monto correcto:

```python
# Lógica actual
total_raw = float(item.get("total") or 0)
total_discount = float(item.get("total_discount") or 0)
discount_alloc_sum = sum(...)  # de discount_allocations
if total_raw > 0:
    if (total_discount or discount_alloc_sum) and total_raw == price*qty:
        total = total_raw - discount  # fallback cuando total no incluye descuento
    else:
        total = total_raw
elif total_discount or discount_alloc_sum:
    total = price*qty - discount
else:
    total = price*qty
```

- Usa `item.total` cuando viene descontado
- Fallback: si `total` = `price*qty` y hay descuento, resta `total_discount` o suma de `discount_allocations`

### PaymentDocumentService

- Usa `item.get("discount_percent", 0)` → siempre 0 porque el transformer no lo envía
- No usa `item_total` del transformer; usa `unit_price` y `item_total` del payload

### DocumentDetail (SII)

- Soporta `discount_percent` (porcentaje de descuento por línea)
- Fórmula: `item_total = (quantity × unit_price) × (1 - discount_percent/100)`

---

## Propuesta de manejo de descuentos

### Opción A: Implícito (actual, sin cambios)

**Comportamiento:** Los montos ya vienen descontados en `item.total`. No se registra explícitamente el descuento.

**Pros:** Simple, ya funciona, totales correctos  
**Contras:** El DTE no muestra explícitamente que hubo descuento; solo precios finales

**Cuándo usar:** Si no hay requisito de mostrar descuentos en el DTE.

---

### Opción B: Precio original + discount_percent (recomendada)

**Comportamiento:** Calcular `discount_percent` a partir de `price`, `total` y `quantity`; enviar precio unitario original y `discount_percent` al DTE.

**Fórmula:**

```
subtotal_antes = price × quantity
subtotal_despues = total (ya incluye descuento)
discount_amount = subtotal_antes - subtotal_despues
discount_percent = (discount_amount / subtotal_antes) × 100  si subtotal_antes > 0
```

**Cambios en el transformer:**

```python
# En transform_shopify_order_to_payment_payload, para cada line_item:
price = float(item.get("price") or 0)
total = float(item.get("total") or price)
qty = max(1, int(item.get("quantity") or 1))
subtotal_antes = price * qty

discount_percent = 0
if subtotal_antes > 0 and total < subtotal_antes:
    discount_amount = subtotal_antes - total
    discount_percent = round((discount_amount / subtotal_antes) * 100, 2)

net_total = _to_net_amount(total, tax_lines, taxes_included)
unit_price = int(net_total / qty) if qty else 0  # precio unitario neto (después de descuento)

line_items.append({
    "title": ...,
    "quantity": qty,
    "unit_price": unit_price,
    "total": int(net_total),
    "discount_percent": discount_percent,
})
```

**Nota:** El SII espera `unit_price` = precio unitario antes de descuento, y `discount_percent` para calcular el total. Si usamos `unit_price` = precio después de descuento, el `discount_percent` debe ser 0 y `item_total` = unit_price × quantity. Hay que validar qué formato espera el SII exactamente.

**Opción B1 (precio unitario original):**

```python
unit_price_net = int(net_total / qty)  # precio unitario neto (después de descuento)
# Para SII: unit_price = precio antes de descuento, discount_percent = X
# O: unit_price = precio después, discount_percent = 0
unit_price_antes = int(_to_net_amount(price * qty, tax_lines, taxes_included) / qty)
discount_percent = ...  # calculado
```

**Pros:** El DTE refleja explícitamente el descuento  
**Contras:** Requiere validar formato SII; descuentos a nivel orden pueden estar repartidos entre líneas

---

### Opción C: Usar total_discount de Shopify

**Comportamiento:** Usar `item.total_discount` cuando exista para validar/calcular descuento.

```python
total_discount = float(item.get("total_discount") or 0)
if total_discount > 0:
    subtotal_antes = float(item.get("price") or 0) * qty
    discount_percent = round((total_discount / subtotal_antes) * 100, 2) if subtotal_antes else 0
```

**Pros:** Usa el dato explícito de Shopify  
**Contras:** `total_discount` puede no venir en todos los webhooks (verificar documentación)

---

### Opción D: Descuentos a nivel orden como línea separada

**Comportamiento:** Si hay `order.total_discounts` y no está repartido en líneas, agregar una línea "Descuento" con monto negativo.

**Contras:** El SII puede no aceptar líneas negativas; hay que validar. Alternativa: prorratear el descuento entre las líneas.

---

## Recomendación

1. **Corto plazo:** Implementar **Opción B** (o B1) en el transformer:
   - Calcular `discount_percent` a partir de `price`, `total` y `quantity`
   - Incluir `discount_percent` en el payload de `line_items`
   - Verificar que el PaymentDocumentService y el cloner propaguen `discount_percent` (ya lo soportan)

2. **Validación:** Confirmar con el SII si el formato debe ser:
   - `unit_price` = precio unitario antes de descuento + `discount_percent`, o
   - `unit_price` = precio unitario después de descuento + `discount_percent = 0`

3. **Descuentos a nivel orden:** Si `discount_applications` tiene `target_type` distinto de `line_item`, evaluar prorratear el descuento entre las líneas según `discount_allocations` de cada línea.

---

## Ejemplo de orden con descuento para testing

```json
{
  "id": 12345,
  "order_number": 1001,
  "total_price": "10710",
  "total_discounts": "1890",
  "taxes_included": true,
  "discount_codes": [
    { "code": "VERANO10", "amount": "1890", "type": "percentage" }
  ],
  "line_items": [
    {
      "title": "Producto A",
      "quantity": 2,
      "price": "10000",
      "total": "18000",
      "total_discount": "2000",
      "tax_lines": [{ "price": "3420" }],
      "discount_allocations": [
        { "amount": "2000", "discount_application_index": 0 }
      ]
    }
  ]
}
```

- Subtotal antes: 20.000 × 1.19 = 23.800 (con IVA)
- Descuento 10%: 2.000 neto
- Subtotal después: 18.000 neto
- IVA: 3.420
- Total línea: 21.420
