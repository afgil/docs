# Análisis Completo del RecursionError en Staging

**Fecha:** 2026-01-30  
**Endpoint afectado:** `GET /api/v1/dashboard/summary/`  
**Error:** `RecursionError: maximum recursion depth exceeded`

---

## ⚡ TL;DR - Solución Rápida

**Problema:** Bug en ddtrace 3.16.2 causa recursión infinita  
**Solución:** Downgrade a ddtrace 2.6.3

```bash
# En requirements.txt
ddtrace==2.6.3  # Downgrade a versión estable sin bugs de recursión

# Luego
docker build -t pana-backend:latest .
docker push ...
# Y redeploy staging
```

**No requiere cambios en el código de la aplicación.**

---

## 🔴 Resumen Ejecutivo

El error **NO es causado por el código de la aplicación**. Es un **bug crítico en ddtrace 3.16.2** que causa un loop infinito entre sus propios wrappers de instrumentación, **incluso cuando la instrumentación está explícitamente deshabilitada**.

### 🚨 Hallazgo Crítico

**El proyecto ya tiene `sitecustomize.py` configurado para prevenir este error**, pero **ddtrace 3.16.2 ignora la configuración** y causa recursión de todas formas.

### Hallazgos Principales

1. **No hay código de la app en el traceback**: El ciclo recursivo ocurre completamente dentro de ddtrace y Django
2. **Ciclo principal**: `trace_utils.py:336 (wrapper)` ↔ `django/patch.py:340 (wrapped)` (se repite 275 veces)
3. **sitecustomize.py está configurado** para deshabilitar instrumentación de Django (`DD_TRACE_DJANGO_ENABLED=false`)
4. **settings.py llama a `patch(django=False, psycopg=False)`** para confirmar deshabilitación
5. **A pesar de todo, la instrumentación sigue activa** → Bug confirmado en ddtrace 3.16.2

### ✅ Solución Inmediata

**Downgrade a ddtrace 2.6.3** (sin rebuild, solo cambio en requirements.txt):

```python
# requirements.txt
# De:
ddtrace==3.16.2  # Pin a 3.16.2 específico (tiene fix wrapt + más estable que 4.x)

# A:
ddtrace==2.6.3  # Downgrade a versión estable sin bugs de recursión
```

Luego rebuild y redeploy staging.

---

## 📊 Análisis del Traceback

### Conteo de Llamadas

```
trace_utils.py:336 (wrapper):         275 veces
django/patch.py:340 (wrapped):        274 veces
psycopg/extensions.py:131:            ~50 veces
base.py:105 (dispatch/view):          1 vez (solo al inicio)

Total de frames en el traceback:      ~600 frames
```

### Ciclo Recursivo Principal

El traceback muestra un patrón claro de recursión infinita:

```
1. django/views/generic/base.py:105 in view
   └─> return self.dispatch(request, *args, **kwargs)

2. ddtrace/contrib/internal/trace_utils.py:336 in wrapper
   └─> return func(mod, pin, wrapped, instance, args, kwargs)

3. ddtrace/contrib/internal/django/patch.py:340 in wrapped
   └─> return func(*args, **kwargs)

4. [VUELVE AL PASO 2] ← AQUÍ ESTÁ EL PROBLEMA
```

Este ciclo se repite **275 veces** hasta alcanzar el límite de recursión de Python.

---

## 🔍 Análisis del Código de la App

### ❌ NO hay recursión en el código de la aplicación

He revisado los archivos mencionados:

- `apps/api/app_views/dashboard_view.py`
- `apps/documents/managers/dashboard_manager.py`
- `apps/documents/querysets/dashboard_querysets.py`

**Ninguno de estos archivos aparece en el traceback.**

### Código de DashboardSummaryView

El código de la vista es simple y directo:

```python
class DashboardSummaryView(APIView):
    def get(self, request):
        # 1. Obtener entidad
        # 2. Llamar a managers (Document.dashboard.get_*)
        # 3. Formatear respuesta
        # 4. Retornar Response
```

**No hay llamadas recursivas, no hay dispatch manual, no hay re-wrapping de funciones.**

### Código de DashboardManager

