# API Master Entities con Paginación - Infinite Scroll

**Endpoint:** `GET /api/auth/master-entities/`  
**Fecha:** 16 Feb 2026  
**Propósito:** Cargar empresas del usuario autenticado con paginación e infinite scroll para el selector del header.

---

## 1. Endpoint Paginado

### GET /api/auth/master-entities/

**Query Params:**
- `page`: Número de página (default: 1)
- `page_size`: Tamaño de página (default: 25, max: 100)
- `search`: Término de búsqueda (busca en `name` y `tax_id`) - **busca sobre TODAS las empresas**, no solo las cargadas

**Response:**

```json
{
  "count": 255,
  "next": 2,
  "previous": null,
  "results": [
    {
      "id": 123,
      "name": "Empresa ABC SPA",
      "tax_id": "12345678-9",
      "successful_batch_documents_count": 150,
      "documents_this_month": 20,
      "documents_last_month": 30,
      "last_activity_date": "2026-02-15",
      ...
    }
  ]
}
```

---

## 2. Cambios en /api/auth/profile/

El endpoint de perfil ahora devuelve:

```json
{
  "email": "usuario@ejemplo.com",
  "master_entities": [...],  // Solo primeras 25
  "master_entities_count": 255,  // Total de empresas
  "master_entities_has_more": true  // Hay más páginas
}
```

**Comportamiento:**
- `master_entities`: Primeras 25 empresas (por defecto)
- `master_entities_count`: Total de empresas del usuario
- `master_entities_has_more`: `true` si hay más de 25 empresas

---

## 3. Implementación Frontend - Infinite Scroll

### Flujo Recomendado

#### Al Abrir el Selector

```typescript
// 1. Al cargar página: profile ya tiene primeras 25 empresas
const profile = await authService.getProfile();
setCompanies(profile.master_entities);
setHasMore(profile.master_entities_has_more);
setTotalCount(profile.master_entities_count);
```

#### Infinite Scroll (al hacer scroll hacia abajo)

```typescript
const loadMoreCompanies = async (page: number) => {
  const response = await fetch(
    `/api/auth/master-entities/?page=${page}&page_size=25`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const data = await response.json();
  
  setCompanies(prev => [...prev, ...data.results]);
  setHasMore(data.next !== null);
  setCurrentPage(page);
};

// En el componente de scroll
const handleScroll = (e) => {
  const { scrollTop, scrollHeight, clientHeight } = e.target;
  if (scrollHeight - scrollTop <= clientHeight * 1.5 && hasMore && !loading) {
    loadMoreCompanies(currentPage + 1);
  }
};
```

#### Búsqueda (busca sobre TODAS las empresas)

```typescript
const searchCompanies = async (searchTerm: string) => {
  // El search busca sobre TODAS las empresas (count total), no solo las 25 cargadas
  const response = await fetch(
    `/api/auth/master-entities/?search=${encodeURIComponent(searchTerm)}&page=1&page_size=25`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const data = await response.json();
  
  setCompanies(data.results);
  setHasMore(data.next !== null);
  setTotalCount(data.count);  // Count actualizado con el filtro
  setCurrentPage(1);
};
```

### Ejemplo React con react-infinite-scroll-component

```typescript
import InfiniteScroll from 'react-infinite-scroll-component';

const CompanySelector = () => {
  const [companies, setCompanies] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');

  // Cargar más al hacer scroll
  const fetchMore = async () => {
    const nextPage = page + 1;
    const data = await companyService.getMasterEntities(nextPage, 25, search);
    setCompanies(prev => [...prev, ...data.results]);
    setHasMore(data.next !== null);
    setPage(nextPage);
  };

  // Buscar (reinicia desde página 1)
  const handleSearch = async (term: string) => {
    setSearch(term);
    const data = await companyService.getMasterEntities(1, 25, term);
    setCompanies(data.results);
    setHasMore(data.next !== null);
    setPage(1);
  };

  return (
    <div>
      <input 
        type="text" 
        placeholder="Buscar empresa..." 
        onChange={(e) => handleSearch(e.target.value)}
      />
      
      <InfiniteScroll
        dataLength={companies.length}
        next={fetchMore}
        hasMore={hasMore}
        loader={<div>Cargando...</div>}
        height={400}
      >
        {companies.map(company => (
          <div key={company.id}>{company.name}</div>
        ))}
      </InfiniteScroll>
    </div>
  );
};
```

