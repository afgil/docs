# Prompt: Gráfico de Histórico de Facturación

## CONTEXTO GENERAL

Se debe implementar un gráfico de histórico de facturación que muestre la facturación real emitida de los últimos 12 meses por defecto.

Este gráfico es financiero y **DEBE ser estrictamente comparable con el valor "Issued" del Cashflow Projection**.

👉 **El histórico NO es una lógica nueva**
👉 **Es la misma facturación emitida, vista en el pasado**

## REGLA CRÍTICA — EQUIVALENCIA CON CASHFLOW PROJECTION

⚠️ **LOS MONTOS DEBEN SER IDÉNTICOS A "Issued" DEL CASHFLOW PROJECTION PARA UN MISMO MES**

Para lograr esto, el cálculo **DEBE cumplir TODAS las siguientes reglas, sin excepción:**

### Reglas obligatorias

✅ **Montos NETOS (sin IVA)**

✅ **Suma de documentos emitidos**

✅ **Resta de notas de crédito asociadas**

✅ **Reutiliza EXACTAMENTE:**

- `CashflowProjectionService._get_document_net_amount()`

✅ **Excluye documentos sandbox cuando la entidad no es sandbox**

✅ **Excluye documentos inválidos (sin folio)**

✅ **Excluye notas de crédito (DTE tipo 61) del cálculo base**

### 🚫 PROHIBIDO

- usar `amount_with_iva`
- recalcular IVA
- duplicar lógica
- "simplificar" el cálculo

👉 **Si el mes actual no cuadra con cashflow projection, la implementación es incorrecta.**

## BACKEND — DJANGO (APP finance)

### Estructura OBLIGATORIA

```
apps/
  finance/
    repositories/
      billing_history_repository.py   # ORM only
    services/
      billing_history_service.py      # Business logic
    app_serializers/
      billing_history_serializer.py   # Output contract
    app_views/
      billing_history_view.py         # HTTP layer
    urls.py
```

🚫 **NO crear nuevas apps**
🚫 **TODO vive en finance**

### Repository — `billing_history_repository.py`

#### Principios

- **SOLO ORM**
- **CERO lógica financiera**
- **Reutilizar querysets existentes**

#### Reutilización obligatoria

Usar querysets ya existentes en:

- `apps.documents.app_models.report_querysets`

Ejemplos (si existen):

- `DocumentReportQuerySet`
- `FinanceReportQuerySet`
- `by_sender()`
- `by_date_range()`
- `invoices_only()`
- `exclude_credit_notes()`

#### Método requerido

```python
def get_issued_documents_by_month(
    self,
    master_entity: MasterEntity,
    start_date: date,
    end_date: date,
):
    """
    Returns issued documents grouped by TruncMonth(date_issued).

    Rules:
    - Filter by sender (master_entity)
    - Filter by issued state
    - Exclude sandbox if master_entity is not sandbox
    - Exclude documents without folio
    - Exclude credit notes (DTE 61)
    - Group by TruncMonth("date_issued")

    IMPORTANT:
    - Do NOT calculate net amounts here
    - Return QuerySet suitable for service-level aggregation
    """
```

### Service — `billing_history_service.py`

#### Principios

- **Cálculo financiero vive aquí**
- **NO duplicar lógica existente**
- **NO inventar reglas nuevas**

#### Reutilización obligatoria

El cálculo NETO **DEBE reutilizar directamente:**

- `CashflowProjectionService._get_document_net_amount()`

🚫 **NO copiar el método**
🚫 **NO reescribirlo**
🚫 **NO "optimizarlo"**

#### Método requerido

```python
def get_billing_history(
    self,
    master_entity: MasterEntity,
    months: int = 12,
) -> list[dict]:
    """
    Returns billing history for the last N months.

    Output per month:
    - month: YYYY-MM
    - amount: float (NET CLP)
    - issued_count: int

    Business rules:
    - Calculate date range from today backwards
    - For each month:
        1. Fetch issued documents (repository)
        2. Calculate NET amount per document using
           CashflowProjectionService._get_document_net_amount()
        3. Subtract associated credit notes
        4. Sum NET amounts
    """
```

