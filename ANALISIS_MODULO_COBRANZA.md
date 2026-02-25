# Análisis del Módulo de Cobranza — Documento Consolidado

## 1. Resumen Ejecutivo

El módulo de cobranza permite a las empresas gestionar cuentas por cobrar: listar clientes con facturas pendientes, enviar correos de cobranza, marcar facturas como pagadas/no pagadas, y subir comprobantes de transferencia. Está integrado con Slack, emails, banking, documentos, **conciliación bancaria** y **WhatsApp**. El flujo se apoya en **plantillas (templates)** de correo y WhatsApp con variables dinámicas.

---

## 2. Cómo Funciona Cada Módulo

### 2.1 Conciliación Bancaria

**Ruta:** `/platform/reconciliation` (o similar)  
**Backend:** `apps/accounting/`

**Flujo:**

1. **Movimientos bancarios:** Se importan desde Fintoc u otra integración. Cada `Movement` tiene monto, fecha, glosa y RUT del pagador.
2. **Recomendaciones:** `ReconciliationRecommendationService` sugiere emparejar movimientos con facturas pendientes por monto, RUT y glosa. Usa `ClientPaymentRut` para asociar RUT de pagador con receptor (cliente).
3. **Conciliación manual:** El usuario crea una `BankReconciliation` que vincula uno o más `Movement` con uno o más `Document` mediante `BankReconciliationDocument`.
4. **`BankReconciliationDocument`:** Para cada documento conciliado guarda `reconciled_amount` y `mark_as_paid` (True/False).
5. **Al guardar la conciliación:** `BankReconciliation.save()` llama a `mark_invoices_as_paid()`:
   - Por cada `BankReconciliationDocument` actualiza `DocumentStatus`.
   - Si `mark_as_paid=True` y el total conciliado cubre el monto neto → `paid_status=PAID`, `pending_amount=None`.
   - Si `mark_as_paid=True` y es pago parcial → `paid_status=PAID` o `PARTIALLY_PAID`, `pending_amount` = saldo pendiente.
   - Si `mark_as_paid=False` → el documento sigue NOT_PAID; se actualiza `pending_amount` con el saldo.
6. **Impacto en cobranza:** La Gestión de Cobranza muestra facturas según `DocumentStatus`. Si la conciliación marca `PAID`, la factura deja de aparecer en pendientes. No hay notificación explícita entre conciliación y cobranza.

---

### 2.2 Tus Contactos

**Ruta:** `/platform/contacts`  
**Archivo:** `src/pages/email/ContactsPage.tsx`

**Qué hace:**

- Gestiona contactos (email, teléfono) asociados a clientes (MasterEntity).
- Los contactos se agrupan por cliente. Cada cliente puede tener varios contactos.
- Permite crear, editar, eliminar contactos y asignar contactos a clientes.
- Importación desde Excel (`ContactImportModal`).
- Los contactos son la fuente de emails para enviar correos de cobranza: si un cliente no tiene contacto con email, no se le puede enviar correo desde Gestión de Cobranza (y se omite silenciosamente).

**Relación con cobranza:** Los correos de cobranza usan el email del cliente (del contacto o de la MasterEntity). Es necesario tener contactos con email configurados para que el envío funcione.

---

### 2.3 Templates (Plantillas de Correo)

**Ubicación:** Configuración → Tu Correo → Templates (`EmailTemplatesSection`); también en Configuración de Cobranza (CollectionSettings).  
**Backend:** `EmailTemplate` en `apps/emails/`

**Qué hace:**

- Las plantillas definen `subject` y `body`/`html_body` con variables Jinja (`{{cliente}}`, `{{monto}}`, `{{facturas}}`, `{{banking.*}}`, etc.).
- Categorías: `cobranza`, `issuance`, `invoice`, `sales`, etc. La categoría `cobranza` marca plantillas para recordatorios.
- Al enviar correos desde Gestión de Cobranza, el usuario puede elegir una plantilla por ID o escribir subject/content manualmente.
- `TemplateRenderingService` reemplaza las variables con datos reales (cliente, facturas, monto, banking).

**Relación con cobranza:** Gestión de Cobranza usa `template_id` o `email_template` (subject, content) en `send_collection_emails`. Si usa `template_id`, se carga el `EmailTemplate` y se renderiza con el contexto del cliente.

---

### 2.4 Configuración de Correos

**Ruta:** `/platform/settings/email` (sección email de CollectionSettings)  
**Archivo:** `src/pages/settings/CollectionSettings.tsx` (section=email)

**Qué hace:**

- **Cuenta de email:** Conectar Gmail (OAuth), Outlook o SMTP. Sin cuenta configurada no se pueden enviar correos.
- **Remitente (From):** Opcional. Permite usar grupo@empresa.com o alias en lugar del email principal.
- **Firmas:** `EmailSignaturesSection` — firmas que se agregan al final de los correos.
- **Templates:** `EmailTemplatesSection` — CRUD de plantillas (crear, editar, duplicar, eliminar). Incluye categorías como "Recordatorios de Cobranza" (`cobranza`, `collections`).

**Relación con cobranza:** La configuración de email y templates es previa al envío de correos de cobranza. Si no hay cuenta conectada, el usuario debe configurarla (por ejemplo desde CollectionSettings o desde el modal de correo).

---

### 2.5 Tu Correo

**Ruta:** `/platform/email`  
**Archivo:** `src/pages/email/EmailPage.tsx`

**Qué hace:**

- Inbox de correos: recibidos y enviados.
- Sincroniza con Gmail/Outlook vía API. Muestra emails agrupados por cliente.
- Permite redactar nuevos correos (`NewEmailModal`), responder, filtrar por cliente, buscar.
- Estado de conexión: si no hay cuenta configurada, muestra `EmailSetupModal` para conectar.

**Relación con cobranza:** Tu Correo es el canal de envío/recepción. Los correos de cobranza enviados desde Gestión de Cobranza pasan por la misma infraestructura (EmailService, Resend/SMTP) y pueden aparecer en "Enviados" si se guardan en el backend. Es un módulo separado de la UI de cobranza pero comparte la misma cuenta y templates.

