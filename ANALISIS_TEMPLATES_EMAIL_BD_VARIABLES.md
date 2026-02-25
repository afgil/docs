# Análisis: Templates de Email en Base de Datos - Problemas con Variables

## Resumen Ejecutivo

Los templates de email guardados en la base de datos (`EmailTemplate`) usan sintaxis Django (`{{ variable }}`, `{% for %}`, etc.) pero presentan varios problemas que hacen que "las variables no funcionen bien y no puedan quedar exactamente igual" cuando el usuario edita o visualiza el resultado.

---

## Arquitectura Actual

- **Modelo**: `EmailTemplate` en `apps/emails/models.py`
- **Renderizado**: `UnifiedTemplateRenderingService` en `apps/emails/email_services/unified_template_rendering_service.py`
- **Motor**: Django Template Engine
- **Contexto**: `_build_context()` construye el dict con `company`, `client`, `invoice`, `invoices`, `banking`, `facturas`, etc.

---

## Problemas Identificados

### 1. **Transformación del contenido antes de renderizar** (causa de "no quedan igual")

El servicio **modifica** el HTML del usuario antes de renderizar:

| Transformación | Método | Efecto |
|----------------|--------|--------|
| Limpieza de `{% endfor %}` sueltos | `_clean_orphaned_endfor()` | Elimina o agrega tags |
| Auto-envolver `<li>` con `{% for invoice in invoices %}` | `_prepare_html_template()` | Añade loops automáticos |
| Auto-envolver `<p>` con bullets | `_prepare_html_template()` | Añade loops automáticos |
| Mover `{% if %}` fuera de `<p>` | `_move_conditionals_outside_paragraphs()` | Reestructura HTML |

**Consecuencia**: Lo que el usuario guarda ≠ lo que se renderiza. El sistema "interpreta" y cambia el template.

### 2. **Inconsistencia de variables documentadas vs. disponibles**

| Documentación (ANALISIS_MODULO_COBRANZA.md) | Contexto real |
|---------------------------------------------|---------------|
| `{{cliente}}` | No existe. Usar `{{ client.name }}` |
| `{{monto}}` | No existe. Usar `{{ invoice.amount }}` o `{{ facturas.monto_total }}` |
| `{{facturas}}` | Existe como objeto: `{{ facturas.cantidad }}`, `{{ facturas.monto_total }}` |
| `{{dias}}` | No está en el contexto por defecto |

**Consecuencia**: Usuarios que siguen documentación existente obtienen variables vacías.

### 3. **Rich text / WYSIWYG corrompe la sintaxis Django**

Cuando el usuario edita en un editor HTML (frontend):

```html
<!-- Usuario quiere: -->
{% if banking %}
<p>Información bancaria</p>
{% endif %}

<!-- El editor produce: -->
<p>{% if banking %}</p>
<p>Información bancaria</p>
<p>{% endif %}</p>
```

Django no puede parsear tags `{% %}` partidos por etiquetas HTML. El test `test_custom_template_with_django_tags_in_p_tags` documenta este caso.

### 4. **Validación de variables insuficiente**

- `validate_template_variables()` solo verifica caracteres inválidos (`<>"'`)
- No valida que las variables existan en el contexto real
- No hay lista canónica de variables permitidas expuesta al usuario
- `allowed_variables` es opcional y poco estricto

### 5. **Dos sistemas de variables en el mismo modelo**

- **Email** (`template_type="email"`): Django `{{ invoice.folio }}`, `{{ company.name }}`
- **WhatsApp** (`template_type="whatsapp"`): `{{1}}`, `{{2}}` (formato Meta)

El modelo `EmailTemplate` sirve ambos. La propiedad `whatsapp_variable_count` busca `{{1}}`, `{{2}}`, pero el renderizado de email usa Django. Confusión para quién mantiene templates.

### 6. **Lógica de auto-wrap frágil**

`_prepare_html_template()` tiene ~200 líneas de regex que:
- Detectan `<li>` con `{{ invoice... }}` y los envuelven en `{% for %}`
- Detectan párrafos con bullets y los envuelven
- Tienen muchos edge cases (condicionales, `<ul>`, etc.)

Si el usuario escribe algo que el regex interpreta mal, el resultado es incorrecto.

---

## Variables Disponibles en el Contexto (Referencia)

### Entidades
| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `company` | Empresa emisora | `{{ company.name }}`, `{{ company.tax_id }}`, `{{ company.email }}` |
| `client` | Cliente/receptor | `{{ client.name }}`, `{{ client.tax_id }}` |
| `sender` | Alias de client (documentos recibidos) | `{{ sender.name }}` |

