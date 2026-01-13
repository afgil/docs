# Evaluación y Validación del CustomerPicker - Frontend

## 1. Alcance Funcional Validado

### 1.1. Listado y Selección

**✅ IMPLEMENTADO:**

- ✅ Carga todos los clientes existentes del usuario mediante endpoint paginado
- ✅ Búsqueda por RUT o nombre (normalización de RUT incluida)
- ✅ Selección de cliente desde lista o buscador
- ✅ Carga inicial automática cuando se abre el dropdown
- ✅ Paginación infinita (load more on scroll)
- ✅ Indicadores de carga durante búsqueda

**Archivos relevantes:**

- `CustomerSearchPanel.tsx`: Panel de búsqueda con dropdown
- `index.tsx`: Hook `useCustomerSearch` para búsqueda paginada
- `strategies/CustomerPickerStrategy.ts`: Estrategias por tipo de documento

**Endpoint usado:**

- `/api/master-entities/{entityId}/customers-configuration/` (según estrategia)

### 1.2. Visualización del Cliente Seleccionado

**✅ IMPLEMENTADO:**

- ✅ Razón social: Campo editable según estrategia (`businessName`)
- ✅ Dirección activa: Muestra dirección seleccionada o permite modo manual
- ✅ Actividad económica activa: Muestra actividad seleccionada o permite modo manual
- ✅ RUT: Solo lectura, visual

**⚠️ PARCIALMENTE IMPLEMENTADO:**

- ⚠️ **Dirección por defecto**: El backend soporta `is_default` en direcciones, pero el CustomerPicker:
  - NO muestra visualmente cuál es la dirección por defecto
  - NO permite cambiar la dirección por defecto
  - Solo auto-selecciona la primera dirección disponible, sin considerar `is_default`
- ⚠️ **Actividad económica por defecto**: Similar a direcciones:
  - NO muestra cuál es la actividad por defecto
  - NO permite cambiar la actividad por defecto
  - Solo auto-selecciona la primera actividad disponible

**Archivos relevantes:**

- `CustomerDetailsForm.tsx`: Formulario de visualización
- `AddressField.tsx`: Campo de selección de dirección
- `ActivityField.tsx`: Campo de selección de actividad

### 1.3. Creación de Nuevos Clientes

**✅ IMPLEMENTADO:**

- ✅ Crear un cliente nuevo (RUT + Razón Social)
- ✅ Validación de RUT con formato chileno
- ✅ Detección automática de cliente existente por RUT
- ✅ Selección de cliente existente si se encuentra

**❌ NO IMPLEMENTADO:**

- ❌ **Asociar direcciones al crear**: El modal solo permite crear cliente básico
  - NO permite agregar direcciones en el momento de creación
  - El backend puede crear direcciones por defecto, pero no se muestran opciones en el modal
- ❌ **Asociar actividades económicas al crear**: Similar a direcciones
  - NO permite agregar actividades en el momento de creación
- ❌ **Definir dirección por defecto**: No existe opción en el flujo de creación
- ❌ **Definir actividad económica por defecto**: No existe opción en el flujo de creación

**Archivos relevantes:**

- `CreateCustomerModal.tsx`: Modal de creación (solo RUT y nombre)

**Endpoint usado:**

- `POST /api/master-entities/` (creación básica)

### 1.4. Integración

**✅ IMPLEMENTADO:**

- ✅ Al seleccionar cliente, direcciones y actividades quedan disponibles en el form
- ✅ Auto-selección de primera dirección/actividad si hay opciones
- ✅ Sincronización con React Hook Form (fuente de verdad)
- ✅ Contexto global (`CustomerContext`) para estado del cliente
- ✅ Modo manual para dirección/actividad si no hay opciones disponibles
- ✅ Los datos del cliente seleccionado están disponibles para formularios de facturación

**Archivos relevantes:**

- `useCustomerFormSync.ts`: Sincronización RHF ↔ Contexto
- `CustomerContext.tsx`: Estado global del cliente
- `useCustomerPickerForm.ts`: Hook principal del formulario

---

## 2. Validación contra Código Existente

### 2.1. Funcionalidades Completamente Implementadas

