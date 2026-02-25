# Configuración de impuestos de Shopify en el webhook orders/paid

## Resumen

La orden de Shopify ya trae el resultado de la configuración de impuestos de la tienda. Debemos usar esos campos para determinar si el documento debe ser afecto (33/39) o exento (34/41).

---

## Campos de impuestos en el webhook

El webhook `orders/paid` envía la orden completa. Shopify incluye:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tax_exempt` | boolean | Si la orden está exenta de impuestos (tienda sin cobro de IVA o cliente exento) |
| `taxes_included` | boolean | Si los precios incluyen impuestos |
| `total_tax` | string | Total de impuestos de la orden |
| `line_items[].tax_lines` | array | Impuestos por línea (price, rate, title) |
| `line_items[].taxable` | boolean | Si el ítem es gravado |

### Fuente

- **GraphQL Admin API**: `Order.taxExempt`, `Order.taxesIncluded`, `Order.totalTaxSet`
- **REST Admin API** (webhook): `order.tax_exempt`, `order.taxes_included`, `order.total_tax`
- API 2023-07+ incluye `tax_exempt` en REST

---

## Lógica de exención

| Condición | Resultado DTE |
|-----------|---------------|
| `tax_exempt === true` | Exento → 34 (factura) o 41 (boleta) |
| `total_tax === "0"` o `0` y sin tax_lines | Exento → 34 o 41 |
| `tax_exempt === false` y `total_tax > 0` | Afecto → 33 o 39 |

**Prioridad:** `order.tax_exempt` es la fuente explícita de la configuración de la tienda. Si no viene, usar `total_tax` y presencia de `tax_lines`.

---

## Conversión a neto cuando tax_exempt

Cuando `tax_exempt === true`:

- La tienda no cobra IVA (o el cliente está exento)
- Los montos de `line_items[].total` ya son finales (no incluyen IVA)
- **No** dividir por 1.19
- Pasar montos tal cual como neto
- El documento 100 debe tener `iva_amount = 0`

Cuando `tax_exempt === false` y `taxes_included === true`:

- Los precios incluyen IVA
- Usar `tax_lines` para restar, o dividir por 1.19 si no hay tax_lines

---

## Costo de delivery (shipping_lines)

El delivery sigue la **misma lógica** que los productos para conversión a neto:

| Escenario | ¿Delivery incluye IVA? | Qué hace el transformer |
|-----------|-------------------------|-------------------------|
| `tax_exempt === true` | No. Monto ya es final | Pasa el precio tal cual (sin dividir) |
| `tax_exempt === false` + `taxes_included === true` | Sí. Precio es bruto | Divide por 1.19 para obtener neto |
| `tax_exempt === false` + `taxes_included === false` | No. Precio ya es neto | Pasa el precio tal cual |

**IVA sobre delivery:** El precio de envío en Shopify suele venir con IVA incluido (precio final al cliente). Para evitar que la factura sume IVA dos veces, se divide por 1.19 para obtener el neto y se marca `delivery_taxable=true`:

| Escenario | Qué hace el transformer |
|-----------|-------------------------|
| `tax_exempt=true` | Envío tal cual (sin dividir), `delivery_taxable=false` |
| `shipping_lines[].tax_lines` con price>0 | Usa tax_strategy (resta tax o divide), `delivery_taxable=true` |
| Sin tax_lines en shipping | Divide por 1.19 (precio incluye IVA), `delivery_taxable=true` |

---

## Flujo de implementación

1. **Transformer** (`shopify_order_to_payment_payload.py`):
   - Leer `order.tax_exempt` (default false si no viene)
   - Si `tax_exempt`: no dividir por 1.19; montos ya son netos
   - Incluir `tax_exempt` en el payload de salida

2. **Strategy** (`shopify_payment_creation_strategy.py`):
   - Leer `tax_exempt` del payload
   - Si `tax_exempt`: `iva_amount = 0`, `total_amount = net_amount`
   - Si no: calcular IVA 19% como hoy

3. **Cloner** (`resolve_target_type_code`):
   - **Prioridad:** usa `tax_exempt` del `order_json` (external_source_data) cuando existe
   - Si `order_json.tax_exempt === true` → 34 o 41 (exento)
   - Si `order_json.tax_exempt === false` → 33 o 39 (afecto)
   - Fallback: `document.document_total.iva_amount == 0` cuando no hay order_json

---

## ShopSettings (opcional futuro)

Si en el futuro se requiere configuración por tienda (override, región, etc.):

- Agregar `tax_exempt_override` o `default_tax_config` en `ShopSettings` (Prisma)
- Por ahora: **usar solo los campos de la orden** (tax_exempt, total_tax)

La orden ya refleja la configuración aplicada por Shopify en el checkout.