---

### 2.6 WhatsApp

**Backend:** `apps/whatsapp/` — `WhatsAppService`, webhooks.  
**Templates:** `EmailTemplate` con `template_type="whatsapp"` y `category="cobranza"`.

**Qué hace actualmente:**

- Existe integración WhatsApp para enviar mensajes (API externa).
- Hay plantillas de cobranza para WhatsApp (ej. "Cobranza WhatsApp - Base") con variables como `{{client.name}}`, `{{facturas.cantidad}}`, `{{multi_invoice_payment_link}}`.

**Lo que NO hace:**

- La Gestión de Cobranza **no** envía por WhatsApp. Solo envía por email. Los modales `WhatsAppPreviewModal` y `WhatsAppSetupModal` están en ClientsManagement pero no hay flujo de envío conectado.

---

### 2.7 Gestión de Cobranza

**Ruta:** `/platform/clients-management`  
**Archivo:** `src/pages/customers/ClientsManagement.tsx`

**Qué hace:**

- Lista clientes con facturas emitidas (tipos 33, 34, 39, 80), filtrados por estado de pago (unpaid, paid, all).
- Por cada cliente: total facturas, pagadas, pendientes, monto pendiente/pagado.
- Al expandir un cliente: tabla de facturas con folio, fecha, monto, vencimiento, estado, acciones.
- **Acciones:** Enviar correo (EmailPreviewModal), marcar como pagada/no pagada/parcialmente pagada, descargar PDF, subir/descargar comprobante.
- **Resumen:** SummarySection con cards (Monto Pendiente, Monto Pagado, Clientes Pendientes, Clientes Pagados).
- **Búsqueda:** UnifiedSearchInput con dominio `collections` (RUT, folio, razón social).
- **Persistencia OAuth:** Si el usuario va a configurar email y vuelve, se restauran las selecciones desde `localStorage` y se reabre el modal de correo.

**Flujo de envío de correos:**

1. Usuario selecciona clientes y/o facturas.
2. Clic en "Enviar correo" → `handleSendCollectionEmails` → guarda selecciones en localStorage → prepara `batchDocuments` → abre `EmailPreviewModal`.
3. En el modal: el usuario elige plantilla o escribe subject/content, revisa preview, envía.
4. Backend: `send_collection_emails` → `TemplateRenderingService` + `get_banking_context` → `EmailService.send_rendered_email`. Clientes sin email se omiten.

**Flujo de marcado de pago:**

- Marcado manual: `resolve-document-ids` → `PATCH /documents/batch/` con `payment_status` (paid/unpaid/partially_paid). Para parcial: `paid_amount`.
- Marcado por conciliación: al guardar una conciliación con `mark_as_paid=True`, `BankReconciliation.mark_invoices_as_paid()` actualiza `DocumentStatus`.

---

## 3. Inventario Detallado de Funcionalidades Existentes

