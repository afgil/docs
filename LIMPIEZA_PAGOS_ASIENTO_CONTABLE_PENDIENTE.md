# Limpieza de pagos – asiento contable (pendiente)

## Contexto

Al marcar documentos de pago (tipo 100) como "limpiados" (reconciliation_status=cleaned) con una categoría, el usuario indicó que debería crearse **un asiento contable que permita eliminar los ingresos no declarados en otros**.

## Estado actual

- **Hecho:** Al limpiar se actualiza `DocumentPaymentMetadata` (reconciliation_status, clean_category, clean_category_custom, clean_note, cleaned_at). No se crea ningún asiento.
- **Pendiente:** Definir tipo de asiento y cuentas para reflejar “ingresos no declarados eliminados” cuando se limpia.

## Propuesta a definir

1. **Tipo de asiento:** Por ejemplo `CLEANED_PAYMENT` o `INCOME_NOT_DECLARED_ELIMINATION` en `AccountingEntry.EntryType`.
2. **Momento:** Crear el asiento en el mismo flujo que hace el PATCH a documentos (p. ej. en `DocumentBatchPatchSerializer.save()` cuando reconciliation_status=cleaned) o en un proceso posterior.
3. **Líneas del asiento:** Cuentas a debitar/acreditar y relación con el documento 100 y la categoría de limpieza (clean_category / clean_category_custom).
4. **Idempotencia:** Clave única por documento limpiado (p. ej. `cleaned_payment_{document_id}`) para no duplicar asientos.

Cuando esté definido, implementar en backend (modelo + lógica de creación de asiento) y, si aplica, exponer en el historial de conciliaciones.
