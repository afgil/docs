# 🔍 Propuesta de Rediseño: Buscador Inteligente Tu Pana

**Autor:** AI Search Analyst  
**Fecha:** 2026-01-18  
**Versión:** 1.0

---

## 📊 Análisis del Estado Actual

### ✅ Lo que funciona bien

1. **Backend robusto:**
   - `SearchManager` con detección de intención (`SearchIntent`)
   - `SearchHistory` model persistiendo búsquedas
   - Notificaciones a Slack funcionando
   - QuerySets optimizados para búsquedas eficientes

2. **Frontend básico:**
   - `GlobalSearchInput` y `UnifiedSearchInput` componentes
   - Autocomplete básico funcionando
   - Navegación entre módulos

### ❌ Problemas identificados

1. **Desincronización URL ↔ Estado:**
   - Estado vive solo en React (`useState`)
   - URL no refleja búsquedas activas
   - Imposible compartir links con búsqueda
   - Historial del navegador no funciona

2. **Histórico invisible:**
   - `SearchHistory` existe pero no hay UI
   - Usuario no puede ver búsquedas anteriores
   - No hay "búsquedas frecuentes"

3. **Autocomplete limitado:**
   - Sugerencias básicas
   - No hay categorización visual
   - No prioriza búsquedas del usuario

4. **Analytics desconectados:**
   - Eventos a Slack pero sin métricas
   - No hay dashboard de analytics
   - Imposible medir efectividad

---

## 🎯 Objetivos del Rediseño

### 1. Sincronización URL ↔ Estado (Estado = URL)

**Principio:** El estado del buscador debe ser completamente derivado de la URL.

```
URL: /platform/invoices?search=macondo&domain=documents_issued&entity=company
     ↓
Estado del buscador se hidrata desde URL
     ↓
Búsqueda se ejecuta automáticamente
```

### 2. Buscador Inteligente con Intención

**Detección automática:**
- `search_by_company` → Buscar por razón social
- `search_by_rut` → Buscar por RUT (con normalización)
- `search_by_folio` → Buscar por folio
- `search_by_user` → Buscar por usuario
- `search_by_document_type` → Filtrar por tipo de documento

**Reescritura de queries:**
- "macondo" → Buscar en razones sociales
- "12345678-9" → Buscar como RUT
- "FAC-001" → Buscar como folio

### 3. Autocomplete + Sugerencias Avanzadas

**Sugerencias en tiempo real:**
- Empresas buscadas previamente
- RUTs conocidos
- Folios recientes
- Búsquedas frecuentes del usuario
- Indicadores visuales (emoji/iconos)

### 4. Histórico de Búsquedas Visible

**Nueva página:** `/search/advanced`

**Features:**
- Buscador completo con filtros avanzados
- Panel de histórico de búsquedas
- Acciones: repetir, editar, guardar como frecuente

### 5. Backend & Data Model

**Reutilizar `SearchHistory` existente:**
- Ya tiene: `user`, `company_id`, `domain`, `query`, `intent`, `results_count`, `created_at`
- Extender si es necesario para analytics

### 6. Métricas Clave

**KPIs a exponer:**
- % búsquedas con resultados
- Top búsquedas por usuario
- Top búsquedas globales
- Búsquedas repetidas
- Tiempo hasta encontrar resultado

---

## 🏗️ Arquitectura Propuesta

### Frontend Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     URL State Manager                        │
│  (React Router useSearchParams + Custom Hook)                │
│  - URL → Estado sincronizado                                 │
│  - Estado → URL sincronizado                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Search State Hook (useSearchState)               │
│  - Hidrata desde URL                                         │
│  - Sincroniza con URL                                        │
│  - Dispara búsquedas automáticas                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           Search Components (Global/Unified)                  │
│  - GlobalSearchInput (Dashboard)                             │
│  - UnifiedSearchInput (Módulos específicos)                  │
│  - AdvancedSearchPage (Nueva página)                         │
└─────────────────────────────────────────────────────────────┘
```

### Backend Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Search API Endpoints                         │
│  - GET /api/search/ (existente)                              │
│  - GET /api/search/suggestions/ (existente)                  │
│  - GET /api/search/history/ (existente)                      │
│  - GET /api/search/analytics/ (NUEVO)                        │
│  - GET /api/search/frequent/ (NUEVO)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              SearchManager (existente)                        │
│  - Detección de intención                                    │
│  - Búsqueda optimizada                                       │
│  - Generación de sugerencias                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           SearchHistory Model (existente)                     │
│  - Persistencia de búsquedas                                 │
│  - Histórico por usuario/empresa                             │
│  - Analytics y métricas                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 Modelo de Datos

### SearchHistory (Existente - Reutilizar)

```python
class SearchHistory(BasePanaModel):
    user = ForeignKey(User)
    company_id = IntegerField
    domain = CharField  # documents_issued, documents_received, etc.
    query = CharField
    intent = CharField  # search_by_company, search_by_rut, etc.
    results_count = IntegerField
    interaction_type = CharField  # search, click, etc.
    created_at = DateTimeField
