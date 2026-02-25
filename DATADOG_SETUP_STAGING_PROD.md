# Configuración de Datadog para Staging y Producción

## Variables de Entorno Requeridas

Para que Datadog funcione correctamente en staging y producción, necesitas configurar las siguientes variables de entorno:

### Variables Obligatorias

```bash
DATADOG_API_KEY=tu_api_key_aqui
DD_SITE=datadoghq.com  # o datadoghq.eu según tu región
DD_ENV=staging  # o production
DD_SERVICE=pana-backend
DD_VERSION=1.0  # o la versión de tu aplicación
DD_GIT_REPOSITORY_URL=github.com/afgil/pana-backend
```

### Variables para Code Origin

```bash
DD_CODE_ORIGIN_FOR_SPANS_ENABLED=true
```

### Variables para Logs y APM

```bash
DD_LOGS_ENABLED=true
DD_LOGS_INJECTION=true
DD_TRACE_ENABLED=true
DD_APM_ENABLED=true
```

## Configuración en GitHub Actions (Staging)

Agregar estas variables en el workflow de deploy:

```yaml
env:
  DATADOG_API_KEY: ${{ secrets.DATADOG_API_KEY }}
  DD_SITE: datadoghq.com
  DD_ENV: staging
  DD_SERVICE: pana-backend
  DD_VERSION: ${{ github.sha }}
  DD_GIT_REPOSITORY_URL: github.com/afgil/pana-backend
  DD_CODE_ORIGIN_FOR_SPANS_ENABLED: true
  DD_LOGS_ENABLED: true
  DD_LOGS_INJECTION: true
  DD_TRACE_ENABLED: true
  DD_APM_ENABLED: true
```

## Configuración en Producción

### Opción 1: Variables de Entorno en el Servidor

Agregar todas las variables de entorno en el servidor de producción (Vercel, Render, etc.)

### Opción 2: Archivo .env

Si usas un archivo `.env` en producción, agregar:

```bash
DATADOG_API_KEY=tu_api_key_produccion
DD_SITE=datadoghq.com
DD_ENV=production
DD_SERVICE=pana-backend
DD_VERSION=1.0
DD_GIT_REPOSITORY_URL=github.com/afgil/pana-backend
DD_CODE_ORIGIN_FOR_SPANS_ENABLED=true
DD_LOGS_ENABLED=true
DD_LOGS_INJECTION=true
DD_TRACE_ENABLED=true
DD_APM_ENABLED=true
```

## Agente de Datadog

### Staging/Producción con Docker

Si tu aplicación corre en Docker, puedes agregar el agente de Datadog como sidecar:

```yaml
services:
  datadog-agent:
    image: datadog/agent:latest
    environment:
      - DD_API_KEY=${DATADOG_API_KEY}
      - DD_SITE=datadoghq.com
      - DD_APM_ENABLED=true
      - DD_APM_NON_LOCAL_TRAFFIC=true
      - DD_CODE_ORIGIN_FOR_SPANS_ENABLED=true
    ports:
      - "8126:8126"
```

### Staging/Producción sin Docker

Si no usas Docker, necesitas instalar el agente de Datadog en el servidor:

1. **Instalar el agente:**
   ```bash
   DD_API_KEY=tu_api_key DD_SITE=datadoghq.com DD_ENV=staging bash -c "$(curl -L https://install.datadoghq.com/scripts/install_script_agent7.sh)"
   ```

2. **Configurar el agente:**
   Editar `/etc/datadog-agent/datadog.yaml`:
   ```yaml
   apm_config:
     enabled: true
     non_local_traffic: true
   ```

3. **Reiniciar el agente:**
   ```bash
   sudo systemctl restart datadog-agent
   ```

## Verificación

### Verificar que los traces lleguen

1. Ve a https://app.datadoghq.com/apm/traces
2. Filtra por `service:pana-backend`
3. Deberías ver traces apareciendo

### Verificar Code Origin

1. Abre un span en Datadog
2. Busca la sección "Code Origin"
3. Deberías ver el código fuente del span

