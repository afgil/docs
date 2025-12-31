#!/usr/bin/env python3
"""
Script Python para combinar archivos OpenAPI divididos automáticamente
Uso: python scripts/combine_openapi.py
"""

import json
import os
import sys
import re
from pathlib import Path
from collections import defaultdict


def validate_and_fix_duplicate_keys(data, file_path=None):
    """
    Valida y corrige claves duplicadas en objetos JSON.
    Especialmente útil para detectar problemas que YAML no permite pero JSON sí.
    """

    def fix_duplicate_description(obj):
        """Corregir objetos 'description' con clave 'description' interna duplicada"""
        if isinstance(obj, dict):
            fixed = {}
            for key, value in obj.items():
                if key == "description" and isinstance(value, dict):
                    # Verificar si tiene una clave "description" interna
                    if "description" in value and "type" in value:
                        # Eliminar la clave "description" interna duplicada
                        fixed_value = {
                            k: v for k, v in value.items() if k != "description"
                        }
                        fixed[key] = fixed_value
                    else:
                        fixed[key] = fix_duplicate_description(value)
                else:
                    fixed[key] = fix_duplicate_description(value)
            return fixed
        elif isinstance(obj, list):
            return [fix_duplicate_description(item) for item in obj]
        return obj

    # Aplicar corrección
    fixed_data = fix_duplicate_description(data)

    # Validar que no haya duplicados en el mismo objeto
    def check_duplicates(obj, path="", duplicates=None):
        if duplicates is None:
            duplicates = []

        if isinstance(obj, dict):
            seen_keys = set()
            for key, value in obj.items():
                if key in seen_keys:
                    full_path = f"{path}.{key}" if path else key
                    duplicates.append(full_path)
                seen_keys.add(key)
                check_duplicates(value, f"{path}.{key}" if path else key, duplicates)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_duplicates(item, f"{path}[{i}]", duplicates)

        return duplicates

    duplicates = check_duplicates(fixed_data)
    if duplicates:
        file_info = f" en {file_path}" if file_path else ""
        print(
            f"⚠️  Advertencia: Se encontraron claves duplicadas{file_info}: {duplicates[:5]}"
        )
        if len(duplicates) > 5:
            print(f"   ... y {len(duplicates) - 5} más")

    return fixed_data