```

### Extensiones Propuestas (si es necesario)

```python
class SearchHistory(BasePanaModel):
    # ... campos existentes ...
    
    # Nuevos campos opcionales:
    clicked_result_id = IntegerField(null=True)  # Si hizo click en un resultado
    time_to_result = IntegerField(null=True)  # Milisegundos hasta encontrar
    is_saved_favorite = BooleanField(default=False)  # Guardado como favorito
    search_context = JSONField(null=True)  # Contexto adicional
```

---

## 🔄 Flujo UX Detallado

### Flujo 1: Búsqueda desde Dashboard

```
1. Usuario escribe "macondo" en GlobalSearchInput
   ↓
2. Autocomplete muestra sugerencias:
   - 🏢 Agricola Macondo SPA (empresa)
   - 🔍 "macondo" (búsqueda reciente)
   - 📄 FAC-123 (folio reciente con "macondo")
   ↓
3. Usuario selecciona "Agricola Macondo SPA"
   ↓
4. URL se actualiza: /platform/invoices?search=macondo&domain=documents_issued&entity=company
   ↓
5. Componente Platform.tsx detecta search param
   ↓
6. Búsqueda se ejecuta automáticamente
   ↓
7. Resultados se muestran filtrados
   ↓
8. SearchHistory.record_search() se ejecuta
   ↓
9. Notificación a Slack (ya existente)
```

### Flujo 2: Recargar página con búsqueda activa

```
1. Usuario recarga /platform/invoices?search=macondo&domain=documents_issued
   ↓
2. Platform.tsx lee URL params en useEffect inicial
   ↓
3. Estado se hidrata desde URL
   ↓
4. Búsqueda se ejecuta automáticamente
   ↓
5. Resultados se muestran (igual que antes del reload)
```

### Flujo 3: Compartir link con búsqueda

```
1. Usuario copia URL: /platform/invoices?search=macondo&domain=documents_issued
   ↓
2. Usuario 2 abre el link
   ↓
3. Página carga con búsqueda aplicada
   ↓
4. Resultados se muestran automáticamente
```

### Flujo 4: Histórico de búsquedas

```
1. Usuario click en "Búsqueda Avanzada" (dashboard)
   ↓
2. Navega a /search/advanced
   ↓
3. Página muestra:
   - Buscador completo con filtros
   - Panel lateral con histórico:
     * Últimas 20 búsquedas
     * Búsquedas frecuentes (top 10)
     * Búsquedas guardadas como favoritas
   ↓
4. Usuario click en búsqueda histórica
   ↓
5. Búsqueda se repite y navega al módulo correspondiente
```

---

## 🌐 Estructura de Endpoints

### Endpoints Existentes (Reutilizar)

```
GET /api/search/
  - Params: q, domain, company_id, limit
  - Retorna: resultados + sugerencias + intención detectada
  - Acción: Registra en SearchHistory

GET /api/search/suggestions/
  - Params: q, domain, company_id, limit
  - Retorna: solo sugerencias de autocomplete

GET /api/search/history/
  - Params: domain (opcional), limit
  - Retorna: historial de búsquedas del usuario
```

### Endpoints Nuevos (Agregar)

```
GET /api/search/analytics/
  - Descripción: Métricas agregadas de búsquedas
  - Params: company_id, date_range (opcional)
  - Retorna:
    {
      "total_searches": 1250,
      "searches_with_results": 980,
      "success_rate": 0.784,
      "top_searches": [
        {"query": "macondo", "count": 45, "intent": "search_by_company"},
        ...
      ],
      "top_intents": {
        "search_by_company": 650,
        "search_by_rut": 320,
        ...
      },
      "average_results_count": 23.5
    }

GET /api/search/frequent/
  - Descripción: Búsquedas frecuentes del usuario
  - Params: company_id, limit (default: 10)
  - Retorna:
    [
      {
        "query": "macondo",
        "intent": "search_by_company",
        "count": 12,
        "last_searched": "2026-01-18T16:22:16Z",
        "domain": "documents_issued"
      },
      ...
    ]

POST /api/search/history/:id/favorite/
  - Descripción: Marcar búsqueda como favorita
  - Retorna: SearchHistory actualizado

DELETE /api/search/history/:id/favorite/
  - Descripción: Desmarcar búsqueda como favorita
