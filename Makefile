.PHONY: help combine-openapi dev build watch clean

# Variables
OPENAPI_DIR = api-reference/openapi
COMBINED_FILE = api-reference/openapi-combined.json

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

combine-openapi: ## Combinar archivos OpenAPI divididos
	@echo "🔄 Combinando archivos OpenAPI..."
	@npm run combine-openapi

dev: ## Ejecutar Mintlify en modo desarrollo (combina OpenAPI automáticamente)
	@echo "🚀 Iniciando Mintlify..."
	@npm run dev

build: ## Construir documentación para producción (combina OpenAPI automáticamente)
	@echo "🔨 Construyendo documentación..."
	@npm run build

watch: ## Monitorear cambios en archivos OpenAPI y regenerar automáticamente
	@echo "👀 Iniciando watcher..."
	@npm run watch-openapi

clean: ## Limpiar archivos generados
	@echo "🧹 Limpiando archivos generados..."
	@rm -f $(COMBINED_FILE)
	@echo "✅ Limpieza completada"

# Regla por defecto
.DEFAULT_GOAL := help
