# Análisis del Flujo: "Crear Nuevo Cliente" en CustomerPicker

## STEP 1 — TRACE THE FLOW

### A) User clicks "Crear nuevo cliente" inside CustomerSearchPanel

**Flujo actual:**

```
CustomerSearchPanel.handleNewCustomerClick()
  ↓
  onNewCustomer() prop callback
  ↓
  CustomerPicker.handleNewCustomerWrapper()
  ↓
  useCustomerPickerForm.handleNewCustomer()
    → form.setValue('showSearchDropdown', false)
  ↓
  DocumentInfo.onNewCustomer callback
    → setShowNewCustomerForm(true)  // ⚠️ Estado LOCAL en DocumentInfo
```

**Problema identificado:**
- El modal `NewCustomerForm` es **propiedad de DocumentInfo** (línea 59: `const [showNewCustomerForm, setShowNewCustomerForm] = useState(false)`)
- El modal se renderiza en DocumentInfo (líneas 498-508), NO dentro de CustomerPicker
- CustomerPicker solo llama al callback `onNewCustomer`, pero NO controla el modal

**Cómo DEBE funcionar:**
- CustomerPicker debe tener un estado interno (en RHF) para controlar el modal: `mode: 'search' | 'create'`
- CustomerPicker debe renderizar `NewCustomerForm` condicionalmente basado en RHF state
- DocumentInfo solo debe recibir `onCustomerChange` cuando el cliente se crea/selecciona

---

### B) User submits NewCustomerForm

**Flujo actual:**

```
NewCustomerForm.onSubmit()
  ↓
  useNewCustomerForm.onSubmit()
    → Crea customerData con: id, tax_id, name, addresses, activities, selected_address, selected_activity
  ↓
  onCustomerCreated(customerData) callback
  ↓
  DocumentInfo.handleCustomerCreated(newCustomer)
    → setShowNewCustomerForm(false)  // Cierra modal
    → setFormData({ ... })  // Actualiza formData con:
      - receiver_id
      - receiver_tax_id
      - receiver_name
      - receiver_business_name
      - receiver_contact
      - customer_addresses
      - customer_activities
      - selected_address_id
      - selected_activity_id
      - receiver_address, receiver_city, receiver_district
      - customer_economic_activity, customer_activity_code
  ↓
  mapFormDataToCustomerFormValues()  // Convierte formData → CustomerFormValues
  ↓
  CustomerPicker recibe defaultValues
  ↓
  useCustomerPickerForm.useEffect()  // Sincroniza defaultValues con RHF
    → form.setValue('id', ...)
    → form.setValue('taxId', ...)
    → form.setValue('businessName', ...)
    → form.setValue('addresses', ...)
    → form.setValue('activities', ...)
    → form.setValue('selectedAddressId', ...)
    → form.setValue('selectedActivityId', ...)
```

**Mapeo de campos:**

| newCustomer (from NewCustomerForm) | formData (DocumentInfo) | CustomerFormValues (CustomerPicker) |
|-----------------------------------|------------------------|-------------------------------------|
| `id` / `master_entity_id` | `receiver_id` | `id` |
| `tax_id` | `receiver_tax_id` | `taxId` |
| `name` | `receiver_name`, `receiver_business_name` | `name`, `businessName` |
| `contact` | `receiver_contact` | `contact` |
| `addresses[]` | `customer_addresses[]` | `addresses[]` |
| `activities[]` | `customer_activities[]` | `activities[]` |
| `selected_address.id` | `selected_address_id` | `selectedAddressId` |
| `selected_activity.id` | `selected_activity_id` | `selectedActivityId` |
| `selected_address.address` | `receiver_address` | `address` |
| `selected_address.district.city.name` | `receiver_city` | `city` |
| `selected_address.district.name` | `receiver_district` | `district` |
| `selected_activity.name` | `customer_economic_activity` | `activityName` |
| `selected_activity.code` | `customer_activity_code` | `activityCode` |

