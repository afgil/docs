# Plan: Guía de Despacho (DTE 52) completa vía API + documentación y MCP

**Estado:** implementado (en revisión) — afgil/pana-backend#4616, afgil/docs#61, Tu-Pana/pana-electronic-invoice#9
**Fecha:** 2026-09-14
**Branch:** `feat/delivery-note-api` (mismo nombre en `pana-backend`, `docs` y `pana-electronic-invoice`)
**Origen:** SOCIEDAD INDUSTRIAS DE BALATAS SOINBAL SPA (92.656.000-K), integrado por API con el
facturador de mercado. Ya anuló dos guías (folios 376 y 379).
**Alcance:**
1. Tipo de despacho, dirección de destino y datos de Aduana en la guía de despacho.
2. Líneas exentas con monto en la guía.
3. Validación de `transport_data` y de campos desconocidos, sin romper a los integradores actuales.
4. Los mismos cambios en API v1 y v2.
5. Documentación de la 52 en v1, v2 y guía de usuario.
6. `llms.txt` / `llms-full.txt` pasan a explicar cómo conectarse al MCP.

Patrón a seguir: [PLAN_FORMA_PAGO_EXPORTACION_API.md](PLAN_FORMA_PAGO_EXPORTACION_API.md) y
[PLAN_CLAUSULA_VENTA_EXPORTACION_API.md](PLAN_CLAUSULA_VENTA_EXPORTACION_API.md).

---

## 1. Qué pide el cliente

Sus guías amparan el traslado de mercadería **de exportación** desde la fábrica al puerto o
aeropuerto. El receptor es la agencia de aduanas. La venta ya está en la factura de exportación.

| # | Pedido | Qué pasó |
|---|---|---|
| 1 | Declarar `IndTraslado = 8` (traslado para exportación, no venta) | Mandaron `header.transfer_indicator: 8`. Ese campo no existe, se descartó sin aviso y el folio 379 (doc 7473116) salió con `IndTraslado = 1` (venta) |
| 1b | Poder elegir el tipo de despacho | Hoy sale siempre `TipoDespacho = 3` |
| 2 | Informar el valor de la mercadería sin que se le calcule IVA | El folio 376 (doc 6587094) salió con $7.860 de IVA sobre un traslado exento y lo anularon. Desde entonces emiten con precio 0 |
| 3 | Aviso de folio (webhook) | **Fuera de este plan**: no tienen el webhook configurado |
| — | "Su referencia de API no cubre el DTE 52" | Es cierto: ni `llms-full.txt` ni `batch.mdx` lo documentan |

Además, en la descripción del ítem mandan chofer, patente, transportista, puertos, DUS y
peso, porque no saben que `transport_data` existe.

---

## 2. Qué exige el SII

Fuentes: *Formato Documentos Tributarios Electrónicos* v2.2 (sii.cl,
`factura_electronica/factura_mercado/formato_dte.pdf`) y el esquema oficial `DTE_v10.xsd`.
Obligatoriedad: 1 = obligatorio, 2 = condicional, 3 = opcional.

### 2.1 Encabezado

| Campo | Guía | Regla |
|---|---|---|
| `IdDoc/IndTraslado` | obligatorio | 1 venta · 2 venta por efectuar · 3 consignación · 4 entrega gratuita · 5 traslado interno · 6 otros traslados no venta · 7 guía de devolución · **8 traslado para exportación (no venta)** · 9 venta para exportación. *"8 y 9: para exportaciones, cuando se dirige la mercadería hacia el puerto, aeropuerto o aduana de embarque"* |
| `IdDoc/TipoDespacho` | 2 | 1 por cuenta del receptor · 2 por cuenta del emisor a instalaciones del cliente · 3 por cuenta del emisor a otras instalaciones. Con `IndTraslado = 5` no se envía: el SII lo reparó en certificación |
| `Transporte/Patente`, `RUTTrans` | 2 | Relevantes si `TipoDespacho` es 2 o 3. Patente de 8 caracteres como máximo |
| `Transporte/Chofer` | 2 | Si va el RUT del chofer, va también el nombre (máximo 30) |
| `Transporte/DirDest` · `CmnaDest` · `CiudadDest` | 2 · 2 · 3 | Largo 70 · 20 · 20. *"Aplica si el destino es distinto de la dirección del receptor"* |

### 2.2 `Transporte/Aduana` en la guía

La tabla del SII dice textual *"En Guías: obligatorio sólo para Indicador tipo traslado = 8 y 9"* para:

| Campo | Largo / tipo | Tabla |
|---|---|---|
| `CodPtoEmbarque` | 4 NUM | Puertos de Aduana (ej. 906 San Antonio, 992 Aerop. A. M. Benítez) |
| `CodPtoDesemb` | 4 NUM | Puertos de Aduana (ej. 134 New York, 292 Santos) |
| `PesoBruto` | 10 enteros + 2 decimales | — |
| `CodUnidPesoBruto` | 2 NUM | Unidades de medida de Aduana (6 = KN) |

Opcionales en la guía: `TotBultos` / `TipoBultos{CodTpoBultos, CantBultos, Marcas...}`,
`PesoNeto`/`CodUnidPesoNeto`, `NombreTransp`, `Booking`, etc.

> **Decisión (2026-09-14): se sigue la tabla del SII sin pruebas en certificación.** La nota
> general del sub-área dice que la información se registra *"sólo si se dispone de ella al
> momento de confeccionar el documento; en caso contrario bastará que vaya escrita en la
> representación impresa"*, pero la tabla de campos dice **obligatorio** para traslado 8/9. Se
> toma lo más estricto: con 8/9 la API exige puertos, peso bruto y unidad.

**Orden dentro de `Aduana` según el XSD** (importa, ver §6.2): `CodModVenta, CodClauVenta,
TotClauVenta, CodViaTransp, NombreTransp, RUTCiaTransp, NomCiaTransp, IdAdicTransp, Booking,
Operador, CodPtoEmbarque, IdAdicPtoEmb, CodPtoDesemb, IdAdicPtoDesemb, Tara, CodUnidMedTara,
PesoBruto, CodUnidPesoBruto, PesoNeto, CodUnidPesoNeto, TotItems, TotBultos, TipoBultos,
MntFlete, MntSeguro, CodPaisRecep, CodPaisDestin`.

### 2.3 Detalle y totales

- `Detalle/IndExe = 1`: *"no afecto o exento de IVA"*. Su monto suma a `Totales/MntExe` y no genera IVA.
- **No usar `IndExe = 4`** ("ítem no venta"): el SII lo permite sólo en guías con `IndTraslado = 1`.
- En la guía los montos (`MntNeto`, `MntExe`, `IVA`) son opcionales (3). Una guía puede llevar valor.
- La regla de que "si todos los ítems son exentos no puede ser 33" aplica a facturas, no a guías.