**Nota importante:** Code Origin funciona mejor cuando:
- El código fuente está disponible (no minificado/compilado)
- El repositorio Git está correctamente configurado
- Los archivos fuente están en el mismo path relativo que en el repositorio

## Para Producción

En producción, asegúrate de:

1. **Tener el código fuente disponible:**
   - No minificar el código Python
   - Mantener los archivos `.py` originales

2. **Configurar el Git repository correctamente:**
   ```bash
   DD_GIT_REPOSITORY_URL=github.com/afgil/pana-backend
   ```

3. **Verificar que el agente tenga acceso:**
   - Si usas Docker, montar el código fuente como volumen
   - Si usas un servidor, asegurar que el código esté en el mismo path

## Troubleshooting

### Los traces no aparecen

- Verificar que `DATADOG_API_KEY` esté configurada
- Verificar que el agente de Datadog esté corriendo (si aplica)
- Verificar que `DD_TRACE_ENABLED=true`
- Revisar logs del agente: `sudo datadog-agent status`

### Code Origin no funciona

**PRIMERO (si ves "Enable Code Origins" en la traza):**
1. Haz clic en el botón azul **"Enable Code Origins"** en la sección Code Origin del span.
2. En **Organization Settings → Integrations → Source Code**, conecta GitHub y el repo `afgil/pana-backend`.
Sin estos dos pasos en Datadog, el código no se mostrará aunque `DD_CODE_ORIGIN_FOR_SPANS_ENABLED=true` esté bien configurado en el backend.

**IMPORTANTE:** Code Origin solo funciona para "service entry spans" (spans creados automáticamente por Django/DRF en requests HTTP reales). NO funciona para spans manuales creados con `tracer.trace()`.

#### 🔍 Checklist de Verificación (en orden de importancia):

1. **✅ Integración del código fuente en Datadog (CRÍTICO - PASO MÁS IMPORTANTE):**
   - Ve a **Settings → Integrations → Source Code Integration**
   - **DEBE estar habilitada** - Sin esto, Code Origin NO funcionará
   - Conecta tu repositorio de GitHub si no está conectado
   - Verifica que el repositorio `github.com/afgil/pana-backend` esté conectado
   - **Si ves el mensaje "Do you want to see your code here? Enable Code Origins" en Datadog,**
     **debes hacer clic en "Enable Code Origins" en la UI de Datadog**
   - Code Origin puede necesitar habilitarse tanto en la configuración (variables de entorno) como en la UI

2. **✅ Variables de entorno (OBLIGATORIO):**
   ```bash
   DD_CODE_ORIGIN_FOR_SPANS_ENABLED=true
   DD_GIT_REPOSITORY_URL=github.com/afgil/pana-backend
   DD_GIT_COMMIT_SHA=<commit_sha>  # Opcional pero recomendado
   ```
   - Verificar que estén configuradas ANTES de iniciar Django
   - Ejecutar: `python scripts/test_code_origin_debug.py` para verificar

3. **✅ Traces llegando a Datadog:**
   - Ve a **APM → Traces** en Datadog
   - Filtra por `service:pana-backend`
   - ¿Ves traces recientes? Si no, verifica `DATADOG_API_KEY` y que el agente esté enviando

4. **✅ Tags de Git en los spans:**
   - Abre un span en Datadog
   - Busca los tags: `_dd.git.repository_url` y `_dd.git.commit.sha`
   - Si no aparecen, las variables de entorno no están configuradas correctamente

5. **✅ Service entry spans:**
   - Code Origin solo funciona para spans creados automáticamente por Django/DRF
   - Estos spans se crean cuando hay requests HTTP reales a tus endpoints
   - Para verificar, busca spans con `@_dd.code_origin.type:*` en Datadog
   - Los spans manuales (`tracer.trace()`) NO tienen Code Origin

6. **⏰ Tiempo de procesamiento:**
   - Code Origin puede tardar **1-5 minutos** en aparecer en Datadog
   - Los tags de Git aparecen inmediatamente
   - La sección "Code Origin" en el span puede tardar unos minutos

