#!/usr/bin/env python3
"""
Script para combinar archivos OpenAPI divididos en un solo archivo
para asegurar compatibilidad con Mintlify.
"""

import json
import os

def combine_openapi_files():
    """Combinar todos los archivos OpenAPI en uno solo"""
    
    base_dir = "api-reference/openapi"
    files = [
        f"{base_dir}/base.json",
        f"{base_dir}/documents.json", 
        f"{base_dir}/master-entities.json",
        f"{base_dir}/credentials.json",
        f"{base_dir}/scheduled-documents.json",
        f"{base_dir}/schemas.json"
    ]
    
    combined = {
        "openapi": "3.0.0",
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {}
        }
    }
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"⚠️  Archivo no encontrado: {file_path}")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Combinar info, servers, security
            if 'info' in data:
                combined['info'] = data['info']
            if 'servers' in data:
                combined['servers'] = data['servers'] 
            if 'security' in data:
                combined['security'] = data['security']
                
            # Combinar paths
            if 'paths' in data:
                combined['paths'].update(data['paths'])
                
            # Combinar components
            if 'components' in data:
                if 'schemas' in data['components']:
                    combined['components']['schemas'].update(data['components']['schemas'])
                if 'securitySchemes' in data['components']:
                    combined['components']['securitySchemes'].update(data['components']['securitySchemes'])
                    
            print(f"✅ Procesado: {file_path}")
            
        except Exception as e:
            print(f"❌ Error procesando {file_path}: {e}")
    
    # Guardar archivo combinado
    output_path = "api-reference/openapi-combined.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    print(f"🎯 Archivo combinado creado: {output_path}")
    print(f"📊 Paths encontrados: {len(combined['paths'])}")
    print(f"📊 Schemas encontrados: {len(combined['components']['schemas'])}")
    
    return output_path

if __name__ == "__main__":
    combine_openapi_files()
