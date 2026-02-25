# Refactorización Vista de Contactos - Frontend

## Resumen
Refactorización de la vista de contactos para mejorar escalabilidad y UX. Ahora muestra empresas primero y luego contactos al hacer clic en cada empresa.

## Problema Original
- Cargaba 50 contactos de todas las empresas en una sola página
- Lento y no escalable
- Mala UX para usuarios con muchos contactos

## Solución Implementada

### Backend (Ya existía)
Los endpoints necesarios ya estaban implementados:

1. **GET /api/emails/contacts/companies/**
   - Lista empresas con count de contactos
   - Paginación: 50 empresas por página
   - Ordenadas por: más contactos primero
   - Query params: `page`, `limit`, `search`

2. **GET /api/emails/contacts/companies/{company_id}/**
   - Lista contactos de una empresa específica
   - Paginación: 50 contactos por página
   - Query params: `page`, `limit`, `search`

### Frontend (Refactorizado)

#### 1. Servicios API
**Archivo:** `src/services/contactsService.ts`

Nuevos métodos agregados:
```typescript
async getCompaniesWithContacts(params?: {
  page?: number;
  limit?: number;
  search?: string;
}): Promise<CompaniesListResponse>

async getContactsByCompany(companyId: number, params?: {
  page?: number;
  limit?: number;
  search?: string;
}): Promise<ContactsListResponse>
```

Nuevas interfaces:
```typescript
interface CompanyWithContacts {
  id: number;
  name: string;
  tax_id: string;
  contacts_count: number;
}

interface CompaniesListResponse {
  count: number;
  next: boolean;
  previous: boolean;
  results: CompanyWithContacts[];
}
```

#### 2. Hooks Personalizados
**Archivos:** `src/components/email/contacts/hooks/`

- `useCompaniesWithContacts.ts` - Maneja la carga de empresas
- `useCompanyContacts.ts` - Maneja la carga de contactos de una empresa específica

#### 3. Componentes Nuevos
**Archivos:** `src/components/email/contacts/components/`

- `CompanyCard.tsx` - Tarjeta individual de empresa con count
- `CompanyListView.tsx` - Vista de lista de empresas
- `CompanyContactsView.tsx` - Vista de contactos de una empresa específica

#### 4. Página Principal Refactorizada
**Archivo:** `src/pages/email/ContactsPage.tsx`

**Dos vistas principales:**

1. **Vista de empresas** (vista inicial)
   - Muestra tarjetas de empresas con count de contactos
   - Búsqueda por nombre o RUT
   - Paginación (50 empresas por página)
   - Ordenadas por: más contactos primero

2. **Vista de contactos de empresa** (al hacer clic)
   - Header con info de empresa y botón "Volver"
   - Lista de contactos de esa empresa
   - Búsqueda dentro de los contactos
   - Paginación (50 contactos por página)
   - Acciones: editar, eliminar
   - Botón "Añadir contacto" (preselecciona la empresa)

## Flujo de Navegación

```
Inicio
  ↓
[Lista de Empresas]
  - Empresa A (15 contactos) ←─┐
  - Empresa B (8 contactos)    │
  - Empresa C (3 contactos)    │ Botón "Volver"
  ↓ (Click en empresa)         │
[Contactos de Empresa A] ──────┘
  - Contacto 1
  - Contacto 2
  - ...
```

## Archivos Modificados

### Backend
- ✅ Endpoints ya existían (no se modificó)

### Frontend
**Nuevos archivos:**
- `src/services/contactsService.ts` (actualizado)
- `src/components/email/contacts/hooks/useCompaniesWithContacts.ts`
- `src/components/email/contacts/hooks/useCompanyContacts.ts`
- `src/components/email/contacts/components/CompanyCard.tsx`
- `src/components/email/contacts/components/CompanyListView.tsx`
- `src/components/email/contacts/components/CompanyContactsView.tsx`

**Modificados:**
- `src/pages/email/ContactsPage.tsx` (refactorizado completamente)
- `src/components/email/contacts/components/index.ts` (exports)
- `src/components/email/contacts/hooks/index.ts` (exports)

**Backup:**
- `src/pages/email/ContactsPage.backup.tsx` (versión original)

## Beneficios

### Performance
- ✅ No carga 50 contactos de todas las empresas de golpe
- ✅ Carga incremental: empresas → contactos de empresa específica
- ✅ Queries optimizadas con QuerySets eficientes

### UX
- ✅ Navegación clara: empresas → contactos
- ✅ Transiciones suaves con loaders
- ✅ Estados de carga explícitos
- ✅ Búsqueda por contexto (empresas vs contactos)
- ✅ Información contextual (count de contactos visible)

### Escalabilidad
- ✅ Puede manejar miles de contactos
- ✅ Paginación en ambas vistas
- ✅ Búsqueda eficiente en backend

## Testing

### Frontend Build
```bash
cd /Users/antoniogil/dev/tupana/pana-frontend
npm run build
```
✅ Build exitoso

### Endpoints a probar
```bash
# Lista empresas con contactos
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/emails/contacts/companies/"

# Contactos de empresa específica
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/emails/contacts/companies/123/"
```

## Consideraciones

### Funcionalidades preservadas
- ✅ Añadir contacto (manual o desde Excel)
- ✅ Editar contacto
- ✅ Eliminar contacto
- ✅ Asignar empresa a contacto
- ✅ Cambiar recipient_type (to/cc/bcc)
- ✅ Búsqueda
- ✅ Paginación
- ✅ Import masivo

### Mejoras futuras
- [ ] Skeleton loaders para mejorar perceived performance
- [ ] Infinite scroll como opción alternativa a paginación
- [ ] Cache de empresas cargadas (evitar recargar al volver)
- [ ] Breadcrumbs para mejor navegación
- [ ] Stats en header (total empresas, total contactos)

## Deployment

### Backend
No requiere cambios (endpoints ya existían)

### Frontend
```bash
cd /Users/antoniogil/dev/tupana/pana-frontend
npm run build
# Deploy según proceso habitual
```

## Rollback
Si hay problemas, restaurar backup:
```bash
cd /Users/antoniogil/dev/tupana/pana-frontend
cp src/pages/email/ContactsPage.backup.tsx src/pages/email/ContactsPage.tsx
```

## Referencias
- Endpoint backend: `apps/emails/app_views/company_contacts_views.py`
- QuerySet optimizado: `apps/emails/querysets/email_contact_querysets.py`
- Frontend service: `src/services/contactsService.ts`
