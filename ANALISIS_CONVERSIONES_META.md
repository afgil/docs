# Análisis: Cómo se Calculan las Conversiones en Meta Ads

## 📊 Métricas Actuales

```
Impresiones: 3.412
Clics: 52
Costo Total: $12.474 CLP
CPC Promedio: $240 CLP
CTR: 1.52%
Conversiones: 28
Tasa Conversión: 53.85% ⚠️ (ANORMALMENTE ALTA)
```

## 🔍 Problema Principal

**La tasa de conversión del 53.85% es anormalmente alta.** Esto indica que Meta está contando múltiples eventos como conversiones, no solo el evento final de registro.

### ¿Por qué está pasando esto?

Meta cuenta como conversión **cualquier evento que esté configurado como "conversión" en el pixel**. Si tienes configurados múltiples eventos (ViewContent, Lead, CompleteRegistration), cada uno cuenta como una conversión separada.

## 📍 Eventos que se Están Disparando

### 1. **ViewContent** (Landing Page View)
- **Dónde**: `trackMetaAdsLandingPage.ts` (línea 87)
- **Cuándo**: Cuando alguien llega a la landing page desde Meta Ads
- **Problema**: Este evento NO debería contar como conversión, solo como engagement

```typescript
// pana-frontend/src/utils/trackMetaAdsLandingPage.ts:87
window.fbq('track', 'ViewContent', eventData);
```

### 2. **Lead** (Start_Onboarding)
- **Dónde**: `trackStartOnboarding.ts` (línea 99)
- **Cuándo**: Cuando hacen click en "Empezar gratis"
- **Problema**: Este evento se dispara ANTES del registro completo

```typescript
// pana-frontend/src/utils/trackStartOnboarding.ts:99
window.fbq('track', 'Lead', {
  content_name: 'Start_Onboarding',
  content_category: 'Onboarding',
});
```

### 3. **Start_Onboarding** (Custom Event)
- **Dónde**: `trackStartOnboarding.ts` (línea 110)
- **Cuándo**: Mismo momento que Lead
- **Problema**: Evento duplicado que también puede estar configurado como conversión

```typescript
// pana-frontend/src/utils/trackStartOnboarding.ts:110
window.fbq('trackCustom', 'Start_Onboarding', {
  content_name: 'Start_Onboarding',
  content_category: 'Onboarding',
});
```

### 4. **CompleteRegistration** (Múltiples Disparos)
- **Dónde 1**: `PasswordStep.tsx` (línea 140) - Cuando completan el password
- **Dónde 2**: `SIICredentialSetup.tsx` (línea 132) - Cuando configuran credenciales SII
- **Dónde 3**: Backend `OnboardingFinalView` (línea 773) - Cuando finalizan onboarding
- **Problema**: Se dispara 3 veces por usuario, causando conversiones duplicadas

## 🐛 Problemas Técnicos Identificados

### 1. **Falta de Deduplicación en Frontend**

El código del frontend NO envía `event_id` para deduplicación:

```typescript
// pana-frontend/src/utils/trackMetaAdsConversion.ts:159
trackMetaPixelEvent(eventName, pixelEventData);
// ❌ No incluye event_id para deduplicación
```

Solo el backend envía `event_id` cuando usa Conversions API directamente:

```python
# pana-backend/apps/users/views.py:751
event_id = hashlib.md5(
    f"{user.id}_{user.email}_{int(time.time())}".encode()
).hexdigest()
```

### 2. **Pixel IDs Diferentes**

- **Frontend**: `1237273991099108` (configurado en `thirdPartyScripts.ts:445`)
- **Backend fallback**: `434002501581257` (configurado en `meta_conversions_api.py:92`)

Esto puede causar problemas de atribución si ambos pixels están activos.

### 3. **Múltiples Disparos de CompleteRegistration**

Un mismo usuario puede disparar `CompleteRegistration` hasta 3 veces:
1. En `PasswordStep` cuando completa el password
2. En `SIICredentialSetup` cuando configura credenciales SII
3. En el backend cuando finaliza el onboarding

## 💡 Soluciones Recomendadas

### Solución 1: Usar Solo CompleteRegistration como Conversión

**En Meta Ads Manager:**
1. Ve a **Events Manager** → **Conversions**
2. Desactiva como conversión:
   - ❌ `ViewContent` (solo engagement)
   - ❌ `Lead` (solo para remarketing)
   - ❌ `Start_Onboarding` (solo para remarketing)
3. Mantén activo solo:
   - ✅ `CompleteRegistration` (conversión real)

### Solución 2: Implementar Deduplicación con event_id

**Modificar `trackMetaAdsConversion.ts`:**

```typescript
// Generar event_id único basado en user_email + timestamp
const generateEventId = (userEmail?: string): string => {
  const timestamp = Date.now();
  const email = userEmail || 'unknown';
  // Crear hash MD5 (similar al backend)
  const hash = btoa(`${email}_${timestamp}`).replace(/[^a-zA-Z0-9]/g, '').substring(0, 32);
  return hash;
};

// En trackMetaPixelEvent, agregar event_id:
const pixelEventData: Record<string, any> = {
  content_name: utmCampaign || 'Registration',
  content_category: 'Signup',
  eventID: generateEventId(data.user_email), // ✅ Agregar event_id
};
```

### Solución 3: Evitar Disparos Múltiples de CompleteRegistration

**Usar un flag en sessionStorage para evitar disparos duplicados:**

```typescript
// En PasswordStep.tsx y SIICredentialSetup.tsx
const hasTrackedCompleteRegistration = sessionStorage.getItem('complete_registration_tracked');

if (!hasTrackedCompleteRegistration) {
  await trackMetaAdsConversion({
    event_name: 'CompleteRegistration',
    user_email: formData.email,
  });
  sessionStorage.setItem('complete_registration_tracked', 'true');
}
```

### Solución 4: Unificar Pixel IDs

**Verificar y usar el mismo Pixel ID en frontend y backend:**

1. Verificar en Meta Events Manager cuál es el Pixel ID correcto
2. Actualizar ambos lugares para usar el mismo ID
3. Eliminar el fallback del backend si no es necesario

## 📈 Resultado Esperado

Después de implementar las soluciones:

- **Conversiones**: Solo `CompleteRegistration` (1 por usuario)
- **Tasa de conversión**: ~10-20% (más realista)
- **Deduplicación**: Eventos duplicados se eliminan automáticamente
- **Atribución**: Más precisa con un solo Pixel ID

## 🔧 Implementación Prioritaria

1. **URGENTE**: Configurar en Meta Ads Manager para que solo `CompleteRegistration` cuente como conversión
2. **ALTA**: Implementar deduplicación con `event_id` en frontend
3. **MEDIA**: Evitar disparos múltiples con sessionStorage
4. **BAJA**: Unificar Pixel IDs (verificar primero cuál es el correcto)

## 📝 Notas Adicionales

- Meta tiene un período de atribución de 7 días por defecto
- Si un usuario hace click hoy y se registra en 3 días, la conversión se atribuye al click original
- Los eventos se deduplican automáticamente si tienen el mismo `event_id` dentro de 48 horas
- El `event_id` debe ser único por usuario y evento, pero consistente si se reenvía
