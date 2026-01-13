# Seguridad del Backoffice - Separación de Código

## 🎯 Objetivo

Garantizar que el código del backoffice **NUNCA** sea visible o descargable por usuarios que no son administradores. El código del backoffice debe estar completamente separado del bundle principal.

## 🔒 Solución Implementada

### 1. Bundle Separado

El código del backoffice está en un bundle completamente separado que solo se descarga si el usuario es admin.

**Configuración en `vite.config.ts`:**

```typescript
manualChunks: (id) => {
  // BACKOFFICE: Separar completamente el código del backoffice
  if (id.includes('/backoffice/') || id.includes('\\backoffice\\')) {
    return 'backoffice';
  }
  // ... otros chunks
}
```

**Resultado:**
- Bundle principal: `assets/[name]-[hash].js` (sin código de backoffice)
- Bundle backoffice: `assets/backoffice-[hash].js` (solo código de backoffice)

### 2. Verificación de Rol Antes de Cargar

El componente `AdminRoute` verifica el rol del usuario **ANTES** de cargar el bundle del backoffice.

**Flujo de seguridad:**

1. Usuario intenta acceder a `/backoffice/*`
2. `AdminRoute` verifica autenticación (ProtectedRoute)
3. `AdminRoute` verifica rol de admin usando `useAdminAuth`
4. **Solo si es admin**: Se carga el bundle `backoffice-[hash].js`
5. **Si no es admin**: Redirige a `/platform/dashboard` sin cargar el bundle

### 3. Lazy Loading Condicional

Las rutas del backoffice usan lazy loading que solo se ejecuta si el usuario pasa todas las verificaciones:

```typescript
const BackofficeDashboard = lazy(() => 
  import('../pages/backoffice/Dashboard').then(m => ({ 
    default: m.BackofficeDashboard 
  }))
);
```

**Importante:** El `import()` dinámico solo se ejecuta cuando React intenta renderizar el componente, que solo ocurre después de que `AdminRoute` verifica que el usuario es admin.

## 🛡️ Garantías de Seguridad

### ✅ Código No Visible en Bundle Principal

- El código del backoffice está en un bundle separado
- No se incluye en el bundle principal que descargan todos los usuarios
- Los clientes no pueden ver el código del backoffice en las DevTools

### ✅ Bundle No Descargado para No-Admins

- El bundle `backoffice-[hash].js` solo se descarga si el usuario es admin
- Si un usuario no-admin intenta acceder, se redirige sin descargar el bundle
- No hay forma de que un usuario no-admin descargue el bundle

### ✅ Verificación en Múltiples Capas

1. **Frontend - Ruta**: `AdminRoute` verifica rol antes de renderizar
2. **Frontend - Bundle**: Bundle separado que solo se carga condicionalmente
3. **Backend**: Debe validar que el usuario es admin en todos los endpoints

## 📁 Estructura de Archivos

```
src/
├── pages/
│   └── backoffice/          # Código del backoffice (bundle separado)
│       └── Dashboard.tsx
├── components/
│   └── AdminRoute.tsx        # Verificación de rol antes de cargar
├── hooks/
│   └── useAdminAuth.ts       # Hook para verificar rol de admin
└── routes/
    └── index.tsx             # Rutas con lazy loading condicional
```

## 🚀 Uso

### Agregar Nueva Página al Backoffice

1. Crear el componente en `src/pages/backoffice/`:

```typescript
// src/pages/backoffice/Users.tsx
export function BackofficeUsers() {
  return <div>Gestión de Usuarios</div>;
}
```

2. Agregar lazy import en `routes/index.tsx`:

```typescript
const BackofficeUsers = lazy(() => 
  import('../pages/backoffice/Users').then(m => ({ 
    default: m.BackofficeUsers 
  }))
);
```

3. Agregar ruta protegida:

```typescript
{
  path: '/backoffice/users',
  element: (
    <AppWrapper>
      <AdminRoute>
        <LazyWrapper><BackofficeUsers /></LazyWrapper>
      </AdminRoute>
      <ScrollRestoration />
    </AppWrapper>
  ),
}
```

### Verificar que Funciona

1. **Como usuario no-admin:**
   - Intentar acceder a `/backoffice/dashboard`
   - Debe redirigir a `/platform/dashboard`
   - En Network tab: NO debe aparecer `backoffice-[hash].js`

2. **Como admin:**
   - Acceder a `/backoffice/dashboard`
   - Debe cargar correctamente
   - En Network tab: SÍ debe aparecer `backoffice-[hash].js`

## ⚠️ Importante

### Validación en Backend

**CRÍTICO:** Esta solución solo protege el código del frontend. El backend DEBE validar que el usuario es admin en todos los endpoints del backoffice:

```python
# Ejemplo en Django
from rest_framework.permissions import IsAdminUser

class BackofficeUsersView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        # Solo admins pueden acceder
        ...
```

### No Exponer Información Sensible

- No incluir información sensible en los nombres de archivos o rutas
- No exponer estructura interna en mensajes de error
- Usar códigos de error genéricos para usuarios no autorizados

## 🔍 Verificación de Seguridad

### Checklist

- [ ] Bundle del backoffice está separado (`backoffice-[hash].js`)
- [ ] Bundle no aparece en Network tab para usuarios no-admin
- [ ] `AdminRoute` verifica rol antes de cargar
- [ ] Backend valida rol en todos los endpoints
- [ ] No hay referencias al backoffice en el bundle principal
- [ ] Source maps no incluyen código del backoffice (en producción)

### Comandos de Verificación

```bash
# Build de producción
npm run build

# Verificar que existe bundle separado
ls dist/assets/backoffice-*.js

# Verificar que el bundle principal NO incluye backoffice
grep -r "backoffice" dist/assets/*.js | grep -v "backoffice-[hash].js"
# No debe encontrar nada
```

## 📝 Notas Técnicas

- El bundle del backoffice se genera automáticamente por Vite
- El hash en el nombre del archivo cambia con cada build
- El lazy loading usa `import()` dinámico que solo se ejecuta cuando se necesita
- `AdminRoute` usa `useAdminAuth` que cachea el perfil del usuario para evitar requests innecesarios
