# Plan: Forma de Pago de Exportación (FmaPagExp) vía API

**Estado:** propuesta, sin implementar
**Fecha:** 2026-09-10
**Branch:** `feat/export-payment-method` (en `pana-backend` y en este repo)
**Origen:** el mismo cliente integrado por API (facturador de mercado) que pidió
la cláusula de venta pregunta por la "condición de pago" de sus facturas de
exportación.
**Alcance:** un único campo nuevo, `export_payment_method_code`, de extremo a
extremo: API → modelo → XML del facturador de mercado → PDF → documentación
pública.
Mismo patrón que la cláusula de venta
([PLAN_CLAUSULA_VENTA_EXPORTACION_API.md](PLAN_CLAUSULA_VENTA_EXPORTACION_API.md),
afgil/pana-backend#4471).

---

## 1. Qué pide el cliente

En un DTE de exportación (110/111/112) la condición de pago es el campo
`IdDoc/FmaPagExp`, **obligatorio** (formato DTE v2.5, campo 14). No es el
`FmaPago` de los documentos nacionales (contado / crédito): la exportación no lo
lleva y usa su propia tabla del SII (`aduana_codes.FORMA_PAGO_EXP`):

| Código | Forma de pago | Código | Forma de pago |
|---|---|---|---|
| 1 | COB1 (cobranza hasta 1 año) | 32 | ANTICIPO |
| 2 | COBRANZA | 50 | ANT/COB (anticipo y cobranza) |
| 11 | ACRED (acreditivo / carta de crédito) | 60 | ANT/CRED (anticipo y acreditivo) |
| 12 | CBOF (cobranza bancaria) | 80 | S/PAGO/COB (sin pago y cobranza) |
| 21 | **S/PAGO (sin pago)** | | |

> "Condición de pago" también puede entenderse como **plazo** (vencimiento o días
> de crédito: `FchVenc`, `TermPagoDias`). Eso es otro trabajo y queda fuera de este
> plan (§7). Se asume que el cliente se refiere a `FmaPagExp`; conviene
> confirmarlo con él antes de implementar.

---

## 2. Estado actual

**Hoy toda factura de exportación emitida por facturador de mercado se declara
al SII como "sin pago" (21), cualquiera sea la forma de pago real.**

1. **La API no tiene dónde recibirlo.** `ExportDetails`
   (`apps/documents/app_models/export_models.py`) no tiene campo de forma de pago
   de exportación, y `export_data` es un `JSONField` libre: si el cliente lo
   manda, se descarta en silencio (el mismo problema que tenía la cláusula).

2. **`header.payment_method` no sirve para exportación, a propósito.**
   `ExportDocumentBuilder._fma_pago()` devuelve `None`
   (`document_builder/builders.py:365`): el esquema de exportación no lleva
   `FmaPago`. Un cliente que manda `"payment_method": "2"` en un 110 no ve ningún
   efecto.

3. **El builder cae al default.** `ExportAduanaBuilder` toma
   `aduana.get("forma_pago_exp")` y, si no viene, usa 21
   (`document_builder/export.py:78`). El adapter no le pasa ese dato:
   `DocumentFacturadorAdapter._aduana()` (`document_facturador_adapter.py:223`)
   hoy sólo completa `clausula_venta`.

### Efecto en el DTE del default 21

El 21 no es inocuo: decide también la conversión a pesos. `ExportOtraMonedaResolver`
(`export.py:37`) elige la estrategia por forma de pago, y con "sin pago" el SII
exige `OtraMoneda/MntTotOtrMnda = 0` (regla HED-1-803). Así que hoy estos
documentos salen con:

- `IdDoc/FmaPagExp = 21`
- `OtraMoneda/MntTotOtrMnda = 0` (el total en pesos anulado)

---

## 3. Cómo llega el dato al XML

Cadena de emisión del facturador de mercado (sin cambios respecto de la cláusula):

```
StrategyIssueMarketBilling._build_dte_data
  └─ DocumentFacturadorAdapter.build(folio)
       └─ _aduana(payload)          ← aquí se agrega forma_pago_exp
            └─ ExportDocumentBuilder
                 └─ ExportAduanaBuilder(doc, items, aduana).apply()
```

`ExportAduanaBuilder` **ya sabe todo lo necesario**; no se toca:

- Resuelve `forma_pago_exp` por código o por nombre (`AduanaCodeResolver`).
- Escribe `IdDoc/FmaPagExp` (`export.py:111`).
- Elige la estrategia de `OtraMoneda` según la forma de pago (`export.py:203`).
- Para ANTICIPO (32) agrega `IdDoc/FchCancel` = fecha de emisión, obligatorio
  según la spec (`export.py:231`).

El cambio en el adapter es el mismo de la cláusula: si el sidecar del set de
certificación no trae `forma_pago_exp`, se completa desde
`export_details.export_payment_method_code`. El sidecar mantiene la precedencia.

---

## 4. Contrato de API

Endpoint existente: `POST /v1/documents/batch/`. Se agrega un campo a
`export_data`.

| Campo | Tipo | Obligatorio | Descripción | XML |
|---|---|---|---|---|
| `export_payment_method_code` | String | No — default `"21"` (S/PAGO) | Forma de pago de exportación, tabla §1 | `IdDoc/FmaPagExp` |

- Se acepta **código o nombre** (`"11"` o `"ACRED"`), igual que `sale_clause_code`.
- Se guarda resuelto a código.
- Si no viene, el documento se emite **exactamente como hoy** (21): no rompe a
  ningún integrador actual.

### 4.1 Ejemplo

```json
"export_data": {
  "destination_country_code": "225",
  "currency_code": "13",
  "sale_mode_code": "1",
  "sale_clause_code": "FOB",
  "export_payment_method_code": "ACRED",
  "exchange_rate": "965.40"
}
```

### 4.2 Validación

- Código o nombre fuera de `FORMA_PAGO_EXP` → `400` con la lista de opciones
  válidas. Igual que con la cláusula, no basta con resolver: `aduana_codes.resolve`
  deja pasar cualquier número tal cual, hay que verificar la pertenencia a la
  tabla.
- Se valida en el serializer, no en la emisión: cada rechazo del SII quema un
  folio.

### 4.3 A confirmar antes de implementar

- **Coherencia con la modalidad de venta.** `sale_mode_code = "9"` también se
  llama "Sin pago". No está verificado si el SII rechaza combinaciones como
  modalidad 9 + forma de pago 11. Revisar la spec antes de decidir si el
  serializer debe validar la combinación o dejarlo pasar.
- **ANTICIPO (32) asume pago en la fecha de emisión.** El builder fija
  `FchCancel = FchEmis`. Si el cliente recibió el anticipo en otra fecha, el DTE lo
  declarará mal. Para este cliente probablemente no aplica; se deja anotado.

---

## 5. Implementación

TDD: cada fase parte por sus tests.

### Fase 1 — Modelo
`ExportDetails.export_payment_method_code` (`CharField`, `blank=True`,
`default=""`). `makemigrations`; `migrate` lo corre el pipeline.
→ `apps/documents/app_models/export_models.py`

### Fase 2 — API
- `DocumentCreateSerializer._validate_export_payment_method`, hermano de
  `_validate_sale_clause`, llamado desde `_validate_export_data`.
- `ExportService._save_export_data` lo persiste sólo si viene la clave (un PATCH
  sin ella no borra el valor guardado, igual que la cláusula);
  `get_export_data()` lo devuelve.
→ `apps/documents/serializers_refactor.py`, `apps/documents/services/export_service.py`

### Fase 3 — Puente al XML (obligatoria)
`DocumentFacturadorAdapter._aduana()`: completar `forma_pago_exp` desde
`export_details.export_payment_method_code`, con el sidecar sandbox manteniendo la
precedencia.
→ `apps/electronic_invoice/services/document_facturador_adapter.py`

### Fase 4 — PDF
Sin esta fase el dato llegaría al SII pero el receptor **no lo vería en el PDF**:

- `dte_pdf_renderer.py:681` oculta la fila "Forma de Pago" en documentos en
  moneda extranjera, con el comentario de que en exportación "sus condiciones de
  pago van en el bloque de Aduana".
- Pero `custom_invoice_pdf_renderer._parse_aduana_from_xml` no lee `FmaPagExp`,
  así que tampoco aparece en el bloque de Aduana.

Cambio: parsear `IdDoc/FmaPagExp`, traducirlo con `FORMA_PAGO_EXP` y agregarlo
como fila "Forma de Pago" del bloque de Aduana, al lado de "Cláusula Venta".
→ `apps/documents/utils/custom_invoice_pdf_renderer.py`, `apps/documents/utils/dte_pdf_renderer.py`

### Fase 5 — Documentación pública (este repo)
- `api-reference/documents/batch.mdx`: agregar `export_payment_method_code` en
  "Campos opcionales" de `export_data` y una sección "Forma de pago de
  exportación" junto a "Cláusula de venta (Incoterm)", con la tabla de códigos.
  Aclarar explícitamente que `header.payment_method` no aplica a exportación.
- Schema `ExportData` en `api-reference/openapi/schemas/schemas.json` y en
  `api-reference/openapi-combined.json`.

⚠️ **No correr `combine_openapi.py`**: pisa el bloque `info` del combinado (el
título queda como "API de Boletas de Honorarios") y reordena los paths. Editar el
combinado a mano, como en la cláusula.

---

## 6. Tests

En `apps/<app>/tests/unit/` o `tests/integration/`, **registrados en
`tests/config.yml`** en las mismas secciones que sus pares de la cláusula.

| Test | Qué verifica |
|---|---|
| `test_export_payment_method_code_is_persisted` | El campo se guarda en `ExportDetails` |
| `test_export_payment_method_accepts_the_name` | `"ACRED"` resuelve a `11` |
| `test_unknown_export_payment_method_is_rejected` | Nombre fuera de tabla → 400 |
| `test_numeric_code_outside_the_sii_table_is_rejected` | `"7"` → 400 |
| `test_document_without_payment_method_is_still_valid` | Sin el campo sigue siendo válido |
| `test_payment_method_reaches_the_aduana_block` | El adapter pasa `forma_pago_exp` |
| `test_certification_sidecar_takes_precedence` | El set de pruebas no cambia |
| `test_fma_pag_exp_is_emitted` | El XML lleva `FmaPagExp = 11` |
| `test_paid_method_converts_total_to_clp` | Con 11, `MntTotOtrMnda` = total × tipo de cambio (no 0) |
| `test_without_payment_method_defaults_to_sin_pago` | Sin el campo el XML sale como hoy: 21 y total en pesos 0 |
| `test_anticipo_sets_fch_cancel` | Con 32, `FchCancel` presente |
| `test_batch_api_captures_payment_method` | HTTP con API key sandbox: `"ACRED"` queda como `"11"` |
| `test_pdf_shows_export_payment_method` | El PDF muestra la forma de pago en el bloque de Aduana |
| `test_pdf_without_payment_method_shows_sin_pago` | Sin el campo el PDF muestra S/PAGO, coherente con el XML |

El test HTTP necesita el mismo parche de `connection.close` que
`test_batch_api_export_sale_clause`. **No usar `TransactionTestCase`**: su flush
falla contra `test_pana` y deja filas residuales.

---

## 7. Fuera de alcance

Queda anotado, sin plan asociado:

- **Plazo de pago (`FchVenc`).** `header.due_date` se acepta y se guarda, pero
  no llega al XML por ningún camino: el adapter del facturador no lo lee, y los
  tres inputs de MIPYME mandan `EFXP_FCH_VENC` vacío a fuego
  (`send_xml_input.py:144`, `xml_firma_input.py:118`, `preview_pdf_input.py:134`).
  Afecta también a facturas nacionales.
- **`TermPagoGlosa` / `TermPagoDias`.** No existen en ningún punto de la emisión.
- **`FmaPago` nacional = 3 (sin costo).** El adapter sólo reconoce contado
  (`is_cash_payment` → 1); cualquier otro valor cae al default 2 (crédito).
- **Camino MIPYME.** Los campos `EDFE_*` no tienen forma de pago de exportación;
  este cliente no usa ese camino.

---

## 8. Referencias de código

| Qué | Dónde |
|---|---|
| Tabla de formas de pago de exportación | `apps/electronic_invoice/services/aduana_codes.py` (`FORMA_PAGO_EXP`) |
| Default 21 cuando no viene | `apps/electronic_invoice/services/document_builder/export.py:78` |
| Escritura de `FmaPagExp` | `export.py:111` |
| Estrategia de `OtraMoneda` por forma de pago | `export.py:37`, `:203` |
| `FchCancel` para ANTICIPO | `export.py:231` |
| Exportación no lleva `FmaPago` | `apps/electronic_invoice/services/document_builder/builders.py:365` |
| Puente `ExportDetails` → `aduana` | `apps/electronic_invoice/services/document_facturador_adapter.py:223` |
| Patrón de validación a copiar | `DocumentCreateSerializer._validate_sale_clause` (`serializers_refactor.py`) |
| Patrón de persistencia a copiar | `ExportService._sale_clause_code` (`export_service.py`) |
| PDF oculta "Forma de Pago" en moneda extranjera | `apps/documents/utils/dte_pdf_renderer.py:681` |
| Parser del bloque Aduana del PDF | `custom_invoice_pdf_renderer._parse_aduana_from_xml` |