7. **✅ Código fuente disponible:**
   - El código fuente debe estar disponible (no minificado/compilado)
   - Los archivos `.py` deben estar en el mismo path relativo que en el repositorio
   - El repositorio debe estar accesible desde Datadog

#### 🛠️ Comandos de Debug:

```bash
# Verificar configuración completa
cd /Users/antoniogil/dev/tupana/pana-backend
source env/bin/activate
python scripts/test_code_origin_debug.py

# Verificar que los traces lleguen al agente
docker exec datadog-agent agent status | grep -A 10 "Receiver"

# Hacer requests HTTP reales para generar service entry spans
curl http://localhost:8000/health/
curl http://localhost:8000/test-datadog/
```

#### 🔍 Verificación en Datadog:

1. Ve a **APM → Traces**
2. Filtra por `service:pana-backend`
3. Busca spans de requests HTTP (ej: `GET /health/`)
4. O usa la query: `@_dd.code_origin.type:*`
5. Abre un span y busca la sección **"Code Origin"**
6. Si no aparece después de 5 minutos, verifica:
   - ✅ Que la integración del código fuente esté habilitada (CRÍTICO)
   - ✅ Que el repositorio esté conectado en Datadog
   - ✅ Que los tags de Git aparezcan en los spans

### Los logs no aparecen

- Verificar que `DD_LOGS_ENABLED=true`
- Verificar que `DD_LOGS_INJECTION=true`
- Verificar que el agente tenga permisos para leer logs

## Enviar errores de Datadog a un canal de Slack

Sí se puede. La configuración se hace **en Datadog**, no en el backend.

### 1. Conectar Slack a Datadog

1. En Datadog: **Organization Settings** (o **Integrations**) → **Slack**.
2. **Install** / **Connect** y autoriza el workspace de Slack.
3. Elige el canal donde quieres recibir las notificaciones (o crea uno, p. ej. `#datadog-errors`).

### 2. Crear un Monitor de logs de error

Para que los **logs de nivel error** disparen una notificación a Slack:

1. **Monitors** → **New Monitor** → **Logs**.
2. **Define the search**: query por ejemplo:
   - `service:pana-backend status:error`  
   - o `service:pana-backend @status:error`  
   - Ajusta `env:staging` / `env:production` si quieres filtrar por entorno.
3. **Set alert conditions**:  
   - "Trigger when the count is above X for the last 5 minutes" (o el umbral que uses).
4. **Notify your team**:  
   - Añade el canal de Slack como destino del mensaje.
5. Mensaje (opcional): usa variables como `{{value}}`, `{{last_triggered_at}}`, etc.

### 3. Monitor de errores APM (excepciones / traces con error)

Para que las **excepciones o traces con error** también avisen por Slack:

1. **Monitors** → **New Monitor** → **APM** (o **Errors**).
2. Elige **Error Rate** (o el tipo que quieras).
3. Filtra por `service:pana-backend` y, si aplica, por `env:staging` o `env:production`.
4. Define umbral y ventana (p. ej. "above 1 % in the last 5 min").
5. En **Notify your team** añade el mismo canal de Slack.

### 4. Error Tracking (si usas la feature)

Si en Datadog tienes **Error Tracking** activado:

1. **Error Tracking** → **Configuration** (o configuración de notificaciones).
2. Ahí suele haber opción para enviar nuevos errores / agrupaciones a un canal de Slack o a un webhook.

### 5. Resumen de destinos típicos

| Origen en Datadog | Dónde configurarlo | Destino Slack |
|-------------------|--------------------|----------------|
| Logs con `status:error` | Monitor tipo **Logs** | Canal elegido en "Notify" |
| Trace/APM error rate     | Monitor tipo **APM** / **Error Rate** | Canal elegido en "Notify" |
| Error Tracking           | Error Tracking → notificaciones      | Canal o integración Slack |

No hace falta tocar código del backend: los logs y traces ya se envían a Datadog; solo hay que definir en Datadog los monitores y conectar Slack como canal de notificación.
