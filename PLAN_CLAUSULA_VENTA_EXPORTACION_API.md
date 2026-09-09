# Plan: Cláusula de Venta (Incoterm) en DTE de Exportación vía API

**Estado:** implementado
**Fecha:** 2026-09-09
**Branch:** `feat/export-sale-clause-incoterm` (en `pana-backend` y en este repo)
**Origen:** cliente integrado por API (facturador de mercado) necesita emitir una
factura de exportación con cláusula **FOB** en vez de **Ex Works**, y no encuentra
dónde entregar ese dato.
**Alcance:** un único campo nuevo, `sale_clause_code`, de extremo a extremo
(API → modelo → XML → PDF). Todo lo demás del bloque Aduana queda fuera (§6).

---

## 1. Qué pide el cliente

FOB, EXW, CIF, etc. son **Incoterms**: la *cláusula de venta* de una operación de
comercio exterior (hasta dónde llega la responsabilidad y el costo del vendedor).

En un DTE de exportación (110/111/112) no es texto libre: es el campo
`CodClauVenta` del bloque `Encabezado/Transporte/Aduana`, con **códigos propios
del SII** (no ISO). Tabla completa en
`apps/electronic_invoice/services/aduana_codes.py:23`:

| Código | Cláusula | Código | Cláusula |
|---|---|---|---|
| 1 | CIF | 8 | OTROS |
| 2 | CFR | 9 | DDP |
| 3 | **EXW** | 10 | FCA |
| 4 | FAS | 11 | CPT |
| 5 | **FOB** | 12 | CIP |
| 6 | S/CL | 17 | DAT |
| | | 18 | DAP |

`TotClauVenta` (monto bajo la cláusula) es un campo aparte y **no entra en este
plan**: el SII acepta la cláusula sin él — el caso de certificación aprobado
"export 2 CASO 1" declara `CLAUSULA DE VENTA: FOB` sin modalidad ni total (ver
comentario en `document_builder/export.py:113`).

---

## 2. Por qué hoy el cliente "no encuentra dónde entregar el dato"

Dos razones, ambas reales:

1. **El campo no existe.** `ExportDetails`
   (`apps/documents/app_models/export_models.py:97`) guarda país, moneda, tipo de
   cambio, puertos, bultos, `sale_mode` (**modalidad** de venta, que no es la
   cláusula) y `export_type`. No hay cláusula de venta.

2. **La API lo descarta en silencio.** `export_data` se declara como
   `serializers.JSONField(required=False)` (`serializers_refactor.py:1018`): un
   diccionario libre. Si el cliente manda `"sale_clause": "FOB"`, la API responde
   **200 y bota el campo**, sin ningún error que le indique que no existe.

Nota aparte: la referencia pública (`api-reference/documents/batch.mdx:277`)
documenta un `export_data` con campos que no existen en el backend
(`transport_mode`, `destination_country`, `destination_port`, `origin_port`) — el
cliente los buscó ahí. Se corrige en la Fase 5.

---

## 3. Cómo llega el campo al XML

Este cliente es **facturador de mercado**: una `EnrolledCompany` en `PRODUCTION`
emite todos sus tipos de DTE por LibreDTE (`market_billing_policy.py:107`),
incluidos 110/111/112. La cadena es:

```
StrategyIssueMarketBilling._build_dte_data      (strategy_issue_market_billing.py:469)
  └─ DocumentFacturadorAdapter.build(folio)     (document_facturador_adapter.py:78)
       └─ build_document_data(**kwargs)
            └─ ExportDocumentBuilder._post_build (builders.py:445)
                 └─ ExportAduanaBuilder(doc, items, aduana).apply()
```

`ExportAduanaBuilder` **ya emite `CodClauVenta`** (`export.py:122`) — no hay que
tocarlo. Lee la clave `clausula_venta` del dict `aduana` que recibe.

El único hueco: el adapter arma ese dict **solo desde el sidecar del set de
certificación**, así que un documento real recibe `aduana = {}`:

```python
def _payload(self) -> dict:
    """Extras del facturador desde el sidecar sandbox (vacío si no es
    un Document de certificación)."""
    sandbox = getattr(self.document, "sandbox_info", None)
    return getattr(sandbox, "facturador_payload", None) or {}
```
`document_facturador_adapter.py:218`

**Por eso la Fase 3 es obligatoria**: sin pasarle la clave `clausula_venta`, el
campo se guarda en la BD y nunca sale al SII. Es una adición mínima —
`ExportAduanaBuilder` ya se ejecuta hoy con el dict vacío, y `_set` solo escribe
la clave cuando el valor viene, así que agregar `clausula_venta` **añade
`CodClauVenta` al XML y nada más**.

---

## 4. Contrato de API

Endpoint existente: `POST /v1/documents/batch/` (`backend/urls.py:567`). No se
crean endpoints nuevos; se agrega un campo a `export_data`.

| Campo | Tipo | Obligatorio | Descripción | XML |
|---|---|---|---|---|
| `sale_clause_code` | String | No (ver §4.2) | Cláusula de venta / Incoterm, tabla §1 | `CodClauVenta` |

Se acepta **código o nombre** (`"5"` o `"FOB"`): `AduanaCodeResolver` ya resuelve
insensible a mayúsculas y acentos (`aduana_resolver.py:26`). El catálogo es la
tabla estática `CLAUSULA_VENTA` de `aduana_codes.py` — **no se crea tabla en BD**
(país/moneda/modalidad la tienen porque las mantiene el wizard; ésta no la
necesita).

### 4.1 Ejemplo