| Funcionalidad | Estado | Archivos |
|--------------|--------|----------|
| Listado paginado de clientes | ✅ | `index.tsx:56-110` |
| Búsqueda por RUT/nombre | ✅ | `CustomerSearchPanel.tsx:84-114` |
| Selección desde lista | ✅ | `CustomerContext.tsx:113-224` |
| Visualización de razón social | ✅ | `CustomerDetailsForm.tsx:88-122` |
| Visualización de dirección activa | ✅ | `AddressField.tsx:19-252` |
| Visualización de actividad activa | ✅ | `ActivityField.tsx:19-216` |
| Creación básica de cliente | ✅ | `CreateCustomerModal.tsx:104-188` |
| Detección de cliente existente | ✅ | `CreateCustomerModal.tsx:76-102` |
| Auto-selección primera dirección/actividad | ✅ | `AddressField.tsx:64-79`, `ActivityField.tsx:59-72` |
| Modo manual para dirección/actividad | ✅ | `AddressField.tsx:114-118`, `ActivityField.tsx:97-101` |
| Sincronización con RHF | ✅ | `useCustomerFormSync.ts` |
| Contexto global | ✅ | `CustomerContext.tsx` |

### 2.2. Funcionalidades Parcialmente Implementadas

| Funcionalidad | Estado | Gap Identificado | Corrección Mínima Necesaria |
|--------------|--------|------------------|----------------------------|
| Dirección por defecto | ⚠️ | No se muestra visualmente ni permite cambiar | 1. Leer `is_default` de direcciones del backend<br>2. Mostrar indicador visual de dirección por defecto<br>3. Auto-seleccionar dirección con `is_default: true` en lugar de la primera<br>4. Agregar opción para cambiar dirección por defecto (si el backend lo soporta) |
| Actividad por defecto | ⚠️ | Similar a dirección por defecto | 1. Leer `is_default` de actividades del backend<br>2. Mostrar indicador visual<br>3. Auto-seleccionar actividad con `is_default: true`<br>4. Agregar opción para cambiar actividad por defecto |

### 2.3. Funcionalidades No Implementadas

| Funcionalidad | Impacto | Prioridad | Corrección Mínima Necesaria |
|--------------|---------|-----------|----------------------------|
| Agregar direcciones al crear cliente | Medio | Media | Extender `CreateCustomerModal` para permitir agregar direcciones (similar a `ClientSettingsForm`) |
| Agregar actividades al crear cliente | Medio | Media | Extender `CreateCustomerModal` para permitir agregar actividades |
| Definir dirección/actividad por defecto al crear | Bajo | Baja | Agregar checkboxes en modal de creación para marcar como default |

---

## 3. Tests

### 3.1. Revisión de Tests Existentes

**Tests encontrados:**

1. `CustomerPicker.integration.test.tsx`: Tests básicos de integración (4 tests)
2. `CustomerContext.test.tsx`: Tests del contexto (4 tests)
3. `CreateCustomerFlow.test.tsx`: Tests de creación (2 tests)
4. `CustomerPicker.loader.test.tsx`: Tests de loaders
5. `CustomerPicker.loading.test.tsx`: Tests de estados de carga
6. `CustomerPicker.selection.test.tsx`: Tests de selección
7. `CustomerPicker.blur.test.tsx`: Tests de blur events
8. `CustomerPicker.context.e2e.test.tsx`: Tests E2E del contexto
9. `CustomerContext.integration.test.tsx`: Tests de integración del contexto
10. `useCustomerSelection.test.ts`: Tests del hook de selección

**Cobertura actual:**

- ✅ Renderizado básico
- ✅ Búsqueda básica
- ✅ Selección de cliente
- ✅ Creación básica de cliente
- ✅ Contexto y estado
- ⚠️ **Falta**: Tests de direcciones múltiples
- ⚠️ **Falta**: Tests de actividades múltiples
- ⚠️ **Falta**: Tests de dirección/actividad por defecto
- ⚠️ **Falta**: Tests de cambio de dirección/actividad por defecto
- ⚠️ **Falta**: Tests de clientes sin direcciones/actividades
- ⚠️ **Falta**: Tests de integración completa (crear → usar en factura)

### 3.2. Tests Nuevos Propuestos (20 Tests)

#### **Grupo 1: Listado y Selección (3 tests)**

**Test 1: Listado inicial carga todos los clientes**

```typescript
// test: listado_inicial_carga_clientes.test.tsx
/**
 * Valida que al abrir el CustomerPicker, se carguen automáticamente 
 * todos los clientes del usuario (sin término de búsqueda)
 * 
 * Setup:
 * - Mock API con 10 clientes en respuesta paginada
 * - EntityContext con entityId válido
 * 
 * Resultado esperado:
 * - Se hace llamada GET a endpoint de clientes con page=1, limit=50
 * - Se muestran los 10 clientes en el dropdown
 * - El dropdown está cerrado inicialmente
 */
```