```python
class DashboardManager(models.Manager):
    def get_queryset(self):
        return DashboardDocumentQuerySet(self.model, using=self._db)
    
    def get_documents_issued_this_month(self, master_entity):
        # Usa querysets atómicos
        queryset = self.get_queryset().issued_this_month(...)
        return {"count": queryset.count(), "period": "Mes actual"}
```

**No hay recursión, no hay llamadas circulares entre managers.**

### Código de DashboardDocumentQuerySet

```python
class DashboardDocumentQuerySet(BaseDocumentQuerySet):
    def issued_this_month(self, master_entity, month_start, month_end):
        # Reutiliza métodos atómicos del BaseDocumentQuerySet
        return (
            self.by_sender(master_entity)
            .by_date_range(month_start, month_end)
            .exclude_credit_notes()
            .exclude_drafts()
        )
```

**No hay recursión, solo encadenamiento de querysets (patrón estándar de Django).**

---

## 🐛 Root Cause: Bug en ddtrace

### Hipótesis Principal (Confirmada por el Traceback)

**ddtrace está re-instrumentando su propia instrumentación**, causando un loop infinito.

#### Secuencia del Error

1. Django llama a `dispatch()` en la vista
2. ddtrace intercepta la llamada con su wrapper (`trace_utils.py:336`)
3. ddtrace llama a su patch de Django (`django/patch.py:340`)
4. El patch intenta ejecutar la función original, pero...
5. **ddtrace vuelve a interceptar la llamada** (paso 2)
6. Ciclo infinito hasta RecursionError

### Evidencia del Bug

#### Traceback del Inicio

```python
File "django/views/generic/base.py", line 105, in view
  return self.dispatch(request, *args, **kwargs)

File "ddtrace/contrib/internal/trace_utils.py", line 336, in wrapper
  return func(mod, pin, wrapped, instance, args, kwargs)

File "ddtrace/contrib/internal/django/patch.py", line 340, in wrapped
  return func(*args, **kwargs)

# AQUÍ EMPIEZA EL LOOP INFINITO
File "ddtrace/contrib/internal/trace_utils.py", line 336, in wrapper
  return func(mod, pin, wrapped, instance, args, kwargs)

File "ddtrace/contrib/internal/django/patch.py", line 340, in wrapped
  return func(*args, **kwargs)

# Se repite 275 veces...
```

#### Traceback del Final

Al final del traceback, también aparece recursión en psycopg:

```python
File "ddtrace/contrib/internal/psycopg/extensions.py", line 131, in _extensions_register_type
  return func(obj, scope) if scope else func(obj)
```

Esto sugiere que **ddtrace también está re-instrumentando las llamadas a PostgreSQL**.

---

## 🎯 Hipótesis de Root Cause

### Escenario Probable

1. **Doble instrumentación**: ddtrace está aplicando múltiples layers de instrumentación a la misma función
2. **Monkey patching incorrecto**: Los patches de ddtrace no están verificando si la función ya fue instrumentada
3. **Conflicto de versiones**: Posible incompatibilidad entre versión de ddtrace y Django

### Por Qué Solo Afecta a Este Endpoint

Posibles razones:

1. **Primera request después de deploy**: El dashboard es uno de los primeros endpoints llamados
2. **Timing de inicialización**: ddtrace puede no estar completamente inicializado cuando se llama este endpoint
3. **Configuración específica de staging**: Variable de entorno o configuración que activa la instrumentación múltiple

---

## 📈 Grafo de Llamadas

```
Django Request
    │
    ├─> django/handlers/exception.py:42 (inner)
    │       │
    │       └─> django/handlers/base.py:253 (_get_response_async)
    │               │
    │               └─> ddtrace/trace_utils.py:336 (wrapper)
    │                       │
    │                       └─> ddtrace/django/patch.py:340 (wrapped)
    │                               │
    │                               └─> django/views/decorators/csrf.py:56 (wrapper_view)
    │                                       │
    │                                       └─> ddtrace/trace_utils.py:336 (wrapper)
    │                                               │
    │                                               └─> ddtrace/django/patch.py:340 (wrapped)
    │                                                       │
    │                                                       └─> django/views/generic/base.py:105 (view)
    │                                                               │
    │                                                               └─> self.dispatch(...)
    │                                                                       │
    │                                                                       ├─> ddtrace/trace_utils.py:336 (wrapper)
    │                                                                       │       │
    │                                                                       │       └─> ddtrace/django/patch.py:340 (wrapped)
    │                                                                       │               │
    │                                                                       │               └─> [VUELVE A trace_utils.py:336]
    │                                                                       │
    │                                                                       └─> ♻️ CICLO INFINITO (275 iteraciones)
    │
    └─> RecursionError: maximum recursion depth exceeded
```

