# Flujo Completo: Seleccionar Cliente en Scheduled Documents

## Problema Actual

Al apretar "Seleccionar Cliente" se cierra el modal y se recarga toda la página/vista.

## Flujo Actual (PROBLEMÁTICO)

### 1. Usuario aprieta "Seleccionar Cliente" en NewCustomerForm

- **Archivo**: `src/components/customers/forms/newCustomer/NewCustomerForm.tsx:193`
- **Botón**: `<button type="submit">` con texto "Seleccionar Cliente"
- **Acción**: Dispara `onSubmit` del formulario

### 2. useNewCustomerForm.onSubmit se ejecuta

- **Archivo**: `src/components/customers/forms/newCustomer/useNewCustomerForm.ts:174`
- **Línea 186-199**: Si el cliente existe, crea `customerData` y llama `onCustomerCreated(customerData)`
- **Línea 212-224**: Si se encuentra la entidad, crea `customerData` y llama `onCustomerCreated(customerData)`
- **Problema**: `customerData` incluye `addresses` y `activities` del primer request, pero pueden estar vacíos

### 3. handleCustomerCreated en ScheduledDocumentDetails

- **Archivo**: `src/components/platform/invoice/scheduled/ScheduledDocumentDetails.tsx:75`
- **Línea 80**: Cierra modal: `setShowNewCustomerForm(false)`
- **Línea 88-100**: Crea `customerItem` y llama `await handleCustomerSelect(customerItem)`
- **PROBLEMA**: Está llamando a `handleCustomerSelect` que hace otra llamada al backend

### 4. handleCustomerSelect en ScheduledDocumentForm

- **Archivo**: `src/components/platform/invoice/scheduled/ScheduledDocumentForm.tsx:850`
- **Línea 859**: Llama `await hydrateCustomerByRut(customer.tax_id || '', customer.name || '', receiverId)`

### 5. hydrateCustomerByRut

- **Archivo**: `src/components/platform/invoice/scheduled/ScheduledDocumentForm.tsx:812`
- **Línea 817-835**: Limpia campos y establece `isLoadingCustomerDetails: true`
- **Línea 844**: Llama `await loadCustomerDetails(rut)` - **OTRA LLAMADA AL BACKEND**

### 6. loadCustomerDetails

- **Archivo**: `src/components/platform/invoice/scheduled/ScheduledDocumentForm.tsx:412`
- **Línea 458**: Hace `api.get('/master-entities/?rut=...')` - **LLAMADA DUPLICADA**
- **Línea 479-537**: Actualiza `formData` con direcciones y actividades

### 7. useScheduledCustomerForm.useEffect se dispara

- **Archivo**: `src/components/platform/invoice/scheduled/forms/customer/useScheduledCustomerForm.ts:64`
- **Línea 72**: `form.reset(defaultValues)` - **RESETEA EL FORMULARIO**
- **Dependencias**: `[defaultValues, form, formData?.receiver_id, addresses.length, activities.length, strategy]`
- **PROBLEMA**: Cada vez que cambia `receiver_id` o `addresses.length`, se resetea el formulario

### 8. defaultValues se recalcula

- **Archivo**: `src/components/platform/invoice/scheduled/forms/customer/useScheduledCustomerForm.ts:29`
- **Dependencias**: `[formData?.receiver_id, formData?.receiver_tax_id, formData?.receiver_name, ...]`
- **Problema**: Cada cambio en `formData` recalcula `defaultValues`, lo que dispara el `useEffect` de nuevo

## Flujo en Multi Invoice Wizard (CORRECTO)

### 1. Usuario aprieta "Seleccionar Cliente"

- Mismo flujo hasta `onCustomerCreated`

### 2. handleCustomerCreated en Multi Invoice Wizard

- **Archivo**: `src/pages/multi-invoice-wizard/index.tsx:1685`
- **Línea 1689**: Cierra modal: `setShowNewCustomerForm(false)`
- **Línea 1693-1696**: Usa datos ya obtenidos: `addresses`, `activities`, `defaultAddress`, `defaultActivity`
- **Línea 1699-1719**: Construye `customerData` con datos ya disponibles
- **Línea 1722**: `setValue('documents.${activeDocIndex}.customer', customerData)` - **DIRECTO, SIN LLAMADAS ADICIONALES**
- **NO llama a handleCustomerSelect ni hace llamadas al backend**

## Solución Implementada

### Cambios en handleCustomerCreated

- **Archivo**: `src/components/platform/invoice/scheduled/ScheduledDocumentDetails.tsx:75`
- **Cambio**: Usar datos directamente como multi invoice wizard
- **NO llamar a handleCustomerSelect**
- **NO hacer llamadas adicionales al backend**
- **Actualizar formData directamente con los datos ya disponibles**

### Cambios Necesarios Adicionales

1. **Optimizar useScheduledCustomerForm.useEffect**
   - Evitar `form.reset()` innecesario
   - Solo resetear cuando realmente cambie el cliente (no solo addresses.length)

2. **Optimizar defaultValues**
   - Evitar recalcular cuando solo cambian direcciones/actividades
   - Solo recalcular cuando cambie el cliente (receiver_id)

## Comparación

| Acción | Scheduled (ANTES) | Multi Invoice Wizard | Scheduled (DESPUÉS) |
|--------|------------------|---------------------|---------------------|
| Cerrar modal | ✅ Sí | ✅ Sí | ✅ Sí |
| Usar datos del primer request | ❌ No | ✅ Sí | ✅ Sí |
| Llamar a handleCustomerSelect | ✅ Sí | ❌ No | ❌ No |
| Llamar a loadCustomerDetails | ✅ Sí | ❌ No | ❌ No |
| Hacer llamada adicional al backend | ✅ Sí | ❌ No | ❌ No |
| Actualizar formData directamente | ❌ No | ✅ Sí | ✅ Sí |
| Resetear formulario RHF | ✅ Sí (cada cambio) | ❌ No | ⚠️ Necesita optimización |
