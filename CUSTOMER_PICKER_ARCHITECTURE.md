# CustomerPicker - Arquitectura del Refactor

## 🎯 Objetivo

Crear un componente reutilizable `CustomerPicker` que unifique toda la lógica de selección/edición de clientes/proveedores usando React Hook Form como única fuente de verdad.

---

## 📐 Arquitectura General

```
CustomerPicker (Componente Principal)
├── CustomerSearchPanel (Búsqueda y selección)
├── CustomerSummary (Resumen del cliente seleccionado)
└── CustomerDetailsForm (Formulario de detalles)
    ├── AddressField (Selector de dirección)
    └── ActivityField (Selector de actividad)
```

---

## 🧱 Component Tree Diagram

```
┌─────────────────────────────────────────────────────────┐
│ CustomerPicker                                           │
│ - Usa: useCustomerPickerForm                            │
│ - Proporciona: FormProvider (RHF)                       │
│ - Props: documentType, defaultValues, onCustomerChange  │
└─────────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
┌────────────────────────┐      ┌──────────────────────────────┐
│ CustomerSearchPanel    │      │ CustomerDetailsForm           │
│ - Input de búsqueda    │      │ - Razón Social               │
│ - Dropdown de resultados│     │ - AddressField               │
│ - Botón "Nuevo"        │      │ - ActivityField              │
│ - Usa: useWatch (RHF)  │      │ - Usa: useFormContext (RHF)  │
└────────────────────────┘      └──────────────────────────────┘
         │                                     │
         │                                     ├──────────────┐
         │                                     │              │
         │                                     ▼              ▼
         │                          ┌──────────────┐ ┌──────────────┐
         │                          │ AddressField  │ │ActivityField │
         │                          │ - Selector   │ │ - Selector   │
         │                          │ - Manual     │ │ - Manual     │
         │                          │ - Usa: RHF   │ │ - Usa: RHF   │
         │                          └──────────────┘ └──────────────┘
         │
         ▼
┌────────────────────────┐
│ CustomerSummary        │
│ - Info del cliente     │
│ - Solo lectura         │
│ - Usa: useWatch (RHF)  │
└────────────────────────┘
```

---

## 📋 Modelo Canónico de Datos

### Interface: `CustomerFormValues`

```typescript
interface CustomerFormValues {
  // Identificación
  id: string | null
  taxId: string
  name: string
  businessName: string

  // Dirección
  addressMode: 'select' | 'manual'
  selectedAddressId: string
  address: string
  city: string
  district: string

  // Actividad
  activityMode: 'select' | 'manual'
  selectedActivityId: string
  activityName: string
  activityCode: string

  // Listas (read-only, pasadas via props)
  addresses: Address[]
  activities: Activity[]

  // UI flags (controlados por form)
  isLoadingCustomerDetails: boolean
  searchTerm: string
  showSearchDropdown: boolean
}
```

**Reglas:**
- ✅ Todos los valores vienen de React Hook Form
- ❌ NO hay estado local en componentes
- ❌ NO hay estado duplicado
- ✅ Las listas (`addresses`, `activities`) se pasan como props, NO se almacenan en el form

---

## 🧠 Strategy Pattern

### Interface: `CustomerPickerStrategy`

```typescript
interface CustomerPickerStrategy {
  // Identificación del tipo de documento
  readonly documentType: string
  
  // Reglas de negocio
  isBusinessNameEditable(): boolean
  requiresAddress(): boolean
  requiresActivity(): boolean
  allowManualAddress(): boolean
  allowManualActivity(): boolean
  
  // Transformaciones
  transformCustomerData(data: Partial<CustomerFormValues>): Partial<CustomerFormValues>
  
  // Textos UI
  getEntityTypeLabel(): string // "cliente" | "proveedor"
  getEntityTypeLabelPlural(): string // "clientes" | "proveedores"
  
  // Endpoints API
  getSearchEndpoint(entityId: string): string
  getDetailsEndpoint(rut: string): string
}
```

### Estrategias Concretas

1. **DefaultCustomerStrategy** (documentType: '33')
   - Razón social editable
   - Dirección requerida
   - Actividad requerida
   - Permite entrada manual