**Test 2: Búsqueda filtra clientes por RUT o nombre**

```typescript
// test: busqueda_filtra_por_rut_o_nombre.test.tsx
/**
 * Valida que la búsqueda filtre correctamente por RUT o nombre
 * 
 * Setup:
 * - Mock API que devuelve clientes filtrados según search param
 * - EntityContext con entityId válido
 * 
 * Resultado esperado:
 * - Al buscar "76.123.456-7", se hace GET con search=76.123.456-7
 * - Al buscar "Empresa Test", se hace GET con search=Empresa Test
 * - Se muestran solo los clientes que coinciden
 * - Se normaliza el RUT correctamente (quita puntos/guiones)
 */
```

**Test 3: Selección de cliente carga detalles completos**

```typescript
// test: seleccion_carga_detalles_completos.test.tsx
/**
 * Valida que al seleccionar un cliente, se carguen sus detalles completos
 * (direcciones, actividades, contacto)
 * 
 * Setup:
 * - Cliente con 3 direcciones y 2 actividades
 * - Mock API para GET /master-entities/{id}/
 * 
 * Resultado esperado:
 * - Se hace llamada GET a /master-entities/{customerId}/
 * - Se muestran las 3 direcciones en AddressField
 * - Se muestran las 2 actividades en ActivityField
 * - Se auto-selecciona la primera dirección y actividad
 * - El formulario muestra razón social, RUT, contacto
 */
```

#### **Grupo 2: Cliente sin Direcciones/Actividades (3 tests)**

**Test 4: Cliente sin direcciones muestra modo manual**

```typescript
// test: cliente_sin_direcciones_modo_manual.test.tsx
/**
 * Valida que un cliente sin direcciones permite ingreso manual
 * 
 * Setup:
 * - Cliente seleccionado con addresses: []
 * - Strategy que requiere dirección
 * 
 * Resultado esperado:
 * - AddressField muestra "Ingresar manualmente" automáticamente
 * - Se muestran inputs para dirección, comuna, ciudad
 * - addressMode está en 'manual'
 * - No hay dropdown de direcciones
 */
```

**Test 5: Cliente sin actividades muestra modo manual**

```typescript
// test: cliente_sin_actividades_modo_manual.test.tsx
/**
 * Valida que un cliente sin actividades permite ingreso manual
 * 
 * Setup:
 * - Cliente seleccionado con activities: []
 * - Strategy que requiere actividad
 * 
 * Resultado esperado:
 * - ActivityField muestra "Ingresar manualmente" automáticamente
 * - Se muestran inputs para nombre y código de actividad
 * - activityMode está en 'manual'
 * - No hay dropdown de actividades
 */
```

**Test 6: Cliente sin direcciones ni actividades permite ambos modos manuales**

```typescript
// test: cliente_sin_direcciones_ni_actividades.test.tsx
/**
 * Valida comportamiento cuando cliente no tiene direcciones NI actividades
 * 
 * Setup:
 * - Cliente con addresses: [] y activities: []
 * - Strategy que requiere ambos
 * 
 * Resultado esperado:
 * - Ambos campos están en modo manual
 * - Usuario puede ingresar dirección y actividad manualmente
 * - No se muestra ningún dropdown
 * - El formulario es válido con valores manuales
 */
```

#### **Grupo 3: Múltiples Direcciones (3 tests)**

**Test 7: Cliente con múltiples direcciones permite selección**

```typescript
// test: cliente_multiples_direcciones_seleccion.test.tsx
/**
 * Valida que un cliente con múltiples direcciones permite seleccionar cualquiera
 * 
 * Setup:
 * - Cliente con 3 direcciones diferentes
 * - Primera dirección auto-seleccionada
 * 
 * Resultado esperado:
 * - Dropdown muestra las 3 direcciones
 * - Primera dirección está seleccionada por defecto
 * - Al seleccionar otra dirección, se actualiza el form
 * - selectedAddressId cambia correctamente
 * - address, city, district se actualizan correctamente
 */
```

**Test 8: Cambio de dirección actualiza formulario correctamente**

```typescript
// test: cambio_direccion_actualiza_formulario.test.tsx
/**
 * Valida que cambiar de dirección actualiza todos los campos relacionados
 * 
 * Setup:
 * - Cliente con 3 direcciones
 * - Dirección 1 seleccionada inicialmente
 * 
 * Resultado esperado:
 * - Al seleccionar dirección 2, selectedAddressId = dirección 2.id
 * - address = dirección 2.address
 * - district = dirección 2.district.name
 * - city = dirección 2.district.city.name
 * - addressMode = 'select'
 */
```

