# Emisión de Boletas de Honorario por Autorización

## Resumen

**SÍ, se puede emitir una boleta de honorario por autorización usando las credenciales SII de una empresa.** El sistema está diseñado específicamente para esto.

## Cómo Funciona

### 1. Tipos de Credenciales

El sistema maneja dos tipos de credenciales SII:

- **`SII`**: Credencial estándar (usuario persona natural o empresa)
- **`sii_company`**: Credencial de empresa (usada para emisión por autorización)

### 2. Selección de Estrategia

Cuando se emite una boleta de honorario tipo **90** (terceros), el sistema automáticamente:

1. **Detecta el tipo de documento** en `IssueStrategySelector.get_strategy()`:
   ```python
   elif dte_code == "90":
       return StrategyIssueThirdPartyHonorary(document)
   ```

2. **Usa la estrategia específica** `StrategyIssueThirdPartyHonorary` que:
   - Retorna `"sii_company"` como tipo de credencial (línea 38)
   - Prepara los datos para emisión por terceros
   - Usa el manager `ThirdPartyHonoraryEmissionManager`

### 3. Obtención de Credenciales

En `StrategyIssueDocument.execute()` (líneas 93-97):

```python
credential_type = self._get_credential_type()  # Retorna "sii_company" para tipo 90
auth_manager, session = self.document.sender._get_auth_manager_with_session(
    credential_type=credential_type
)
```

El método `_get_auth_manager_with_session()` busca credenciales en este orden:

1. **Primero busca credencial `sii_company`** asociada a la entidad
2. Si no encuentra, puede hacer fallback a credencial `SII` (según configuración)

### 4. Modo Delegado (Autorización)

El sistema detecta automáticamente si debe usar **modo delegado** cuando:

- El RUT de la credencial (`credential.user`) ≠ RUT de la empresa (`entity.tax_id`)
- O cuando `auth_manager.rut` ≠ `auth_manager.company_rut`

Esto se verifica en `apps/scrapers/sii/utils/delegated_mode.py`:

```python
def needs_delegated_mode(credential=None, entity=None, auth_manager=None):
    """
    Determina si se debe usar modo delegado (emisión por tercero).
    
    Modo delegado se activa cuando:
    - credential.user (RUT del dueño de la credencial) != entity.tax_id (RUT de la empresa)
    """
```

### 5. Flujo Completo de Emisión

```
1. Usuario solicita emitir boleta tipo 90
   ↓
2. IssueStrategySelector detecta tipo 90
   ↓
3. Retorna StrategyIssueThirdPartyHonorary
   ↓
4. StrategyIssueThirdPartyHonorary._get_credential_type() retorna "sii_company"
   ↓
5. StrategyIssueDocument.execute() obtiene credencial sii_company
   ↓
6. MasterEntity._get_auth_manager_with_session(credential_type="sii_company")
   ↓
7. AuthService busca credencial tipo "sii_company" asociada a la entidad
   ↓
8. Si encuentra credencial sii_company, la usa
   ↓
9. Si no encuentra, puede hacer fallback a credencial SII (si está configurado)
   ↓
10. ThirdPartyHonoraryEmissionManager ejecuta la emisión
   ↓
11. El sistema detecta modo delegado si credential.user != entity.tax_id
   ↓
12. Se emite la boleta con los datos de autorización correctos
```

## Validación del Código

### Archivos Clave

1. **`apps/documents/strategies/issuers/strategy_issue_third_party_honorary.py`**
   - Línea 28-38: `_get_credential_type()` retorna `"sii_company"`
   - Línea 40-141: `_issue_document()` prepara y ejecuta la emisión

2. **`apps/documents/strategies/issuers/strategy_selector.py`**
   - Línea 140-144: Selecciona `StrategyIssueThirdPartyHonorary` para tipo 90

3. **`apps/documents/strategies/issuers/strategy_issue_document.py`**
   - Línea 93-97: Obtiene credencial usando el tipo retornado por la estrategia

4. **`apps/scrapers/sii/utils/delegated_mode.py`**
   - Línea 9-52: Detecta si debe usar modo delegado

5. **`apps/master_entities/services/auth_service.py`**
   - Línea 24-122: Obtiene credenciales según tipo (`sii` o `sii_company`)

### Tests que Validan el Funcionamiento

- `apps/documents/tests/unit/test_third_party_honorary_credentials.py`
  - Verifica que se usa credencial `sii_company` (no `SII`)
  - Línea 123-191: Test específico que valida el uso de `sii_company`

## Caso de Uso: Usuario 19615893-6 y Empresa GYN CONSULTORES SPA

Según la verificación realizada:

- ✅ Usuario **19615893-6** tiene credencial **VALID** (ID: 376)
- ✅ La credencial está asociada a **GYN CONSULTORES SPA** (77705822-3)
- ✅ La credencial es tipo **SII** (no `sii_company`)

**Para emitir boletas de honorario tipo 90 por autorización:**

1. La empresa GYN CONSULTORES SPA necesita tener una credencial tipo **`sii_company`**
2. Esta credencial debe estar asociada a la empresa
3. El sistema automáticamente usará esta credencial cuando se emita una boleta tipo 90
4. Si el RUT de la credencial es diferente al RUT de la empresa, se activará modo delegado

## Conclusión

**SÍ, el código está diseñado para emitir boletas de honorario por autorización usando credenciales SII de empresa.** El sistema:

1. ✅ Detecta automáticamente boletas tipo 90
2. ✅ Usa credenciales tipo `sii_company` (no `SII`)
3. ✅ Activa modo delegado cuando corresponde
4. ✅ Maneja la emisión por terceros correctamente

La única condición es que la empresa debe tener una credencial tipo `sii_company` asociada para que el sistema la use automáticamente.