2. **PurchaseInvoiceStrategy** (documentType: '46')
   - Razón social NO editable
   - Dirección requerida
   - Actividad requerida
   - Permite entrada manual

3. **ExportCustomerStrategy** (documentType: '110')
   - Razón social editable
   - Dirección requerida
   - Actividad NO requerida
   - Permite entrada manual

4. **HonoraryInvoiceStrategy** (documentType: '39')
   - Razón social editable
   - Dirección NO requerida
   - Actividad NO requerida
   - Permite entrada manual

---

## 🪝 Hook: `useCustomerPickerForm`

```typescript
interface UseCustomerPickerFormOptions {
  documentType: string
  defaultValues: Partial<CustomerFormValues>
  addresses?: Address[]
  activities?: Activity[]
  onCustomerChange?: (values: CustomerFormValues) => void
}

interface UseCustomerPickerFormReturn {
  form: UseFormReturn<CustomerFormValues>
  strategy: CustomerPickerStrategy
  // Handlers
  handleCustomerSelect: (customer: CustomerListItem) => void
  handleNewCustomer: () => void
  handleSearch: (term: string) => void
  // Estado derivado (desde RHF)
  selectedCustomer: CustomerFormValues | null
  isLoading: boolean
}
```

**Responsabilidades:**
- ✅ Inicializar React Hook Form
- ✅ Seleccionar estrategia según `documentType`
- ✅ Exponer handlers para búsqueda/selección
- ✅ Sincronizar cambios del form con callback `onCustomerChange`
- ❌ NO contiene lógica de UI
- ❌ NO hace fetch de datos (eso lo hace el componente padre)

---

## 🧩 Componentes

### 1. `CustomerPicker` (Componente Principal)

```typescript
interface CustomerPickerProps {
  documentType: string
  defaultValues?: Partial<CustomerFormValues>
  addresses?: Address[]
  activities?: Activity[]
  customers?: CustomerListItem[]
  isLoadingCustomers?: boolean
  onCustomerChange?: (values: CustomerFormValues) => void
  onSearch?: (term: string) => void
  onLoadMore?: () => void
  onNewCustomer?: () => void
}
```

**Responsabilidades:**
- Proporcionar `FormProvider` (RHF)
- Orquestar sub-componentes
- NO posee datos
- NO decide reglas de negocio

---

### 2. `CustomerSearchPanel`

```typescript
interface CustomerSearchPanelProps {
  // Recibe form via FormProvider (useFormContext)
  customers: CustomerListItem[]
  isLoadingMore?: boolean
  onLoadMore?: () => void
  onNewCustomer?: () => void
}
```

**Responsabilidades:**
- Renderizar input de búsqueda
- Renderizar dropdown de resultados
- Leer/escribir `searchTerm` y `showSearchDropdown` desde RHF
- NO decide qué endpoint usar
- NO filtra clientes (eso lo hace el backend)

---

### 3. `CustomerDetailsForm`

```typescript
interface CustomerDetailsFormProps {
  // Recibe form via FormProvider (useFormContext)
  addresses: Address[]
  activities: Activity[]
  fieldErrors?: Record<string, boolean>
  onClearFieldError?: (field: string) => void
}
```

**Responsabilidades:**
- Renderizar campos de razón social, dirección, actividad
- Usar estrategia para habilitar/deshabilitar campos
- NO decide reglas de negocio
- NO valida (RHF lo hace)

---

### 4. `AddressField`

```typescript
interface AddressFieldProps {
  // Recibe form via FormProvider (useFormContext)
  addresses: Address[]
  onAddressSelect?: (address: Address) => void
}
```

**Responsabilidades:**
- Renderizar selector de dirección
- Manejar modo "manual" vs "select"
- Leer/escribir valores desde RHF
- NO decide si está habilitado (lo decide la estrategia)

---

### 5. `ActivityField`

```typescript
interface ActivityFieldProps {
  // Recibe form via FormProvider (useFormContext)
  activities: Activity[]
  onActivitySelect?: (activity: Activity) => void
}
```

**Responsabilidades:**
- Renderizar selector de actividad
- Manejar modo "manual" vs "select"
- Leer/escribir valores desde RHF
- NO decide si está habilitado (lo decide la estrategia)

---