---

## 4. Ventajas

✅ **Performance:**
- `/api/auth/profile/` ahora devuelve solo 25 empresas (antes 255) → mucho más rápido
- Infinite scroll carga empresas bajo demanda
- Search busca sobre todas (backend filtra), no solo en las 25 cargadas del cliente

✅ **UX:**
- Selector se abre rápido (solo primeras 25)
- Scroll suave carga más empresas
- Búsqueda instantánea sobre todas las empresas

✅ **Escalabilidad:**
- Funciona con 10, 100 o 1000 empresas
- El backend pagina eficientemente (índices en MasterEntity)

---

## 5. Testing

### Backend

```bash
# Probar paginación
curl 'http://localhost:8000/api/auth/master-entities/?page=1&page_size=5' \
  -H 'Authorization: Bearer <token>'

# Probar search
curl 'http://localhost:8000/api/auth/master-entities/?search=spa' \
  -H 'Authorization: Bearer <token>'

# Probar profile (debe devolver solo 25 + count + has_more)
curl 'http://localhost:8000/api/auth/profile/' \
  -H 'Authorization: Bearer <token>'
```

### Frontend

1. Abrir selector de empresas → debe cargar solo primeras 25
2. Scroll hacia abajo → debe cargar siguientes 25 automáticamente
3. Buscar "spa" → debe buscar en TODAS las empresas y mostrar solo resultados
4. Con búsqueda activa, scroll debe paginar sobre los resultados filtrados

---

## 6. Migración Frontend

### Servicio API (src/services/authService.ts)

```typescript
export interface MasterEntitiesResponse {
  count: number;
  next: number | null;
  previous: number | null;
  results: MasterEntity[];
}

class AuthService {
  // ... métodos existentes ...

  async getMasterEntities(
    page: number = 1, 
    pageSize: number = 25, 
    search: string = ''
  ): Promise<MasterEntitiesResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (search) {
      params.append('search', search);
    }
    
    const response = await api.get(`/auth/master-entities/?${params}`);
    return response.data;
  }
}
```

### Hook useInfiniteMasterEntities

```typescript
export const useInfiniteMasterEntities = () => {
  const [companies, setCompanies] = useState<MasterEntity[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const loadMore = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const data = await authService.getMasterEntities(page, 25, search);
      setCompanies(prev => [...prev, ...data.results]);
      setHasMore(data.next !== null);
      setPage(prev => prev + 1);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (term: string) => {
    setSearch(term);
    setLoading(true);
    try {
      const data = await authService.getMasterEntities(1, 25, term);
      setCompanies(data.results);
      setHasMore(data.next !== null);
      setPage(2);
    } finally {
      setLoading(false);
    }
  };

  return { companies, hasMore, loadMore, handleSearch, loading };
};
```

---

## 7. Notas Importantes

1. **Search es server-side:** El backend filtra todas las empresas; el frontend no debe filtrar localmente.
2. **Paginación por página:** Usa `page` (no cursor), así el frontend puede ir a cualquier página.
3. **page_size=25 por defecto:** Balance entre rapidez y UX (no muy pocas empresas por request).
4. **max page_size=100:** El backend limita a 100 para evitar overload.

---

## 8. Performance

**Antes:**
- `/api/auth/profile/` devolvía 255 empresas → pesado
- Selector tardaba en abrir si usuario tiene muchas empresas

**Después:**
- `/api/auth/profile/` devuelve solo 25 → rápido
- Selector abre instantáneamente
- Empresas adicionales se cargan bajo demanda

**Latencia esperada:**
- `/api/auth/profile/`: <500ms (antes podía ser >2s con 255 empresas)
- `/api/auth/master-entities/?page=N`: <300ms por página
