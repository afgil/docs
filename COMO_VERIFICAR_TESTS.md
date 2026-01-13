# 🧪 Cómo Verificar que los Tests Funcionan

## 🚀 Verificación Rápida (2 minutos)

### 1. Ejecutar tests del módulo scheduled

```bash
cd /Users/antoniogil/dev/tupana/pana-frontend
npm run test -- src/components/platform/invoice/scheduled/ --run
```

**Resultado esperado:**
```
✓ Test Files  8 passed (8)
✓ Tests      70 passed (70)
  Duration   ~2 segundos
```

---

## 🔍 Verificación Detallada (5 minutos)

### 1. Tests Unitarios de Estrategias

```bash
npm run test -- src/components/platform/invoice/scheduled/strategies/__tests__/ --run
```

**Debe mostrar:**
```
✓ DocumentStrategyFactory.test.ts    6 tests ✅
✓ InvoiceStrategy.test.ts           13 tests ✅
✓ ExportInvoiceStrategy.test.ts     12 tests ✅
✓ PurchaseInvoiceStrategy.test.ts   10 tests ✅
```

**Qué verifica:**
- ✅ Factory devuelve estrategia correcta por tipo
- ✅ Factura (33): Razón social editable, dirección/actividad obligatorias
- ✅ Exportación (110): Razón social editable + preserva custom, dirección/actividad opcionales
- ✅ Compra (46): Razón social no editable, dirección/actividad obligatorias

---

### 2. Tests de Hooks Especializados

```bash
npm run test -- src/components/platform/invoice/scheduled/hooks/__tests__/ --run
```

**Debe mostrar:**
```
✓ useAddressSelection.test.ts        6 tests ✅
✓ useActivitySelection.test.ts       6 tests ✅
```

**Qué verifica:**
- ✅ Selección manual de dirección/actividad
- ✅ Auto-selección de primera opción
- ✅ Cambio entre modo select/manual
- ✅ Manejo de listas vacías
- ✅ Manejo de IDs inválidos

---

### 3. Tests E2E de Cliente Nuevo

```bash
npm run test -- src/components/platform/invoice/scheduled/__tests__/customer-creation-flow.e2e.test.tsx --run
```

**Debe mostrar:**
```
✓ customer-creation-flow.e2e.test.tsx  11 tests ✅

Casos testeados:
  ✓ Cliente nuevo se carga con direcciones y actividades
  ✓ Primera dirección se auto-selecciona
  ✓ Primera actividad se auto-selecciona
  ✓ Razón social según tipo de documento (3 tests)
  ✓ Datos persisten correctamente
  ✓ Caché funciona (2 tests)
  ✓ Manejo de errores (2 tests)
```

**Qué verifica:**
- ✅ API trae datos completos (addresses + activities)
- ✅ Auto-selección funciona correctamente
- ✅ Estrategias se aplican según tipo de documento
- ✅ Datos persisten en estructura correcta
- ✅ Caché evita requests duplicados
- ✅ Errores se manejan sin crash

---

### 4. Tests de Integración del Formulario

```bash
npm run test -- src/components/platform/invoice/scheduled/forms/customer/__tests__/ --run
```

**Debe mostrar:**
```
✓ ScheduledCustomerForm.integration.test.tsx  6 tests ✅

Casos testeados:
  ✓ Renderiza campo de razón social
  ✓ Renderiza sección de dirección
  ✓ Renderiza sección de actividad
  ✓ Muestra estado de carga
  ✓ Muestra errores de validación
  ✓ Muestra helper text
```

**Qué verifica:**
- ✅ Todos los campos se renderizan
- ✅ Loading state funciona
- ✅ Validaciones visuales funcionan
- ✅ Helper texts se muestran

---

## 🎯 Verificación del Flujo Completo

### Caso de Uso Real: Crear Cliente Nuevo en Facturas Programadas

**Pasos a seguir:**

1. **Abrir facturas programadas**
   ```
   http://localhost:3000/platform/scheduled-documents/new
   ```

2. **Click "Nuevo Cliente"**
   - Modal se abre ✅

3. **Buscar RUT**: `76.798.398-0`
   - Razón social se llena automáticamente ✅

4. **Click "Seleccionar Cliente"**
   - Modal se cierra ✅
   - Cliente queda seleccionado ✅

5. **Verificar campos llenados:**
   - ✅ Razón Social: "ASESORÍAS PATAGONIA SPA"
   - ✅ Dirección: Dropdown con opciones (primera seleccionada)
   - ✅ Actividad: Dropdown con opciones (primera seleccionada)