### 3.1 Endpoints API (Backend)

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/master-entities/{id}/collection/clients/` | GET | `paymentStatus`: `all` \| `paid` \| `unpaid` \| `partially_paid` | Lista clientes con facturas emitidas. Por defecto `unpaid`. Excluye documentos con nota de crédito total/parcial. Tipos 33, 34, 39, 80. |
| `/master-entities/{id}/collection/clients/{client_id}/invoices/` | GET | `paymentStatus`: `paid` \| `unpaid` \| `partially_paid` (opcional) | Facturas de un cliente. `client_id` = `receiver_id`. Retorna `[]` si `client_id` es `undefined`. |
| `/master-entities/{id}/collection/send-emails/` | POST | `client_ids`, `invoice_ids`, `email_template` (`subject`, `content`) o `template_id` | Envía correos de cobranza. Usa `TemplateRenderingService` o `EmailTemplate`. Incluye `get_banking_context` si hay cuenta bancaria. Clientes sin email se omiten silenciosamente. |
| `/master-entities/{id}/collection/resolve-document-ids/` | POST | `client_ids`, `invoice_ids`, `intent`: `for_mark_paid` \| `for_mark_unpaid` | Resuelve IDs a `document_ids` para `PATCH /documents/batch/`. |
| `PATCH /documents/batch/` | PATCH | `ids`, `patch`: `{ payment_status, paid_amount? }` | Actualización masiva de `payment_status` (paid, unpaid, partially_paid). Para `partially_paid` requiere `paid_amount`. |
| `GET /documents/summary/collection/` | GET | `entity_id`, `start`, `end` (YYYY-MM-DD) | Resumen: `pending_amount`, `paid_amount`, `pending_clients`, `paid_clients`. Facturas pendientes sin límite de fecha; pagadas en rango. Tipos 33, 34, 39. |
| `GET /api/documents/reports/accounts-receivable/` | GET | `entity_id` | Resumen completo: `aging_buckets`, `payment_status`, `top_clients`, `reference_date`. Usado por `CollectionReport` (PaymentStatusChart, TopDebtorsTable). |
| `GET /documents/{id}/files/{file_type}/download/` | GET | `file_type`: `PDF` \| `XML` \| `PAYMENT_PROOF` | Descarga PDF/XML/comprobante. Notifica Slack `noti-cobranza` al descargar PDF. |
| `POST /documents/{id}/files/{file_type}/upload/` | POST | `file`: archivo | Sube PDF/XML/comprobante. Notifica Slack `noti-cobranza` al subir comprobante de transferencia. |

### 3.2 Tipos de Documento y Filtros

| Tipo | Código | Descripción | ¿Incluido en Cobranza? |
|------|--------|-------------|------------------------|
| Factura Electrónica | 33 | Factura afecta | Sí (listado, facturas, resumen, reportes) |
| Factura Exenta | 34 | Factura exenta | Sí |
| Boleta Electrónica | 39 | Boleta de venta | Sí |
| Boleta Honorarios | 80 | Boleta de honorarios | Sí (listado, facturas cliente, accounts-receivable). No en `CollectionSummaryView` (solo 33, 34, 39) |
| Factura Compra | 46 | Documento recibido | No |
| Nota de Crédito | 61 | NC | No (se excluyen documentos con NC total/parcial) |

**Filtros de estado de pago:**

- `all`: todos los clientes con facturas.
- `paid`: solo clientes con facturas totalmente pagadas.
- `unpaid`: solo clientes con facturas pendientes (no pagadas + parcialmente pagadas).
- `partially_paid`: solo clientes con facturas parcialmente pagadas.

**Filtro sandbox:** `master_entity.is_sandbox` define si se filtran documentos con `sandbox_info__isnull=False` o `True`.

### 3.3 Campos de Factura (CollectionInvoiceSerializer)

| Campo | Tipo | Origen |
|-------|------|--------|
| `id` | ID | Document |
| `folio` | string | Document |
| `date_issued` | date | Document |
| `amount_with_iva` | float | Document |
| `due_date` | date | `date_issued + 30 días` (hardcodeado) |
| `days_overdue` | int | `max(0, hoy - due_date)` |
| `status` | string | `paid` \| `unpaid` \| `partially_paid` \| `overdue` |
| `paid_status` | bool | DocumentStatus |
| `payment_status` | string | `paid` \| `unpaid` \| `partially_paid` |
| `pending_amount` | float \| null | DocumentStatus.pending_amount (para parcialmente pagadas) |
| `has_payment_proof` | bool | Existe documento con `file_type=PAYMENT_PROOF` |
| `sender` / `receiver` | object | `{ id, name, tax_id }` |
| `dte_type` | object | `{ code }` |

### 3.4 Campos de Cliente (CollectionClientSerializer)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `receiver` | int | ID del receptor (MasterEntity) |
| `name` | string | Nombre del cliente |
| `tax_id` | string | RUT |
| `total_invoices` | int | Cantidad según filtro (all/paid/unpaid/partially_paid) |
| `paid_invoices` | int | Solo PAID |
| `pending_invoices` | int | NOT_PAID + PARTIALLY_PAID |
| `total_paid_amount` | decimal | Suma de facturas pagadas |
| `total_pending_amount` | decimal | Suma de pendientes (incluye `pending_amount` para parcialmente pagadas) |
| `status` | string | `all` \| `pending` \| `overdue` |
| `days_overdue` | int | Máximo días vencidos de facturas pendientes |
| `master_entity_id` | int | Empresa |
| `document_count` | int | Documentos del receptor |

### 3.5 Envío de Emails

- **Contexto:** `TemplateRenderingService.render_from_template` o `render_from_strings` con variables Jinja.
- **Variables típicas:** `{{cliente}}`, `{{monto}}`, `{{facturas}}`, `{{dias}}`, `{{banking.*}}`, `{{invoice.folio}}`, `{{multi_invoice_payment_link}}`.
- **Banking:** `get_banking_context` añade datos de cuenta bancaria para correos.
- **Plantillas:** `EmailTemplate` con `category="cobranza"` y `template_type="email"` o `"whatsapp"`.
- **Omitidos:** Clientes sin email se omiten con `continue`; no hay feedback.

### 3.6 Marcado de Pago (PATCH batch)

- **paid:** factura totalmente pagada.
- **unpaid:** factura no pagada.
- **partially_paid:** factura parcialmente pagada; requiere `paid_amount`.
- **Flujo:** `resolve-document-ids` → `PATCH /documents/batch/` con `ids` y `patch`.
- **Intent:** `for_mark_paid` para pendientes; `for_mark_unpaid` para pagadas/parcialmente pagadas.

### 3.7 Comprobantes de Transferencia (DocumentFile)

- **file_type:** `PAYMENT_PROOF`.
- **Subida:** `POST /documents/{id}/files/PAYMENT_PROOF/upload/`. Fuente: `UPLOADED_BY_USER`. Notifica Slack `noti-cobranza`.
- **Descarga:** `GET /documents/{id}/files/PAYMENT_PROOF/download/`. Notifica Slack al descargar certificado PDF.
- **Acceso:** Emisor o receptor pueden subir/descargar comprobante.

### 3.8 Notificaciones Slack (canal `noti-cobranza`)

| Evento | Mensaje |
|--------|---------|
| Acceso a Gestión de Cobranza | Usuario X accedió a gestión de cobranza |
| Descarga PDF certificado | Detalle de documento descargado |
| Subida comprobante | Detalle de comprobante subido |

### 3.9 Búsqueda Global

- **Dominio:** `SearchDomain.COLLECTIONS`.
- **Base:** Documentos emitidos (`sender_id=company_id`, `state="issued"`).
- **Campos extra:** `days_overdue`, `due_date` en resultados serializados.
- **Intentos:** RUT, folio, monto, razón social, estado.

### 3.10 Reporte de Cobranza (CollectionReport)

- **Ruta:** `/platform/reports/collection` (o equivalente).
- **Componentes:**
  - **PaymentStatusChart:** gráfico pie con `payment_status` ( Pagadas, Pendientes, etc.). Excluye "Con Nota de Crédito".
  - **TopDebtorsTable:** tabla de top deudores con nombre, RUT, monto y días.
- **Endpoint:** `GET /api/documents/reports/accounts-receivable/?entity_id=X`.
- **Datos:** `aging_buckets`, `payment_status`, `top_clients`, `reference_date`.

### 3.11 Vista Principal (ClientsManagement)

- **Ruta:** `/platform/clients-management`.
- **Secciones:**
  - **Filtro estado de pago:** All, Pagadas, Pendientes, Parcialmente pagadas (URL query `paymentStatus`).
  - **Búsqueda local:** por nombre o RUT (cliente).
  - **Lista de clientes:** expandible para ver facturas.
  - **Resumen (SummarySection):** tipo `collection`, `defaultDays=30`, cards: Monto Pendiente, Monto Pagado, Clientes Pendientes, Clientes Pagados.
  - **DateRangePicker:** rango de fechas para el resumen.
  - **Acciones:**
    - Enviar correos (EmailPreviewModal).
    - Marcar como pagada / no pagada / parcialmente pagada.
    - Modal de pago parcial (PartialPaymentModal) con monto.
    - Barra flotante de acciones (PaymentFloatingActionBar) según selección.
    - Descargar PDF (por factura).
    - Subir comprobante (por factura).
- **Integración WhatsApp:** `WhatsAppPreviewModal`, `WhatsAppSetupModal`, `useWhatsAppModal`. Modales para envío por WhatsApp (templates existen; envío desde cobranza no implementado).
- **Persistencia OAuth:** en retorno de configuración de email, restaura selecciones desde `localStorage` (`collectionSelectedClients`, `collectionSelectedInvoices`) y abre `EmailPreviewModal`.

### 3.12 Servicio Frontend (collectionService)

| Método | Descripción |
|--------|-------------|
| `getCollectionClients(entityId, paymentStatus)` | GET clients |
| `getClientInvoices(entityId, clientId, paymentStatus?)` | GET invoices |
| `sendCollectionEmails(entityId, data)` | POST send-emails |
| `getCollectionDocumentIds(entityId, data, intent)` | POST resolve-document-ids |
| `markInvoicesAsPaid(entityId, data)` | Resuelve IDs + PATCH batch |
| `markInvoicesAsPartiallyPaid(entityId, invoiceIds, paidAmount)` | Wrapper de `markInvoicesAsPaid` |
| `markInvoicesAsUnpaid(entityId, data)` | Resuelve IDs + PATCH batch |
| `formatCurrency(amount)` | Formato CLP |
| `formatDate(dateString)` | Formato chileno |
| `getDaysOverdue(dueDate)` | Días vencidos |
| `getStatusInfo(status, dueDate, pendingAmount?)` | Badge: Pagada, Pagada parcialmente, Vencida (X días), Pendiente |
| `validateEmailTemplate(template)` | Valida subject y content |
| `getEmailVariables()` | Lista de variables para templates |
| `getDefaultEmailTemplate()` | Plantilla por defecto de cobranza |

### 3.13 Estrategias y Factories (Frontend)

- **PaymentDomain:** `'payments' | 'collection'` en `strategies/payment/types.ts`.
- **SelectedInvoicesPaymentStateStrategy:** estado de pago de facturas seleccionadas.
- **PaymentActionsFactory:** acciones según estado (marcar pagada, no pagada, parcial).
- **SummaryStrategyFactory:** `DefaultCollectionSummaryStrategy` para tipo `collection`.
- **usePaymentStatusHandlers:** handlers para actualizar estado de pago.
- **usePaymentFilterFromUrl:** sincronización de filtro con URL.

### 3.14 Queries Base (report_querysets.py)

- **collection_base_invoices(master_entity):** Base común. Tipos 33, 34, 39, 80. Emitidos con folio. Excluye NC. Filtro sandbox.
- **collection_pending_invoices(master_entity):** Excluye solo PAID (incluye NOT_PAID y PARTIALLY_PAD).
- **collection_paid_invoices(master_entity):** Solo PAID.
- **with_aging_info(reference_date):** `days_since_issue`, `days_overdue`, `aging_bucket` (Corriente, 1-30, 31-60, 61+ días).

### 3.15 Conciliación Bancaria (impacto en Cobranza)

- **DocumentStatus.paid_status:** PAID, NOT_PAID, PARTIALLY_PAID.
- **BankReconciliationDocument.mark_as_paid:** al conciliar, actualiza `DocumentStatus`.
- **ClientPaymentRut:** asocia RUT de pagador con receptor para matching.
- **ReconciliationRecommendationService:** sugiere matches por monto, RUT y glosa.

### 3.16 Resumen de Datos por Endpoint

| Endpoint | Respuesta |
|----------|-----------|
| `GET clients` | `[{ receiver, name, tax_id, total_invoices, paid_invoices, pending_invoices, total_paid_amount, total_pending_amount, status, days_overdue, ... }]` |
| `GET invoices` | `[{ id, folio, date_issued, amount_with_iva, due_date, days_overdue, status, paid_status, payment_status, pending_amount, has_payment_proof, sender, receiver, dte_type }]` |
| `GET summary/collection` | `{ pending_amount, paid_amount, pending_clients, paid_clients }` |
| `GET accounts-receivable` | `{ aging_buckets, payment_status, top_clients, reference_date }` |

---

## 4. Arquitectura Actual

### Backend
| Componente | Ubicación | Responsabilidad |
|------------|-----------|-----------------|
| CollectionManagementViewSet | `master_entities/app_views/collection_management.py` | CRUD de clientes, facturas, envío de emails, resolución de IDs |
| AccountsReceivableQuerySet | `documents/app_models/report_querysets.py` | Queries base (collection_base_invoices, collection_pending_invoices) |
| CollectionSummaryView | `documents/app_views/reports.py` | Resumen pendiente/pagado para dashboards |
| DocumentFile (comprobantes) | `documents/app_views/document_file_views.py` | Notificación Slack al subir/descargar |

### Frontend
| Componente | Ubicación | Responsabilidad |
|------------|-----------|-----------------|
| ClientsManagement | `pages/customers/ClientsManagement.tsx` | Vista principal de cobranza |
| collectionService | `services/collectionService.ts` | API calls, formateo, validación |
| CollectionReport | `pages/reports/CollectionReport.tsx` | Gráficos de estado de pago, top deudores |

### Integraciones
- **Slack**: noti-cobranza (acceso, descarga PDF, comprobante subido)
- **Emails**: plantillas, banking context, Resend
- **Banking**: información de cuenta para correos
- **Búsqueda**: domain "collections" en búsqueda global

---

### 4.1 Módulos Relacionados (Conciliación, WhatsApp, Correos, Templates)

### Conciliación Bancaria (`apps/accounting/`)

| Componente | Ubicación | Relación con Cobranza |
|------------|-----------|------------------------|
| BankReconciliation | `app_models/bank_reconciliation.py` | Al conciliar un movimiento con un documento, se actualiza `DocumentStatus.paid_status` |
| BankReconciliationDocument | `app_models/bank_reconciliation_document.py` | `mark_as_paid`: si True, marca el documento como PAID; si False, deja saldo pendiente |
| ReconciliationRecommendationService | `services/reconciliation_recommendation_service.py` | Sugiere matches movimiento↔documento por monto, RUT y glosa |
| ClientPaymentRut | `app_models/client_payment_rut.py` | Asocia RUT de pagador con receptor para mejorar matching |

**Flujo**: Movimiento bancario → recomendación automática → usuario concilia → `DocumentStatus` se actualiza (PAID/PARTIALLY_PAID) → **Cobranza** refleja el cambio (facturas pasan de pendientes a pagadas).

**Gaps**: No hay notificación o sincronización explícita entre conciliación y cobranza. La vista de cobranza usa `DocumentStatus`; la conciliación lo actualiza. Funciona, pero no hay feedback cross-módulo (ej. "esta factura fue conciliada automáticamente").

### WhatsApp (`apps/whatsapp/`)

| Componente | Ubicación | Relación con Cobranza |
|------------|-----------|------------------------|
| WhatsAppService | `services.py` | Envío de mensajes (API externa) |
| Views | `app_views/views.py` | Webhooks, verificación |

**Templates de cobranza WhatsApp**: Existe `EmailTemplate` con `template_type="whatsapp"` y `category="cobranza"` (ej. "Cobranza WhatsApp - Base"). Variables: `{{client.name}}`, `{{facturas.cantidad}}`, `{{company.name}}`, `{% for invoice in invoices %}`, `{{multi_invoice_payment_link}}`.

**Gaps**: El módulo de cobranza **solo envía correos** (`send_collection_emails`). No hay endpoint ni flujo para enviar recordatorios por WhatsApp desde Gestión de Cobranza. Los templates existen pero no están integrados en el flujo de cobranza.

### Correos (`apps/emails/`)

| Componente | Ubicación | Relación con Cobranza |
|------------|-----------|------------------------|
| EmailService | `services.py` | Envío vía Resend, Gmail, Outlook, SMTP |
| EmailAccount | `models.py` | Cuenta por usuario-empresa (Gmail/Outlook/SMTP) |
| TemplateRenderingService | `email_services/unified_template_rendering_service.py` | Renderiza templates con variables |
| get_banking_context | `utils.py` | Datos bancarios para templates |

**Flujo cobranza**: `send_collection_emails` → `TemplateRenderingService.render_from_template` o `render_from_strings` → `EmailService.send_rendered_email` → Resend/ SMTP.

**Gaps**: Sin rate limiting en envío masivo (riesgo de bloqueo). No hay plantillas por defecto de cobranza en el sistema; el usuario debe crear o escribir HTML/texto manualmente.

### Templates (`EmailTemplate`)

| Campo | Uso en Cobranza |
|-------|-----------------|
| `name` | Ej. "Cobranza Vencida", "Cobranza WhatsApp - Base" |
| `category` | `"cobranza"` para filtrar en UI |
| `template_type` | `"email"` o `"whatsapp"` |
| `body` / `html_body` | Contenido con variables Django/Jinja |
| `master_entity` | Template por empresa (opcional) |

**Variables típicas**: `{{cliente}}`, `{{monto}}`, `{{facturas}}`, `{{dias}}`, `{{banking.*}}`, `{{invoice.folio}}`, `{{multi_invoice_payment_link}}`.

**Gaps**: No hay templates precargados para cobranza (el usuario empieza desde cero). La categoría `cobranza` existe pero no hay filtro en la UI de cobranza para "usar solo templates de cobranza". Falta documentación de variables disponibles por contexto.

### 4.2 Flujo Integrado (Cobranza ↔ Conciliación ↔ Correos ↔ Templates)

```
[Factura emitida] → DocumentStatus NOT_PAID
        ↓
