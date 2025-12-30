#!/usr/bin/env node
/**
 * Script para combinar archivos OpenAPI divididos automáticamente
 * Uso: npm run combine-openapi
 */

const fs = require('fs');
const path = require('path');

function combineOpenAPI() {
  console.log('🔄 Creando archivos OpenAPI completos...');

  const baseDir = 'api-reference/openapi';

  // Cargar base completa
  const baseData = JSON.parse(fs.readFileSync(`${baseDir}/base-complete.json`, 'utf8'));
  const combined = JSON.parse(JSON.stringify(baseData)); // Deep copy

  // Archivos a combinar (solo paths y schemas)
  const files = [
    `${baseDir}/documents.json`,
    `${baseDir}/master-entities.json`,
    `${baseDir}/credentials.json`,
    `${baseDir}/scheduled-documents.json`,
    `${baseDir}/schemas.json`
  ];

  let processedCount = 0;

  for (const filePath of files) {
    if (!fs.existsSync(filePath)) {
      console.warn(`⚠️  Archivo no encontrado: ${filePath}`);
      continue;
    }

    try {
      const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));

      // Combinar paths
      if (data.paths) {
        Object.assign(combined.paths, data.paths);
      }

      // Combinar components
      if (data.components) {
        if (data.components.schemas) {
          if (!combined.components) combined.components = {};
          if (!combined.components.schemas) combined.components.schemas = {};
          Object.assign(combined.components.schemas, data.components.schemas);
        }
        if (data.components.securitySchemes) {
          if (!combined.components.securitySchemes) combined.components.securitySchemes = {};
          Object.assign(combined.components.securitySchemes, data.components.securitySchemes);
        }
      }

      processedCount++;
      console.log(`✅ Procesado: ${filePath}`);

    } catch (error) {
      console.error(`❌ Error procesando ${filePath}:`, error.message);
      process.exit(1);
    }
  }

  // Crear directorio si no existe
  const outputDir = path.dirname('api-reference/openapi-complete.json');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Guardar archivo combinado
  fs.writeFileSync('api-reference/openapi-complete.json', JSON.stringify(combined, null, 2));

  console.log(`🎯 Archivo OpenAPI completo creado: api-reference/openapi-complete.json`);
  console.log(`📊 Archivos procesados: ${processedCount}/${files.length}`);
  console.log(`📊 Paths encontrados: ${Object.keys(combined.paths).length}`);
  console.log(`📊 Schemas encontrados: ${Object.keys(combined.components.schemas).length}`);
}

if (require.main === module) {
  combineOpenAPI();
}

module.exports = { combineOpenAPI };
