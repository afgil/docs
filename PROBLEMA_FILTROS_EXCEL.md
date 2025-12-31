# Problema: Filtros en localStorage ocultan documentos después de subir Excel

## Descripción del Problema

Después de subir un Excel, **en la página de preview de documentos** (`/platform/bulk-invoice-preview`), no se muestran todos los documentos. El problema funciona en modo incógnito, lo que confirma que es un problema de localStorage guardado.

**⚠️ NOTA:** El problema NO está en la página principal de documentos (`/platform`), sino en la página de preview después de subir el Excel (`BulkInvoiceDraft`).

## Causa Raíz

El problema está en **`BulkInvoiceDraft.tsx`** donde se restaura el estado previo desde localStorage cuando se carga la página de preview:

```typescript
// Línea 174-187: restorePreviewState()
const restorePreviewState = () => {
    const savedState = localStorage.getItem('bulkInvoicePreviewState');
    if (savedState) {
        const previewState = JSON.parse(savedState);
        setSearchTerm(previewState.searchTerm || ''); // ⚠️ Filtro de búsqueda
        setShowIncomplete(previewState.showIncomplete || false); // ⚠️ Filtro de completos/incompletos
    }
};
```

Cuando un usuario:

1. Sube un Excel y ve la preview con algunos filtros aplicados (ej: `showIncomplete: true` o `searchTerm: "cliente"`)
2. Navega a otra página
3. Sube otro Excel nuevo
4. Vuelve a la preview

**El estado previo se restaura desde localStorage**, por lo que los filtros anteriores (`showIncomplete`, `searchTerm`) ocultan los documentos nuevos del Excel.

## Variables de localStorage que causan el problema

### 1. **`bulkInvoicePreviewState` (Culpable principal) ✅ RESUELTO**

- **Ubicación:** `localStorage.getItem('bulkInvoicePreviewState')`
- **Contiene:**
  - `showIncomplete: true/false` - Filtro que muestra solo completos o solo incompletos
  - `searchTerm: "texto"` - Término de búsqueda que filtra documentos
  - `selectedInvoiceId: number` - ID del documento seleccionado
- **Problema:** Se restaura automáticamente cuando se carga `BulkInvoiceDraft`, ocultando documentos nuevos
- **Solución:** Se limpia automáticamente cuando se detecta una nueva subida de Excel

### 2. **Otras variables (No causan el problema directamente)**

**Filtros en la URL (solo afectan `/platform`, no `/platform/bulk-invoice-preview`):**

- Guarda la URL anterior con todos sus parámetros
- Se usa para navegar "atrás" pero no debería filtrar documentos
- **Ubicación:** `localStorage.getItem('previousDocumentsUrl')`
- **Se guarda en:**
  - `Platform.tsx` líneas 876, 939, 994
  - `DocumentsHeader.tsx` líneas 79, 98

**`previousDocumentsUrl` (Secundario):**

- Guarda la URL anterior con todos sus parámetros
- Se usa para navegar "atrás" pero no debería filtrar documentos
- **Ubicación:** `localStorage.getItem('previousDocumentsUrl')`

**`selectedDocs` y `selectedDocsEntityId` (No filtra):**

- Solo mantiene la selección de documentos, no filtra qué se muestra
- **Ubicación:** `localStorage.getItem('selectedDocs')`

## Solución Implementada ✅

### Problema Real Identificado

El problema estaba en **`BulkInvoiceDraft.tsx`**. Cuando se sube un Excel nuevo, el componente restauraba el estado previo desde `localStorage.getItem('bulkInvoicePreviewState')`, que incluía:

- `showIncomplete: true/false` - Filtro que muestra solo completos o solo incompletos
- `searchTerm: "texto"` - Término de búsqueda que filtra documentos

Estos filtros guardados ocultaban los documentos nuevos del Excel.

### Solución Aplicada

**1. Detectar nueva subida y limpiar filtros automáticamente:**

En `BulkInvoiceDraft.tsx`, se modificó el `useEffect` que carga documentos para:

- Detectar si es una nueva subida de Excel (cuando `location.state?.documentsCreated` existe)
- Limpiar `searchTerm` y `showIncomplete` cuando se detecta nueva subida
- Eliminar `bulkInvoicePreviewState` del localStorage

**2. No restaurar estado previo en nuevas subidas:**

Se modificó el `useEffect` que restaura el estado previo para:

- Verificar si viene de una nueva subida antes de restaurar
- Si es nueva subida, limpiar filtros inmediatamente en lugar de restaurar

### Código Implementado

```typescript
// En el useEffect que carga documentos (línea ~287)
if (isNewUpload) {
    console.log('🧹 Nueva subida de Excel detectada - limpiando filtros');
    setSearchTerm('');
    setShowIncomplete(false);
    localStorage.removeItem('bulkInvoicePreviewState');
}

// En el useEffect que restaura estado (línea ~194)
const isNewUpload = !!location.state?.documentsCreated;
if (!isNewUpload) {
    restorePreviewState();
} else {
    console.log('🧹 Nueva subida detectada - no restaurando estado previo');
    setSearchTerm('');
    setShowIncomplete(false);
    localStorage.removeItem('bulkInvoicePreviewState');
}
```

### Resultado

Ahora, cuando se sube un Excel nuevo, todos los documentos se muestran correctamente sin filtros previos que los oculten.

## Cómo verificar el problema

1. Abrir la consola del navegador (F12)
2. Subir un Excel y navegar a la preview (`/platform/bulk-invoice-preview`)
3. Verificar localStorage:

   ```javascript
   // En la consola del navegador
   const previewState = localStorage.getItem('bulkInvoicePreviewState');
   console.log('bulkInvoicePreviewState:', previewState ? JSON.parse(previewState) : null);
   
   // Verificar si hay filtros activos
   const state = previewState ? JSON.parse(previewState) : {};
   console.log('searchTerm:', state.searchTerm);
   console.log('showIncomplete:', state.showIncomplete);
   ```

4. Si `searchTerm` tiene un valor o `showIncomplete` es `true`, esos son los filtros que están ocultando documentos

## Archivos Modificados ✅

1. **`pana-frontend/src/components/platform/invoice/bulk/BulkInvoiceDraft.tsx`** ✅
   - Líneas ~194-197: Modificado para no restaurar estado previo en nuevas subidas
   - Líneas ~287-338: Modificado para detectar nuevas subidas y limpiar filtros automáticamente
   - **Variable problemática identificada:** `bulkInvoicePreviewState` en localStorage