**Test 9: Dirección por defecto se auto-selecciona correctamente**

```typescript
// test: direccion_por_defecto_auto_seleccion.test.tsx
/**
 * Valida que si hay una dirección marcada como is_default, se auto-selecciona
 * en lugar de la primera
 * 
 * Setup:
 * - Cliente con 3 direcciones
 * - Dirección 2 tiene is_default: true
 * 
 * Resultado esperado:
 * - Al cargar cliente, se selecciona dirección 2 (no la primera)
 * - selectedAddressId = dirección 2.id
 * - Si no hay is_default, se selecciona la primera (comportamiento actual)
 */
```

#### **Grupo 4: Múltiples Actividades (3 tests)**

**Test 10: Cliente con múltiples actividades permite selección**

```typescript
// test: cliente_multiples_actividades_seleccion.test.tsx
/**
 * Valida que un cliente con múltiples actividades permite seleccionar cualquiera
 * 
 * Setup:
 * - Cliente con 4 actividades económicas
 * - Primera actividad auto-seleccionada
 * 
 * Resultado esperado:
 * - Dropdown muestra las 4 actividades
 * - Primera actividad está seleccionada por defecto
 * - Al seleccionar otra actividad, se actualiza el form
 * - selectedActivityId, activityName, activityCode se actualizan correctamente
 */
```

**Test 11: Cambio de actividad actualiza formulario correctamente**

```typescript
// test: cambio_actividad_actualiza_formulario.test.tsx
/**
 * Valida que cambiar de actividad actualiza todos los campos relacionados
 * 
 * Setup:
 * - Cliente con 4 actividades
 * - Actividad 1 seleccionada inicialmente
 * 
 * Resultado esperado:
 * - Al seleccionar actividad 3, selectedActivityId = actividad 3.id
 * - activityName = actividad 3.name
 * - activityCode = actividad 3.code
 * - activityMode = 'select'
 */
```

**Test 12: Actividad por defecto se auto-selecciona correctamente**

```typescript
// test: actividad_por_defecto_auto_seleccion.test.tsx
/**
 * Valida que si hay una actividad marcada como is_default, se auto-selecciona
 * 
 * Setup:
 * - Cliente con 4 actividades
 * - Actividad 3 tiene is_default: true
 * 
 * Resultado esperado:
 * - Al cargar cliente, se selecciona actividad 3 (no la primera)
 * - selectedActivityId = actividad 3.id
 * - Si no hay is_default, se selecciona la primera (comportamiento actual)
 */
```

#### **Grupo 5: Creación de Clientes (3 tests)**

**Test 13: Crear cliente nuevo sin direcciones/actividades**

```typescript
// test: crear_cliente_sin_direcciones_actividades.test.tsx
/**
 * Valida creación de cliente básico sin direcciones ni actividades
 * 
 * Setup:
 * - Modal de creación abierto
 * - RUT y nombre ingresados
 * - Mock API para POST /master-entities/
 * 
 * Resultado esperado:
 * - POST con tax_id y name
 * - Cliente creado se selecciona automáticamente
 * - addresses y activities están vacíos
 * - addressMode y activityMode están en 'manual'
 * - El modal se cierra
 */
```

**Test 14: Crear cliente detecta si ya existe**

```typescript
// test: crear_cliente_detecta_existente.test.tsx
/**
 * Valida que al ingresar RUT, se detecta si el cliente ya existe
 * 
 * Setup:
 * - Modal de creación abierto
 * - RUT ingresado que ya existe en sistema
 * - Mock API para GET /master-entities/?rut=...
 * 
 * Resultado esperado:
 * - Al hacer blur del campo RUT, se hace GET con el RUT
 * - Si existe, se muestra mensaje "Cliente ya existe"
 * - Se muestra botón "Seleccionar Cliente Existente"
 * - Al hacer click, se selecciona el cliente existente
 */
```

**Test 15: Cliente recién creado tiene datos disponibles para facturación**

```typescript
// test: cliente_creado_disponible_facturacion.test.tsx
/**
 * Valida que un cliente recién creado tiene todos sus datos disponibles
 * para ser usado en formularios de facturación
 * 
 * Setup:
 * - Cliente creado con POST /master-entities/
 * - Respuesta incluye id, tax_id, name, addresses: [], activities: []
 * 
 * Resultado esperado:
 * - customerState.selectedCustomerId tiene el ID del cliente
 * - Form tiene todos los campos del cliente (taxId, name, businessName)
 * - addresses y activities están disponibles (aunque vacíos)
 * - El cliente puede usarse en formularios de facturación
 * - Los datos están sincronizados entre contexto y RHF
 */
```

