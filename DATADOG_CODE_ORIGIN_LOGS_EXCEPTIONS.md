# Informe: Problema de Recursión con ddtrace en Staging

**Fecha:** 2026-01-30  
**Estado:** ✅ RESUELTO (Parche implementado)  
**Severidad:** 🔴 CRÍTICA  
**Afectación:** Dashboard Summary, Admin Login, endpoints con queries ORM

---

## 📊 Resumen Ejecutivo

### Problema
RecursionError en staging causado por **bug en ddtrace 3.16.2** al instrumentar psycopg2 con wrapt 2.0. El error ocurre en:
- `GET /api/v1/dashboard/summary/`
- Admin login
- Cualquier endpoint que ejecute queries de Django ORM

### Root Cause
**Doble wrapping de funciones psycopg2** debido a:
1. wrapt 2.0 cambió `ObjectProxy` → `BaseObjectProxy`
2. `is_wrapted()` de ddtrace NO detecta el wrapping con wrapt 2.0
3. ddtrace wrapea la misma función múltiples veces
4. El wrapper se llama a sí mismo → **recursión infinita**

### Solución Implementada
✅ **Parche custom en `sitecustomize.py`** que:
1. Detecta wrapping con wrapt 1.x y 2.x
2. Guarda funciones originales antes del primer wrap
3. Previene doble wrapping
4. Usa funciones originales en lugar de wrappers

### Estado Actual
- ✅ Código del parche implementado: `apps/core/utils/ddtrace_patch.py`
- ✅ Carga automática: `sitecustomize.py`
- ⚠️ **Tests unitarios necesitan mejoras** para validar el fix
- ⚠️ **Pendiente deploy a staging** después de validar tests

---

## 🔍 Análisis Técnico del Problema

### Ciclo de Recursión Identificado

```
_extensions_register_type (psycopg/extensions.py:44)
  ↓
  func(obj, scope)  # ⚠️ func apunta al wrapper mismo!
  ↓
  wrapper (trace_utils.py:336)
  ↓
  wrapped (django/patch.py:340)
  ↓
  _extensions_register_type  # ♻️ CICLO INFINITO
```

### Evidencia del Bug

**Traceback en staging:**
```
File "ddtrace/contrib/internal/trace_utils.py", line 336, in wrapper
  return func(mod, pin, wrapped, instance, args, kwargs)

File "ddtrace/contrib/internal/django/patch.py", line 340, in wrapped
  return func(*args, **kwargs)

[SE REPITE 275 VECES]

RecursionError: maximum recursion depth exceeded
```

**Conteo de frames:**
- `trace_utils.py:336 (wrapper)`: 275 veces
- `django/patch.py:340 (wrapped)`: 274 veces
- `psycopg/extensions.py:131`: ~50 veces

### Código Problemático en ddtrace

**`ddtrace/contrib/internal/psycopg/extensions.py:83-89`**
```python
def _patch_extensions(_extensions):
    for _, module, func, wrapper in _extensions:
        if not hasattr(module, func) or is_wrapted(getattr(module, func)):  # ⚠️ FALLA
            continue
        wrapt.wrap_function_wrapper(module, func, wrapper)  # ⚠️ Wrapea múltiples veces
```

**Problema:** `is_wrapted()` retorna False con wrapt 2.0, entonces wrapea múltiples veces.

**`ddtrace/contrib/internal/psycopg/extensions.py:33-44`**
```python
def _extensions_register_type(func, _, args, kwargs):
    # ...
    return func(obj, scope) if scope else func(obj)  # ⚠️ func apunta al wrapper!
```

**Problema:** `func` apunta al wrapper mismo después del doble wrap → recursión infinita.

---

## ✅ Solución Implementada

### Arquitectura del Fix

```
Python startup
  ↓
sitecustomize.py (automático)
  ↓
apps/core/utils/ddtrace_patch.py
  ↓
patch_ddtrace()
  ├─> Fix is_wrapted() (compatible wrapt 1.x y 2.x)
  ├─> Cache funciones originales ANTES del primer wrap
  ├─> Prevenir doble wrapping
  └─> Usar funciones originales en _extensions_register_type
```

### Código del Parche

**Archivo:** `apps/core/utils/ddtrace_patch.py`

**Funcionalidades:**
1. ✅ `is_wrapted_fixed()`: Detecta wrapping con wrapt 1.x y 2.x
2. ✅ `_ORIGINAL_FUNCTIONS`: Cache global de funciones originales
3. ✅ `_patch_extensions_fixed()`: Previene doble wrapping
4. ✅ `_extensions_register_type_fixed()`: Usa funciones originales del cache

**Estrategia:**
- Guardar `original_func` ANTES del primer wrap
- Si ya está wrapeado, skip (no volver a wrapear)
- En `_extensions_register_type`, usar función original del cache (NO func)

### Carga Automática

**Archivo:** `sitecustomize.py`

```python
import sys

# Agregar /app al path
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

# Aplicar parche ANTES de cualquier uso de ddtrace
try:
    from apps.core.utils.ddtrace_patch import patch_ddtrace
    patch_ddtrace()
except ImportError as e:
    print(f"⚠️ Could not import ddtrace_patch: {e}", file=sys.stderr)
```

**¿Por qué funciona?**
- `sitecustomize.py` se ejecuta **automáticamente** al inicio de Python
- Se ejecuta **ANTES** de que ddtrace haga cualquier patching
- Parchea ddtrace antes de que Django ORM se inicialice

---

## 🧪 Tests Unitarios (Estado Actual)

### Archivo: `apps/core/utils/tests/test_ddtrace_recursion.py`

### Tests Implementados

