# Flujo: Crear Cliente en Facturas Programadas

## Problema actual

1. **El cliente nuevo NO se selecciona** en el formulario después de crearlo
2. **La página se recarga** al hacer clic en "Crear Cliente"

---

## Flujo actual (paso a paso) al apretar "Crear Cliente"

1. **NewCustomerForm** (dentro del modal):
   - El botón tiene `type="submit"` → dispara el submit del `<form>` del NewCustomerForm
   - `handleSubmit(e)` se ejecuta con `e.preventDefault()`
   - Llama a `api.get(/master-entities/?rut=...)` para buscar/crear el cliente
   - Si OK: llama `onCustomerCreated(newCustomerData)` con `{id, tax_id, name}`

2. **handleCustomerCreated** (en DocumentInfo / ScheduledDocumentDetails):
   - Construye `customerItem` con los datos (address/activity vacíos porque NewCustomerForm no los pasa)
   - Llama `handleCustomerSelect(customerItem)` → actualiza formData, selectedCustomerRut, searchTerm
   - Llama `onCustomerCreated(newCustomer)` (callback del padre)
   - Llama `setShowNewCustomerForm(false)` → cierra el modal

3. **onCustomerCreated** (en ScheduledDocumentForm):
   - Actualiza formData con receiver_id, receiver_name, receiver_tax_id, receiver_business_name
   - Llama `loadCustomerDetails(tax_id)` para cargar direcciones y actividades

4. **Problema raíz: formularios anidados**
   - El modal con NewCustomerForm está **dentro** del `<form>` de ScheduledDocumentForm
   - En HTML, los formularios anidados son inválidos
   - Al hacer submit del formulario interno, el navegador puede:
     - Enviar el formulario externo (el de guardar documento programado)
     - Provocar recarga/navegación
   - La recarga ocurre **antes** de que los updates de React se reflejen → el cliente no se ve seleccionado

---

## Comparación: Multi-Invoice Wizard (funciona)

- El modal se renderiza **fuera** del formulario principal
- Estructura: `{wizardContent}{modal}` como hermanos
- El formulario del wizard termina en la línea 2402
- El modal está en un bloque separado (líneas 2407-2440)
- No hay formularios anidados → no hay submit accidental del form padre

---

## 3 soluciones propuestas

### Solución 1: Mover el modal fuera del formulario (como Multi-Invoice Wizard)

**Descripción:** Renderizar el modal de NewCustomerForm como hermano del form, no como hijo.

**Pros:**

- Misma arquitectura que Multi-Invoice Wizard (consistencia)
- Elimina el problema de formularios anidados de raíz
- Solución estándar y probada

**Contras:**

- Requiere refactorizar la estructura de ScheduledDocumentForm (mover estado del modal al nivel del form)

---

### Solución 2: Cambiar el botón "Crear Cliente" a type="button" y usar onClick

**Descripción:** En NewCustomerForm, cambiar el botón de `type="submit"` a `type="button"` y llamar handleSubmit desde onClick.

**Pros:**

- Cambio mínimo (solo NewCustomerForm)
- Evita que el botón dispare submit del form padre

**Contras:**

- El form interno seguiría anidado (HTML inválido)
- Podría haber otros edge cases con formularios anidados

---

### Solución 3: Usar React Portal para renderizar el modal fuera del DOM del form

**Descripción:** Renderizar el modal con `ReactDOM.createPortal()` en `document.body`, fuera del árbol del form.

**Pros:**

- El modal queda fuera del form en el DOM real
- No requiere cambiar la estructura de componentes

**Contras:**

- Más complejo
- El modal ya usa `position: fixed` que lo saca visualmente del flujo, pero en el DOM sigue siendo hijo del form

---

## Solución elegida: **Solución 1** (mover modal fuera del form)

**Razones:**

1. Es el patrón que ya funciona en Multi-Invoice Wizard
2. Resuelve el problema estructural (formularios anidados)
3. Código más limpio y mantenible
4. No depende de trucos (type="button" podría no ser suficiente si hay otros submits)

---

## Implementación realizada

1. **ScheduledDocumentForm**: Estado `showNewCustomerForm` y modal en `modalContent` (fuera del `<form>`)
2. **ScheduledDocumentDetails**: Recibe `onNewCustomerClick` y lo pasa a DocumentInfo
3. **DocumentInfo**: Botón "Nuevo Cliente" llama `onNewCustomerClick()` en lugar de abrir modal local
4. **handleNewCustomerCreated**: En ScheduledDocumentForm, construye customerItem, llama `handleCustomerSelect`, cierra modal
