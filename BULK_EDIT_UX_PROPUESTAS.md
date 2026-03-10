# Editor masivo – 3 propuestas de UX (referentes: Airtable, Google Sheets, Linear/Jira)

## Estado actual
- Botón «Editar masivo» en barra de acciones → abre **modal** con Actividad económica, Dirección, Comuna, Ciudad.
- Usuario aplica cambios y cierra el modal; luego debe hacer clic en «Guardar» para persistir.
- **Problemas**: el modal tapa la tabla (pierdes contexto de qué filas tocaste), flujo en dos pasos (aplicar + guardar) poco claro.

---

## Solución 1: Barra contextual (floating bar) — **ELEGIDA**
**Referentes:** Linear, Jira (bulk edit bar), Notion (toolbar al seleccionar).

**Comportamiento:**
- Al tener **una o más filas seleccionadas**, aparece una **barra fija debajo de la tabla** (o pegada al borde inferior del viewport) con los mismos campos en formato **compacto** (una fila de inputs o agrupados en acordeón).
- La tabla **sigue visible**; las filas seleccionadas siguen resaltadas.
- Botones: «Aplicar a N» y «Descartar» (o «Cerrar»). Sin modal.
- Opcional: al aplicar, la barra se colapsa o muestra un breve «Aplicado a N documentos» y se mantiene abierta por si quieres seguir editando.

**Ventajas:** Contexto siempre visible, patrón conocido, no invasivo.  
**Desventajas:** En móvil la barra puede ocupar mucho; se puede hacer colapsable.

---

## Solución 2: Panel lateral (drawer)
**Referentes:** Notion (propiedades en panel), Airtable (a veces panel derecho).

**Comportamiento:**
- «Editar masivo» abre un **drawer desde la derecha** (~360–400px) con el formulario.
- La tabla permanece visible a la izquierda con las filas seleccionadas resaltadas.
- Mismo contenido que el modal actual; solo cambia el contenedor (drawer en vez de modal centrado).

**Ventajas:** No tapa toda la pantalla, mantiene contexto.  
**Desventajas:** En pantallas pequeñas resta espacio a la tabla; sigue siendo un «paso aparte».

---

## Solución 3: Inline + «Aplicar a selección»
**Referentes:** Airtable (fill down), Google Sheets (rellenar hacia abajo).

**Comportamiento:**
- Las celdas editables (actividad, dirección, etc.) permiten edición inline (doble clic o ícono).
- Si hay **varias filas seleccionadas** y el usuario edita **una celda** en una de ellas, un **popover** pregunta: «¿Aplicar este valor a las N filas seleccionadas?» [Sí] [No].
- No hay formulario masivo separado; el masivo es «copiar este valor a las demás».

**Ventajas:** Muy directo, mínimo cambio de contexto.  
**Desventajas:** No sirve para «rellenar 4 campos a la vez» (dirección + comuna + ciudad + actividad); habría que repetir el flujo por campo. Mejor para un solo campo.

---

## Decisión: Solución 1 (Barra contextual)
- Mantiene la capacidad de editar **varios campos a la vez** (actividad, dirección, comuna, ciudad).
- La tabla y la selección siguen visibles; no se abre un modal que tape todo.
- Patrón alineado con Linear/Jira y con la idea de «toolbar al seleccionar» de Notion.
- Implementación: barra fija debajo de la tabla (o anclada al bottom cuando hay selección), misma API `onApply` que el modal actual; se puede reutilizar la lógica y sustituir el modal por esta barra.
