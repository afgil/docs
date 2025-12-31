#!/usr/bin/env python3
"""
Script para validar schemas OpenAPI antes de combinarlos.
Previene problemas de claves duplicadas y estructuras inválidas.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict


def find_duplicate_description_pattern(content):
    """
    Encuentra el patrón problemático: objetos "description" con clave "description" interna.
    Este patrón causa problemas en YAML (que usa Mintlify) porque no permite claves duplicadas.
    """
    pattern = r'"description":\s*\{\s*"type":\s*"string",\s*"description":\s*"([^"]+)"'
    matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))
    return matches


def fix_duplicate_description_pattern(content):
    """
    Corrige el patrón problemático eliminando la clave "description" interna.
    """
    # Patrón con ejemplo opcional
    pattern = r'"description":\s*\{\s*"type":\s*"string",\s*"description":\s*"([^"]+)"(\s*,\s*"example":\s*"([^"]+)")?\s*\}'
    
    def replace_match(match):
        example_value = match.group(3)
        if example_value:
            return f'"description": {{\n                "type": "string",\n                "example": "{example_value}"\n              }}'
        else:
            return f'"description": {{\n                "type": "string"\n              }}'
    
    fixed = re.sub(pattern, replace_match, content, flags=re.MULTILINE | re.DOTALL)
    return fixed


def validate_file(file_path, fix=False):
    """
    Valida un archivo OpenAPI y opcionalmente lo corrige.
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ Archivo no encontrado: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Validar JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ JSON inválido en {file_path}: {e}")
            return False
        
        # Buscar patrón problemático
        matches = find_duplicate_description_pattern(content)
        
        if matches:
            print(f"⚠️  {file_path.name}: {len(matches)} casos problemáticos encontrados")
            for match in matches[:3]:
                line_num = content[:match.start()].count('\n') + 1
                print(f"   Línea {line_num}: {match.group(1)[:50]}")
            
            if fix:
                print(f"🔧 Corrigiendo {file_path.name}...")
                fixed_content = fix_duplicate_description_pattern(content)
                
                # Validar que el JSON sigue siendo válido
                try:
                    json.loads(fixed_content)
                    # Guardar archivo corregido
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json.loads(fixed_content), f, indent=2, ensure_ascii=False)
                    print(f"✅ {file_path.name} corregido")
                    return True
                except json.JSONDecodeError as e:
                    print(f"❌ Error al corregir {file_path.name}: {e}")
                    return False
            else:
                return False
        else:
            print(f"✅ {file_path.name}: Sin problemas")
            return True
            
    except Exception as e:
        print(f"❌ Error procesando {file_path}: {e}")
        return False


def validate_all_schemas(base_dir="api-reference/openapi", fix=False):
    """
    Valida todos los archivos OpenAPI en el directorio.
    """
    base_path = Path(base_dir)
    all_valid = True
    
    print("=" * 70)
    print("VALIDACIÓN DE SCHEMAS OPENAPI")
    print("=" * 70)
    
    # Validar schemas.json específicamente
    schemas_file = base_path / "schemas" / "schemas.json"
    if schemas_file.exists():
        print(f"\n📋 Validando {schemas_file.relative_to(base_path.parent)}:")
        if not validate_file(schemas_file, fix=fix):
            all_valid = False
    
    # Validar otros archivos JSON
    print(f"\n📋 Validando otros archivos OpenAPI:")
    for json_file in base_path.rglob("*.json"):
        if json_file.name == "schemas.json" or "complete" in json_file.name:
            continue
        if not validate_file(json_file, fix=fix):
            all_valid = False
    
    print("\n" + "=" * 70)
    if all_valid:
        print("✅ TODOS LOS ARCHIVOS SON VÁLIDOS")
    else:
        print("⚠️  ALGUNOS ARCHIVOS TIENEN PROBLEMAS")
        if not fix:
            print("   Ejecuta con --fix para corregir automáticamente")
    
    return all_valid


def main():
    """Función principal"""
    fix = "--fix" in sys.argv or "-f" in sys.argv
    
    if fix:
        print("🔧 Modo corrección activado\n")
    
    success = validate_all_schemas(fix=fix)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

