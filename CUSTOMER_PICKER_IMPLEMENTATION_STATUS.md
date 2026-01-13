# CustomerPicker - Estado de Implementación

## ✅ Completado

### 1. Interfaces y Tipos
- ✅ `CustomerPicker.types.ts` - Modelo canónico de datos
- ✅ `CustomerFormValues` - Interface principal
- ✅ `Address`, `Activity`, `CustomerListItem` - Tipos auxiliares

### 2. Strategy Pattern
- ✅ `CustomerPickerStrategy.ts` - Interface de estrategia
- ✅ `DefaultCustomerStrategy.ts` - Estrategia para facturas normales (33)
- ✅ `PurchaseInvoiceStrategy.ts` - Estrategia para facturas de compra (46, 1046)
- ✅ `CustomerPickerStrategyFactory.ts` - Factory para obtener estrategias

### 3. Hook Principal
- ✅ `useCustomerPickerForm.ts` - Hook que:
  - Inicializa React Hook Form
  - Selecciona estrategia según documentType
  - Expone handlers para búsqueda/selección
  - Sincroniza cambios con callback

### 4. Componentes
- ✅ `CustomerPicker/index.tsx` - Componente principal
- ✅ `CustomerSearchPanel.tsx` - Panel de búsqueda
- ✅ `CustomerDetailsForm.tsx` - Formulario de detalles
- ✅ `AddressField.tsx` - Campo de dirección
- ✅ `ActivityField.tsx` - Campo de actividad

### 5. Documentación
- ✅ `CUSTOMER_PICKER_ARCHITECTURE.md` - Arquitectura completa
- ✅ `CUSTOMER_PICKER_USAGE_EXAMPLES.md` - Ejemplos de uso

---

## ⚠️ Pendiente / Mejoras Necesarias

### 1. Estrategias Adicionales
- ⏳ `ExportCustomerStrategy` (documentType: '110')
- ⏳ `HonoraryInvoiceStrategy` (documentType: '39')
- ⏳ `PurchaseOrderStrategy` (documentType: '801')

### 2. Mejoras en Componentes

#### CustomerSearchPanel
- ⏳ Mejorar UI del dropdown (usar el mismo estilo que CustomerSearchNew)
- ⏳ Agregar soporte para paginación infinita
- ⏳ Agregar indicador de "no hay resultados"

#### AddressField y ActivityField
- ⏳ Mejorar UI para que coincida con AddressSelector y ActivitySelector actuales
- ⏳ Agregar soporte para dropdowns personalizados (no solo `<select>`)

#### CustomerDetailsForm
- ⏳ Agregar validación visual de campos requeridos
- ⏳ Mejorar mensajes de error

### 3. Integración con Código Existente

#### Migración de ScheduledCustomerForm
- ⏳ Reemplazar `ScheduledCustomerForm` con `CustomerPicker`
- ⏳ Mantener compatibilidad con tests existentes
- ⏳ Actualizar `ScheduledDocumentDetails` para usar `CustomerPicker`

#### Migración de CustomerInfo
- ⏳ Reemplazar `CustomerInfo` con `CustomerPicker`
- ⏳ Mantener compatibilidad con Multi Invoice Wizard
- ⏳ Actualizar endpoints de búsqueda

#### Migración de CustomerSearch
- ⏳ Reemplazar `CustomerSearch` y `CustomerSearchNew` con `CustomerPicker`
- ⏳ Actualizar todos los lugares que usan estos componentes

### 4. Testing
- ⏳ Tests unitarios para estrategias
- ⏳ Tests unitarios para hook `useCustomerPickerForm`
- ⏳ Tests de integración para `CustomerPicker`
- ⏳ Tests E2E para flujos completos

### 5. Optimizaciones
- ⏳ Memoización de componentes pesados
- ⏳ Debounce en búsqueda
- ⏳ Lazy loading de direcciones/actividades

---

## 🔄 Flujo de Datos Actual

```
1. Componente Padre
   ├─> Hace fetch de customers cuando se busca
   ├─> Hace fetch de addresses/activities cuando se selecciona customer
   └─> Pasa datos a CustomerPicker

2. CustomerPicker
   ├─> useCustomerPickerForm → inicializa RHF + strategy
   ├─> FormProvider → proporciona contexto RHF
   ├─> CustomerSearchPanel → búsqueda y selección
   └─> CustomerDetailsForm → formulario de detalles

3. Cuando cambian valores en RHF
   └─> onCustomerChange callback → actualiza estado del padre
```

---

## 📝 Notas de Implementación

### Decisiones de Diseño

1. **React Hook Form como única fuente de verdad**
   - Todos los valores vienen de RHF
   - No hay estado local en componentes
   - Los cambios se propagan vía callbacks

2. **Strategy Pattern para comportamiento específico**
   - NO usar condicionales `if (documentType === '46')` en componentes
   - TODO comportamiento específico está en estrategias

3. **Separación de responsabilidades**
   - CustomerPicker NO hace fetch de datos
   - CustomerPicker NO decide qué endpoint usar
   - El componente padre es responsable de datos y API

4. **Composición sobre herencia**
   - Componentes pequeños y reutilizables
   - Cada componente tiene una responsabilidad única

---

## 🚀 Próximos Pasos Recomendados

1. **Fase 1: Completar Estrategias**
   - Implementar estrategias faltantes
   - Agregar tests para estrategias

2. **Fase 2: Mejorar UI**
   - Mejorar estilos de componentes
   - Hacer que coincida con diseño actual

3. **Fase 3: Migración Gradual**
   - Empezar con ScheduledCustomerForm (menos crítico)
   - Luego CustomerInfo (más usado)
   - Finalmente eliminar componentes antiguos

4. **Fase 4: Testing y Optimización**
   - Tests completos
   - Optimizaciones de rendimiento
   - Documentación final

---

## ⚠️ Advertencias

1. **NO usar en producción todavía**
   - La implementación está incompleta
   - Faltan tests
   - Faltan estrategias

2. **Compatibilidad**
   - Los componentes antiguos siguen funcionando
   - La migración debe ser gradual
   - Mantener tests existentes durante la migración

3. **Breaking Changes**
   - La interface `CustomerFormValues` puede cambiar
   - Las props de `CustomerPicker` pueden cambiar
   - Documentar todos los cambios

