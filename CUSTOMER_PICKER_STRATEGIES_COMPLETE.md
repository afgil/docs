# CustomerPicker - Estrategias Completadas

## ✅ Estrategias Implementadas

### 1. DefaultCustomerStrategy (documentType: '33')
**Uso:** Facturas normales

**Características:**
- ✅ Razón social editable
- ✅ Dirección requerida
- ✅ Actividad requerida
- ✅ Permite entrada manual

**Endpoint:** `/master-entities/{entityId}/customers/`

---

### 2. PurchaseInvoiceStrategy (documentType: '46', '1046')
**Uso:** Facturas de compra

**Características:**
- ❌ Razón social NO editable (se toma del proveedor)
- ✅ Dirección requerida
- ✅ Actividad requerida
- ✅ Permite entrada manual

**Endpoint:** `/master-entities/{entityId}/purchase-suppliers/`

---

### 3. ExportCustomerStrategy (documentType: '110', '111', '112')
**Uso:** Facturas de exportación

**Características:**
- ✅ Razón social SIEMPRE editable (puede ser diferente al nombre del cliente)
- ❌ Dirección opcional (cliente extranjero)
- ❌ Actividad opcional (cliente extranjero)
- ✅ Permite entrada manual

**Endpoint:** `/master-entities/{entityId}/customers/`

**Notas:**
- Preserva el `receiver_business_name` personalizado si existe
- Si no hay valor personalizado, usa el nombre del cliente

---

### 4. HonoraryInvoiceStrategy (documentType: '80', '90')
**Uso:** Boletas de honorarios

**Características:**
- ✅ Razón social editable
- ❌ Dirección opcional (pueden ser personas naturales)
- ❌ Actividad opcional (pueden ser personas naturales)
- ✅ Permite entrada manual

**Endpoint:** `/master-entities/{entityId}/customers/`

**Tipos:**
- `80`: Boleta de Honorarios (profesionales independientes)
- `90`: Boleta Honorarios Terceros (plataformas digitales)

---

### 5. PurchaseOrderStrategy (documentType: '801')
**Uso:** Órdenes de compra

**Características:**
- ❌ Razón social NO editable (se toma del proveedor desde documentos recibidos)
- ✅ Dirección requerida
- ✅ Actividad requerida
- ✅ Permite entrada manual

**Endpoint:** `/master-entities/{entityId}/suppliers-from-received/`

**Nota:** Usa endpoint diferente porque los proveedores vienen de documentos recibidos, no de la lista de proveedores de compra.

---

## 📊 Tabla Comparativa

| Estrategia | DocumentType | Razón Social Editable | Dirección Requerida | Actividad Requerida | Endpoint |
|------------|--------------|----------------------|---------------------|---------------------|----------|
| DefaultCustomerStrategy | 33 | ✅ | ✅ | ✅ | customers |
| PurchaseInvoiceStrategy | 46, 1046 | ❌ | ✅ | ✅ | purchase-suppliers |
| ExportCustomerStrategy | 110, 111, 112 | ✅ | ❌ | ❌ | customers |
| HonoraryInvoiceStrategy | 80, 90 | ✅ | ❌ | ❌ | customers |
| PurchaseOrderStrategy | 801 | ❌ | ✅ | ✅ | suppliers-from-received |

---

## 🔄 Uso en CustomerPickerStrategyFactory

```typescript
// Todas las estrategias están registradas automáticamente
const strategy = CustomerPickerStrategyFactory.getStrategy('110');
// Retorna: ExportCustomerStrategy

const strategy = CustomerPickerStrategyFactory.getStrategy('80');
// Retorna: HonoraryInvoiceStrategy

const strategy = CustomerPickerStrategyFactory.getStrategy('801');
// Retorna: PurchaseOrderStrategy
```

---

## ✅ Estado de Implementación

- ✅ DefaultCustomerStrategy
- ✅ PurchaseInvoiceStrategy
- ✅ ExportCustomerStrategy
- ✅ HonoraryInvoiceStrategy
- ✅ PurchaseOrderStrategy

**Todas las estrategias principales están completadas.**

---

## 📝 Notas de Implementación

### ExportCustomerStrategy
- Preserva valores personalizados de `businessName`
- Útil para clientes extranjeros donde la razón social puede ser diferente

### HonoraryInvoiceStrategy
- Permite flexibilidad para personas naturales
- No requiere dirección ni actividad (común en honorarios)

### PurchaseOrderStrategy
- Usa endpoint especial `suppliers-from-received`
- Similar a PurchaseInvoiceStrategy pero con fuente de datos diferente