```json
{
  "documents": [
    {
      "dte_type": "110",
      "export_data": {
        "destination_country_code": "225",
        "currency_code": "13",
        "sale_mode_code": "1",
        "sale_clause_code": "5",
        "exchange_rate": "965.40"
      },
      "details": [
        { "item_name": "Producto exportado", "quantity": 100, "unit_price": 125 }
      ]
    }
  ]
}
```

### 4.2 Validación

- Código fuera de `CLAUSULA_VENTA` → `400`:
  `{"export_data": "sale_clause_code='FOBX' no es una cláusula de venta válida del SII"}`
- Ausente → se emite sin `CodClauVenta`, igual que hoy (**sin cambio de
  comportamiento para los integradores actuales**).

Se valida en el serializer, no en la emisión: cada rechazo del SII quema un
folio (la lección que dejó `ExportServiceIndicatorValidator`).

---

## 5. Implementación

TDD: cada fase parte por sus tests.

### Fase 1 — Modelo
`ExportDetails.sale_clause_code` (`CharField`, opcional).
`makemigrations` (nunca escribir la migración a mano); `migrate` lo corre el
usuario / pipeline.
→ `apps/documents/app_models/export_models.py`

### Fase 2 — API
- `_validate_export_data` (`serializers_refactor.py:1212`): valida el código
  contra `CLAUSULA_VENTA`.
- `ExportService._save_export_data` (`export_service.py:100`) lo persiste;
  `get_export_data()` (`export_service.py:297`) lo devuelve, para que el `GET`
  del documento y la respuesta del batch reflejen lo emitido.
→ `apps/documents/serializers_refactor.py`, `apps/documents/services/export_service.py`

### Fase 3 — Puente al XML (obligatoria, ver §3)
En `DocumentFacturadorAdapter`, pasar `aduana={"clausula_venta": <código>}` cuando
el documento sea 110/111/112 y tenga `export_details.sale_clause_code`. El sidecar
sandbox **mantiene la precedencia** en certificación, para no alterar el set de
pruebas ya aprobado por el SII.
→ `apps/electronic_invoice/services/document_facturador_adapter.py`

### Fase 4 — PDF
Nada que hacer: `custom_invoice_pdf_renderer.py:297` ya lee `CodClauVenta` del XML
y lo imprime como "Cláusula Venta". Hoy sale vacío solo porque el XML no lo trae.

### Fase 5 — Documentación pública (repo `docs`)
`sale_clause_code` documentado en `api-reference/documents/batch.mdx` y en el
schema `ExportData` del OpenAPI. De paso se corrigieron los campos inexistentes
que la referencia describía (§2, nota).

⚠️ **No correr `combine_openapi.py`**: regenera `openapi-combined.json` pisando
el bloque `info` con el del último archivo procesado (el título termina como
"API de Boletas de Honorarios") y reordena los paths. El combinado se editó a
mano para agregar sólo el campo nuevo. Arreglar el script queda pendiente.

Queda sin tocar `api-reference/mdx/documents-batch.mdx`: es una copia obsoleta
que no está en el nav de `docs.json`, y describe campos que nunca existieron
(`export_clause`, `transport_mode`).

---

## 6. Fuera de alcance

Decisión explícita: este plan entrega **solo la cláusula de venta**. No se toca el
resto del bloque Aduana ni el camino MIPYME.

Queda anotado, sin plan asociado: para un DTE de exportación real emitido por
facturador de mercado, el resto de los datos de aduana que el cliente ya manda por
API (país, puertos, bultos, moneda, tipo de cambio, tax ID) se guardan en
`ExportDetails` pero **tampoco llegan al XML**, por el mismo hueco del §3;
`Totales.TpoMoneda` sale hardcodeado `"DOLAR USA"` (`export.py:196`) y
`OtraMoneda.TpoCambio` hardcodeado `950` (`export.py:200`).

---

## 7. Tests

En `apps/<app>/tests/unit/` o `tests/integration/`, y **registrados en
`tests/config.yml`** bajo `pull_request`.

| Test | Qué verifica |
|---|---|
| `test_export_data_accepts_sale_clause_code` | El campo se persiste en `ExportDetails` |
| `test_export_data_accepts_sale_clause_by_name` | `"FOB"` resuelve a `5` |
| `test_export_data_rejects_invalid_sale_clause` | Código fuera de tabla → 400 |
| `test_export_adapter_emits_cod_clau_venta` | Un `Document` real con el campo produce `CodClauVenta` en el XML |
| `test_export_adapter_without_sale_clause_unchanged` | Sin el campo, el XML sale idéntico a hoy (no regresión) |
| `test_export_adapter_sandbox_sidecar_takes_precedence` | El set de certificación sigue leyendo el sidecar |
| `test_export_data_roundtrip_returns_sale_clause` | El `GET` devuelve el campo |

---

## 8. Referencias de código

| Qué | Dónde |
|---|---|
| Tabla de cláusulas de venta | `apps/electronic_invoice/services/aduana_codes.py:23` |
| Emisión de `CodClauVenta` (ya existe) | `apps/electronic_invoice/services/document_builder/export.py:122` |
| Origen del `aduana` (el hueco) | `apps/electronic_invoice/services/document_facturador_adapter.py:218` |
| Ruteo a facturador de mercado | `apps/documents/strategies/issuers/market_billing/market_billing_policy.py:107` |
| Modelo `ExportDetails` | `apps/documents/app_models/export_models.py:97` |
| Validación de `export_data` | `apps/documents/serializers_refactor.py:1212` |
| Persistencia / lectura de `export_data` | `apps/documents/services/export_service.py:100` y `:297` |
| Resolver de códigos | `apps/electronic_invoice/services/aduana_resolver.py:26` |
| PDF (ya lee la cláusula) | `apps/documents/utils/custom_invoice_pdf_renderer.py:297` |
