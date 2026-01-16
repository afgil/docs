# 🤖 Automatización de Archivos OpenAPI

Este documento explica cómo funciona el sistema automatizado para combinar archivos OpenAPI divididos.

## 📁 Estructura de Archivos

```
docs/
├── api-reference/
│   └── openapi/
│       ├── base-complete.json     # Info básica, servers, security, components
│       ├── documents.json         # Endpoints /documents/*
│       ├── master-entities.json   # Endpoint /master-entities
│       ├── credentials.json       # Endpoints /credentials/*
│       ├── scheduled-documents.json # Endpoints /scheduled-documents/*
│       └── schemas.json           # Todos los schemas compartidos
├── api-reference/
│   └── openapi-combined.json      # 🆕 Archivo combinado (generado)
└── scripts/
    ├── combine-openapi.js         # Script Node.js
    └── combine_openapi.py         # Script Python alternativo
```

## 🚀 Comandos Automáticos

### Usando npm (recomendado)

```bash
# Combinar archivos manualmente
npm run combine-openapi

# Ejecutar documentación (combina automáticamente)
npm run dev

# Construir para producción (combina automáticamente)
npm run build

# Monitorear cambios automáticamente
npm run watch-openapi
```

### Usando Make

```bash
# Mostrar ayuda
make help

# Combinar archivos
make combine-openapi

# Ejecutar documentación
make dev

# Construir para producción
make build

# Monitorear cambios
make watch

# Limpiar archivos generados
make clean
```

### Usando Python (alternativo)

```bash
# Ejecutar script Python
python scripts/combine_openapi.py
```

## 🔄 Automatización Integrada

### Git Hooks
- **pre-commit**: Se ejecuta automáticamente antes de cada commit
- Asegura que el archivo combinado siempre esté actualizado

### Watcher
- Monitorea cambios en archivos `.json` en `api-reference/openapi/`
- Regenera automáticamente el archivo combinado cuando detecta cambios
- Útil durante el desarrollo

### Scripts de npm
- `npm run dev` y `npm run build` combinan archivos automáticamente
- No necesitas recordar ejecutar comandos manualmente

## 📋 Flujo de Trabajo

### Para Desarrollo
1. **Edita archivos individuales** en `api-reference/openapi/`
2. **El watcher regenera automáticamente** el archivo combinado
3. **La documentación se actualiza** en tiempo real

### Para Commit
1. **Haz cambios** en archivos OpenAPI
2. **Ejecuta `git commit`** 
3. **El hook pre-commit combina automáticamente** los archivos
4. **El archivo combinado se incluye** en el commit

### Para Deploy
1. **Los scripts de npm/build combinan automáticamente** los archivos
2. **No necesitas intervención manual**

## ⚙️ Configuración

### Git Hook (Automático)
Ya está configurado en `.git/hooks/pre-commit`

### Watcher (Manual)
Ejecuta `npm run watch-openapi` en una terminal separada durante el desarrollo

## 🔧 Personalización

### Agregar Nuevo Archivo OpenAPI
1. Crea el archivo en `api-reference/openapi/nuevo.json`
2. Agrega la ruta al array `files` en:
   - `scripts/combine-openapi.js`
   - `scripts/combine_openapi.py`

### Cambiar Archivo de Salida
Modifica la variable `output_path` en los scripts

## 🎯 Beneficios

✅ **Totalmente automático** - No intervención manual requerida
✅ **Múltiples opciones** - npm, Make, Python
✅ **Integración Git** - Hooks automáticos
✅ **Desarrollo eficiente** - Watcher en tiempo real
✅ **Deploy seguro** - Combinación automática en build

¡El sistema maneja todo automáticamente! 🎉
