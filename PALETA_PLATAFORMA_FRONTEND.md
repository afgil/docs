# Paleta de colores – Plataforma (frontend)

Resumen de dónde hay colores fuertes y qué se unificó.

## Ya unificado (slate/gris)

- **TopBar**: ítems activos y hover `text-gray-900 font-medium` / `bg-gray-100`; logo `text-slate-600`; badge Sandbox `bg-slate-100 text-slate-700`.
- **Sidebar**: estado activo en gris; badge "Próximamente" `bg-slate-100 text-slate-700`.
- **Pagination**: focus y página actual `focus:ring-slate-500`, `bg-slate-700`.
- **routes/index.tsx**: loader inicial `border-slate-300 border-t-slate-600`.
- **Conciliación**: banners, tablas, panel detalle, barra de progreso de sync `bg-slate-600` (antes indigo).
- **Cartola bancaria**: BankingMovements, LoadingMovementsBanner, MovementsTable, BankConnectionManager en slate/emerald suave.

## Colores fuertes que siguen (por archivo)

### Semánticos (recomendado mantener)

- **Errores/peligro**: `red-50`, `red-400`, `red-600`, `red-700` en BillingPage, PaymentMethodSection, Platform.tsx, ReconciliationPaymentsPage (mensaje error sync), ChargesPage (backoffice). Tienen sentido para errores.
- **Éxito/positivo**: `green-100/800` pagado, `emerald-600/700` montos positivos en tablas. Se pueden dejar o suavizar a emerald.
- **Gastos/negativo**: `red-50/800` en badge Gastos en BankingMovements; `text-red-600/700` en montos negativos. Correcto como semántica.

### UI que se podría unificar después

| Archivo | Uso | Sugerencia |
|--------|-----|------------|
| **BillingPage.tsx** | Azul/verde/amarillo: plan, precio, badges activo/pagado, botones, iconos CreditCard/Zap/Receipt | Primario/neutro → slate; “activo”/pagado → emerald suave; “pendiente” → amber/slate. |
| **PaymentMethodSection.tsx** | Spinner `green-600`; aviso amarillo (border/icono/texto) | Spinner → slate; aviso → slate o amber muy suave. |
| **Platform.tsx** | Banner aviso amarillo; enlaces azules; botones verde/emerald/red/azul; cards hover azul | Aviso → slate/amber suave; primarios → slate; rojo solo para acciones destructivas. |
| **ChargesPage.tsx** (backoffice) | Verde/rojo éxito/error en resultados | Dejar semántico o suavizar verde a emerald. |
| **BankingReconciliationConfigContent.tsx** | Toggles, loaders, bordes, botones, badges verdes; muchos `green-*` | Unificar a slate para UI; emerald solo si se quiere “éxito/conectado”. |
| **ReconciliationMovementsTable.tsx** | Montos verde/rojo; filtro recomendados y botón verde | Montos → emerald/red; filtro/botón → slate. |

## Criterio recomendado

- **Navegación, botones primarios, focus, loaders, badges neutros**: `slate` / `gray`.
- **Éxito / positivo / pagado / ingresos**: `emerald` suave (opcional mantener algo de green).
- **Error / peligro / negativo / gastos**: `red` (mantener).
- **Avisos / pendiente**: `slate` o `amber` muy suave, evitando amarillo fuerte.

Si quieres, el siguiente paso puede ser aplicar esta paleta en BillingPage, PaymentMethodSection, Platform.tsx y BankingReconciliationConfigContent/ReconciliationMovementsTable.