## 🔄 Flujo de Datos

```
1. Componente Padre
   └─> Pasa: documentType, defaultValues, addresses, activities
   
2. CustomerPicker
   └─> useCustomerPickerForm(documentType, defaultValues)
       └─> Inicializa RHF
       └─> Selecciona Strategy
       └─> Expone form + strategy
   
3. CustomerPicker renderiza
   └─> FormProvider (form)
       ├─> CustomerSearchPanel
       │   └─> useFormContext() → lee/escribe searchTerm
       ├─> CustomerDetailsForm
       │   ├─> useFormContext() → lee/escribe businessName
       │   ├─> AddressField
       │   │   └─> useFormContext() → lee/escribe addressMode, selectedAddressId
       │   └─> ActivityField
       │       └─> useFormContext() → lee/escribe activityMode, selectedActivityId
       └─> useWatch() → detecta cambios → onCustomerChange(values)
```

---

## ✅ Principios de Diseño

1. **Single Source of Truth**: React Hook Form es la única fuente de verdad
2. **Separation of Concerns**: Cada componente tiene una responsabilidad única
3. **Strategy Pattern**: Comportamiento específico por tipo de documento
4. **Composition over Inheritance**: Componentes pequeños y reutilizables
5. **No Side Effects in Render**: Toda la lógica está en hooks
6. **Strong Typing**: TypeScript en todas partes

---

## 📦 Estructura de Archivos

```
src/components/customers/
├── CustomerPicker/
│   ├── index.tsx                    # Componente principal
│   ├── CustomerPicker.types.ts       # Interfaces
│   ├── CustomerSearchPanel.tsx      # Panel de búsqueda
│   ├── CustomerDetailsForm.tsx      # Formulario de detalles
│   ├── AddressField.tsx              # Campo de dirección
│   ├── ActivityField.tsx             # Campo de actividad
│   ├── useCustomerPickerForm.ts      # Hook principal
│   └── strategies/
│       ├── CustomerPickerStrategy.ts # Interface
│       ├── DefaultCustomerStrategy.ts
│       ├── PurchaseInvoiceStrategy.ts
│       ├── ExportCustomerStrategy.ts
│       └── HonoraryInvoiceStrategy.ts
```

---

## 🚀 Ejemplo de Uso

### En Scheduled Documents

```typescript
<CustomerPicker
  documentType={formData.dte_type_id}
  defaultValues={{
    id: formData.receiver_id,
    taxId: formData.receiver_tax_id,
    name: formData.receiver_name,
    businessName: formData.receiver_business_name,
    // ...
  }}
  addresses={formData.customer_addresses}
  activities={formData.customer_activities}
  customers={customers}
  onCustomerChange={(values) => {
    setFormData(prev => ({
      ...prev,
      receiver_id: values.id,
      receiver_tax_id: values.taxId,
      receiver_name: values.name,
      receiver_business_name: values.businessName,
      // ...
    }))
  }}
  onSearch={(term) => {
    // Llamar API de búsqueda
  }}
/>
```

### En Multi Invoice Wizard

```typescript
<CustomerPicker
  documentType={watch(`documents.${activeDocIndex}.dte_type_id`)}
  defaultValues={watch(`documents.${activeDocIndex}.customer`)}
  onCustomerChange={(values) => {
    setValue(`documents.${activeDocIndex}.customer`, values)
  }}
/>
```

---

## ⚠️ Restricciones

- ❌ NO usar `useState`, `useReducer`, o estado local
- ❌ NO hacer fetch de datos dentro de componentes
- ❌ NO usar condicionales `if (documentType === '46')` en JSX
- ❌ NO duplicar lógica entre componentes
- ✅ TODO debe venir de React Hook Form
- ✅ TODO comportamiento específico debe estar en Strategy

---

## 📝 Próximos Pasos

1. Crear interfaces y tipos
2. Implementar estrategias
3. Implementar hook `useCustomerPickerForm`
4. Implementar componentes
5. Migrar `ScheduledCustomerForm` a usar `CustomerPicker`
6. Migrar `CustomerInfo` a usar `CustomerPicker`
7. Migrar Multi Invoice Wizard a usar `CustomerPicker`
8. Eliminar componentes antiguos