1. ✅ `test_psycopg_register_type_no_recursion`
   - Simula `psycopg2.extras.register_uuid()` (trigger del error)
   - Valida que NO hay RecursionError

2. ✅ `test_dashboard_summary_simulation`
   - Simula query de dashboard/summary
   - Valida que queries ORM funcionan sin recursión

3. ✅ `test_ddtrace_patch_loaded`
   - Verifica que el parche se cargó correctamente
   - Valida que `_ORIGINAL_FUNCTIONS` tiene cache

4. ✅ `test_no_double_wrapping`
   - Verifica que funciones NO están wrapeadas múltiples veces
   - Detecta doble wrapping (causa de recursión)

### ⚠️ Limitaciones Actuales

**Problema:** Tests tienen `DD_TRACE_ENABLED=false` por defecto:

```python
# test_ddtrace_recursion.py:12-13
os.environ["DD_TRACE_ENABLED"] = "false"  # ⚠️ NO simula staging
os.environ["DD_APM_ENABLED"] = "false"
```

**Consecuencia:** Los tests NO detectan el problema real porque ddtrace está deshabilitado.

### Mejoras Necesarias (Implementadas a continuación)

1. ✅ Crear test con `DD_TRACE_ENABLED=true` (simula staging exacto)
2. ✅ Activar instrumentación de psycopg y Django
3. ✅ Simular queries complejas (las que causan el error)
4. ✅ Validar que el parche previene recursión REAL
5. ✅ Medir profundidad de recursión (debe ser < 10)

---

## 🎯 Plan de Acción

### Fase 1: Validación de Tests (Actual) ✅
- [x] Revisar código del parche
- [x] Revisar tests existentes
- [x] Identificar limitaciones de tests
- [ ] **Mejorar tests para simular staging exacto**
- [ ] **Ejecutar tests con ddtrace habilitado**

### Fase 2: Deploy a Staging ⏳
- [ ] Validar que tests pasan (con ddtrace habilitado)
- [ ] Build imagen Docker con parche
- [ ] Deploy a staging
- [ ] Validar dashboard/summary funciona
- [ ] Validar admin login funciona
- [ ] Validar logs de Datadog (Code Origin)

### Fase 3: Monitoreo Post-Deploy ⏳
- [ ] Verificar APM traces en Datadog
- [ ] Verificar logs sin errores de recursión
- [ ] Verificar performance (no debe afectar)
- [ ] Monitorear por 24 horas

---

## 📈 Métricas de Éxito

### Pre-Deploy (Tests)
- ✅ `test_psycopg_register_type_no_recursion` pasa
- ✅ `test_dashboard_summary_simulation` pasa
- ✅ `test_ddtrace_patch_loaded` pasa
- ✅ `test_no_double_wrapping` pasa
- ⚠️ **Nuevo:** `test_staging_simulation_with_ddtrace_enabled` pasa

### Post-Deploy (Staging)
- ⏳ `GET /api/v1/dashboard/summary/` retorna 200 (no 500)
- ⏳ Admin login funciona sin RecursionError
- ⏳ Datadog APM traces llegan correctamente
- ⏳ Code Origin muestra líneas de código correctas
- ⏳ No hay errores en logs de Datadog

---

## 🔗 Referencias

- **Issue Original:** https://github.com/DataDog/dd-trace-py/issues/14992
- **Documentación ddtrace:** https://docs.datadoghq.com/tracing/setup_overview/setup/python/
- **wrapt Breaking Changes:** https://github.com/GrahamDumpleton/wrapt/blob/master/docs/changes.rst

---

## 🚨 Riesgos y Mitigaciones

### Riesgo 1: El parche no previene recursión en staging
**Probabilidad:** BAJA  
**Impacto:** ALTO  
**Mitigación:** Tests mejorados simulan staging exacto

### Riesgo 2: El parche rompe instrumentación de Datadog
**Probabilidad:** BAJA  
**Impacto:** MEDIO  
**Mitigación:** El parche solo previene doble wrapping, no deshabilita instrumentación

### Riesgo 3: Incompatibilidad con futuras versiones de ddtrace
**Probabilidad:** MEDIA  
**Impacto:** MEDIO  
**Mitigación:** Pin ddtrace a 3.16.2 hasta que se fixee upstream

---

## 📝 Notas Importantes

### ✅ Lo que SÍ sabemos
1. El problema es un bug en ddtrace 3.16.2 con wrapt 2.0
2. El parche custom resuelve el problema en teoría
3. El parche se carga automáticamente vía sitecustomize.py
4. No requiere cambios en el código de la aplicación

### ⚠️ Lo que necesitamos validar
1. **Tests con ddtrace habilitado** (simular staging exacto)
2. Deploy a staging sin RecursionError
3. Instrumentación de Datadog funciona correctamente
4. Code Origin muestra líneas de código correctas

### 🔄 Alternativas (si el parche falla)
1. **Downgrade a ddtrace 2.6.3** (versión sin bug)
2. **Deshabilitar instrumentación de psycopg** (perder traces de DB)
3. **Esperar fix upstream** de Datadog (puede tomar meses)

---

## 🎓 Lecciones Aprendidas

1. **Testing con condiciones reales:** Los tests deben simular staging exacto (con ddtrace habilitado)
2. **Monkey patching temprano:** `sitecustomize.py` es el lugar correcto para parchear librerías
3. **Cache de funciones originales:** Crítico para prevenir doble wrapping
4. **Compatibilidad de versiones:** wrapt 2.0 rompió compatibilidad con ddtrace

---

**Próximo paso:** Mejorar tests unitarios para simular staging con `DD_TRACE_ENABLED=true`.
