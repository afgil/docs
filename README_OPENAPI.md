# 📚 Guía para Generar el OpenAPI Consolidado

Este documento explica cómo generar el archivo OpenAPI consolidado (`openapi-complete.json`) que combina todos los archivos OpenAPI divididos en un solo archivo para uso con Mintlify.

## 🎯 ¿Por qué necesitamos esto?

Mintlify requiere un archivo OpenAPI único y consolidado para generar la documentación de la API. Sin embargo, para mantener la organización y facilitar el mantenimiento, mantenemos los endpoints separados en archivos individuales dentro de `api-reference/openapi/`.

## 📁 Estructura de Archivos

```
docs/
├── api-reference/
│   └── openapi/
│       ├── base/
│       │   └── base-complete.json    # Info básica, servers, security
│       ├── documents/
│       │   ├── list.json
│       │   ├── batch.json
│       │   └── get.json
│       ├── credentials/
│       │   ├── list.json
│       │   └── create.json
│       ├── master-entities/
│       │   └── master-entities.json
│       ├── scheduled-documents/
│       │   ├── scheduled-documents-list.json
│       │   ├── scheduled-documents-create.json
│       │   └── ...
│       ├── document-states/          # Nuevos endpoints
│       │   └── document-states.json
│       └── schemas/
│           └── schemas.json
└── api-reference/
    └── openapi-complete.json         # 🎯 Archivo consolidado (generado)
```

## 🚀 Métodos para Generar el OpenAPI Consolidado

### Método 1: Usando npm (Recomendado)

```bash
cd docs
npm run combine-openapi
```

Este comando ejecuta el script Python que combina todos los archivos OpenAPI en `openapi-complete.json`.

### Método 2: Usando Make

```bash
cd docs
make combine-openapi
```

### Método 3: Usando Python directamente

```bash
cd docs
python3 scripts/combine_openapi.py
```

## 🔄 Automatización

El archivo consolidado se genera automáticamente en los siguientes casos:

1. **Antes de ejecutar la documentación localmente:**

   ```bash
   npm run dev
   ```

   Ejecuta `predev` que combina los archivos automáticamente.

2. **Antes de construir para producción:**

   ```bash
   npm run build
   ```

   Ejecuta `prebuild` que combina los archivos automáticamente.

3. **Antes de hacer commit (si está configurado el hook):**
   El hook `pre-commit` ejecuta `precommit` que combina los archivos.

## 📝 Proceso de Combinación

El script `scripts/combine_openapi.py` realiza los siguientes pasos:

1. **Validación de schemas:** Valida y corrige problemas comunes en los archivos OpenAPI antes de combinar.

2. **Carga del archivo base:** Carga `base/base-complete.json` que contiene la información básica (info, servers, security).

3. **Combinación de paths:** Itera sobre todos los archivos OpenAPI y combina los `paths` en un solo objeto.

4. **Combinación de schemas:** Combina todos los `components.schemas` en un solo objeto.

5. **Validación final:** Valida el archivo combinado y corrige problemas detectados.

6. **Guardado:** Guarda el resultado en `api-reference/openapi-complete.json`.

## 🔧 Agregar Nuevos Endpoints

Cuando agregues un nuevo endpoint OpenAPI:

1. **Crea el archivo JSON** en el directorio correspondiente:

   ```bash
   docs/api-reference/openapi/document-states/document-states.json
   ```

2. **Agrega la ruta al script** en `scripts/combine_openapi.py`:

   ```python
   files = [
       # ... archivos existentes ...
       base_dir / "document-states" / "document-states.json",
   ]
   ```

3. **Ejecuta el script** para generar el consolidado:

   ```bash
   npm run combine-openapi
   ```

## ✅ Verificación

Después de generar el archivo consolidado, puedes verificar que todo esté correcto:

1. **Verificar que el archivo existe:**

   ```bash
   ls -lh docs/api-reference/openapi-complete.json
   ```

2. **Validar el JSON:**

   ```bash
   python3 -m json.tool docs/api-reference/openapi-complete.json > /dev/null
   ```

3. **Verificar en la documentación:**

   ```bash
   npm run dev
   ```

   Y navegar a la sección de API Reference en el navegador.

## 🐛 Solución de Problemas

### Error: "Archivo base no encontrado"

Asegúrate de que existe `api-reference/openapi/base/base-complete.json`.

### Error: "Archivo no encontrado: ..."

Verifica que todos los archivos listados en `scripts/combine_openapi.py` existan.

### Error: "Claves duplicadas"

El script intenta corregir automáticamente claves duplicadas. Si persiste el error, revisa manualmente el archivo problemático.

### El archivo consolidado no se actualiza

1. Verifica que el script se ejecutó correctamente.
2. Limpia el archivo y regenera:

   ```bash
   rm docs/api-reference/openapi-complete.json
   npm run combine-openapi
   ```

## 📚 Referencias

- [Documentación de Mintlify](https://mintlify.com/docs)
- [Especificación OpenAPI 3.0](https://swagger.io/specification/)
- [OPENAPI_AUTOMATION.md](./OPENAPI_AUTOMATION.md) - Documentación adicional sobre automatización

## 🎯 Resumen Rápido

```bash
# Generar OpenAPI consolidado
cd docs
npm run combine-openapi

# Verificar
ls -lh api-reference/openapi-complete.json

# Ejecutar documentación (combina automáticamente)
npm run dev
```


