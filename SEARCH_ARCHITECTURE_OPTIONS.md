# Análisis de 3 Soluciones para el Sistema de Búsqueda

## Problema Actual

El sistema de búsqueda no muestra las sugerencias correctamente cuando el usuario escribe. El dropdown muestra el historial en lugar de las sugerencias actuales.

## Solución 1: Context con Reducer + Servicio Separado

### Arquitectura

```
SearchContext (Provider)
  ├── SearchState (reducer)
  ├── SearchService (lógica de API)
  └── SearchActions (dispatch actions)

UnifiedSearchInput (componente presentacional)
  └── useSearchContext() (consume estado)
```

### Ventajas

- ✅ Estado centralizado y predecible
- ✅ Separación clara de responsabilidades
- ✅ Fácil de testear
- ✅ Reutilizable en múltiples componentes
- ✅ Sincronización automática entre componentes

### Desventajas

- ⚠️ Más código inicial
- ⚠️ Curva de aprendizaje para el equipo

### Archivos

- `context/SearchContext.tsx` - Provider y Context
- `context/searchReducer.ts` - Lógica de estado
- `services/searchStateService.ts` - Lógica de negocio
- `hooks/useSearchContext.ts` - Hook de consumo

---

## Solución 2: Context Simple + Hook Mejorado

### Arquitectura

```
SearchContext (Provider simple)
  ├── Estado: query, suggestions, history
  └── Métodos: setQuery, loadSuggestions, etc.

useSearchContext() (hook mejorado)
  ├── Debounce interno
  ├── Carga de sugerencias
  └── Sincronización con URL

UnifiedSearchInput (componente presentacional)
```

### Ventajas

- ✅ Más simple que Solución 1
- ✅ Menos archivos
- ✅ Mantiene la lógica en el hook
- ✅ Fácil de entender

### Desventajas

- ⚠️ Lógica de negocio mezclada con estado
- ⚠️ Menos escalable
- ⚠️ Más difícil de testear

### Archivos

- `context/SearchContext.tsx` - Provider y Context
- `hooks/useSearchContext.ts` - Hook con toda la lógica

---

## Solución 3: Context con Reducer + Middleware Pattern

### Arquitectura

```
SearchContext (Provider)
  ├── SearchReducer (estado)
  ├── SearchMiddleware (efectos secundarios)
  └── SearchSelectors (computed values)

SearchService (servicio independiente)
  ├── API calls
  └── Transformación de datos

UnifiedSearchInput (componente presentacional)
```

### Ventajas

- ✅ Máxima separación de responsabilidades
- ✅ Muy escalable
- ✅ Fácil de extender con nuevas features
- ✅ Testeable por capas
- ✅ Patrón profesional y mantenible

### Desventajas

- ⚠️ Más complejo inicialmente
- ⚠️ Más archivos

### Archivos

- `context/SearchContext.tsx` - Provider
- `context/searchReducer.ts` - Reducer
- `context/searchMiddleware.ts` - Efectos secundarios
- `context/searchSelectors.ts` - Selectores
- `services/searchService.ts` - Servicio de API
- `hooks/useSearchContext.ts` - Hook de consumo

---

## Análisis y Recomendación

### Comparación

| Criterio | Solución 1 | Solución 2 | Solución 3 |
|----------|-----------|-----------|-----------|
| Simplicidad | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Escalabilidad | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Testeabilidad | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Mantenibilidad | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Separación de responsabilidades | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

### Decisión: **Solución 1** (Context con Reducer + Servicio Separado)

**Razones:**

1. **Balance perfecto**: No es tan simple que sea difícil de mantener, ni tan complejo que sea difícil de entender
2. **Separación clara**: Estado, lógica de negocio y presentación están separados
3. **Testeable**: Cada capa se puede testear independientemente
4. **Escalable**: Fácil agregar nuevas features sin romper lo existente
5. **Patrón familiar**: Similar a EntityContext que ya usan en el proyecto

### Implementación Elegida

```
src/
├── context/
│   ├── SearchContext.tsx          # Provider y Context
│   └── searchReducer.ts           # Reducer para estado
├── services/
│   └── searchStateService.ts      # Lógica de negocio (debounce, carga)
├── hooks/
│   └── useSearchContext.ts        # Hook de consumo
└── components/
    └── search/
        └── UnifiedSearchInput.tsx # Componente presentacional
```
