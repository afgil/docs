#!/usr/bin/env python3
"""
Script Python para combinar archivos OpenAPI divididos automáticamente
Uso: python scripts/combine_openapi.py
"""

import json
import os
import sys
from pathlib import Path

def combine_openapi_files():
    """Combinar todos los archivos OpenAPI en uno solo"""
    
    print('🔄 Combinando archivos OpenAPI con Python...')
    
    base_dir = Path('api-reference/openapi')
    
    # Cargar base completa
    base_file = base_dir / 'base' / 'base-complete.json'
    if not base_file.exists():
        print(f'❌ Archivo base no encontrado: {base_file}')
        return False
    
    with open(base_file, 'r', encoding='utf-8') as f:
        combined = json.load(f)
    
    # Archivos a combinar (solo paths y schemas, no base)
    files = [
        # Documents
        base_dir / 'documents' / 'list.json',
        base_dir / 'documents' / 'batch.json',
        # Credentials
        base_dir / 'credentials' / 'list.json',
        base_dir / 'credentials' / 'create.json',
        # Master entities
        base_dir / 'master-entities' / 'master-entities.json',
        # Scheduled documents
        base_dir / 'scheduled-documents' / 'scheduled-documents-list.json',
        base_dir / 'scheduled-documents' / 'scheduled-documents-create.json',
        base_dir / 'scheduled-documents' / 'scheduled-documents-get.json',
        base_dir / 'scheduled-documents' / 'scheduled-documents-update.json',
        base_dir / 'scheduled-documents' / 'scheduled-documents-delete.json',
        base_dir / 'scheduled-documents' / 'scheduled-documents-preview.json',
        # Schemas
        base_dir / 'schemas' / 'schemas.json'
    ]
    
    processed_count = 0
    
    for file_path in files:
        if not file_path.exists():
            print(f'⚠️  Archivo no encontrado: {file_path}')
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Combinar paths (combinar métodos si el path ya existe)
            if 'paths' in data:
                for path, methods in data['paths'].items():
                    if path not in combined['paths']:
                        combined['paths'][path] = {}
                    combined['paths'][path].update(methods)
            
            # Combinar components
            if 'components' in data:
                if 'schemas' in data['components']:
                    if 'components' not in combined:
                        combined['components'] = {}
                    if 'schemas' not in combined['components']:
                        combined['components']['schemas'] = {}
                    combined['components']['schemas'].update(data['components']['schemas'])
                if 'securitySchemes' in data['components']:
                    if 'components' not in combined:
                        combined['components'] = {}
                    if 'securitySchemes' not in combined['components']:
                        combined['components']['securitySchemes'] = {}
                    combined['components']['securitySchemes'].update(data['components']['securitySchemes'])
            
            processed_count += 1
            print(f'✅ Procesado: {file_path}')
            
        except Exception as e:
            print(f'❌ Error procesando {file_path}: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    # Guardar archivo combinado
    output_path = Path('api-reference/openapi-complete.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    print(f'🎯 Archivo combinado creado: {output_path}')
    print(f'📊 Archivos procesados: {processed_count}/{len(files)}')
    print(f'📊 Paths encontrados: {len(combined["paths"])}')
    print(f'📊 Schemas encontrados: {len(combined.get("components", {}).get("schemas", {}))}')
    
    return True

if __name__ == '__main__':
    success = combine_openapi_files()
    sys.exit(0 if success else 1)
