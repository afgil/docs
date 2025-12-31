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

    # Procesar PRIMERO el archivo base que contiene info, servers y security
    base_file = os.path.join(base_dir, "base", "base-complete.json")
    files = [base_file] if os.path.exists(base_file) else []

    # Luego procesar los demás archivos
    subdirs = [
        "credentials",
        "documents",
        "master-entities",
        "scheduled-documents",
        "schemas"
    ]

    for subdir in subdirs:
        subdir_path = os.path.join(base_dir, subdir)
        if os.path.exists(subdir_path):
            # Buscar todos los archivos .json en cada subdirectorio
            for filename in os.listdir(subdir_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(subdir_path, filename)
                    files.append(file_path)
        else:
            print(f"⚠️  Directorio no encontrado: {subdir_path}")
    
    combined = {
        "openapi": "3.0.0",
        "info": {},
        "servers": [],
        "security": [],
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
            
            # Combinar info, servers, security (actualizar en lugar de agregar)
            if 'info' in data and data['info']:
                combined['info'].update(data['info'])
            if 'servers' in data and data['servers']:
                combined['servers'] = data['servers']
            if 'security' in data and data['security']:
                combined['security'] = data['security']
                
            # Combinar paths (fusionar métodos dentro de cada path con deep merge)
            if 'paths' in data:
                for path_name, path_data in data['paths'].items():
                    if path_name not in combined['paths']:
                        combined['paths'][path_name] = {}
                    # Fusionar los métodos HTTP dentro del path con deep merge
                    for method_name, method_data in path_data.items():
                        if method_name not in combined['paths'][path_name]:
                            combined['paths'][path_name][method_name] = method_data
                        else:
                            # Deep merge para preservar ejemplos y otros campos
                            existing = combined['paths'][path_name][method_name]
                            # Fusionar requestBody profundamente
                            if 'requestBody' in method_data and 'requestBody' in existing:
                                existing_rb = existing['requestBody']
                                new_rb = method_data['requestBody']
                                if 'content' in new_rb and 'content' in existing_rb:
                                    for content_type, content_data in new_rb['content'].items():
                                        if content_type in existing_rb['content']:
                                            # Preservar ejemplo si existe en el nuevo
                                            if 'example' in content_data:
                                                existing_rb['content'][content_type]['example'] = content_data['example']
                                            # Preservar schema si no existe
                                            if 'schema' not in existing_rb['content'][content_type] and 'schema' in content_data:
                                                existing_rb['content'][content_type]['schema'] = content_data['schema']
                                        else:
                                            existing_rb['content'][content_type] = content_data
                                elif 'content' in new_rb:
                                    existing['requestBody']['content'] = new_rb['content']
                            elif 'requestBody' in method_data:
                                existing['requestBody'] = method_data['requestBody']
                            # Actualizar otros campos
                            existing.update({k: v for k, v in method_data.items() if k != 'requestBody'})
                
            # Combinar components
            if 'components' in data:
                if 'schemas' in data['components']:
                    combined['components']['schemas'].update(data['components']['schemas'])
                if 'securitySchemes' in data['components']:
                    combined['components']['securitySchemes'].update(data['components']['securitySchemes'])
                    
            print(f"✅ Procesado: {file_path}")
            
        except Exception as e:
            print(f"❌ Error procesando {file_path}: {e}")
    
    # Limpiar datos vacíos
    if not combined['info']:
        del combined['info']
    if not combined['servers']:
        del combined['servers']
    if not combined['security']:
        del combined['security']

    # Guardar archivo combinado con el orden correcto
    output_path = "api-reference/openapi-combined.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    print(f"🎯 Archivo combinado creado: {output_path}")
    print(f"📊 Paths encontrados: {len(combined['paths'])}")
    print(f"📊 Schemas encontrados: {len(combined['components']['schemas'])}")
    
    return output_path

if __name__ == "__main__":
    combine_openapi_files()
