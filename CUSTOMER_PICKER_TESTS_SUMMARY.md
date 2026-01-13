# CustomerPicker - Resumen de Tests

## ✅ Tests Creados

### 1. CustomerPickerStrategy.test.tsx (38 tests)

**Ubicación:** `src/components/customers/CustomerPicker/__tests__/CustomerPickerStrategy.test.tsx`

**Cubre:**

- ✅ CustomerPickerStrategyFactory - Todas las estrategias
- ✅ DefaultCustomerStrategy - Comportamiento completo
- ✅ PurchaseInvoiceStrategy - Comportamiento completo
- ✅ ExportCustomerStrategy - Comportamiento completo
- ✅ HonoraryInvoiceStrategy - Comportamiento completo
- ✅ PurchaseOrderStrategy - Comportamiento completo

**Tests específicos:**

- Factory retorna estrategia correcta para cada documentType
- Factory retorna DefaultCustomerStrategy para tipos desconocidos
- Cada estrategia tiene el documentType correcto
- Cada estrategia implementa correctamente todos los métodos
- Validación de reglas de negocio (editable, requerido, etc.)
- Validación de endpoints correctos

### 2. CustomerPicker.test.tsx (3 tests)

**Ubicación:** `src/components/customers/CustomerPicker/__tests__/CustomerPicker.test.tsx`

**Cubre:**

- ✅ Renderizado básico del componente
- ✅ Props correctas pasadas a useCustomerPickerForm
- ✅ Renderizado de CustomerDetailsForm cuando hay cliente seleccionado

**Nota:** Los tests del componente son básicos porque el componente es principalmente un orquestador. La lógica compleja está en:

- `useCustomerPickerForm` (debería tener sus propios tests)
- `CustomerSearchPanel` (debería tener sus propios tests)
- `CustomerDetailsForm` (debería tener sus propios tests)

---

## 📊 Estado de Tests

### Tests de CustomerPicker

- ✅ **41 tests pasando**
  - 38 tests de estrategias
  - 3 tests del componente principal

### Tests Existentes (Scheduled)

- ✅ **76 tests pasando** (sin cambios)
  - Tests de ScheduledCustomerForm
  - Tests de customer selection
  - Tests de customer creation
  - Tests de manual input flow

---

## 🔄 Próximos Pasos para Tests

### Tests Pendientes

1. **useCustomerPickerForm.test.ts**
   - Inicialización de React Hook Form
   - Selección de estrategia
   - Handlers (handleCustomerSelect, handleNewCustomer, handleSearch)
   - Sincronización con onCustomerChange

2. **CustomerSearchPanel.test.tsx**
   - Renderizado del input de búsqueda
   - Renderizado del dropdown
   - Selección de cliente
   - Búsqueda y filtrado
   - Botón "Nuevo cliente"

3. **CustomerDetailsForm.test.tsx**
   - Renderizado de campos
   - Validación según estrategia
   - Campos requeridos/opcionales
   - Modo manual vs select

4. **AddressField.test.tsx**
   - Selector de dirección
   - Modo manual
   - Auto-selección

5. **ActivityField.test.tsx**
   - Selector de actividad
   - Modo manual
   - Auto-selección

### Tests de Integración

1. **CustomerPicker.integration.test.tsx**
   - Flujo completo de selección de cliente
   - Flujo completo de creación de cliente
   - Cambio entre diferentes tipos de documentos
   - Persistencia de datos

---

## 📝 Notas de Testing

### Mocks Necesarios

1. **react-hook-form**
   - `FormProvider`
   - `useFormContext`
   - `useController`
   - `useForm`

2. **useCustomerPickerForm**
   - Mock del hook completo
   - Mock de estrategia
   - Mock de form values

3. **API calls**
   - Mock de `api.get` para búsqueda
   - Mock de `api.get` para detalles

### Estructura de Tests

```
CustomerPicker/
├── __tests__/
│   ├── CustomerPicker.test.tsx          ✅ (3 tests)
│   ├── CustomerPickerStrategy.test.tsx  ✅ (38 tests)
│   ├── useCustomerPickerForm.test.ts    ⏳ (pendiente)
│   ├── CustomerSearchPanel.test.tsx     ⏳ (pendiente)
│   ├── CustomerDetailsForm.test.tsx     ⏳ (pendiente)
│   ├── AddressField.test.tsx            ⏳ (pendiente)
│   ├── ActivityField.test.tsx           ⏳ (pendiente)
│   └── CustomerPicker.integration.test.tsx ⏳ (pendiente)
```

---

## ✅ Comandos de Testing

```bash
# Ejecutar todos los tests de CustomerPicker
npm run test -- CustomerPicker --run

# Ejecutar tests de estrategias
npm run test -- CustomerPickerStrategy --run

# Ejecutar tests de scheduled (existentes)
npm run test -- scheduled --run

# Ejecutar todos los tests
npm run test --run
```

---

## 🎯 Cobertura Actual

- ✅ **Estrategias:** 100% (38/38 tests)
- ✅ **Componente Principal:** Básico (3/3 tests)
- ⏳ **Hooks:** 0% (pendiente)
- ⏳ **Sub-componentes:** 0% (pendiente)
- ⏳ **Integración:** 0% (pendiente)

**Total:** 41 tests pasando ✅