[Gestión Cobranza] → Lista clientes con pendientes
        ↓
[Usuario envía correo] → EmailTemplate (cobranza) + banking context → Resend
        ↓
[Cliente paga] → Transferencia bancaria
        ↓
[Conciliación] → Movement + Document match → BankReconciliationDocument (mark_as_paid=True)
        ↓
[DocumentStatus] → PAID
        ↓
[Cobranza] → Factura ya no aparece en pendientes
```

**Canal WhatsApp**: No integrado. Templates existen; falta flujo de envío desde cobranza.

---

## 5. Análisis Técnico

### 5.1 Errores y Bugs

| Prioridad | Problema | Ubicación | Descripción |
|-----------|----------|-----------|-------------|
| **Alta** | `print()` en lugar de logger | `collection_management.py:183-184` | Errores de Slack se imprimen con `print()` en lugar de `logger.warning()` |
| **Alta** | Inconsistencia en tipos de documento | `CollectionSummaryView` vs `collection_management` | CollectionSummaryView filtra solo 33, 34, 39. collection_management incluye 80 (boletas honorarios). Reportes pueden no coincidir |
| **Media** | Clientes sin email omitidos silenciosamente | `send_collection_emails:441-442` | Si el cliente no tiene email, se hace `continue` sin registrar error ni feedback al usuario |
| **Media** | Due date hardcodeado 30 días | `CollectionInvoiceSerializer:97`, `_calculate_client_status:203` | Todas las facturas asumen 30 días de plazo. No hay configuración por empresa ni por tipo de documento |
| **Baja** | Respuesta vacía cuando `client_id` es undefined | `get_client_invoices:319-320` | Retorna `[]` sin mensaje explicativo |
| **Media** | Cobranza no usa templates de WhatsApp | `send_collection_emails` | Solo envía email; templates WhatsApp de cobranza existen pero no se usan |
| **Baja** | No hay templates precargados de cobranza | `EmailTemplate` | Usuario debe crear plantilla desde cero |
| **Baja** | Conciliación no notifica a cobranza | `BankReconciliation` | Al conciliar, DocumentStatus se actualiza pero no hay notificación/feedback en módulo cobranza |

### 5.2 Problemas de Performance

| Problema | Impacto | Ubicación |
|----------|---------|-----------|
| **N+1 en get_collection_clients** | Por cada cliente se ejecutan múltiples queries: total_invoices.count(), paid_invoices.count(), pending_invoices_qs, list(pending_invoices_qs), paid_invoices sum, etc. Con 100+ clientes, la carga puede ser lenta | `collection_management.py:244-386` |
| **Sin paginación** | La lista de clientes se carga completa. Empresas con 500+ clientes tendrán problemas | `get_collection_clients` |
| **Iteración en Python para total_pending** | `for invoice in pending_invoices_list` podría hacerse con `aggregate(Sum())` en DB | `collection_management.py:305-319` |
| **CollectionSummaryView suma en Python** | `sum(float(invoice.amount_with_iva or 0) for invoice in pending_queryset)` carga todos los registros en memoria | `reports.py:1008-1010` |

### 5.3 Refactors Recomendados

| Refactor | Justificación | Esfuerzo |
|----------|---------------|----------|
| **Extraer CollectionManager/Service** | La vista tiene ~400 líneas con lógica de negocio. Regla: fat models, thin views. Mover lógica a `CollectionManager` o `CollectionService` | Medio |
| **Unificar lógica de queries** | `CollectionSummaryView` debería usar `AccountsReceivableQuerySet.collection_pending_invoices()` en lugar de duplicar filtros. Incluir tipo 80 en ambos si aplica | Bajo |
| **Paginación en get_collection_clients** | Agregar `limit`/`offset` o cursor-based pagination | Bajo |
| **Optimizar get_collection_clients con annotate** | Usar `annotate()` y `Subquery` para calcular totales en una sola query por cliente | Alto |
| **Separar serializers** | `CollectionInvoiceSerializer` sobrescribe `to_representation` completo. Considerar heredar de un serializer más ligero o usar `SerializerMethodField` | Bajo |
| **Unificar capa de envío** | Crear `CollectionNotificationService` que soporte email + WhatsApp, usando templates por canal | Medio |
| **Templates por categoría** | En UI de cobranza, filtrar `EmailTemplate` por `category="cobranza"` al elegir plantilla | Bajo |

### 5.4 Cobertura de Tests

| Área | Tests actuales | Gaps |
|------|----------------|------|
| collection_management | `test_unit_collection_clients_missing_document_status`, `test_collection_resolve_document_ids`, `test_collection_template_integration` | No hay tests para get_collection_clients con datos reales, send_collection_emails, get_client_invoices |
| report_querysets | Indirectamente vía otros tests | No hay tests unitarios explícitos para collection_pending_invoices, collection_paid_invoices |
| CollectionSummaryView | No encontrados | Sin tests |
| Conciliación↔Cobranza | `test_reconciliation_with_credit_debit_notes` | No hay tests que verifiquen que al conciliar, la vista de cobranza refleje el cambio |
| Templates cobranza | `test_whatsapp_collection_template` | Solo prueba render; no flujo end-to-end de envío |

---

## 6. Nuevas Funcionalidades Sugeridas

### 6.1 Prioridad Alta

| Feature | Descripción | Valor de negocio |
|---------|-------------|------------------|
| **Fecha de vencimiento configurable** | Permitir a la empresa definir días de plazo por defecto (ej. 30, 60, 90) o por tipo de documento | Cobranza más precisa según condiciones de cada negocio |
| **Recordatorios automáticos programados** | Celery task que envíe correos de cobranza X días antes/después del vencimiento (configurable) | Reduce trabajo manual, mejora recuperación |
| **Notificación cuando cliente no tiene email** | En send_collection_emails, retornar lista de clientes omitidos por falta de email | Transparencia para el usuario |
| **Paginación y búsqueda** | Paginación en clientes, filtro por nombre/RUT | Escalabilidad para empresas grandes |
| **Envío WhatsApp desde cobranza** | Botón "Enviar por WhatsApp" en send_collection_emails, usando templates existentes | Mayor tasa de respuesta |
| **Templates precargados cobranza** | Crear 2–3 plantillas por defecto (email + WhatsApp) al configurar empresa | Menos fricción para empezar |

### 6.2 Prioridad Media

| Feature | Descripción | Valor de negocio |
|---------|-------------|------------------|
| **Integración WhatsApp cobranza** | Enviar recordatorios por WhatsApp (ya existe canal WhatsApp en el proyecto) | Mayor tasa de apertura vs email |
| **Link de pago** | Generar link de pago (ej. Webpay, Mercado Pago) para incluir en correos | Facilita cobro inmediato |
| **Exportación Excel** | Exportar reporte de cobranza (clientes, facturas pendientes, montos) | Análisis offline, reportes a gerencia |
| **Métricas DSO y aging** | Días de venta pendientes (DSO), aging por bandas (0-30, 31-60, 61-90, 90+) | Dashboards ejecutivos |
| **Priorización de cobranza** | Ordenar clientes por días vencidos, monto pendiente, o score de riesgo | Enfocar esfuerzo en deudores críticos |
| **Feedback conciliación↔cobranza** | En cobranza, indicar "conciliado automáticamente" si el pago vino de conciliación bancaria | Transparencia del origen del pago |
| **Rate limiting en emails** | Limitar envíos por minuto en send_collection_emails para evitar bloqueos SMTP/Resend | Estabilidad |
| **Documentación variables template** | Documentar en UI: `{{cliente}}`, `{{monto}}`, `{{facturas}}`, `{{banking.*}}`, etc. | Facilita personalización |

### 6.3 Prioridad Baja

| Feature | Descripción | Valor de negocio |
|---------|-------------|------------------|
| **Acuerdos de pago** | Registrar acuerdos (ej. "pagar en 3 cuotas") y seguimiento | Gestión de cobranza compleja |
| **Cesión de facturas** | Integración con módulo de cesión (factoring) | Empresas que facturan cesión |
| **Historial de cobranza** | Log de emails enviados, llamadas registradas por cliente | Trazabilidad |
| **Multi-moneda** | Soporte para facturas en USD u otras monedas en cobranza | Empresas exportadoras |
| **Sugerencia desde conciliación** | En conciliación, "este movimiento podría cobrar factura X" con link a cobranza | Flujo bidireccional |

---

## 7. Análisis de Negocio

### 7.1 Estado Actual del Módulo

El módulo cubre el flujo básico de cobranza:
1. Ver clientes con facturas pendientes
2. Ver detalle de facturas por cliente
3. Enviar correos de cobranza con plantillas
4. Marcar facturas como pagadas/no pagadas
5. Subir comprobantes de transferencia
6. Incluir datos bancarios en correos (opcional)

### 7.2 Gaps vs Competencia

| Competidor/Referencia | Lo que ofrecen | Tu Pana ofrece |
|-----------------------|----------------|----------------|
| **Factoring / Cesión** | Cesión de facturas, anticipo de cobro | Solo cesión básica (otro módulo), no integrada con cobranza |
| **Herramientas de cobranza (Pagale, Cobranza.cl)** | Recordatorios automáticos, link de pago, scoring | Recordatorios manuales, sin link de pago |
| **ERP (SAP, Odoo)** | Aging, DSO, flujos de cobranza configurables | Aging básico en reportes, sin DSO explícito |
| **Facturación electrónica (Facturador)** | Solo emisión, poco enfoque en cobranza | Emisión + cobranza integrada |

### 7.3 Ventajas Competitivas Potenciales

| Oportunidad | Descripción | Diferencial |
|-------------|-------------|-------------|
| **Cobranza integrada con facturación** | Ya tienen emisión SII, documentos, clientes. La cobranza está en el mismo flujo. | Competidores de cobranza son standalone; Tu Pana es todo-en-uno |
| **Automatización inteligente** | Recordatorios automáticos + condiciones configurables (ej. "si vence en 7 días y monto > X") | Reducción de trabajo manual, consistencia |
| **Canal WhatsApp** | Ya tienen WhatsApp. Cobranza por WhatsApp tiene mayor tasa de respuesta que email | Diferenciador en Chile donde WhatsApp es masivo |
| **Información bancaria en correos** | Ya existe. Competidores suelen pedir configurar manualmente | Menos fricción para el cliente |
| **Comprobante de transferencia** | Subir comprobante y marcar como pagado. Flujo fluido | Algunos competidores no tienen esto integrado |
| **Pago en línea nativo** | Si se agrega link de pago (Webpay, etc.), el ciclo emisión→cobranza→pago se cierra | Loop cerrado sin salir de la plataforma |
| **Cobranza para Shopify** | Órdenes de Shopify generan facturas; cobranza de esas facturas podría priorizarse | Ecosistema completo para tiendas |

### 7.4 Métricas de Éxito Sugeridas

- **DSO (Days Sales Outstanding)**: días promedio para cobrar
- **Tasa de recuperación**: % de facturas cobradas en primer recordatorio
- **Tiempo hasta primer cobro**: días desde emisión hasta primer contacto
- **Adopción**: % de empresas que usan cobranza vs solo emisión

---

## 8. Juicio de Producto: Lo que está bien y lo que falta

### 8.1 Lo que está bien a nivel de producto

| Área | Fortaleza | Impacto |
|------|-----------|---------|
| **Flujo emisión→cobranza cerrado** | La cobranza está integrada con documentos emitidos. El usuario ve las mismas facturas que emitió, sin duplicar datos ni sincronizar sistemas externos. | Es el diferencial principal vs herramientas standalone de cobranza. Flujo de trabajo natural. |
| **Información bancaria en correos** | `get_banking_context` inyecta datos de cuenta bancaria (banco, RUT, cuenta) en los correos sin configuración manual extra. | Reduce fricción: el cliente recibe los datos para transferir en el mismo correo. Competidores suelen pedir configurar esto aparte. |
| **Marcado de pago flexible** | Soporta paid, unpaid y partially_paid con `paid_amount`. Permite marcar facturas manualmente o vía conciliación bancaria. | Cubre casos reales: pagos parciales, conciliaciones anticipadas, correcciones. |
| **Comprobante de transferencia** | Subir y descargar comprobante por factura, con trazabilidad (Slack). Marcar como pagado desde la misma vista. | Flujo práctico: el cliente paga → subes el comprobante → marcas pagado. Todo en un solo lugar. |
| **Conciliación bancaria integrada** | `BankReconciliation` actualiza `DocumentStatus` al conciliar. Las facturas pasan de pendientes a pagadas sin intervención manual. | Reduce trabajo duplicado: quien concilia no tiene que marcar facturas en cobranza. |
| **Templates con variables** | Variables Jinja (`{{cliente}}`, `{{monto}}`, `{{facturas}}`, `{{banking.*}}`) permiten personalizar correos sin tocar código. | Escalabilidad: cada empresa adapta el mensaje a su tono. |
| **Contactos por cliente** | Módulo de contactos asociado a clientes, con importación Excel. Fuente única de emails para cobranza. | Base para comunicación multicanal futura (email hoy, WhatsApp mañana). |
| **Reporte de cobranza** | PaymentStatusChart, TopDebtorsTable, aging buckets. Vista ejecutiva del estado de cuentas por cobrar. | Da visibilidad sin salir de la plataforma. |
| **Búsqueda global** | Dominio `collections` en búsqueda unificada. Buscar por RUT, folio, razón social. | Encuentra facturas rápido sin filtrar manualmente. |
| **OAuth y persistencia** | Si el usuario va a configurar email y vuelve, se restauran selecciones y se reabre el modal de correo. | Buena UX en el flujo de onboarding/configuración. |
| **Auto-emails de emisión** | `AutoEmailsConfiguration` con cuerpo configurable, To/CC/BCC, include_bank_info. Envío automático al emitir. | Diferencia entre “enviar al emitir” y “recordatorio de cobranza”. Configuración flexible. |

### 8.2 Lo que falta o está incompleto

| Área | Problema | Impacto en producto |
|------|----------|----------------------|
| **Recordatorios automáticos** | No hay Celery task ni flujo para enviar correos de cobranza X días antes/después del vencimiento. Todo es manual. | El usuario debe recordar cuándo cobrar. Competidores (Pagale, Cobranza.cl) ofrecen esto como estándar. Pérdida de oportunidad de mejora en recuperación. |
| **WhatsApp no integrado** | Templates de cobranza WhatsApp existen pero no hay botón ni flujo para enviar desde Gestión de Cobranza. Solo email. | En Chile, WhatsApp tiene mayor tasa de apertura que email. Oferta a medias: templates listos pero sin uso. |
| **Fecha de vencimiento fija** | 30 días hardcodeado. No configurable por empresa ni por tipo de documento. | Cobranza incorrecta: facturas a 60 o 90 días aparecen vencidas antes de tiempo. Días vencidos y aging distorsionados. |
| **Clientes sin email invisibles** | Si no tienen email, se omiten al enviar sin avisar. No hay lista de “clientes omitidos” ni guía para completar datos. | El usuario cree que envió a todos; en realidad faltan varios. Pérdida de confianza. |
| **Sin templates precargados** | El usuario crea plantillas desde cero. No hay “Cobranza estándar” o “Recordatorio vencido” listos para usar. | Mayor fricción de onboarding. Empresas pequeñas no saben por dónde empezar. |
| **Paginación y performance** | Lista de clientes sin paginación. N+1 en queries. Empresas con 200+ clientes sufren lentitud. | Producto no escala. Posible abandono en PyMEs con muchos clientes. |
| **Feedback conciliación↔cobranza** | Al conciliar, DocumentStatus se actualiza pero la UI de cobranza no indica “conciliado automáticamente”. | El usuario no entiende por qué una factura pasó de pendiente a pagada. Falta trazabilidad. |
| **Sin link de pago** | No hay generación de link de pago (Webpay, Mercado Pago, etc.) para incluir en correos. | El cliente debe ir al banco a transferir. Competidores ofrecen “pagar aquí” en un clic. Ciclo de cobro más lento. |
| **Sin historial de cobranza** | No hay log de correos enviados, llamadas ni fechas de contacto por cliente. | Imposible auditar o dar seguimiento a una cobranza. |
| **Documentación de variables** | Las variables de template (`{{cliente}}`, `{{banking.*}}`, etc.) no están documentadas en la UI. | El usuario debe probar o pedir ayuda. Personalización más difícil. |
| **Tu Correo vs Cobranza** | Tu Correo (inbox) y Gestión de Cobranza son módulos separados. Los correos enviados desde cobranza podrían no aparecer claramente en el historial del cliente. | Experiencia fragmentada. El usuario no ve el flujo completo de comunicación con el cliente. |

### 8.3 Síntesis del juicio

**Fortalezas principales:** El producto tiene un flujo emisión→cobranza→pago coherente, integrado con documentos, banking y conciliación. La información bancaria en correos, el marcado de pago flexible (incluyendo parcial) y el comprobante de transferencia responden bien a necesidades reales. La base de contactos, templates y reportes es sólida para escalar.

**Debilidades críticas:** La ausencia de recordatorios automáticos y la falta de integración de WhatsApp en cobranza son gaps evidentes frente a competencia y uso real en Chile. La fecha de vencimiento fija y los clientes sin email omitidos generan errores silenciosos que afectan la confiabilidad de la cobranza.

**Recomendación:** Priorizar (1) recordatorios automáticos y (2) envío de cobranza por WhatsApp para acercarse al estándar del mercado. En paralelo, corregir vencimiento configurable y feedback de clientes omitidos para mejorar fiabilidad. El link de pago y el historial de cobranza son siguientes pasos de diferenciación.

---

## 9. Plan de Acción Sugerido

### Fase 1: Estabilización (1–2 sprints)
1. Reemplazar `print()` por `logger` en collection_management
2. Unificar queries entre CollectionSummaryView y collection_management (incluir tipo 80 si aplica)
3. Retornar clientes omitidos por falta de email en send_collection_emails
4. Agregar tests unitarios para get_collection_clients y send_collection_emails

### Fase 2: Performance (1 sprint)
1. Paginación en get_collection_clients
2. Optimizar queries con annotate/aggregate
3. Usar Sum() en DB en CollectionSummaryView en lugar de sum() en Python

### Fase 3: Valor de negocio (2–3 sprints)
1. Fecha de vencimiento configurable por empresa
2. Recordatorios automáticos programados
3. Exportación Excel de reporte de cobranza
4. Métricas DSO y aging en dashboard

### Fase 4: Diferenciación (3+ sprints)
1. Integración WhatsApp para cobranza
2. Link de pago en correos
3. Priorización/score de cobranza

---

## 10. Conclusión

El módulo de cobranza tiene una base sólida: flujo funcional, integración con documentos, emails, banking, **conciliación bancaria** (vía DocumentStatus) y **templates** (EmailTemplate con categoría cobranza). Los principales gaps son:

- **Técnicos**: performance (N+1, sin paginación), inconsistencias entre vistas, logging incorrecto
- **Funcionales**: falta de automatización, vencimiento fijo, poca visibilidad (clientes sin email)
- **Integración**: **WhatsApp** tiene templates de cobranza pero no está integrado en el flujo de envío; **conciliación** actualiza DocumentStatus pero no hay feedback cruzado; **templates** no tienen precarga ni filtro por categoría en UI
- **Estratégicos**: oportunidad de diferenciarse con WhatsApp, link de pago y métricas avanzadas

Priorizar estabilización y performance, y luego integrar WhatsApp + mejorar templates, permitirá escalar sin deuda técnica y aprovechar los módulos ya existentes.
