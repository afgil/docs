#!/usr/bin/env node
/**
 * Watcher que monitorea cambios en archivos OpenAPI y regenera automáticamente
 * Uso: npm run watch-openapi
 */

const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

console.log('👀 Iniciando watcher de archivos OpenAPI...');
console.log('📁 Monitoreando: api-reference/openapi/*.json');

const watchDir = 'api-reference/openapi';
const combineCommand = 'npm run combine-openapi';

// Función para ejecutar el comando de combinación
function combineFiles() {
  console.log('\n🔄 Detectado cambio, combinando archivos...');
  
  exec(combineCommand, (error, stdout, stderr) => {
    if (error) {
      console.error(`❌ Error: ${error.message}`);
      return;
    }
    
    if (stderr) {
      console.error(`⚠️  Advertencia: ${stderr}`);
    }
    
    console.log('✅ Archivos combinados exitosamente');
    console.log('👀 Continuando monitoreo...');
  });
}

// Monitorear cambios en archivos
fs.watch(watchDir, { recursive: true }, (eventType, filename) => {
  if (filename && filename.endsWith('.json') && !filename.includes('combined')) {
    console.log(`📝 Cambio detectado en: ${filename}`);
    combineFiles();
  }
});

console.log('🎯 Watcher activo. Presiona Ctrl+C para detener.');
console.log('💡 Los archivos se combinarán automáticamente cuando cambies algún .json');

// Combinar inicialmente
combineFiles();

// Mantener el proceso vivo
process.on('SIGINT', () => {
  console.log('\n👋 Watcher detenido');
  process.exit(0);
});