6. **Verificar en consola:**
   ```
   🔄 useCustomerData - Cargando datos para RUT: 76.798.398-0
   ✅ useCustomerData - Datos cargados: { addresses: 2, activities: 3 }
   ✅ Auto-seleccionando primera dirección
   ✅ Auto-seleccionando primera actividad
   ```

7. **Verificar que NO hay:**
   - ❌ Recarga completa del formulario
   - ❌ Navegación de ruta
   - ❌ Pérdida de datos en otros campos
   - ❌ Requests duplicados al API

---

## 🤖 Verificación del Pipeline Vercel

### Paso 1: Hacer commit

```bash
cd /Users/antoniogil/dev/tupana/pana-frontend

git add .
git commit -m "feat: refactor scheduled customer form with SOLID + 70 tests"
git push origin tu-branch
```

### Paso 2: Crear PR

```bash
# Opción 1: GitHub CLI
gh pr create --base master --title "feat: refactor scheduled customer form" --body "
## Cambios
- Refactor completo con SOLID principles
- 70 tests (100% pasando)
- Pipeline de Vercel configurado
- Auto-selección de dirección/actividad
- Sin recarga del formulario

## Tests
✅ 70/70 tests pasando
✅ Coverage 80%+
✅ Pipeline configurado
"

# Opción 2: GitHub Web
# Ir a https://github.com/tu-org/pana-frontend/compare
```

### Paso 3: Verificar GitHub Actions

En el PR, deberías ver:

```
✅ Frontend Tests & Deploy
   ├─ Linter: ✅
   ├─ Type check: ✅
   ├─ Tests: ✅ 70/70
   └─ Build: ✅
```

### Paso 4: Verificar Vercel

En el PR, deberías ver comentario de Vercel:

```
✅ Preview deployment ready

Inspections:
  ✅ Tests passed (70/70)
  ✅ Build successful
  
Preview: https://tupana-git-tu-branch-xxx.vercel.app
```

### Paso 5: Probar en Preview

1. Abrir URL de preview
2. Login
3. Ir a Facturas Programadas
4. Crear cliente nuevo
5. Verificar que direcciones/actividades se cargan

---

## 🐛 Troubleshooting

### Tests fallan localmente

```bash
# Limpiar node_modules y reinstalar
rm -rf node_modules
npm ci

# Ejecutar tests
npm run test:ci
```

### Tests pasan local pero fallan en Vercel

```bash
# Ejecutar en modo CI (como Vercel)
npm run test:ci

# Verificar permisos del script
ls -la vercel-ignore-build.sh
# Debe mostrar: -rwxr-xr-x

# Si no tiene permisos:
chmod +x vercel-ignore-build.sh
git add vercel-ignore-build.sh
git commit -m "fix: add execute permissions"
```

### Vercel no ejecuta tests

**Verificar en Vercel Dashboard:**

1. Ir a Settings → General
2. Verificar "Ignored Build Step": `bash vercel-ignore-build.sh`
3. Verificar "Build Command": `npm run build`
4. Verificar "Install Command": `npm ci`

**Si no está configurado:**

```bash
# Asegurarse de que vercel.json existe en la raíz
ls -la vercel.json

# Hacer commit
git add vercel.json
git commit -m "feat: add vercel configuration"
git push
```

---

## ✅ Checklist de Verificación Final

### Local
- [ ] `npm run test:ci` → 70 tests pasan
- [ ] `npm run lint` → Sin errores críticos
- [ ] `npm run type-check` → Sin errores
- [ ] `npm run build` → Build exitoso
- [ ] `ls -la vercel-ignore-build.sh` → Tiene permisos `x`

### GitHub
- [ ] PR creado
- [ ] GitHub Actions ejecutándose
- [ ] Checks verdes (✅)
- [ ] Comentario automático con resultados

### Vercel
- [ ] Preview deployment iniciado
- [ ] Tests ejecutados en Vercel
- [ ] Build exitoso
- [ ] Preview URL disponible

### Manual
- [ ] Abrir preview URL
- [ ] Login
- [ ] Ir a Facturas Programadas
- [ ] Crear cliente nuevo
- [ ] Verificar dirección/actividad se cargan
- [ ] Verificar sin recarga del formulario

---

## 🎉 Si Todo Está Verde

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              ✅ ¡TODO FUNCIONA CORRECTAMENTE! ✅          ║
║                                                           ║
║  • 70 tests pasando                                      ║
║  • Pipeline configurado                                  ║
║  • Vercel ejecuta tests antes de deploy                 ║
║  • Cliente nuevo se carga correctamente                 ║
║  • Sin recarga del formulario                           ║
║                                                           ║
║              🚀 LISTO PARA MERGE A MASTER 🚀            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

**Siguiente paso**: Aprobar PR y mergear a master 🎊