### Documentos
| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `invoice` | Primera factura (singleton) | `{{ invoice.folio }}`, `{{ invoice.amount }}`, `{{ invoice.date }}` |
| `invoices` | Lista de facturas | `{% for invoice in invoices %}...{% endfor %}` |
| `document` | Alias de invoice | `{{ document.folio }}`, `{{ document.date_issued }}`, `{{ document.total_amount }}` |

### Resumen de facturas
| Variable | Descripción |
|----------|-------------|
| `facturas.cantidad` | Número de facturas |
| `facturas.monto_total` | Total formateado (ej: "$1.234.567") |

### Bancario
| Variable | Descripción | Requiere `{% if banking %}` |
|----------|-------------|----------------------------|
| `banking.bank_name` | Nombre del banco | Sí |
| `banking.account_number` | Número de cuenta | Sí |
| `banking.account_type` | Tipo de cuenta | Sí |
| `banking.account_holder` | Titular | Sí |
| `banking.account_holder_tax_id` | RUT del titular | Sí |
| `banking.account_type_display` | Tipo mostrado | Sí |

### Fechas
| Variable | Descripción |
|----------|-------------|
| `MES` | Nombre del mes (ej: "enero") |
| `AÑO` / `ANO` | Año |
| `DIA` | Día |
| `NUMERO_MES` | Mes con 2 dígitos (ej: "01") |

### Links
| Variable | Descripción |
|----------|-------------|
| `link_pago` | URL de pago |
| `multi_invoice_payment_link` | URL de pago multi-factura |
| `base_url` | URL base del frontend |

---

## Propuesta de Solución

### Opción A: Simplificar – Variables con marcadores fijos

**Idea**: Sustituir Django templates por un sistema de marcadores simple y predecible.

- Sintaxis: `{{NOMBRE_VARIABLE}}` donde NOMBRE_VARIABLE es una de una lista cerrada.
- Ejemplo: `{{CLIENTE_NOMBRE}}`, `{{FOLIO}}`, `{{MONTO}}`, `{{LINK_PAGO}}`.
- No usar `{% for %}`, `{% if %}`: el backend decide el contenido (p. ej. tabla de facturas como bloque).

**Pros**: Sin corrupción por WYSIWYG, sin transformaciones, fácil de documentar.  
**Contras**: Menos flexibilidad (no loops/condicionales en el template).

### Opción B: Separar modo "código" vs "visual"

- **Modo código**: textarea plano, sin WYSIWYG. Usuario escribe `{{ invoice.folio }}` directamente.
- **Modo visual**: el editor no toca `{{ }}` ni `{% %}`, o usa placeholders que se mapean a variables.

**Pros**: Mantiene la flexibilidad de Django.  
**Contras**: Requiere un editor que preserve la sintaxis (p. ej. no partir tags dentro de `<p>`).

### Opción C: Migrar a templates en archivos (como `email_templates/`)

- Definir plantillas base en Python (como `client_invoice_notification_email.py`).
- La BD guarda solo **overrides** por empresa: subject customizado, bloques opcionales, etc.
- Las variables viven en código, no las escribe el usuario.

**Pros**: Consistencia, testeo, sin problemas de WYSIWYG.  
**Contras**: Menos editable por usuario final, más trabajo de implementación.

### Opción D: Mejoras incrementales (mínimo para estabilizar)

1. **Documentar variables canónicas** en la UI (lista con descripción y ejemplo).
2. **Eliminar o reducir auto-wrap**: que el usuario escriba `{% for invoice in invoices %}` explícitamente.
3. **Validación al guardar**: comprobar que las variables usadas existan en el contexto y fallar si no.
4. **Endpoint de preview** con contexto de ejemplo para probar templates.
5. **Editor**: usar textarea o editor que preserve `{{ }}` y `{% %}` (sin partir tags en HTML).

---

## Recomendación

Para que "las variables funcionen bien y queden exactamente igual":

1. **Corto plazo (Opción D)**:
   - Documentar variables en la UI.
   - Validar variables al guardar contra el contexto real.
   - Reducir o eliminar `_prepare_html_template` (auto-wrap).
   - Usar editor que no corrompa la sintaxis Django.

2. **Mediano plazo**:
   - Evaluar Opción A si la flexibilidad actual no se usa.
   - O Opción B si se necesita mantener Django con editor más robusto.

Si indicas qué opción prefieres (A, B, C o D), puedo detallar pasos de implementación concretos.