**Problema identificado:**
- Hay **3 transformaciones** de datos: `newCustomer` → `formData` → `CustomerFormValues`
- Cada transformación puede perder datos o tener inconsistencias
- `defaultValues` en RHF **NO son reactivos** - solo se usan en la inicialización
- El `useEffect` en `useCustomerPickerForm` intenta sincronizar, pero depende de que `defaultValues` cambien, lo cual puede no ocurrir si React no detecta el cambio

---

## STEP 2 — CUSTOMER PICKER HYDRATION CHECK

**Análisis de cómo CustomerPicker recibe datos después de la creación:**

1. **mapFormDataToCustomerFormValues()** (líneas 141-230 en ScheduledDocumentDetails.tsx):
   - Convierte `formData` a `CustomerFormValues`
   - Se ejecuta en cada render
   - Retorna un objeto nuevo cada vez (puede causar re-renders innecesarios)

2. **defaultValues pasados a CustomerPicker**:
   - Se pasan como prop: `defaultValues={mapFormDataToCustomerFormValues()}`
   - Se recalculan en cada render del padre

3. **useCustomerPickerForm inicialización**:
   - `useForm({ defaultValues: formDefaultValues })` - **Solo se ejecuta una vez**
   - Los `defaultValues` NO se actualizan automáticamente cuando cambian

4. **useEffect de sincronización** (líneas 95-228 en useCustomerPickerForm.ts):
   - Intenta sincronizar `defaultValues` externos con RHF usando `form.setValue()`
   - Se ejecuta cuando cambian `defaultValues`, `addresses`, o `activities`
   - **Problema**: Si `defaultValues` es un objeto nuevo pero con los mismos valores, React puede no detectar el cambio

**¿Por qué `defaultValues` solo NO es suficiente?**

> `defaultValues` en React Hook Form son **solo para la inicialización**. Una vez que el formulario está montado, cambiar `defaultValues` NO actualiza el formulario automáticamente. Se requiere llamar explícitamente a `form.reset(newValues)` o `form.setValue()` para cada campo.

**Comportamiento requerido después del cambio:**
- CustomerPicker debe llamar `form.reset(mappedValues)` cuando se crea un nuevo cliente
- NO depender de `defaultValues` reactivos
- El modal debe cerrarse actualizando un campo en RHF (ej: `mode: 'search'`)

---

## STEP 3 — FORM VISIBILITY & LOADER ANALYSIS

**Campos en RHF después de la creación (verificación paso a paso):**

| Campo | ¿Se establece? | Fuente |
|-------|----------------|--------|
| `id` | ✅ Sí | `form.setValue('id', defaultValues.id)` (línea 97) |
| `taxId` | ✅ Sí | `form.setValue('taxId', defaultValues.taxId)` (línea 100) |
| `businessName` | ✅ Sí | `form.setValue('businessName', defaultValues.businessName)` (línea 106) |
| `contact` | ✅ Sí | `form.setValue('contact', defaultValues.contact)` (línea 109) |
| `addresses` | ✅ Sí | `form.setValue('addresses', addresses)` (línea 114) |
| `activities` | ✅ Sí | `form.setValue('activities', activities)` (línea 115) |
| `selectedAddressId` | ✅ Sí | Lógica compleja (líneas 119-161) - selecciona primera si no hay selección |
| `selectedActivityId` | ✅ Sí | Lógica compleja (líneas 179-227) - selecciona primera si no hay selección |
| `addressMode` | ✅ Sí | Se establece a `'select'` si hay direcciones (línea 130, 138, 152, 160) |
| `activityMode` | ✅ Sí | Se establece a `'select'` si hay actividades (línea 189, 196, 207, 214) |
| `isLoadingCustomerDetails` | ⚠️ Parcial | Se establece desde `defaultValues.isLoadingCustomerDetails` (línea 69), pero puede no actualizarse |

**Análisis de CustomerDetailsForm:**

**shouldShowLoader calculation** (líneas 30-40 en CustomerDetailsForm.tsx):
```typescript
const isLoading = form.watch('isLoadingCustomerDetails');
const requiresAddress = strategy.requiresAddress();
const requiresActivity = strategy.requiresActivity();
const selectedAddressId = form.watch('selectedAddressId');
const selectedActivityId = form.watch('selectedActivityId');
const addresses = form.watch('addresses');
const activities = form.watch('activities');

const hasAddressLoaded = !requiresAddress || (addresses.length > 0 && selectedAddressId);
const hasActivityLoaded = !requiresActivity || (activities.length > 0 && selectedActivityId);
const shouldShowLoader = isLoading || !hasAddressLoaded || !hasActivityLoaded;
```