def validate_openapi_structure(data, file_path=None):
    """Validar estructura OpenAPI y detectar problemas comunes"""
    issues = []

    # Validar que no haya objetos "description" con clave "description" interna
    def check_description_objects(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "description" and isinstance(value, dict):
                    if "description" in value:
                        full_path = f"{path}.{key}" if path else key
                        issues.append(
                            f"Objeto 'description' con clave 'description' interna en {full_path}"
                        )
                check_description_objects(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_description_objects(item, f"{path}[{i}]")

    check_description_objects(data)

    if issues:
        file_info = f" en {file_path}" if file_path else ""
        print(f"⚠️  Problemas detectados{file_info}:")
        for issue in issues[:5]:
            print(f"   - {issue}")
        if len(issues) > 5:
            print(f"   ... y {len(issues) - 5} más")
        return False

    return True


def validate_and_fix_schemas_before_combine():
    """Validar y corregir schemas antes de combinar"""
    import re

    base_dir = Path("api-reference/openapi")
    schemas_file = base_dir / "schemas" / "schemas.json"

    if not schemas_file.exists():
        return True

    try:
        with open(schemas_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Buscar patrón problemático
        pattern = r'"description":\s*\{\s*"type":\s*"string",\s*"description":\s*"([^"]+)"(\s*,\s*"example":\s*"([^"]+)")?\s*\}'
        matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))

        if matches:
            print(
                f"🔧 Corrigiendo {len(matches)} casos problemáticos en schemas.json..."
            )

            def fix_match(match):
                example_value = match.group(3)
                if example_value:
                    return f'"description": {{\n                "type": "string",\n                "example": "{example_value}"\n              }}'
                else:
                    return f'"description": {{\n                "type": "string"\n              }}'

            fixed_content = re.sub(
                pattern, fix_match, content, flags=re.MULTILINE | re.DOTALL
            )

            # Validar JSON
            try:
                json.loads(fixed_content)
                # Guardar
                with open(schemas_file, "w", encoding="utf-8") as f:
                    json.dump(
                        json.loads(fixed_content), f, indent=2, ensure_ascii=False
                    )
                print(f"✅ schemas.json corregido")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Error al corregir: {e}")
                return False
        else:
            return True
    except Exception as e:
        print(f"⚠️  Error validando schemas: {e}")
        return True  # Continuar aunque haya error


def combine_openapi_files():
    """Combinar todos los archivos OpenAPI en uno solo"""

    # Validar y corregir schemas antes de combinar
    print("🔍 Validando schemas antes de combinar...")
    validate_and_fix_schemas_before_combine()

    print("\n🔄 Combinando archivos OpenAPI con Python...")

    base_dir = Path("api-reference/openapi")

    # Cargar base completa
    base_file = base_dir / "base" / "base-complete.json"
    if not base_file.exists():
        print(f"❌ Archivo base no encontrado: {base_file}")
        return False

    with open(base_file, "r", encoding="utf-8") as f:
        combined = json.load(f)

    # Archivos a combinar (solo paths y schemas, no base)
    files = [
        # Documents
        base_dir / "documents" / "list.json",
        base_dir / "documents" / "batch.json",
        base_dir / "documents" / "get.json",
        # Credentials
        base_dir / "credentials" / "list.json",
        base_dir / "credentials" / "create.json",
        # Master entities
        base_dir / "master-entities" / "master-entities.json",
        # Scheduled documents
        base_dir / "scheduled-documents" / "scheduled-documents-list.json",
        base_dir / "scheduled-documents" / "scheduled-documents-create.json",
        base_dir / "scheduled-documents" / "scheduled-documents-get.json",
        base_dir / "scheduled-documents" / "scheduled-documents-update.json",
        base_dir / "scheduled-documents" / "scheduled-documents-delete.json",
        base_dir / "scheduled-documents" / "scheduled-documents-preview.json",
        # Schemas
        base_dir / "schemas" / "schemas.json",
    ]

    processed_count = 0

    for file_path in files:
        if not file_path.exists():
            print(f"⚠️  Archivo no encontrado: {file_path}")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validar y corregir antes de combinar
            data = validate_and_fix_duplicate_keys(data, str(file_path))
            if not validate_openapi_structure(data, str(file_path)):
                print(
                    f"⚠️  Advertencia: Problemas detectados en {file_path}, pero continuando..."
                )

            # Combinar paths (combinar métodos si el path ya existe)
            if "paths" in data:
                for path, methods in data["paths"].items():
                    if path not in combined["paths"]:
                        combined["paths"][path] = {}
                    combined["paths"][path].update(methods)

            # Combinar components
            if "components" in data:
                if "schemas" in data["components"]:
                    if "components" not in combined:
                        combined["components"] = {}
                    if "schemas" not in combined["components"]:
                        combined["components"]["schemas"] = {}
                    combined["components"]["schemas"].update(
                        data["components"]["schemas"]
                    )
                if "securitySchemes" in data["components"]:
                    if "components" not in combined:
                        combined["components"] = {}
                    if "securitySchemes" not in combined["components"]:
                        combined["components"]["securitySchemes"] = {}
                    combined["components"]["securitySchemes"].update(
                        data["components"]["securitySchemes"]
                    )

            processed_count += 1
            print(f"✅ Procesado: {file_path}")

        except Exception as e:
            print(f"❌ Error procesando {file_path}: {e}")
            import traceback

            traceback.print_exc()
            return False

    # Validar y corregir el resultado final
    print("\n🔍 Validando archivo combinado final...")
    combined = validate_and_fix_duplicate_keys(combined)
    if not validate_openapi_structure(combined):
        print(
            "⚠️  Advertencia: Problemas detectados en archivo combinado, pero guardando..."
        )

    # Guardar archivo combinado
    output_path = Path("api-reference/openapi-complete.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"🎯 Archivo combinado creado: {output_path}")
    print(f"📊 Archivos procesados: {processed_count}/{len(files)}")
    print(f'📊 Paths encontrados: {len(combined["paths"])}')
    print(
        f'📊 Schemas encontrados: {len(combined.get("components", {}).get("schemas", {}))}'
    )

    return True


if __name__ == "__main__":
    success = combine_openapi_files()
    sys.exit(0 if success else 1)