```

---

## 🎨 Componentes Frontend

### 1. `useSearchState` Hook (Nuevo)

**Responsabilidad:** Sincronizar estado del buscador con URL.

```typescript
function useSearchState(defaultDomain: SearchDomain) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();

  // Hidratar estado desde URL
  const searchTerm = searchParams.get('search') || '';
  const domain = (searchParams.get('domain') as SearchDomain) || defaultDomain;
  const intent = searchParams.get('intent') || null;

  // Actualizar URL cuando cambia el estado
  const updateSearch = useCallback((query: string, newDomain?: SearchDomain) => {
    const newParams = new URLSearchParams(searchParams);
    if (query) {
      newParams.set('search', query);
    } else {
      newParams.delete('search');
    }
    if (newDomain) {
      newParams.set('domain', newDomain);
    }
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // Ejecutar búsqueda cuando cambia la URL
  useEffect(() => {
    if (searchTerm) {
      // Disparar búsqueda automáticamente
      performSearch(searchTerm, domain);
    }
  }, [searchTerm, domain, location.pathname]);

  return {
    searchTerm,
    domain,
    intent,
    updateSearch,
    clearSearch: () => updateSearch(''),
  };
}
```

### 2. `AdvancedSearchPage` Component (Nuevo)

**Ruta:** `/search/advanced`

**Características:**
- Buscador completo con todos los filtros
- Panel lateral con histórico
- Acciones: repetir, editar, favoritar

**Estructura:**
```tsx
<AdvancedSearchPage>
  <SearchBar advanced={true} />
  <div className="grid grid-cols-3 gap-4">
    <div className="col-span-2">
      <SearchResults />
    </div>
    <div className="col-span-1">
      <SearchHistoryPanel />
      <FrequentSearches />
      <SavedSearches />
    </div>
  </div>
</AdvancedSearchPage>
```

### 3. Mejoras en `GlobalSearchInput` y `UnifiedSearchInput`

**Cambios:**
- Usar `useSearchState` para sincronizar con URL
- Mejorar autocomplete con categorías visuales
- Mostrar búsquedas frecuentes en dropdown

---

## 📏 Reglas de Sincronización URL ↔ Estado

### 1. URL → Estado (Hidratación)

**Cuándo:**
- Al cargar componente (`useEffect` inicial)
- Al cambiar `location.pathname` (navegación)
- Al cambiar `searchParams` (back/forward)

**Cómo:**
```typescript
useEffect(() => {
  const searchFromURL = searchParams.get('search');
  if (searchFromURL && searchFromURL !== localState) {
    setLocalState(searchFromURL);
    executeSearch(searchFromURL);
  }
}, [searchParams, location.pathname]);
```

### 2. Estado → URL (Sincronización)

**Cuándo:**
- Al escribir en el input (con debounce)
- Al seleccionar sugerencia
- Al cambiar dominio de búsqueda

**Cómo:**
```typescript
const updateSearch = (query: string) => {
  const newParams = new URLSearchParams(searchParams);
  newParams.set('search', query);
  setSearchParams(newParams, { replace: true }); // replace: true evita spam de historial
};
```

### 3. Parámetros de URL

**Estructura:**
```
/platform/invoices?search=macondo&domain=documents_issued&intent=search_by_company&entity=company
```

**Parámetros:**
- `search`: Término de búsqueda
- `domain`: Dominio (`documents_issued`, `documents_received`, etc.)
- `intent`: Intención detectada (opcional, para analytics)
- `entity`: Tipo de entidad si aplica (`company`, `folio`, etc.)

### 4. Deep Links

**Ejemplo:**
```
/platform/invoices?search=AGRICOLA+MACONDO+SPA&domain=documents_issued&intent=search_by_company
```

**Comportamiento:**
1. Usuario abre el link
2. `Platform.tsx` detecta params en URL
3. Búsqueda se ejecuta automáticamente
4. Resultados se muestran filtrados

---

## 📊 Analytics & Métricas

### Métricas Clave

1. **Success Rate:**
   ```python
   success_rate = searches_with_results / total_searches
   ```

2. **Top Searches:**
   ```python
   top_searches = SearchHistory.objects.filter(
       company_id=company_id
   ).values('query').annotate(
       count=Count('id')
   ).order_by('-count')[:10]
   ```

3. **Búsquedas Repetidas:**
   ```python
   repeated_searches = SearchHistory.objects.filter(
       user=user,
       company_id=company_id
   ).values('query').annotate(
       count=Count('id')
   ).filter(count__gt=1)
   ```

4. **Tiempo hasta Resultado:**
   - (Futuro: medir tiempo desde inicio de búsqueda hasta click en resultado)

### Dashboard de Analytics (Futuro)

**Endpoint:** `GET /api/search/analytics/`

**Visualizaciones:**
- Gráfico de éxito de búsquedas (% con resultados)
- Top 10 búsquedas
- Distribución de intenciones
- Búsquedas por dominio
- Tendencias temporales

---

## 🚀 Plan de Implementación

### Fase 1: Sincronización URL (Prioridad ALTA)

1. ✅ Crear `useSearchState` hook
2. ✅ Actualizar `GlobalSearchInput` para usar hook
3. ✅ Actualizar `UnifiedSearchInput` para usar hook
4. ✅ Actualizar `Platform.tsx` para hidratar desde URL
5. ✅ Actualizar `ScheduledDocumentsPage.tsx` para hidratar desde URL
6. ✅ Testing: reload, share links, back/forward

**Tiempo estimado:** 2-3 días

### Fase 2: Histórico Visible (Prioridad MEDIA)

1. ✅ Crear `/search/advanced` ruta
2. ✅ Crear `AdvancedSearchPage` component
3. ✅ Crear `SearchHistoryPanel` component
4. ✅ Agregar endpoints `/api/search/frequent/`
5. ✅ Agregar endpoints para favoritos
6. ✅ Testing: repetir búsquedas, guardar favoritas

**Tiempo estimado:** 3-4 días

### Fase 3: Autocomplete Mejorado (Prioridad MEDIA)

1. ✅ Mejorar categorización visual (emojis/iconos)
2. ✅ Priorizar búsquedas del usuario
3. ✅ Agregar búsquedas frecuentes al dropdown
4. ✅ Testing: UX de autocomplete

**Tiempo estimado:** 2 días

### Fase 4: Analytics (Prioridad BAJA)

1. ✅ Crear endpoint `/api/search/analytics/`
2. ✅ Agregar dashboard de analytics (futuro)
3. ✅ Testing: métricas correctas

**Tiempo estimado:** 2-3 días

---

## 💡 Ideas de Mejoras Futuras

### 1. Ranking Inteligente con ML

**Objetivo:** Priorizar resultados según comportamiento del usuario.

**Implementación:**
- Trackear clicks en resultados
- Entrenar modelo para ranking personalizado
- Priorizar resultados más clickeados por usuario

### 2. Recomendaciones Automáticas

**Objetivo:** Sugerir búsquedas relacionadas.

**Implementación:**
- Analizar búsquedas similares de otros usuarios
- "Otros usuarios también buscaron..."
- Clustering de búsquedas

### 3. Búsqueda con IA (ChatGPT Integration)

**Objetivo:** Permitir búsquedas en lenguaje natural.

**Ejemplo:**
- Usuario: "muéstrame todas las facturas de Macondo del último mes"
- Sistema: Detecta intención, construye query, muestra resultados

### 4. Búsqueda Multi-Dominio

**Objetivo:** Buscar en todos los dominios simultáneamente.

**Implementación:**
- Búsqueda paralela en todos los dominios
- Agrupar resultados por dominio
- Mostrar totales por dominio

### 5. Guardado de Búsquedas Avanzadas

**Objetivo:** Guardar búsquedas complejas como "plantillas".

**Ejemplo:**
- Guardar: "Facturas emitidas a Macondo, estado pagado, último mes"
- Reusar búsqueda guardada con un click

---

## ✅ Checklist de Validación

### Funcionalidad

- [ ] URL se actualiza al buscar
- [ ] Estado se hidrata desde URL al cargar
- [ ] Búsquedas se ejecutan automáticamente desde URL
- [ ] Links compartidos funcionan correctamente
- [ ] Back/forward del navegador funciona
- [ ] Histórico de búsquedas se muestra correctamente
- [ ] Búsquedas frecuentes se calculan correctamente
- [ ] Favoritos funcionan

### UX

- [ ] Autocomplete es rápido y útil
- [ ] Sugerencias están bien categorizadas
- [ ] Búsqueda avanzada es intuitiva
- [ ] Histórico es fácil de usar

### Performance

- [ ] Búsquedas son rápidas (< 200ms)
- [ ] Autocomplete no bloquea la UI
- [ ] URL updates no causan re-renders innecesarios

### Analytics

- [ ] Eventos se registran correctamente
- [ ] Métricas se calculan correctamente
- [ ] Dashboard muestra datos útiles

---

## 📚 Referencias

- **Documentación Search Backend:** `apps/core/search/README.md`
- **SearchManager:** `apps/core/search/manager.py`
- **SearchHistory Model:** `apps/core/app_models/search_history.py`
- **SearchNotificationStrategy:** `apps/core/search/strategies/search_notification_strategy.py`

---

**Fin del documento de propuesta**