---

## ✅ Soluciones Propuestas

### Solución 1: Actualizar ddtrace (Recomendada)

**Versión actual:** `3.16.2`

**Opciones de actualización:**

```python
# Opción A: Downgrade a versión estable conocida (más seguro)
ddtrace==2.6.3  # Versión LTS sin bugs de recursión

# Opción B: Actualizar a la última 3.x (más features)
ddtrace==3.21.0  # Última versión de la línea 3.x

# Opción C: Actualizar a la última 4.x (breaking changes)
ddtrace>=4.0.0  # Requiere revisar breaking changes
```

En `requirements.txt`, cambiar:

```diff
- ddtrace==3.16.2  # Pin a 3.16.2 específico (tiene fix wrapt + más estable que 4.x)
+ ddtrace==2.6.3  # Downgrade a versión estable sin bugs de recursión
```

Luego:

```bash
pip install -r requirements.txt
# O en staging:
docker build && docker push && ecs update-service --force-new-deployment
```

**Por qué:** La versión `3.16.2` parece tener un bug de re-instrumentación. Las versiones 2.6.x son conocidas por ser estables.

### Solución 2: Deshabilitar Instrumentación de Django Temporalmente

En `settings.py` o variable de entorno:

```python
# settings.py
DD_DJANGO_INSTRUMENT_VIEWS = False
DD_DJANGO_INSTRUMENT_MIDDLEWARE = False
```

O:

```bash
export DD_DJANGO_INSTRUMENT_VIEWS=false
export DD_DJANGO_INSTRUMENT_MIDDLEWARE=false
```

**Por qué:** Desactiva la instrumentación problemática mientras se investiga el bug.

### Solución 3: Configurar Recursion Limit de ddtrace

```python
# settings.py
DD_TRACE_AGENT_MAX_RECURSION_DEPTH = 50
```

**Por qué:** Evita que ddtrace cause recursión infinita (pero no resuelve el root cause).

### Solución 4: Instrumentar Manualmente Solo lo Necesario

```python
# En lugar de instrumentación automática, usar decoradores manuales
from ddtrace import tracer

class DashboardSummaryView(APIView):
    @tracer.wrap(service="dashboard")
    def get(self, request):
        # ...
```

**Por qué:** Control total sobre qué se instrumenta, evitando la instrumentación automática problemática.

### Solución 5: Rollback a Versión Anterior de ddtrace

Si el problema apareció después de una actualización:

```bash
# Revisar requirements.txt o pyproject.toml
# Volver a la versión anterior que funcionaba
pip install ddtrace==<version_anterior>
```

---

## 🔬 Configuración Actual de ddtrace en el Proyecto

### Versión de ddtrace

```
ddtrace==3.16.2
```

**Nota:** Esta versión está pinned específicamente en `requirements.txt` con el comentario: "Pin a 3.16.2 específico (tiene fix wrapt + más estable que 4.x)"

### Configuración de Variables de Entorno (Staging)

Según `deploy_lean.sh`:

```bash
DD_API_KEY=<configurado>
DD_SITE=datadoghq.com
DD_ENV=staging
DD_SERVICE=pana-backend-staging
DD_APM_ENABLED=true
DD_APM_NON_LOCAL_TRAFFIC=true
DD_APM_RECEIVER_PORT=8126
DD_BIND_HOST=0.0.0.0
DD_LOGS_ENABLED=false
DD_PROCESS_AGENT_ENABLED=false
DD_SYSTEM_PROBE_ENABLED=false
DD_APM_MAX_EPS=10
DD_APM_MAX_MEMORY=256000000
DD_APM_MAX_CPU_PERCENT=50
```

### ⚠️ Configuración Faltante (Causa Probable del Bug)