---

## 3. Estado actual (verificado sobre `origin/master` fd4c3e01b y en producción)

### 3.1 API

1. **v1 y v2 comparten vista y serializers.** `POST /v1/documents/batch/` y
   `POST /api/v2/documents/batch/` usan `DocumentBatchCreateAPIView` →
   `DocumentBatchCreateSerializer` → `BulkDocumentItemSerializer(DocumentCreateSerializer)`.
   v2 sólo cambia la **respuesta** (`V2ResponseMixin`: sobre `{data, meta, links}`, `public_id`,
   `?fields=`). **El payload de entrada es idéntico**, así que un cambio en el serializer queda
   en las dos versiones. Lo que hay que duplicar es la documentación y las respuestas (§4.6).
2. **`transport_data` es un `JSONField` libre** (`serializers_refactor.py:1037`), sin validación.
   `TransportService.save_transport_data` hace `TransportData.objects.create(**transport_data)`
   dentro de `try/except Exception` (`transport_service.py:20-44`). **Una llave desconocida
   descarta la fila entera sin avisar** y la guía se emite como venta.
3. **Bug:** `DocumentCreateSerializer.create/update` llaman a `document._save_transport_data(...)`
   (`serializers_refactor.py:1571, 1739, 2045, 2324`), y ese método **no existe** (el real es
   `save_transport_data`). La actualización por batch con `id` y las programadas
   (`scheduled_document_batch_mixin.py:790`) revientan con `AttributeError` si traen transporte.
4. **`DocumentDetail` no tiene flag de exención** y `InvoiceTotalBuilder` sólo sabe de exención
   total del documento (por tipo o por referencia). `DocumentTotal.exempt_amount` existe, pero
   nunca se llena.
5. **Las respuestas no devuelven transporte.** `GET /v1/documents/{id}` y
   `GET /api/v2/documents/{id}/` (`DocumentDetailAPIView`) no incluyen `transport_data`,
   `export_data` ni `exempt_amount`. El batch sólo devuelve `export_data` para 110-112.
6. **`dte_type` desconocido cae a 33 sin avisar** (`serializers_refactor.py:280-284`).
7. **Los errores de validación del batch responden 422**, no 400 (`batch_views.py:810, 824, 1056`).
8. **Flujo gateway:** a los clientes con `routing_mode = gateway_queued` los atiende una Lambda
   (`lambdas/gateway_batch_validator`), que valida sólo estructura y responde 202. Django valida
   después, y si falla el documento queda en `standby` sin respuesta 4xx al cliente.

### 3.2 Medición: qué mandan hoy los integradores

Lectura de `BatchDocument.input_payload`, fuente API, últimos 90 días: **466.154 documentos,
175 combinaciones emisor/API key, 1.498 guías (52)**.

- **65 de 175 mandan llaves que los serializers no declaran.** Parte son contrato real que se
  lee directo del payload crudo (`header.authorized_user_rut`, `is_sandbox`, `payment_status`,
  `master_entity_id`). Otras no las lee nadie:

| Nivel | Llaves que nadie lee (docs) | Quién |
|---|---|---|
| `header` | `currency` (125), `comment` (53), **`transfer_indicator` (6)**, `rut_mandante` (1) | exportadores, SOINBAL |
| `document_issuer` | `country` (1.194), `phone` (19), `contact` (8) | |
| `document_receiver` | `country` (1.227), `email` (792)\*, `foreign_tax_id` (142), `commune` (35), `activity` (34), `tax_id` (8) | |
| `export_data` | **`transport_mode` (149), `destination_country` (149), `export_clause` (147)**, `export_receiver_city/address` (21), `origin_port`, `destination_port` (3) | 5 exportadores (API keys 207, 320, 342, 354, 341) |
| `details`, `transport_data` | ninguna | |

\* `email` hay que verificarlo en la auditoría (§8.1): puede leerse fuera del serializer.

- **Los nombres de `export_data` que nadie lee son los del ejemplo desactualizado de
  `llms-full.txt`.** La documentación vieja está haciendo que al menos 5 exportadores pierdan la
  cláusula de venta sin enterarse. Por lo mismo, **rechazar campos desconocidos no se puede
  activar de golpe** (§8).
- Todas las guías con `transport_data` usan sólo llaves válidas. Los 1.124 casos quedaron en BD.

### 3.3 Emisión: facturador de mercado

Cadena: `StrategyIssueMarketBilling._build_dte_data` → `DocumentFacturadorAdapter.build()` →
`GuiaDocumentBuilder` → `libredte_client` →
`POST {LIBREDTE_API_URL}/documentos/construir` con
`{"document_data": <dict>, "caf_xml", "certificate_base64", "certificate_pass"}`. El dict llega
**tal cual** al `DocumentBag` de lib-core; en Python sólo se sanea a Latin-1.

