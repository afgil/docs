# Comparación de campos IssueManager: documento fallido vs VERSU OK

## Objetivo

Comparar **todos los campos** que se envían a `IssueManager.execute()` entre el documento que falla (id 1199055, IssueTry 40976) y facturas VERSU emitidas correctamente (mismo emisor 2332968, tipo 33, producción).

## Parámetros que recibe IssueManager.execute()

- `receiver_data` (dict): rut, business_name, business_activity, contact, address, district, city
- `items_data` (list): item_name, quantity, unit_price, item_total, item_code, item_type_code, unit, discount_percent, item_description
- `date_issued` (str)
- `payment_form` (1=Contado, 2=Crédito)
- `references_data` (list)
- `issuer_data` (dict): business_name, business_activity, activity_code, branch_code, address, district, city, **email**, **phone**, EHDR_CODIGO
- `dte_type`, `code`, `is_partial_credit_note`, `original_amount`, `transport_data`, `export_data`, `vat_withheld`

## Resultado del análisis (script `scripts/compare_issue_manager_payload_versu.py`)

### Diferencias que son solo de negocio (otra factura, otro cliente)

- `date_issued`, `receiver_data.*`, `items_data[0].*` (item_name, unit_price, item_total, item_description, etc.): distinto porque los documentos OK son otras facturas (otros clientes, otros ítems, otras fechas). **No son la causa del fallo.**

### Diferencias que sí pueden afectar al SII

| Campo              | Documento FALLIDO (1199055) | Documentos OK (VERSU)   |
|--------------------|-----------------------------|--------------------------|
| **issuer_data.email** | `None`                      | `'calarach@gmail.com'` o `''` |
| **issuer_data.phone** | `None`                      | `''`                     |

En el documento fallido, el **DocumentIssuer** de VERSU no tiene `email` ni `phone` guardados. En los documentos OK sí (o al menos string vacío).

### Impacto en lo que se envía al SII (XmlFirmaInput)

En `apps/scrapers/mipyme/inputs/xml_firma_input.py`:

- Si `issuer_data.get("email")` es `None`, se usa el **default** `"antoniogiloreilly@gmail.com"`.
- Si `issuer_data.get("phone")` es `None`, se usa el **default** `"963000871"`.

Por tanto, para el documento que falla, al SII se le está enviando:

- **EFXP_EMAIL_EMISOR**: un email que no es de VERSU (email por defecto del código).
- **EFXP_FONO_EMISOR**: un teléfono por defecto.

En las facturas OK, al tener `email` y `phone` en el DocumentIssuer (o `''`), se envía el valor real o vacío, no esos defaults.

**Conclusión:** La única diferencia estructural/riesgosa entre el payload del documento fallido y el de los OK es que el fallido tiene **issuer_data.email** e **issuer_data.phone** en `None`, lo que hace que en el request de XML Firma se usen valores por defecto de otro emisor. No está probado que el SII rechace por eso (el error que devuelve es genérico), pero es la única discrepancia relevante en los campos que se mandan al Issue Manager.

## Recomendaciones

1. **Completar email y teléfono del DocumentIssuer** para la entidad VERSU (o en general para todos los emisores) para que no queden en `None` y no se usen los defaults de `xml_firma_input`.
2. **O** cambiar `XmlFirmaInput` para que cuando `email`/`phone` sean `None` se envíe string vacío `""` en lugar de valores por defecto hardcodeados.

## Cómo reproducir el análisis

```bash
cd /Users/antoniogil/dev/tupana/pana-backend
source env/bin/activate
python scripts/compare_issue_manager_payload_versu.py
```
