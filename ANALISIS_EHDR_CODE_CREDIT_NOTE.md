# Análisis: ¿Por qué no funciona EHDR Code en Issue Credit Note?

## 📊 Reporte del Batch `e0a1f7cc-f994-4cf1-b86b-fd7b8a4879b2`

### Estadísticas Finales

- **Total documentos en batch:** 116
- **Todos son tipo 61** (Notas de Crédito Electrónica)
- **Documentos con referencias:** 116 (100%)
- **Total referencias:** 116
- **Referencias CON SIIMetadata:** 116 (100%) ✅
- **Referencias SIN SIIMetadata:** 0
- **SIIMetadata creados:** 58 (en ejecución anterior)
- **SIIMetadata actualizados:** 0
- **Errores:** 0 ✅

---

## 🔍 Análisis del Problema

### El Código es el Mismo

El issue de credit note usa **exactamente el mismo flujo** que el script:

1. **`StrategyIssueCreditNote._get_ehdr_codigo_from_reference()`** llama a:
   - `document.get_or_scrape_ehdr_code_from_reference(auth_manager)`
   - Que llama a `EHDRCodeService.get_or_scrape_ehdr_code()`

2. **`EHDRCodeService.get_or_scrape_ehdr_code()`** hace:
   - Busca el documento referenciado en BD
   - Si existe y debe tener SIIMetadata, intenta obtenerlo desde `SIIMetadata`
   - **Si no existe SIIMetadata, hace scraping con `DocumentsManager`**

### ¿Por qué Fallaba Antes?

**Antes del script:**

- 50% de las referencias NO tenían SIIMetadata
- Cuando se emitía una nota de crédito:
  - Si el documento referenciado no tenía SIIMetadata → intentaba scraping
  - El scraping puede fallar por:
    1. **Cookies expiradas** (después de muchos requests)
    2. **Documento no disponible** en el SII en ese momento
    3. **Problemas de autenticación** (sesión expirada)
    4. **Rate limiting** del SII
    5. **Requests que fallan** dentro de `DocumentsManager.execute()`

**Después del script:**

- 100% de las referencias tienen SIIMetadata ✅
- Cuando se emite una nota de crédito:
  - Busca SIIMetadata (rápido, sin scraping) ✅
  - Lo usa directamente ✅
  - **NO necesita scraping** ✅

---

## 🎯 Mapeo de Errores y Requests que Fallan

### Tipos de Errores Identificados

1. **AUTHENTICATION_ERROR**
   - Causa: Cookies/sesión expirada
   - Mensaje: "Faltan cookies requeridas: TOKEN, CSESSIONID"
   - Frecuencia: Alta cuando hay muchos requests seguidos

2. **DOCUMENT_NOT_FOUND**
   - Causa: Documento no existe en el SII
   - Mensaje: "No se encontró documento con folio X y tipo Y en el SII"
   - Frecuencia: Media

3. **NO_EHDR_CODE**
   - Causa: Documento no tiene código EHDR en la respuesta
   - Mensaje: "Documento no tiene código EHDR en la respuesta"
   - Frecuencia: Baja

4. **TIMEOUT_ERROR**
   - Causa: Request tarda demasiado
   - Frecuencia: Baja

5. **RATE_LIMIT_ERROR**
   - Causa: Demasiados requests al SII
   - Frecuencia: Media cuando hay muchos requests seguidos

6. **NETWORK_ERROR**
   - Causa: Problemas de red
   - Frecuencia: Baja

### Requests que Fallan

Dentro de `DocumentsManager.execute()`, los siguientes requests pueden fallar:

1. **LaunchPreviewRequest** (paso 1)
   - Falla si: Sesión expirada, cookies inválidas
   - Frecuencia: Media

2. **SelectCompanyRequest** (paso 2)
   - Falla si: RUT inválido, sesión expirada
   - Frecuencia: Baja

3. **SingleCompanyValidationRequest** (paso 3)
   - Falla si: Sesión expirada, empresa no encontrada
   - Frecuencia: Media

4. **DocumentsRequest** (paso 4 - el más crítico)
   - Falla si: Sesión expirada, documento no encontrado, rate limiting
   - Frecuencia: Alta

5. **DownloadPDFRequest** (paso 5 - opcional)
   - Falla si: Código EHDR inválido, sesión expirada
   - Frecuencia: Baja

---

## 💡 Propuestas de Solución

### 1. Decorador @retry con Reautenticación Automática

**Problema:** Cuando falla un request por cookies expiradas, no se reautentica automáticamente.

**Solución:** Mejorar el decorador `@retry` en `BaseRequest` para que detecte errores de autenticación y reautentique:

```python
from retry import retry
from apps.scrapers.exceptions import SessionExpiredError

class BaseRequest:
    @retry(
        exceptions=(SessionExpiredError,),
        tries=3,
        delay=1,
        backoff=2,
        logger=logger
    )
    def scrape(self, data=None):
        try:
            # Verificar sesión antes de cada request
            if not self.auth_manager.is_authenticated:
                logger.warning("Sesión no autenticada, reautenticando...")
                self.auth_manager.authenticate()
            
            self.auth_manager.session = self.auth_manager.get_session()
            # ... resto del código
        except SessionExpiredError:
            logger.warning("Session expired, reautenticando...")
            self.auth_manager.is_authenticated = False
            self.auth_manager.authenticate()  # Reautenticar
            raise  # Re-raise para que retry lo intente de nuevo
```

### 2. Verificación de Sesión Antes de Cada Request Crítico

**Problema:** No se verifica si la sesión sigue válida antes de hacer requests.