#### **Grupo 6: Integración y Casos Límite (5 tests)**

**Test 16: Seleccionar cliente existente vs cliente recién creado**

```typescript
// test: seleccion_existente_vs_creado.test.tsx
/**
 * Valida diferencias de comportamiento entre seleccionar cliente existente
 * y cliente recién creado
 * 
 * Setup:
 * - Cliente existente con direcciones/actividades
 * - Cliente recién creado sin direcciones/actividades
 * 
 * Resultado esperado:
 * - Cliente existente: carga direcciones/actividades desde API
 * - Cliente creado: usa datos del POST (pueden estar vacíos)
 * - Ambos actualizan el contexto correctamente
 * - Ambos sincronizan con RHF correctamente
 * - isLoadingCustomerDetails es false para cliente creado (no hay carga adicional)
 */
```

**Test 17: Cambio entre clientes preserva selecciones previas cuando es posible**

```typescript
// test: cambio_clientes_preserva_selecciones.test.tsx
/**
 * Valida que al cambiar de cliente, se preservan selecciones si los IDs coinciden
 * 
 * Setup:
 * - Cliente A seleccionado con dirección ID 2 y actividad ID 3
 * - Cambiar a Cliente B que también tiene dirección ID 2 y actividad ID 3
 * 
 * Resultado esperado:
 * - Si Cliente B tiene dirección ID 2, se preserva la selección
 * - Si Cliente B no tiene dirección ID 2, se selecciona la primera/disponible
 * - Similar para actividades
 */
```

**Test 18: Cliente con dirección/actividad por defecto cambia correctamente**

```typescript
// test: cambio_direccion_actividad_defecto.test.tsx
/**
 * Valida cambio de dirección/actividad por defecto
 * 
 * Setup:
 * - Cliente con dirección 2 como default (is_default: true)
 * - Cliente con actividad 3 como default (is_default: true)
 * - Usuario cambia a dirección 1 y actividad 1
 * 
 * Resultado esperado:
 * - Al cambiar manualmente, se selecciona dirección 1 y actividad 1
 * - selectedAddressId y selectedActivityId se actualizan
 * - El cambio NO afecta is_default en el backend (eso se maneja en configuración)
 * - Los valores en el form son correctos para facturación
 */
```

**Test 19: Búsqueda con resultados vacíos muestra mensaje apropiado**

```typescript
// test: busqueda_resultados_vacios.test.tsx
/**
 * Valida comportamiento cuando la búsqueda no devuelve resultados
 * 
 * Setup:
 * - Búsqueda de "ClienteInexistente123"
 * - Mock API devuelve results: []
 * 
 * Resultado esperado:
 * - Se muestra mensaje "No se encontraron clientes que coincidan con la búsqueda"
 * - Opción "Crear nuevo cliente" sigue disponible
 * - El dropdown está abierto
 * - No hay errores en consola
 */
```

**Test 20: Integración completa: crear → seleccionar → usar en factura**

```typescript
// test: integracion_completa_crear_usar_factura.test.tsx
/**
 * Test E2E completo del flujo: crear cliente → seleccionar → usar en factura
 * 
 * Setup:
 * - Usuario crea cliente nuevo
 * - Usuario ingresa dirección y actividad manualmente
 * - Usuario selecciona el cliente en formulario de factura
 * 
 * Resultado esperado:
 * - Cliente se crea correctamente
 * - Dirección y actividad manual se guardan en el form
 * - Al usar en factura, todos los datos están disponibles:
 *   - taxId, name, businessName, contact
 *   - address, district, city
 *   - activityName, activityCode
 * - Los datos están sincronizados entre contexto y formulario de factura
 * - No hay datos perdidos en el proceso
 */
```

---

## 4. Resumen y Priorización

### 4.1. Gaps Funcionales Críticos

1. **Dirección/Actividad por defecto no se respeta** (Prioridad: Media)
   - Impacto: El sistema puede seleccionar la dirección/actividad incorrecta
   - Corrección: Leer `is_default` del backend y auto-seleccionar correctamente

2. **No se puede agregar direcciones/actividades al crear cliente** (Prioridad: Media)
   - Impacto: Usuario debe crear cliente y luego editar para agregar direcciones
   - Corrección: Extender `CreateCustomerModal` con secciones de direcciones/actividades