### Serializer — `billing_history_serializer.py`

```python
class BillingHistoryMonthSerializer(serializers.Serializer):
    month = serializers.CharField(max_length=7)  # YYYY-MM
    amount = serializers.FloatField(help_text="Net amount in CLP")
    issued_count = serializers.IntegerField()
```

### View — `billing_history_view.py`

```python
class BillingHistoryView(APIView):
    """
    GET /api/finance/billing-history/

    Query params:
    - months (int, default: 12)

    Auth:
    - master_entity obtained from EntityContext
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Resolve master_entity from context
        # Parse months param (default = 12)
        # Call BillingHistoryService
        # Serialize and return response
```

### URL

```python
path("billing-history/", BillingHistoryView.as_view(), name="billing-history")
```

## FRONTEND — REACT

### Estructura OBLIGATORIA

```
src/
  modules/
    finance/
      charts/
        BillingHistoryChart.tsx
        index.ts
      hooks/
        useBillingHistory.ts
      types/
        billing.ts
```

### Chart — `BillingHistoryChart.tsx`

#### Reglas críticas

- **Reutilizar estilos de `CashflowProjectionChart.tsx`**
- **Mismo color que "Issued" (azul)**
- **Misma tipografía, spacing y animaciones**

#### Especificaciones

- **Tipo:** Bar Chart
- **Serie única:** Facturación emitida
- **Color:** `#2563eb`
- **Eje X:** últimos N meses
- **Eje Y:**
  - CLP
  - sin decimales
  - separador de miles
- **Label en barra:** monto NETO
- **Tooltip:**
  - Mes
  - Monto NETO completo
  - Cantidad de documentos
- **Texto explicativo:**
  - "Calculated using the same logic as Issued in Cashflow Projection"

### Hook — `useBillingHistory.ts`

```typescript
export function useBillingHistory(months: number = 12): {
  data: BillingHistoryMonth[] | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}
```

- Enviar `months` por query param
- `master_entity` desde EntityContext
- Manejar loading / error / empty

### Types — `billing.ts`

```typescript
export type BillingHistoryMonth = {
  month: string; // YYYY-MM
  amount: number; // CLP net
  issued_count: number;
};
```

## INTEGRACIÓN EN REPORTES DE VENTAS

**CRÍTICO:** El gráfico debe agregarse en `SalesReport.tsx` en lugar del componente Metabase.

### Ubicación

- **Archivo:** `src/components/reports/reports/SalesReport.tsx`
- **Reemplazar:** Cualquier uso de `MetabaseReport` relacionado con histórico de facturación
- **Agregar:** `BillingHistoryChart` como una nueva sección

### Estructura sugerida

```tsx
// En SalesReport.tsx
import { BillingHistoryChart } from '../../../modules/finance/charts/BillingHistoryChart';

// Agregar sección:
<div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
  <h3 className="text-lg font-semibold mb-4">Histórico de Facturación</h3>
  <BillingHistoryChart />
</div>
```

## VALIDACIÓN DE EQUIVALENCIA (OBLIGATORIA)

⚠️ **TEST CRÍTICO — NO OPCIONAL**

```python
def test_billing_history_equivalent_to_cashflow():
    """
    Billing history current month MUST equal
    cashflow projection issued current month.
    """
    billing_amount = billing_history[0]["amount"]
    cashflow_amount = cashflow_projection[0]["issued"]

    assert abs(billing_amount - cashflow_amount) < 1.0
```

**Si este test falla:**

- ❌ la implementación es incorrecta
- ❌ no se debe mergear

## TESTING MÍNIMO

### Backend

- Últimos 12 meses por defecto
- Montos NETOS
- Equivalente a cashflow projection
- Respeta sandbox

### Frontend

- Render correcto
- Tooltip correcto
- Estados loading / error

## NOTA FINAL (NO NEGOCIABLE)

Este gráfico:

- es financiero
- es crítico
- **NO define lógica**
- **SOLO reutiliza y refleja**

**Cashflow Projection define la verdad**
**Billing History la muestra en el tiempo**

🚫 **NO romper esta equivalencia.**