**Condiciones donde el loader NUNCA desaparece:**

1. **Si `isLoadingCustomerDetails` es `true` y nunca se actualiza a `false`**
2. **Si `requiresAddress` es `true` pero:**
   - `addresses.length === 0` (no hay direcciones)
   - O `selectedAddressId` está vacío (aunque haya direcciones)
3. **Si `requiresActivity` es `true` pero:**
   - `activities.length === 0` (no hay actividades)
   - O `selectedActivityId` está vacío (aunque haya actividades)

**Problema identificado:**
- Si `addresses` y `activities` existen pero `selectedAddressId`/`selectedActivityId` no se establecen correctamente, el loader nunca desaparece
- El `useEffect` en `useCustomerPickerForm` intenta seleccionar automáticamente la primera dirección/actividad, pero puede fallar si:
  - El efecto no se ejecuta (dependencias no cambian)
  - La lógica de selección tiene un bug

---

## STEP 4 — ROOT CAUSE (SINGLE SENTENCE)

**Root Cause:**
> **RHF nunca se resetea explícitamente después de crear un cliente nuevo** - el sistema depende de `defaultValues` reactivos y un `useEffect` complejo que puede no ejecutarse correctamente, causando que los campos `id`, `selectedAddressId`, y `selectedActivityId` no se establezcan, lo que impide que `CustomerDetailsForm` se renderice y que el loader desaparezca.

---

## STEP 5 — MINIMAL FIX (NO BACKEND / NO UX REDESIGN)

### Ubicación del fix:

1. **CustomerPicker/index.tsx**: Agregar estado interno para modal y renderizar `NewCustomerForm`
2. **useCustomerPickerForm.ts**: Agregar handler `handleCustomerCreated` que llama a `form.reset()`
3. **ScheduledDocumentDetails.tsx**: Remover modal `NewCustomerForm` y callback `handleCustomerCreated`

### Implementación:

#### 1. CustomerPicker/index.tsx

```typescript
// Agregar import
import { NewCustomerForm } from '../../NewCustomerForm';

// Agregar estado para modal (controlado por RHF)
const showCreateModal = form.watch('showCreateModal') ?? false;

// Agregar handler para cuando se crea un cliente
const handleCustomerCreated = (newCustomer: any) => {
    // Mapear newCustomer → CustomerFormValues
    const mappedValues: CustomerFormValues = {
        id: String(newCustomer.id ?? newCustomer.master_entity_id ?? ''),
        taxId: newCustomer.tax_id ?? '',
        name: newCustomer.name ?? '',
        businessName: newCustomer.name ?? '',
        contact: newCustomer.contact ?? '',
        addresses: newCustomer.addresses ?? [],
        activities: newCustomer.activities ?? [],
        selectedAddressId: newCustomer.selected_address?.id ? String(newCustomer.selected_address.id) : 
            (newCustomer.addresses?.[0]?.id ? String(newCustomer.addresses[0].id) : ''),
        selectedActivityId: newCustomer.selected_activity?.id ? String(newCustomer.selected_activity.id) : 
            (newCustomer.activities?.[0]?.id ? String(newCustomer.activities[0].id) : ''),
        address: newCustomer.selected_address?.address ?? newCustomer.addresses?.[0]?.address ?? '',
        city: newCustomer.selected_address?.district?.city?.name ?? newCustomer.addresses?.[0]?.district?.city?.name ?? '',
        district: newCustomer.selected_address?.district?.name ?? newCustomer.addresses?.[0]?.district?.name ?? '',
        activityName: newCustomer.selected_activity?.name ?? newCustomer.activities?.[0]?.name ?? '',
        activityCode: newCustomer.selected_activity?.code ?? newCustomer.activities?.[0]?.code ?? '',
        addressMode: (newCustomer.addresses?.length > 0) ? 'select' : 'manual',
        activityMode: (newCustomer.activities?.length > 0) ? 'select' : 'manual',
        isLoadingCustomerDetails: false,
        searchTerm: newCustomer.name ?? '',
        showSearchDropdown: false,
        showCreateModal: false, // Cerrar modal
    };
    
    // Resetear RHF con los nuevos valores
    form.reset(mappedValues);
    
    // Notificar al padre
    if (onCustomerChange) {
        onCustomerChange(mappedValues);
    }
};

// Modificar handleNewCustomerWrapper
const handleNewCustomerWrapper = () => {
    form.setValue('showCreateModal', true);
    if (onNewCustomer) {
        onNewCustomer(); // Mantener compatibilidad
    }
};

// Agregar render condicional de NewCustomerForm
{showCreateModal && (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <NewCustomerForm
                onCustomerCreated={handleCustomerCreated}
                onCancel={() => form.setValue('showCreateModal', false)}
                initialRut={form.watch('searchTerm') || ''}
            />
        </div>
    </div>
)}
```