- `IndTraslado`: sale de `transport_data.transport_type` (PR #4353).
- `TipoDespacho`: se infiere del texto `dispatched_by`, que sólo existe en el set de
  certificación. **En producción sale siempre 3.**
- `Transporte`: `Patente`, `RUTTrans` y `Chofer`. **No hay `DirDest`/`CmnaDest`/`CiudadDest`.**
- `Aduana`: sólo la arma `ExportAduanaBuilder`, y sólo para 110-112. No sirve tal cual para la
  guía, porque además fuerza receptor extranjero (55555555-5), `OtraMoneda` y `FmaPagExp`.
  Tampoco emite en orden de XSD: funciona en exportación porque PHP reordena.
- `IndExe`: sólo desde el sidecar del set de certificación (`line_exempt`).

### 3.4 Microservicio `pana-electronic-invoice` (lib-core)

- **Los totales los calcula lib-core desde el `Detalle`** (`NormalizeDetalleTrait`,
  `NormalizeIvaMntTotalTrait`). Python **no debe mandar `Totales`**: se duplican.
- `NormalizeTransporteTrait` ordena sólo las llaves de primer nivel de `Transporte`. **El interior
  de `Aduana` no se reordena para la 52.**
- `NormalizeGuiaDespachoJob` parte de `MntNeto: 0, TasaIVA: 19, IVA: 0`. Con todas las líneas
  exentas el XML sale con `MntNeto 0, MntExe X, TasaIVA 19, IVA 0, MntTotal X`. La nota de
  crédito sí quita `TasaIVA` cuando no hay neto (`NormalizeNotaCreditoJob.php:93-96`); la guía
  no. Se corrige en lib-core (§6.3).
- Los validadores y sanitizadores específicos de la guía están vacíos: `Transporte` y `Aduana`
  pasan sin chequeo.

### 3.5 PDF

- `DeliveryNoteTransportSection` no muestra el destino.
- **Bug:** `_parse_aduana_from_xml` busca `CodPtoEmb`, pero el tag es `CodPtoEmbarque`
  (`custom_invoice_pdf_renderer.py:431`). El puerto de embarque nunca se imprime, tampoco en la 110.
- **Bug:** `ind = "EX" if ind_exe == "2" else "AF"` (`custom_invoice_pdf_renderer.py:493`).
  Una línea con `IndExe = 1` se rotula como afecta.

### 3.6 Facturador gratuito (MiPyme)

En el payload del portal (`base_payload_builder_input.py`) no hay nada para `TipoDespacho`,
destino, Aduana ni exención por línea. En el repo no hay un HTML guardado del formulario, así
que **no se sabe si el portal los admite** (§7).

---

## 4. Contrato de API

Endpoint existente: `POST /v1/documents/batch/` y `POST /api/v2/documents/batch/`, con el mismo
payload. No cambia ningún campo actual; todo lo nuevo es opcional.

### 4.1 `transport_data`

Pasa de `JSONField` a un serializer anidado real, `TransportDataInputSerializer`.

| Campo | Tipo | Nuevo | Obligatorio | Validación | XML |
|---|---|---|---|---|---|
| `transport_type` | string `"1"`–`"9"` | — | No (default `"1"`, como hoy) | Tabla §2.1 | `IdDoc/IndTraslado` |
| `dispatch_type` | string `"1"`–`"3"` | **sí** | No (default: comportamiento actual, 3; se omite con traslado 5) | Rechazado con `transport_type = "5"` | `IdDoc/TipoDespacho` |
| `transport_rut` | string | — | No | `ChileanIdentifier` | `Transporte/RUTTrans` |
| `transport_plate` | string | — | No | Se normaliza (mayúsculas, sin guion ni espacios) y queda en ≤ 8 | `Transporte/Patente` |
| `driver_rut` | string | — | No | `ChileanIdentifier` | `Transporte/Chofer/RUTChofer` |
| `driver_name` | string | — | No | ≤ 30 al emitir (§4.5) | `Transporte/Chofer/NombreChofer` |
| `destination_address` | string ≤ 70 | **sí** | No | | `Transporte/DirDest` |
| `destination_district` | string ≤ 20 | **sí** | No | | `Transporte/CmnaDest` |
| `destination_city` | string ≤ 20 | **sí** | No | | `Transporte/CiudadDest` |
| `departure_port_code` | string | **sí** | **Sí con traslado 8/9** (§2.2) | Código o nombre de la tabla de puertos | `Aduana/CodPtoEmbarque` |
| `arrival_port_code` | string | **sí** | Ídem | Ídem | `Aduana/CodPtoDesemb` |
| `gross_weight` | decimal (10,2) | **sí** | Ídem | > 0 | `Aduana/PesoBruto` |
| `gross_weight_unit_code` | string | **sí** | Ídem | Tabla de unidades de Aduana | `Aduana/CodUnidPesoBruto` |
| `total_packages` | int | **sí** | No | > 0 | `Aduana/TotBultos` + `TipoBultos/CantBultos` |
| `package_type_code` | string | **sí** | Si viene `total_packages` | Tabla de tipos de bulto | `Aduana/TipoBultos/CodTpoBultos` |
| `timber_enabled` y campos CONAF | — | — | No | Como hoy | `ManejoMadera` |

Decisiones:
- **Nombres iguales a `export_data`** donde el concepto coincide (`departure_port_code`,
  `arrival_port_code`, `total_packages`), para que un exportador use las mismas llaves en la
  guía y en la factura.
- **Aduana va plano dentro de `transport_data`**, como hoy los campos CONAF, y no en
  `export_data`: en la guía, `export_data` exige país, moneda y modalidad de venta, que no aplican.
- **Los códigos aceptan código o nombre** (`"992"` o `"AEROP.A.M.BENITEZ"`), igual que la
  cláusula de venta. Se guardan resueltos a código. **Hay que validar la pertenencia a la tabla**:
  `AduanaCodeResolver` deja pasar cualquier número tal cual.
- Los campos de Aduana con un `transport_type` distinto de 8/9 → 422: no corresponden.

### 4.2 `details[]`

| Campo | Tipo | Nuevo | Default | Validación | XML |
|---|---|---|---|---|---|
| `is_exempt` | bool | **sí** | `false` | Sólo en DTE 52 en esta etapa. En otro tipo → 422 "no soportado para este tipo de documento" | `Detalle/IndExe = 1` |

Se deja sin flag a nivel documento, para que haya una sola forma: si todo es exento, se marcan
todas las líneas. Extenderlo a 33/56/61 queda fuera (§14).

### 4.3 Ejemplo (el caso de SOINBAL)

```json
{
  "documents": [{
    "dte_type": {"code": "52"},
    "date_issued": "2026-09-15",
    "document_issuer": {"rut": "92656000-K"},
    "document_receiver": {"rut": "<RUT agencia de aduanas>", "business_name": "AGENCIA DE ADUANAS FRANCISCO PARDO Y CIA LTDA"},
    "transport_data": {
      "transport_type": "8",
      "dispatch_type": "3",
      "transport_rut": "<RUT TLH>",
      "transport_plate": "PJRL69",
      "driver_rut": "10134136-4",
      "driver_name": "Jose Valenzuela",
      "destination_address": "Aeropuerto Arturo Merino Benitez",
      "destination_district": "Pudahuel",
      "destination_city": "Santiago",
      "departure_port_code": "992",
      "arrival_port_code": "134",
      "gross_weight": "1414.00",
      "gross_weight_unit_code": "6",
      "total_packages": 3,
      "package_type_code": "22"
    },
    "details": [{
      "item_name": "BALATAS DE FRENO",
      "item_description": "Partida arancelaria 6813.81.00",
      "quantity": 3,
      "unit_price": 1350000,
      "is_exempt": true
    }],
    "references": [{
      "dte_type_code": "807",
      "reference_folio": "13717477-4",
      "reference_date": "2026-09-15",
      "reference_reason": "DUS 13717477-4"
    }]
  }]
}
```

### 4.4 Validación y errores

- Se valida en el serializer, no al emitir: cada rechazo del SII quema un folio.
- Errores con **422**, igual que el resto del batch. En v2 se envuelven en el formato de
  errores v2 (`apps/api/v2_errors.py`); hay que agregar códigos en `api-reference/v2/errors.mdx`.
- Mensajes con la ruta del campo y las opciones válidas, por ejemplo:
  `{"documents": [{"transport_data": {"dispatch_type": ["Valor inválido. Opciones: 1, 2, 3."]}}]}`.

### 4.5 Compatibilidad con integradores actuales

| Cambio | ¿Rompe? | Mitigación |
|---|---|---|
| Campos nuevos opcionales | No | Default = comportamiento actual |
| `transport_data` pasa a serializer | Podría, si alguien manda valores hoy inválidos (patente > 8, chofer > 30, RUT malo) | Medir antes (§8.1). Normalizar y truncar en vez de rechazar para lo que ya se acepta: el portal MiPyme ya trunca patente a 8 y chofer a 30. El facturador hoy no trunca y el XSD lo rechazaría |
| Chofer con sólo RUT o sólo nombre | Hoy el facturador lo descarta sin avisar | Medir. Si nadie lo manda así → 422 |
| Llaves desconocidas | **Sí, para 65 clientes** | §8: modo por API key |
| `dte_type` desconocido cae a 33 | Sí, si alguien depende de eso | Queda dentro del modo estricto (§8) |

### 4.6 Respuestas (v1 y v2)

Hoy ningún `GET` devuelve el transporte. Se agrega en:
- `DocumentDetailAPIView` (`GET /v1/documents/{id}` y `GET /api/v2/documents/{id}/`):
  `transport_data` completo (con los campos nuevos), `details[].is_exempt` y
  `document_total.exempt_amount`. En v2 respetando `?fields=`.
- `GET /v1/documents/batch/{uuid}` (`DocumentBatchDetailSerializer.get_documents`) y la
  respuesta del `POST` batch (`_build_batch_response`).
- `TransportService.get_transport_data` y el `TransportDataSerializer` de salida, que hoy
  exponen la mitad de los campos.

---

## 5. Modelos y migraciones

Todo en `apps/documents`, con `makemigrations`. `migrate` lo corre el pipeline.

| Modelo | Cambio |
|---|---|
| `TransportData` | `dispatch_type` (CharField 1, choices 1-3, `blank=True`, default `""`) · `destination_address` (70) · `destination_district` (20) · `destination_city` (20) · `departure_port_code` (4) · `arrival_port_code` (4) · `gross_weight` (Decimal 12,2, null) · `gross_weight_unit_code` (2) · `total_packages` (PositiveInteger, null) · `package_type_code` (3). Todos opcionales |
| `DocumentDetail` | `is_exempt` (BooleanField, default `False`). La tabla es grande: verificar que en Postgres sea `ADD COLUMN ... DEFAULT false` sin reescritura (PG ≥ 11 lo hace así) |
| `DocumentTotal` | Sin cambio de esquema: se empieza a llenar `exempt_amount` |

Se descartó guardar Aduana de la guía en `ExportDetails`: exige país, moneda, tipo de cambio y
modalidad de venta, y relajarlo afectaría la validación de la 110.

---

## 6. Payload al microservicio LibreDTE

### 6.1 `document_data` resultante (caso §4.3)

```python
{
  "Encabezado": {
    "IdDoc": {"TipoDTE": 52, "Folio": 380, "FchEmis": "2026-09-15",
              "TipoDespacho": 3, "IndTraslado": 8},
    "Emisor": {...},
    "Receptor": {...},              # la agencia de aduanas, NO receptor extranjero
    "Transporte": {
      "Patente": "PJRL69",
      "RUTTrans": "<RUT>",
      "Chofer": {"RUTChofer": "10134136-4", "NombreChofer": "Jose Valenzuela"},
      "DirDest": "Aeropuerto Arturo Merino Benitez",
      "CmnaDest": "Pudahuel",
      "CiudadDest": "Santiago",
      "Aduana": {                   # EN ORDEN DE XSD (§2.2)
        "CodPtoEmbarque": 992,
        "CodPtoDesemb": 134,
        "PesoBruto": 1414.00,
        "CodUnidPesoBruto": 6,
        "TotBultos": 3,
        "TipoBultos": [{"CodTpoBultos": 22, "CantBultos": 3}]
      }
    }
    # SIN "Totales": lib-core los calcula desde el Detalle
  },
  "Detalle": [{"NroLinDet": 1, "NmbItem": "BALATAS DE FRENO", "DscItem": "...",
               "QtyItem": 3, "PrcItem": 1350000, "MontoItem": 4050000, "IndExe": 1}],
  "Referencia": [{"NroLinRef": 1, "TpoDocRef": "807", "FolioRef": "13717477-4",
                  "FchRef": "2026-09-15", "RazonRef": "DUS 13717477-4"}]
}
```

XML esperado en `Totales`: `MntExe 4050000, MntTotal 4050000`, sin `MntNeto`, `TasaIVA` ni
`IVA` (tras el cambio de §6.3).

### 6.2 Cambios en `pana-backend`

| Pieza | Cambio |
|---|---|
| `DocumentFacturadorAdapter._transport` | Agrega `DirDest`, `CmnaDest`, `CiudadDest` |
| `DocumentFacturadorAdapter` | `_dispatch_type()` desde `transport_data.dispatch_type` y `_delivery_note_customs()` para 52 con traslado 8/9. El sidecar de certificación mantiene la precedencia, igual que en `_aduana` |
| `DocumentFacturadorAdapter._items` | `IndExe = 1` si `detail.is_exempt`, o si la línea está en `line_exempt` del sidecar |
| `GuiaDocumentBuilder` | Kwarg `dispatch_type` explícito con precedencia sobre la inferencia por texto (mismo patrón que `transfer_indicator`). Kwarg `customs`: con 8/9 agrega `Transporte/Aduana`. Sigue omitiendo `TipoDespacho` con traslado 5 |
| `TransportBuilder` | Campos de destino, truncados a 70/20/20 |
| **Nuevo** `components/customs.py` → `CustomsBlockBuilder` | Sale de `ExportAduanaBuilder._build_aduana/_apply_bultos/_apply_pesos` y **emite en orden de XSD**. `ExportAduanaBuilder` pasa a usarlo, conservando lo propio de exportación (receptor extranjero, `OtraMoneda`, `FmaPagExp`). Así no hay lógica duplicada y la 110 queda en orden de esquema aunque PHP ya la reordene |
| `document_builder/__init__.py` | Pasa los kwargs nuevos por la fachada `build_document_data` |

### 6.3 Cambios en `pana-electronic-invoice`

**Decisión (2026-09-14): se aplica sin prueba previa**, siguiendo el formato del SII (`MntNeto`
es la suma de ítems afectos y la tasa e IVA se refieren a ese neto) y el precedente de la nota de
crédito, que el SII ya acepta. En `NormalizeGuiaDespachoJob`, después de
`normalizeIvaMntTotal`:

```php
if (!$data['Encabezado']['Totales']['MntNeto']) {
    $data['Encabezado']['Totales']['MntNeto'] = false;
    $data['Encabezado']['Totales']['TasaIVA'] = false;
    $data['Encabezado']['Totales']['IVA'] = false;
}
```

Mismo patrón que `NormalizeNotaCreditoJob`, con su fixture en
`lib-core/tests/fixtures/yaml/documentos_ok/052_guia_despacho/`. No corresponde reordenar
`Aduana` en PHP: lo resuelve `CustomsBlockBuilder`.

### 6.4 Totales en la plataforma

`InvoiceTotalBuilder.calculate_totals_from_details` separa las líneas `is_exempt`: el neto
afecto lleva IVA y el exento va a `exempt_amount`, con
`total = neto + IVA + exento`. Es la misma aritmética de lib-core, así que la API, la
plataforma y el XML muestran lo mismo. Se agrega `exempt_amount` al retorno de
`_process_totals` y a `DocumentTotal`.

### 6.5 PDF

- `_parse_transporte_from_xml` + `DeliveryNoteTransportSection`: dirección de destino.
- Bloque Aduana: corregir el tag `CodPtoEmbarque` y mostrar la unidad del peso bruto.
- Línea con `IndExe = 1` → "EX".
- `build_draft_dte_xml` (preview): escribe destino, Aduana e `IndExe` para que el preview
  coincida con lo emitido.

---

## 7. Facturador gratuito (MiPyme)

Allí el XML lo arma el SII con lo que llenamos en su formulario, así que sólo se puede enviar
lo que el formulario tenga.

### 7.1 Prueba realizada (2026-09-14, sin emitir ni quemar folios)

Con IMPREGNADORA YUKON SPA (78.041.752-8, emite guías por MiPyme, clave SII), usando el mismo
`locked_sii_session` y los mismos requests que el preview de producción. Un guard en la sesión
abortaba cualquier URL del portal distinta de `mipeLaunchPage`, `mipeSelEmpresa`,
`mipeDisplayPreView`, `mipePreView` y `PreViewFrame`; en particular `mipeGenXMLFirma.cgi`, que es
donde MiPyme asigna el folio. Las previsualizaciones salieron con **"FOLIO NO ASIGNADO"**.

1. **Inventario del formulario** (`GET mipeGenFacEx.cgi?PTDC_CODIGO=52`): 45 campos. De
   transporte sólo hay `EFXP_IND_VENTA` (select con los 9 tipos de traslado, **incluido el 8**),
   `EFXP_RUT_TRANSPORTE/DV`, `EFXP_PATENTE`, `EFXP_RUT_CHOFER/DV`, `EFXP_NOMBRE_CHOFER`,
   `EFXP_RUT_SOLICITA/DV` y el bloque de madera. **No hay tipo de despacho, destino, Aduana ni
   exención por línea.** Para la 52 el formulario rotula "Monto Neto" e "IVA 19%" fijos.
2. **Previsualización A (traslado 8, sin extras) vs B (A + campos candidatos):** en B se agregaron
   los campos de Aduana del formulario de exportación (`EDFE_PTO_EMBAR`, `EDFE_PTO_DESEM`,
   `EDFE_TOT_BOLT`) y nombres probables de destino, despacho y exención (`EFXP_DIR_DEST`,
   `EFXP_CMNA_DEST`, `EFXP_CIUDAD_DEST`, `EFXP_TIPO_DESPACHO`, `EFXP_IND_EXE_01`...). **El texto
   de ambos PDFs es idéntico: el portal los ignora.**
3. **El portal le calcula IVA 19% a una guía de traslado 8** (neto $1.080.000 → IVA $205.200). No
   hay forma de evitarlo desde el formulario.

### 7.2 Decisión

| Campo | Facturador de mercado | Facturador gratuito (MiPyme) |
|---|---|---|
| `transport_type` (incl. 8 y 9) | Sí | Sí (ya mapeado a `EFXP_IND_VENTA`) |
| `dispatch_type` | Sí | **422**: *"no disponible para emisores del facturador gratuito del SII"* |
| `destination_*` | Sí | **422** |
| Aduana (`departure_port_code`...) | Sí | **422** |
| `details[].is_exempt` | Sí | **422** |

- Con traslado 8/9 la regla de §4.1 (Aduana obligatoria) aplica **sólo al facturador de
  mercado**: el portal no tiene dónde recibirla, así que exigirla dejaría a los emisores MiPyme
  sin poder emitir guías de exportación.
- Documentación: advertir que en el facturador gratuito una guía con precio **siempre lleva
  IVA 19%**. Para un traslado de exportación con valor, la opción es el facturador de mercado.
- Para saber el camino al validar se usa la misma política que ya elige la estrategia de emisión
  (`MarketBillingPolicy` / `EnrolledCompany`). Así el serializer puede responder 422 antes de
  crear el documento.
- El HTML del formulario queda como fixture (`apps/scrapers/mipyme/tests/fixtures/guia_52_form.html`)
  con un test que falla si el SII agrega campos nuevos de despacho, destino o exención.
- La PR 5 del §9 pasa a ser sólo la validación 422 por camino (no hay mapeo `EFXP_*` que hacer).

---

## 8. Campos desconocidos: validación estricta

### 8.1 Contrato real (antes de validar nada)

1. **Auditoría de lecturas crudas:** listar cada llave que el intake lee de `initial_data` /
   `input_payload` fuera de los serializers (`authorized_user_rut`, `is_sandbox`,
   `payment_status`, `master_entity_id`, `receiver_*`, `vatwithheld`, `gross_unit_price`,
   `document_receiver.email`...).
2. **Contrato único:** `apps/documents/contracts/document_payload_contract.json` con las llaves
   permitidas por nivel. Es la unión de los campos del serializer y las lecturas crudas.
3. **Test de no deriva:** compara el contrato contra los campos declarados de cada serializer.
   Si alguien agrega un campo y no actualiza el contrato, falla.
4. Con el contrato, repetir la medición de §3.2 (el script queda en `scripts/`) y obtener la
   lista exacta por API key.

### 8.2 Comportamiento

- El chequeo compara el payload **crudo** antes de `to_internal_value`, que muta el documento
  (inyecta `sender`/`receiver`, renombra `vatwithheld`, acepta `receiver_*` planos).
- **Sólo para requests con API key** (v1 y v2). No para el frontend (JWT), Excel ni programadas,
  que usan los mismos serializers.
- **Aviso primero, rechazo después:**
  - **Modo aviso** (todas las keys, inmediato): la respuesta del batch agrega
    `warnings: [{"path": "documents[0].header.transfer_indicator", "message": "Campo desconocido; se ignoró.", "hint": "¿Quisiste decir transport_data.transport_type?"}]`.
    Es aditivo: nadie se rompe. Se registra además en log y métrica por API key.
  - **Modo estricto** (nuevo campo `APIKey.strict_payload_validation`): el mismo hallazgo pasa a
    ser **422**. Default `True` para keys nuevas; las existentes quedan en `False` hasta
    limpiarlas.
- **Sugerencias (`hint`)** para los errores conocidos: `header.transfer_indicator` →
  `transport_data.transport_type`; `export_data.export_clause` → `sale_clause_code`;
  `export_data.destination_country` → `destination_country_code`;
  `export_data.transport_mode` → (no existe; vía de transporte).
- `dte_type` desconocido deja de caer a 33 en modo estricto.

### 8.3 Gateway

Para las keys `gateway_queued`, la Lambda responde 202 antes de que Django valide. El chequeo
estricto tiene que estar **también en la Lambda** (`_validate_structure`) y en
`GatewayIntakeBatchStructuralSerializer`, leyendo el **mismo** contrato JSON empaquetado en el
zip. En modo aviso, los `warnings` se guardan en el batch y se devuelven en
`GET /v1/documents/batch/{uuid}`.

### 8.4 Salida a producción

1. Deploy en modo aviso.
2. Contactar a los 65 clientes con la lista de sus llaves (sale del script). Prioridad para los
   5 exportadores que pierden la cláusula y para SOINBAL.
3. Pasar a estricto key por key cuando dejen de aparecer avisos.
4. **A decidir:** aceptar como alias los nombres viejos de `export_data` documentados en
   `llms-full.txt`. Arreglaría a esos exportadores sin que cambien código, pero **cambia lo que
   se emite al SII** (hoy salen sin cláusula), así que requiere avisarles antes.

---

## 9. Implementación (por PR, TDD en cada fase)

| PR | Repo | Contenido | Depende de |
|---|---|---|---|
| **0** | — | ✅ Cerrada: formulario MiPyme probado (§7); sin certificación por decisión (§12); MCP sin configuración adicional (§11.2) | — |
| **A** | docs | `llms.txt` / `llms-full.txt` → MCP + página `mcp.mdx` (§11.2) | — (puede ir primero) |
| **1** | backend | Bugs sin cambio de contrato: `_save_transport_data`, `TransportService` sin tragarse excepciones, `GET`/batch devuelven `transport_data`, PDF (`CodPtoEmbarque`, rótulo EX) | — |
| **2** | backend + docs | `transport_data` con serializer, `dispatch_type`, destino, Aduana de la guía (modelo, serializer, adapter, builder, `CustomsBlockBuilder`, PDF, respuestas v1/v2) + docs §11.1 | 0, 1 |
| **3** | backend + lib-core + docs | `details[].is_exempt`, totales con exento, `IndExe` en el adapter, PDF, fix condicional de lib-core + docs | 0, 1 |
| **4** | backend + docs | Contrato único, modo aviso, `APIKey.strict_payload_validation`, Lambda gateway, hints + docs de errores v1/v2 | 1 |
| **5** | backend | 422 para emisores MiPyme que manden despacho, destino, Aduana o exención (§7.2), con el fixture del formulario | 2, 3 |

**2 y 3 son las que destraban a SOINBAL.** La 4 es la raíz de las idas y vueltas, pero su salida
en estricto depende del contacto con clientes, por eso su activación va al final aunque el
modo aviso pueda salir antes.

---

## 10. Tests

Registrados en `tests/config.yml`, en las secciones de sus pares.

| Test | Qué verifica |
|---|---|
| `test_transport_data_rejects_unknown_dispatch_type` | `dispatch_type: "4"` → 422 |
| `test_dispatch_type_rejected_for_internal_transfer` | `"5"` + `dispatch_type` → 422 |
| `test_customs_fields_rejected_outside_export_transfer` | Puertos con `transport_type: "1"` → 422 |
| `test_port_accepts_code_or_name` / `test_port_outside_table_rejected` | `"992"` y `"AEROP.A.M.BENITEZ"` → 992; `"7777"` → 422 |
| `test_plate_is_normalized_to_sii_length` | `"PJRL-69"` → `PJRL69` |
| `test_update_with_transport_data_does_not_crash` | Regresión de `_save_transport_data` |
| `test_transport_save_error_is_not_swallowed` | Error de persistencia → excepción, no un documento sin transporte |
| `test_dispatch_type_reaches_iddoc` | Adapter + builder: `TipoDespacho = 2` |
| `test_destination_reaches_transporte` | `DirDest/CmnaDest/CiudadDest`, truncados |
| `test_export_transfer_emits_customs_in_xsd_order` | Orden exacto de llaves en `Aduana` |
| `test_export_invoice_customs_unchanged` | La 110 emite los mismos valores tras extraer `CustomsBlockBuilder` |
| `test_certification_sidecar_takes_precedence` | El set de pruebas no cambia |
| `test_exempt_line_sets_indexe` / `test_exempt_line_only_for_delivery_note` | `IndExe = 1`; en una 33 → 422 |
| `test_totals_split_exempt_and_taxed_lines` | Neto, IVA, exento y total con líneas mixtas |
| `test_fully_exempt_delivery_note_totals` | IVA 0, total = exento |
| `test_detail_response_includes_transport_and_exempt` | `GET` v1 y v2 (con `?fields=` en v2) |
| `test_batch_api_delivery_note_export_transfer` | HTTP `POST /v1/documents/batch/` y `/api/v2/documents/batch/` con key sandbox: caso §4.3 end-to-end |
| `test_unknown_field_warning_in_lenient_mode` | `warnings` con ruta y hint, documento creado |
| `test_unknown_field_rejected_in_strict_mode` | 422 |
| `test_contract_matches_serializers` | No deriva del contrato |
| `test_frontend_jwt_request_not_strict` | El frontend no se ve afectado |
| `test_gateway_lambda_applies_contract` | Lambda con el mismo contrato |
| `test_pdf_shows_destination_and_loading_port` / `test_pdf_exempt_line_label` | PDF |
| lib-core: fixture `052_006_traslado_exportacion_exento.yaml` | Totales sin `MntNeto`/`TasaIVA`/`IVA` cuando todo es exento |
| `test_mipyme_sender_rejects_delivery_note_customs` | Emisor MiPyme + Aduana/destino/despacho/exento → 422 |
| `test_mipyme_export_transfer_without_customs_is_valid` | Emisor MiPyme + traslado 8 sin Aduana → válido |
| `test_mipyme_delivery_note_form_has_no_new_fields` | El fixture del formulario no tiene campos de despacho/destino/exención |

Notas del plan anterior que siguen vigentes: los tests HTTP necesitan el parche de
`connection.close` de `test_batch_api_export_sale_clause`; no usar `TransactionTestCase`; crear
en el `setUp` las filas de catálogo que se usen.

---

## 11. Documentación (repo `docs`)

**Salir del `main` remoto** (hoy `2d7b6b5`, con v2), no del checkout local, que está en una
rama ya mergeada y 17 commits atrás.

### 11.1 DTE 52 y cambios de contrato

| Archivo | Cambio | PR |
|---|---|---|
| `user-guide/documents.mdx` (compartido v1/v2) | Sección de la guía: tipos de traslado y despacho en lenguaje de usuario, cuándo informar destino y Aduana | 2 |
| `api-reference/documents/batch.mdx` (v1) | Bloque `<details>` para DTE 52 junto a los de 33/34/110..., sección de `transport_data` con la tabla §4.1, ejemplo §4.3, `details[].is_exempt` y errores 422 | 2, 3 |
| `api-reference/openapi/schemas/schemas.json` | `TransportData` con campos nuevos **y descripciones en español** (hoy en inglés), `DocumentDetail.is_exempt`, `exempt_amount` en la respuesta | 2, 3 |
| `api-reference/openapi-combined.json` (v1) | Mismo cambio **a mano** | 2, 3 |
| `api-reference/openapi-v2.json` | Mismo cambio en `TransportData` (línea ~7962), `DocumentDetail` (~6928) y la respuesta del detalle | 2, 3 |
| `api-reference/v2/errors.mdx` + errores v1 | Códigos nuevos: campo inválido de transporte, campo desconocido y la estructura de `warnings` | 4 |
| `api-reference/v2/introduction.mdx` | "Convenciones v2": validación estricta por API key | 4 |

⚠️ **`combine_openapi.py` pisa el bloque `info` del combinado** y reordena los paths. Además
**corre solo** en `npm run dev`, `build` y `precommit` (`package.json`). Antes de cada commit hay
que revisar el diff de `openapi-combined.json` y revertir lo que haya tocado el script.

### 11.2 `llms.txt` y `llms-full.txt` → cómo conectarse al MCP

Hoy son un resumen escrito a mano de la API v1. No mencionan la 52, sus ejemplos de
`export_data` están obsoletos (§3.2) y apuntan a páginas que no están en la navegación. Pasan a
describir el MCP, que no se desactualiza con cada campo nuevo: las herramientas se describen
solas al conectarse.

**Datos verificados** (`curl` al endpoint público):
- URL: `https://mcp.tupana.ai/mcp` (Streamable HTTP; sin token responde 401).
- OAuth 2.1 + PKCE con registro dinámico de clientes
  (`/.well-known/oauth-authorization-server`): no hay API key ni client ID que entregar. El
  usuario inicia sesión con su cuenta Tupana (email/clave o Google).
- Scopes `tupana:read` y `tupana:write`. Acceso limitado a las empresas del usuario.

**`llms.txt`** (índice corto):
1. Qué es Tupana y qué se puede hacer desde un asistente.
2. Conexión al MCP (URL + "inicia sesión con tu cuenta Tupana").
3. Enlaces: página `mcp.mdx`, API v2 (por defecto) y v1, y las especificaciones OpenAPI
   (`openapi-v2.json`, `openapi-combined.json`) como **única fuente legible por máquina** para
   quien integre por API.

**`llms-full.txt`:**
1. Conexión paso a paso por cliente:
   - Claude (claude.ai / Desktop): Configuración → Conectores → agregar conector personalizado con la URL.
   - Claude Code: `claude mcp add --transport http tupana https://mcp.tupana.ai/mcp`.
   - Cursor: `mcp.json` con `{"mcpServers": {"tupana": {"url": "https://mcp.tupana.ai/mcp"}}}`.
   - ChatGPT y otros clientes MCP remotos (**verificar los pasos antes de publicar**).
2. Autenticación: inicio de sesión con la cuenta Tupana (email/clave o Google), sin API key ni
   configuración adicional. Acceso a las empresas del usuario. Las acciones que emiten o envían
   piden confirmación explícita en la conversación.
3. Capacidades por categoría (documentos, clientes, libros SII/F29, banco y conciliación,
   contabilidad, gráficos), **sin copiar la lista de herramientas**. Se indica pedir
   `list_capabilities` / `how_to`, que salen del propio servidor.
4. Qué no hace el MCP (p. ej. hoy no emite guías de despacho) y cuándo usar la API.
5. Aclaración: `mcp.tupana.ai` no es el buscador de documentación que Mintlify puede exponer en
   el dominio de docs.

**Página humana `user-guide/mcp.mdx`** en la navegación de ambas versiones, con el mismo
contenido. Es la fuente canónica y los `.txt` la resumen.

> ⚠️ **Trade-off.** SOINBAL armó su integración leyendo `llms-full.txt`. Al sacar la API del
> `.txt`, los integradores que usan agentes de código pierden ese resumen. Se compensa
> apuntando a los JSON OpenAPI, que se mantienen con cada PR (§11.3).

### 11.3 Que la documentación no vuelva a quedar atrás

- **Checklist en la plantilla de PR del backend** (`.github/pull_request_template.md`): "¿Cambia
  el payload o la respuesta de la API? → PR en `docs` con el mismo nombre de rama (v1
  `batch.mdx` + `schemas.json` + `openapi-combined.json`, y `openapi-v2.json`)".
- **El contrato único (§8.1) como referencia:** script en `docs/scripts/` que compara
  `TransportData`, `DocumentDetail`, `ExportData`, etc. de `openapi-v2.json` y
  `openapi-combined.json` contra `document_payload_contract.json` del backend, y falla si hay
  campos que no están en los dos. Primero se corre a mano en cada PR; después, en CI del repo
  `docs`.
- **Arreglar `test_openapi_documentation_validation.py`** del backend: apunta a
  `docs/api-reference/openapi-combined.json`, que no existe en ese repo, así que hoy no valida
  nada. O se elimina, o se reemplaza por el script anterior.
- Correr `verify_docs.py` y `check_curl_examples.py` del repo `docs` antes de mergear.
- Al cerrar cada PR, marcar este plan como implementado, igual que los anteriores.

---

## 12. Certificación en el SII

**Decisión (2026-09-14): no se hacen pruebas en certificación.** Se implementa según el formato
oficial del SII (§2) y el esquema `DTE_v10.xsd`:
- Aduana obligatoria con traslado 8/9 en el facturador de mercado (§2.2).
- Orden de `Aduana` según el XSD (§6.2).
- Guía toda exenta sin `MntNeto`/`TasaIVA`/`IVA` (§6.3).
- `TipoDespacho` omitido con traslado 5, como ya se hace.

Riesgo asumido: un reparo del SII en la primera guía real de exportación. Mitigación: revisar la
respuesta del SII de las primeras guías de SOINBAL después del deploy, antes de avisar a otros
clientes.

---

## 13. A confirmar antes de implementar

- **Largos existentes** (patente > 8, chofer > 30, chofer incompleto): medirlo sobre
  `input_payload` de 52 antes de decidir entre rechazar o normalizar.
- **Seguridad del MCP (fuera de este plan, anotado):** el servidor declara `tupana:read` y
  `tupana:write`, pero las herramientas que emiten no verifican el scope del token
  (`apps/mcp_server/tools*.py`). Hoy un token de sólo lectura puede emitir.
- **Alias de nombres viejos de `export_data`** (§8.4).
- **`document_receiver.email` y otras llaves con alto uso:** confirmar en la auditoría §8.1 si
  se leen en algún lado antes de clasificarlas como desconocidas.

---

## 14. Fuera de alcance

- Aviso de folio por webhook (pregunta 3 del cliente).
- `is_exempt` por línea para 33, 56 y 61 (requiere revisar la regla 33 → 34 y el camino MiPyme).
- Herramienta MCP para emitir guías de despacho.
- Anular o corregir el folio 379 ya emitido como venta: decisión del cliente.
- Puertos, pesos y bultos de la **factura** de exportación (110) en producción: el adapter hoy
  sólo pasa cláusula, forma de pago y tipo de cambio. `CustomsBlockBuilder` lo deja preparado,
  pero conectarlo es otro plan.
- `POST /v1/documents` (creación individual): usa otro serializer sin `transport_data` y
  parece fallar con `KeyError` en rutas sin `master_entity_id`. Queda anotado para revisar.

---

## 15. Referencias de código

| Qué | Dónde |
|---|---|
| Vista y serializer del batch (v1 y v2) | `apps/documents/app_views/batch_views.py:51`, `apps/documents/app_serializers/batch_serializers.py:252, 1761` |
| Wrapper v2 (sólo respuesta) | `apps/api/v2_public_id.py:329-352` |
| `transport_data` como `JSONField` | `apps/documents/serializers_refactor.py:1037` |
| Guardado que traga errores | `apps/documents/services/transport_service.py:20-44` |
| `_save_transport_data` inexistente | `serializers_refactor.py:1571, 1739, 2045, 2324` |
| Totales al crear | `apps/documents/builders/invoice_total_builder.py:144-399` |
| Detalle del documento (GET) | `apps/documents/app_views/document_detail_view.py:33` |
| Lambda gateway | `lambdas/gateway_batch_validator/handler.py:260-331` |
| Validador estructural espejo | `apps/documents/app_serializers/gateway_intake_structural_serializer.py:73` |
| Lectura cruda de `authorized_user_rut` | `apps/documents/services/batch_issuance_intake_service.py:170-198` |
| Adapter del facturador | `apps/electronic_invoice/services/document_facturador_adapter.py` (`_items` 402, `_transport` 176, `_aduana` 234) |
| Builder de la guía | `apps/electronic_invoice/services/document_builder/builders.py:449-514` |
| Transporte y madera | `apps/electronic_invoice/services/document_builder/components/transport.py` |
| Aduana de exportación | `apps/electronic_invoice/services/document_builder/export.py:46-237` |
| Tablas de Aduana | `apps/electronic_invoice/services/aduana_codes.py` (`PUERTOS`, `UNIDADES`, `TIPOS_BULTO`) |
| Cliente HTTP a LibreDTE | `apps/electronic_invoice/services/libredte_client.py:205-229` |
| Normalizador de la guía (PHP) | `pana-electronic-invoice/lib-core/src/Package/Billing/Component/Document/Worker/Normalizer/Job/NormalizeGuiaDespachoJob.php` |
| Patrón `TasaIVA` sin neto (PHP) | `.../Job/NormalizeNotaCreditoJob.php:93-96` |
| PDF transporte / Aduana / exento | `apps/documents/utils/dte_pdf_renderer.py:914-1009`, `custom_invoice_pdf_renderer.py:387-439, 493` |
| Payload MiPyme | `apps/scrapers/mipyme/inputs/base_payload_builder_input.py:579-599, 618-745` |
| Servidor MCP | `apps/mcp_server/server.py`, `server_core.py`, `oauth_provider.py`, `consent.py` |
| llms actuales | `docs/llms.txt`, `docs/llms-full.txt` (raíz del repo `docs`) |

---

## 16. Implementación: desvíos respecto del plan

- **Una PR por repo** en vez de las PRs 1-5 separadas del §9, con commits atómicos (tests antes de cada cambio).
- **Formato de los 422 del batch:** DRF indexa los errores por posición (`{"documents": {"0": {...}}}`), no en lista, y v2 devuelve el mismo cuerpo que v1 (el sobre de errores v2 no aplica a esta vista). La documentación quedó con el formato real.
- **Contrato:** `exchange_rate_source` quedó fuera (lo calcula `ExportService`, no lo manda el cliente). `check_api_contract.py` detectó cuatro campos de `details` aceptados y no documentados (`line_number`, `item_total`, `show_item_type`, `ticket`), que se agregaron a OpenAPI v1 y v2.
- **Totales con líneas exentas:** la separación exento/neto sólo aplica al cálculo normal de documentos afectos; los exentos por tipo y las facturas de compra no cambian.
- **Chofer:** se exige RUT y nombre juntos (0 casos incompletos en 90 días); el nombre se trunca a 30 al emitir (37 guías recientes lo superan).
- **Gateway:** la Lambda aplica el mismo contrato con copias idénticas del módulo y del JSON (test de sincronía) y lee `strict_payload_validation` del caché de DynamoDB. Después del deploy hay que correr `manage.py backfill_api_key_cache`.
- **`test_openapi_documentation_validation.py`** no se tocó: no lee el JSON de docs, sólo lo menciona en el docstring.
- **lib-core:** la condición también exige `MntExe` no vacío, para que una guía sin montos (traslado interno) conserve su salida actual.
- **Plantilla de PR** del backend con el checklist de documentación (§11.3).