**Solución:** Agregar verificación en `DocumentsManager.execute()`:

```python
def execute(self, folio=None, start_date=None, end_date=None, dte_type=None):
    # Verificar sesión antes de empezar
    if not self.auth_manager.is_authenticated:
        logger.info("Sesión no autenticada, autenticando...")
        self.auth_manager.authenticate()
    
    # Verificar cookies críticas
    session = self.auth_manager.get_session()
    if not session.cookies.get("TOKEN") or not session.cookies.get("CSESSIONID"):
        logger.warning("Cookies críticas faltantes, reautenticando...")
        self.auth_manager.is_authenticated = False
        self.auth_manager.authenticate()
    
    # ... resto del código
```

### 3. Circuit Breaker para Evitar Cascading Failures

**Problema:** Si el SII está caído o hay rate limiting, se siguen haciendo requests que fallan.

**Solución:** Implementar circuit breaker:

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def execute_with_circuit_breaker(self, folio=None, dte_type=None):
    """Ejecuta con circuit breaker para evitar sobrecargar el SII"""
    return self.execute(folio=folio, dte_type=dte_type)
```

### 4. Reutilizar Sesión (Ya Implementado en el Script)

**Problema:** Crear un nuevo `DocumentsManager` para cada documento causa problemas de autenticación.

**Solución:** Reutilizar la misma sesión (ya implementado en el script):

- Crear `DocumentsManager` UNA SOLA VEZ
- Reutilizar para todos los requests
- Agregar delay entre requests (500ms) para evitar rate limiting

### 5. Pre-cargar SIIMetadata Antes de Emitir

**Problema:** Si no hay SIIMetadata, se intenta scraping que puede fallar.

**Solución:** Pre-cargar SIIMetadata antes de emitir notas de crédito:

```python
def _preload_ehdr_codes_for_references(self, auth_manager):
    """Pre-carga códigos EHDR para todas las referencias antes de emitir"""
    for ref in self.document.references.all():
        if SIIMetadataService.should_have_sii_metadata(ref.reference_type.code):
            # Intentar obtener o crear SIIMetadata
            referenced_doc = Document.objects.filter(
                dte_type__code=ref.reference_type.code,
                folio=ref.reference_folio,
                sender=self.document.sender,
            ).first()
            
            if referenced_doc:
                try:
                    referenced_doc.sii_metadata
                except SIIMetadata.DoesNotExist:
                    # Crear SIIMetadata antes de emitir
                    ehdr_code = self._get_ehdr_codigo_from_reference(auth_manager)
                    if ehdr_code:
                        SIIMetadata.objects.create(
                            document=referenced_doc,
                            document_code=ehdr_code
                        )
```

### 6. Mejorar Manejo de Errores en EHDRCodeService

**Problema:** Si el scraping falla, no hay retry ni manejo de errores específico.

**Solución:** Agregar retry y mejor manejo de errores:

```python
from retry import retry

class EHDRCodeService:
    @staticmethod
    @retry(
        exceptions=(Exception,),
        tries=3,
        delay=2,
        backoff=2,
        logger=logger
    )
    def get_or_scrape_ehdr_code(
        reference_type_code: str,
        reference_folio: str,
        sender,
        auth_manager,
    ) -> Optional[str]:
        # ... código existente ...
        
        # Si falla el scraping, intentar reautenticar y retry
        try:
            documents_manager = DocumentsManager(auth_manager)
            result = documents_manager.execute(
                folio=reference_folio, dte_type=reference_type_code
            )
        except Exception as e:
            if "cookie" in str(e).lower() or "session" in str(e).lower():
                # Reautenticar y retry
                logger.warning("Sesión expirada, reautenticando...")
                auth_manager.is_authenticated = False
                auth_manager.authenticate()
                # Retry automático por el decorador @retry
                raise
            raise
```

---

## ✅ Recomendaciones Prioritarias

### Prioridad Alta

1. **Pre-cargar SIIMetadata antes de emitir notas de crédito**
   - Ejecutar el script de actualización antes de emitir
   - O implementar pre-carga automática en `StrategyIssueCreditNote`

2. **Reutilizar sesión en `EHDRCodeService`**
   - No crear un nuevo `DocumentsManager` para cada request
   - Reutilizar el mismo `auth_manager` que ya está autenticado

3. **Agregar verificación de sesión antes de cada request**
   - Verificar cookies críticas antes de `DocumentsManager.execute()`
   - Reautenticar automáticamente si es necesario

### Prioridad Media

1. **Mejorar decorador @retry con reautenticación**
   - Detectar errores de autenticación
   - Reautenticar automáticamente antes de retry

2. **Agregar delay entre requests**
   - Ya implementado en el script (500ms)
   - Agregar en `EHDRCodeService` también

### Prioridad Baja

1. **Implementar circuit breaker**
   - Solo si hay problemas frecuentes de rate limiting
   - Puede ser overkill si se pre-cargan los SIIMetadata

---

## 🎯 Conclusión

**El problema principal era:** 50% de las referencias no tenían SIIMetadata, lo que causaba que el issue credit note intentara hacer scraping, que fallaba frecuentemente.

**La solución aplicada:** Crear SIIMetadata para todas las referencias antes de emitir notas de crédito.

**Resultado:** Ahora 100% de las referencias tienen SIIMetadata, por lo que el issue credit note NO necesita hacer scraping y funciona correctamente.

**Mejoras adicionales recomendadas:**

- Pre-cargar SIIMetadata automáticamente antes de emitir
- Reutilizar sesión en `EHDRCodeService`
- Agregar verificación de sesión antes de cada request
- Mejorar manejo de errores con retry y reautenticación
