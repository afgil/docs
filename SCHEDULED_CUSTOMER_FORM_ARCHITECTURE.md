# Arquitectura del Formulario de Cliente en Documentos Programados

## 🏗️ Principios SOLID Aplicados

### 1. **Single Responsibility Principle (SRP)**
Cada hook/clase tiene una única responsabilidad:

- `useCustomerData`: Cargar datos del cliente desde el backend
- `useAddressSelection`: Lógica de selección de direcciones
- `useActivitySelection`: Lógica de selección de actividades
- `useFormSync`: Sincronización RHF ↔ formData
- `useScheduledCustomerForm`: Orquestador que compone los hooks anteriores

### 2. **Open/Closed Principle (OCP)**
El sistema está abierto a extensión pero cerrado a modificación:

- Nuevos tipos de documentos se agregan creando nuevas estrategias
- `DocumentStrategyFactory.registerStrategy()` permite registrar estrategias sin modificar código existente

### 3. **Liskov Substitution Principle (LSP)**
Todas las estrategias implementan `DocumentStrategy`:

```typescript
interface DocumentStrategy {
    isBusinessNameEditable(): boolean;
    getDefaultBusinessName(customerName: string, currentValue?: string): string;
    requiresAddress(): boolean;
    requiresActivity(): boolean;
    validateCustomerData(data: Partial<CustomerData>): { valid: boolean; errors: string[] };
    transformCustomerData(data: Partial<CustomerData>): Partial<CustomerData>;
}
```

Cualquier estrategia puede sustituir a otra sin romper el código.

### 4. **Interface Segregation Principle (ISP)**
Los hooks especializados exponen solo los métodos necesarios:

```typescript
// useAddressSelection solo expone métodos relacionados con direcciones
const { selectAddress, autoSelectFirstAddress, switchToManualMode, hasAddresses } = useAddressSelection();

// useActivitySelection solo expone métodos relacionados con actividades
const { selectActivity, autoSelectFirstActivity, switchToManualMode, hasActivities } = useActivitySelection();
```

### 5. **Dependency Inversion Principle (DIP)**
El código depende de abstracciones (interfaces), no de implementaciones concretas:

```typescript
// El hook depende de la interfaz DocumentStrategy, no de implementaciones específicas
const strategy = DocumentStrategyFactory.getStrategy(documentType);
```

---

## 📁 Estructura de Archivos

```
scheduled/
├── strategies/                           # Estrategias por tipo de documento (LSP)
│   ├── BaseDocumentStrategy.ts          # Interface base + implementación abstracta
│   ├── InvoiceStrategy.ts               # Factura normal (33)
│   ├── ExportInvoiceStrategy.ts         # Factura exportación (110)
│   ├── PurchaseInvoiceStrategy.ts       # Factura compra (46)
│   └── DocumentStrategyFactory.ts       # Factory para crear estrategias
│
├── hooks/                                # Hooks especializados (SRP)
│   ├── useCustomerData.ts               # Carga de datos del backend
│   ├── useAddressSelection.ts           # Selección de direcciones
│   ├── useActivitySelection.ts          # Selección de actividades
│   └── useFormSync.ts                   # Sincronización RHF ↔ formData
│
└── forms/customer/                       # Formulario de cliente
    ├── scheduledCustomerSchema.ts       # Schema y tipos
    ├── useScheduledCustomerForm.ts      # Hook orquestador
    └── ScheduledCustomerForm.tsx        # Componente UI
```

---

## 🔄 Flujo de Datos

### 1. Selección de Cliente Nuevo

```
Usuario click "Nuevo Cliente"
    ↓
Modal NewCustomerForm se abre
    ↓
Usuario busca RUT → API trae datos básicos
    ↓
Usuario click "Seleccionar Cliente"
    ↓
handleCustomerCreated() → handleCustomerSelect()
    ↓
setFormData() actualiza receiver_id, receiver_name, etc.
    ↓
useCustomerData.loadCustomerDetails(rut)
    ↓
API GET /master-entities/?rut=... → addresses + activities
    ↓
setFormData() actualiza customer_addresses, customer_activities
    ↓
useScheduledCustomerForm detecta cambio (useEffect)
    ↓
useAddressSelection.autoSelectFirstAddress()
useActivitySelection.autoSelectFirstActivity()
    ↓
form.setValue() actualiza todos los campos en RHF
    ↓
useFormSync sincroniza cambios a formData
    ↓
✅ Formulario muestra dirección y actividad seleccionadas
```