### 4.2. Tests Prioritarios para Implementar

**Alta Prioridad (Cubrir primero):**

- Test 3: Selección carga detalles completos
- Test 9: Dirección por defecto auto-selección
- Test 12: Actividad por defecto auto-selección
- Test 16: Cliente existente vs creado
- Test 20: Integración completa E2E

**Media Prioridad:**

- Test 4-6: Cliente sin direcciones/actividades
- Test 7-8: Múltiples direcciones
- Test 10-11: Múltiples actividades
- Test 13-15: Creación de clientes

**Baja Prioridad (Nice to have):**

- Test 1-2: Listado y búsqueda (ya cubiertos parcialmente)
- Test 17-19: Casos límite

### 4.3. Recomendaciones

1. **Implementar soporte para dirección/actividad por defecto antes de agregar más tests**
2. **Crear tests primero (TDD) para las funcionalidades faltantes**
3. **Priorizar tests de integración E2E que validen el flujo completo**
4. **Agregar tests de regresión cuando se implementen nuevas funcionalidades**

---

## 5. Estructura de Tests Propuesta

```
src/components/customers/CustomerPicker/__tests__/
├── unit/
│   ├── CustomerContext.test.tsx (existente)
│   ├── AddressField.test.tsx (nuevo)
│   ├── ActivityField.test.tsx (nuevo)
│   └── CreateCustomerModal.test.tsx (extender existente)
├── integration/
│   ├── CustomerPicker.integration.test.tsx (existente - extender)
│   ├── listado_inicial_carga_clientes.test.tsx (nuevo)
│   ├── busqueda_filtra_por_rut_o_nombre.test.tsx (nuevo)
│   ├── seleccion_carga_detalles_completos.test.tsx (nuevo)
│   ├── cliente_sin_direcciones_modo_manual.test.tsx (nuevo)
│   ├── cliente_sin_actividades_modo_manual.test.tsx (nuevo)
│   ├── cliente_sin_direcciones_ni_actividades.test.tsx (nuevo)
│   ├── cliente_multiples_direcciones_seleccion.test.tsx (nuevo)
│   ├── cambio_direccion_actualiza_formulario.test.tsx (nuevo)
│   ├── direccion_por_defecto_auto_seleccion.test.tsx (nuevo)
│   ├── cliente_multiples_actividades_seleccion.test.tsx (nuevo)
│   ├── cambio_actividad_actualiza_formulario.test.tsx (nuevo)
│   ├── actividad_por_defecto_auto_seleccion.test.tsx (nuevo)
│   ├── crear_cliente_sin_direcciones_actividades.test.tsx (nuevo)
│   ├── crear_cliente_detecta_existente.test.tsx (nuevo)
│   ├── cliente_creado_disponible_facturacion.test.tsx (nuevo)
│   ├── seleccion_existente_vs_creado.test.tsx (nuevo)
│   ├── cambio_clientes_preserva_selecciones.test.tsx (nuevo)
│   ├── cambio_direccion_actividad_defecto.test.tsx (nuevo)
│   ├── busqueda_resultados_vacios.test.tsx (nuevo)
│   └── integracion_completa_crear_usar_factura.test.tsx (nuevo)
└── e2e/
    └── CustomerPicker.e2e.test.tsx (nuevo - flujo completo)
```

---

## 6. Checklist de Validación

### 6.1. Funcionalidades Core

- [x] Listado de clientes
- [x] Búsqueda por RUT/nombre
- [x] Selección de cliente
- [x] Visualización de datos del cliente
- [x] Creación básica de cliente
- [ ] Dirección por defecto (parcial)
- [ ] Actividad por defecto (parcial)
- [ ] Agregar direcciones al crear
- [ ] Agregar actividades al crear

### 6.2. Tests

- [x] Tests básicos de integración
- [x] Tests de contexto
- [x] Tests de creación básica
- [ ] Tests de múltiples direcciones
- [ ] Tests de múltiples actividades
- [ ] Tests de dirección/actividad por defecto
- [ ] Tests de cliente sin direcciones/actividades
- [ ] Tests de integración completa E2E

### 6.3. Integración

- [x] Sincronización RHF ↔ Contexto
- [x] Datos disponibles para facturación
- [x] Auto-selección de primera opción
- [ ] Respeto de opciones por defecto
- [ ] Gestión completa de direcciones/actividades al crear

---

**Documento generado:** 2024
**Última actualización:** 2024