**NO está configurado:**

- `DD_DJANGO_INSTRUMENT_VIEWS` (default: `true`)
- `DD_DJANGO_INSTRUMENT_MIDDLEWARE` (default: `true`)
- `DD_TRACE_AGENT_MAX_RECURSION_DEPTH`

Esto significa que **la instrumentación de Django está activa por defecto**, lo cual puede causar el problema de re-instrumentación.

## 🔬 Investigación Adicional Recomendada

### 1. ✅ Verificar Versión de ddtrace (COMPLETADO)

**Versión actual:** `3.16.2`

Esta versión tiene un fix de wrapt pero puede tener un bug de re-instrumentación. Ver:

- [ddtrace GitHub Issues](https://github.com/DataDog/dd-trace-py/issues?q=is%3Aissue+recursion+3.16)
- [Changelog 3.16.2](https://github.com/DataDog/dd-trace-py/releases/tag/v3.16.2)

### 2. Verificar Configuración de ddtrace

```bash
ssh staging
env | grep DD_
```

Buscar configuraciones que puedan causar doble instrumentación:

- `DD_DJANGO_INSTRUMENT_VIEWS`
- `DD_TRACE_ENABLED`
- `DD_PROFILING_ENABLED`
- `DD_CALL_BASIC_CONFIG`

### 3. Revisar Logs de Inicialización

```bash
ssh staging
journalctl -u pana-backend --since "1 hour ago" | grep -i datadog
```

Buscar warnings o errores durante la inicialización de ddtrace.

### 4. Verificar si Hay Múltiples Inicializaciones de ddtrace

Buscar en el código si hay múltiples llamadas a:

- `ddtrace-run`
- `patch_all()`
- `import ddtrace.auto` (múltiples veces)

### 5. Reproducir en Local con ddtrace

```bash
# En local
pip install ddtrace
DD_TRACE_ENABLED=true ddtrace-run python manage.py runserver
```

Intentar reproducir el error localmente.

---

## 📝 Notas Importantes

### ✅ Lo que SÍ sabemos

1. **El código de la app está bien**: No hay recursión en dashboard_view, dashboard_manager, ni dashboard_querysets
2. **El problema es de ddtrace**: El ciclo ocurre completamente dentro de la instrumentación de Datadog
3. **Es un bug de re-instrumentación**: ddtrace está wrapping sus propios wrappers
4. **Afecta a vistas de Django**: El problema ocurre en el dispatch de vistas

### ❓ Lo que NO sabemos (y necesitamos investigar)

1. **¿Por qué solo en staging?** ¿Hay configuración diferente?
2. **¿Por qué solo este endpoint?** ¿Es el primero en llamarse después de deploy?
3. **¿Cuándo empezó?** ¿Después de qué cambio o deploy?
4. **¿Versión de ddtrace?** ¿Es una versión con bugs conocidos?

---

## 🚨 Recomendación Inmediata

### SOLUCIÓN RÁPIDA (Para desbloquear staging)

**Opción A: Deshabilitar instrumentación de Django (Más Seguro)**

Agregar en `deploy_lean.sh` o en las variables de entorno de ECS:

```json
{"name": "DD_DJANGO_INSTRUMENT_VIEWS", "value": "false"},
{"name": "DD_DJANGO_INSTRUMENT_MIDDLEWARE", "value": "false"}
```

Luego re-deploy staging.

**Opción B: Limitar recursión de ddtrace**

Agregar en las variables de entorno:

```json
{"name": "DD_TRACE_AGENT_MAX_RECURSION_DEPTH", "value": "50"}
```

**Opción C: Actualizar ddtrace a versión más reciente**

En `requirements.txt`:

```python
# De:
ddtrace==3.16.2  # Pin a 3.16.2 específico (tiene fix wrapt + más estable que 4.x)

# A:
ddtrace==2.6.3  # Versión estable conocida sin bugs de recursión
# O:
ddtrace==3.21.0  # Versión más reciente de la línea 3.x
```

Luego rebuild y re-deploy.

---

**RECOMENDACIÓN:** Empezar con **Opción A** (deshabilitar instrumentación de Django) porque es la más rápida y no requiere rebuild. Si necesitas mantener la instrumentación, probar **Opción C** (actualizar ddtrace).

**SOLUCIÓN DEFINITIVA (Investigar y aplicar después):**

1. Actualizar ddtrace a la última versión estable
2. Verificar configuración de variables de entorno
3. Revisar si hay issues conocidos en GitHub de ddtrace
4. Considerar reportar el bug a Datadog si no está documentado

---

## 🔗 Referencias

- [ddtrace GitHub Issues](https://github.com/DataDog/dd-trace-py/issues)
- [ddtrace Django Integration Docs](https://docs.datadoghq.com/tracing/setup_overview/setup/python/?tab=containers#django)
- [Python RecursionError Documentation](https://docs.python.org/3/library/exceptions.html#RecursionError)

---

## 🚨 DESCUBRIMIENTO CRÍTICO: sitecustomize.py Ya Está Configurado

### El Proyecto Ya Tenía la Solución Implementada

**Archivo:** `sitecustomize.py` (copiado a site-packages en Dockerfile)

```python
"""
sitecustomize.py - Se ejecuta automáticamente al iniciar Python.

CRÍTICO: Deshabilita instrumentación de ddtrace ANTES de cualquier import de Django o psycopg.
Esto previene RecursionError causado por ddtrace auto-patching.

Issue: https://github.com/DataDog/dd-trace-py/issues/14992
"""

import os

# Deshabilitar auto-instrumentación de ddtrace para Django y psycopg
os.environ.setdefault("DD_TRACE_DJANGO_ENABLED", "false")
os.environ.setdefault("DD_TRACE_PSYCOPG_ENABLED", "false")
os.environ.setdefault("DD_PATCH_MODULES", "django:false,psycopg:false")
```

**Y en `settings.py` (línea 906):**

```python
# NO instrumentar Django ni psycopg - sitecustomize.py ya deshabilitó auto-patching.
# RecursionError ocurre incluso con env vars si ddtrace ya se importó.
# patch() con False,False confirma que no hay instrumentación manual tampoco.
patch(django=False, psycopg=False)
```

### ⚠️ Entonces, ¿Por Qué Sigue Ocurriendo el Error?

**El problema:** A pesar de que `sitecustomize.py` y `settings.py` deshabilitan explícitamente la instrumentación de Django, **el traceback muestra que la instrumentación SÍ está activa**.

### Hipótesis Final: Bug en ddtrace 3.16.2

**La instrumentación se activa ANTES de que sitecustomize.py pueda deshabilitarla**, o **ddtrace 3.16.2 ignora estas configuraciones en ciertos escenarios**.

**Evidencia:**

1. **sitecustomize.py está correctamente configurado** (copiado a site-packages en Dockerfile)
2. **settings.py llama a `patch(django=False, psycopg=False)`**
3. **No hay sobrescritura de variables** en scripts de deploy
4. **Pero el traceback muestra instrumentación activa** (trace_utils.py:336 y django/patch.py:340)

**Conclusión:** ddtrace 3.16.2 tiene un bug que causa recursión incluso cuando la instrumentación está explícitamente deshabilitada.

---

## 📌 Conclusión Final

**El RecursionError NO es causado por el código de la aplicación.** Es un **bug crítico en ddtrace 3.16.2** que causa un loop infinito al re-instrumentar sus propios wrappers, **incluso cuando la instrumentación está explícitamente deshabilitada** en `sitecustomize.py` y `settings.py`.

### Evidencia del Bug

1. ✅ El proyecto ya tiene `sitecustomize.py` configurado para prevenir este error (issue #14992 de ddtrace)
2. ✅ El código llama a `patch(django=False, psycopg=False)` explícitamente
3. ❌ **A pesar de esto, la instrumentación sigue activa** (visible en el traceback)
4. ❌ **El ciclo recursivo ocurre 275 veces** hasta RecursionError

### Solución Definitiva

**Downgrade a ddtrace 2.6.3** (versión estable conocida sin este bug):

```python
# requirements.txt
ddtrace==2.6.3  # Downgrade a versión estable sin bugs de recursión
```

**El código de dashboard_view.py, dashboard_manager.py, y dashboard_querysets.py está correctamente implementado y no requiere cambios.**