### 2. Cambio de Tipo de Documento

```
Usuario cambia dte_type_id
    ↓
DocumentStrategyFactory.getStrategy(newType)
    ↓
Nueva estrategia se aplica
    ↓
strategy.transformCustomerData() ajusta datos según reglas
    ↓
Ejemplo: Factura Exportación (110)
    → receiver_business_name se preserva (editable)
    → Dirección/actividad opcionales
    ↓
Ejemplo: Factura Compra (46)
    → receiver_business_name = receiver_name (no editable)
    → Dirección/actividad obligatorias
```

---

## 🎯 Ventajas de la Nueva Arquitectura

### ✅ **Mantenibilidad**
- Código modular y fácil de entender
- Cada archivo tiene una responsabilidad clara
- Fácil de testear (cada hook se puede testear aisladamente)

### ✅ **Extensibilidad**
- Agregar nuevo tipo de documento: crear nueva estrategia
- Agregar nueva validación: extender `BaseDocumentStrategyImpl`
- Agregar nuevo hook: composición sin modificar existentes

### ✅ **DRY (Don't Repeat Yourself)**
- Lógica de selección de direcciones/actividades reutilizable
- Sincronización RHF ↔ formData centralizada en `useFormSync`
- Validaciones centralizadas en estrategias

### ✅ **Single Source of Truth**
- React Hook Form es la única fuente de verdad
- `formData` es solo para persistencia/submit
- No hay estados duplicados ni sincronizaciones manuales

### ✅ **Type Safety**
- TypeScript en todos los archivos
- Interfaces bien definidas
- Autocomplete y detección de errores en tiempo de desarrollo

---

## 🧪 Cómo Testear

### Test Manual

1. **Factura Normal (33)**:
   - Seleccionar cliente → Dirección y actividad auto-seleccionadas
   - Razón social editable
   - Dirección y actividad obligatorias

2. **Factura Exportación (110)**:
   - Seleccionar cliente → Razón social editable (preserva personalización)
   - Dirección y actividad opcionales
   - Cambiar razón social → Se preserva el cambio

3. **Factura Compra (46)**:
   - Seleccionar proveedor → Razón social = nombre proveedor (no editable)
   - Dirección y actividad obligatorias
   - Cambiar razón social → Se fuerza al nombre del proveedor

### Test Unitario (Ejemplo)

```typescript
describe('DocumentStrategyFactory', () => {
    it('should return InvoiceStrategy for type 33', () => {
        const strategy = DocumentStrategyFactory.getStrategy('33');
        expect(strategy.documentType).toBe('33');
        expect(strategy.isBusinessNameEditable()).toBe(true);
    });

    it('should return ExportInvoiceStrategy for type 110', () => {
        const strategy = DocumentStrategyFactory.getStrategy('110');
        expect(strategy.documentType).toBe('110');
        expect(strategy.requiresAddress()).toBe(false);
    });
});
```

---

## 📝 Logs de Debug

Los logs siguen un patrón consistente:

- `🔄` = Procesando/Sincronizando
- `✅` = Éxito/Completado
- `⚠️` = Advertencia
- `❌` = Error

Ejemplo de logs esperados:

```
🔄 useCustomerData - Cargando datos para RUT: 76.798.398-0
✅ useCustomerData - Datos cargados: { rut: "76.798.398-0", addresses: 2, activities: 3 }
🔄 useScheduledCustomerForm - Sincronizando formulario: { receiver_id: "123", addresses: 2, activities: 3, strategy: "33" }
✅ Auto-seleccionando primera dirección
✅ Auto-seleccionando primera actividad
🔄 useFormSync - Sincronizando campo: receiver_business_name = "ASESORÍAS PATAGONIA SPA"
```

---

## 🚀 Próximos Pasos (Opcional)

1. **Validación con Zod**: Reemplazar validación manual por Zod schemas
2. **Tests Unitarios**: Agregar tests para cada estrategia y hook
3. **Tests E2E**: Cypress/Playwright para flujos completos
4. **Documentación de API**: Swagger/OpenAPI para endpoints
5. **Optimización**: Memoización de estrategias, lazy loading de hooks

---

## 📚 Referencias

- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [React Hook Form](https://react-hook-form.com/)
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)
- [Factory Pattern](https://refactoring.guru/design-patterns/factory-method)
- [Martin Fowler - Refactoring](https://martinfowler.com/books/refactoring.html)