#### 2. useCustomerPickerForm.ts

```typescript
// Agregar 'showCreateModal' a CustomerFormValues (en CustomerPicker.types.ts)
// showCreateModal: boolean;

// Agregar a formDefaultValues
showCreateModal: defaultValues.showCreateModal ?? false,

// NO se necesita cambio adicional - el reset en CustomerPicker es suficiente
```

#### 3. ScheduledDocumentDetails.tsx

```typescript
// REMOVER:
// - const [showNewCustomerForm, setShowNewCustomerForm] = useState(false);
// - El render de NewCustomerForm (líneas 498-508)
// - handleCustomerCreated (líneas 77-138) - ya no es necesario

// MODIFICAR onNewCustomer en CustomerPicker:
onNewCustomer={() => {}} // Vacío - CustomerPicker maneja todo internamente
```

---

## STEP 6 — VERIFICATION CHECKLIST

Después del fix, verificar:

- [ ] "Crear nuevo cliente" se abre/cierra por CustomerPicker (NO DocumentInfo)
  - Verificar que `showCreateModal` está en RHF, no en estado local de DocumentInfo
- [ ] Modal/panel se cierra al crear exitosamente
  - Verificar que `form.setValue('showCreateModal', false)` se llama en `handleCustomerCreated`
- [ ] CustomerPicker search input muestra el cliente
  - Verificar que `form.setValue('searchTerm', newCustomer.name)` se establece
- [ ] CustomerDetailsForm se renderiza inmediatamente
  - Verificar que `form.watch('id')` es truthy después de `form.reset()`
- [ ] Business name es visible y editable (según estrategia)
  - Verificar que `businessName` se establece y `strategy.isBusinessNameEditable()` se respeta
- [ ] Address selector muestra la dirección correcta por defecto
  - Verificar que `selectedAddressId` y campos de dirección se establecen
- [ ] Activity selector muestra la actividad correcta por defecto
  - Verificar que `selectedActivityId` y campos de actividad se establecen
- [ ] Loader desaparece
  - Verificar que `isLoadingCustomerDetails` es `false` y `hasAddressLoaded`/`hasActivityLoaded` son `true`
- [ ] No queda el error "Selecciona un cliente"
  - Verificar que `selectedTaxId` (en CustomerSearchPanel) es truthy
- [ ] DocumentInfo recibe valores actualizados SOLO a través de `onCustomerChange`
  - Verificar que `handleCustomerCreated` en DocumentInfo ya no existe
  - Verificar que `handleCustomerChange` se llama con los valores correctos

---

## RESUMEN DE CAMBIOS REQUERIDOS

1. **CustomerPicker debe poseer el modal NewCustomerForm**
2. **CustomerPicker debe llamar `form.reset()` explícitamente después de crear cliente**
3. **DocumentInfo debe remover toda lógica de creación de cliente**
4. **El flujo debe ser: NewCustomerForm → CustomerPicker.handleCustomerCreated → form.reset() → onCustomerChange → DocumentInfo.handleCustomerChange**

