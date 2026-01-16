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
    Corrige automáticamente:
    - Objetos 'description' con clave 'description' interna
    - Conflictos de 'type' en items vs properties
    - Cualquier otra clave duplicada en el mismo objeto
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

    def fix_type_conflict_in_items(obj):
        """
        Corregir conflictos de 'type' en items de arrays.
        Si items tiene 'type' y también properties.type, renombrar properties.type a 'state_type'
        (para document_states) o 'item_type' (para otros casos).
        """
        if isinstance(obj, dict):
            fixed = {}
            for key, value in obj.items():
                if key == "items" and isinstance(value, dict):
                    # Verificar si hay conflicto
                    if "type" in value and "properties" in value:
                        if (
                            isinstance(value["properties"], dict)
                            and "type" in value["properties"]
                        ):
                            # Determinar el nombre correcto según el contexto
                            # Si es document_states, usar 'state_type', sino 'item_type'
                            new_name = "state_type"  # Por defecto para document_states

                            # Renombrar 'type' en properties
                            fixed_props = {}
                            for prop_key, prop_value in value["properties"].items():
                                if prop_key == "type":
                                    fixed_props[new_name] = prop_value
                                    # Actualizar descripción si existe
                                    if (
                                        isinstance(prop_value, dict)
                                        and "description" in prop_value
                                    ):
                                        fixed_props[new_name][
                                            "description"
                                        ] = "Tipo de estado del documento"
                                else:
                                    fixed_props[prop_key] = prop_value
                            fixed_value = {**value, "properties": fixed_props}
                            fixed[key] = fix_type_conflict_in_items(fixed_value)
                        else:
                            fixed[key] = fix_type_conflict_in_items(value)
                    else:
                        fixed[key] = fix_type_conflict_in_items(value)
                else:
                    fixed[key] = fix_type_conflict_in_items(value)
            return fixed
        elif isinstance(obj, list):
            return [fix_type_conflict_in_items(item) for item in obj]
        return obj

    # Aplicar correcciones
    fixed_data = fix_duplicate_description(data)
    fixed_data = fix_type_conflict_in_items(fixed_data)

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
    """
    Validar estructura OpenAPI y detectar problemas comunes.
    Retorna True si está válido, False si hay problemas.
    """
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

    # Validar conflictos de 'type' en items
    def check_type_conflicts(obj, path=""):
        if isinstance(obj, dict):
            if "items" in obj and isinstance(obj["items"], dict):
                items_obj = obj["items"]
                if "type" in items_obj and "properties" in items_obj:
                    if isinstance(items_obj["properties"], dict):
                        if "type" in items_obj["properties"]:
                            full_path = f"{path}.items" if path else "items"
                            issues.append(
                                f"Conflicto de 'type' en {full_path}: items tiene 'type' y properties también tiene 'type'"
                            )
            for key, value in obj.items():
                check_type_conflicts(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_type_conflicts(item, f"{path}[{i}]")

    check_description_objects(data)
    check_type_conflicts(data)

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
    """
    Validar y corregir schemas antes de combinar.
    Corrige automáticamente problemas comunes en los archivos de origen.
    """
    base_dir = Path("api-reference/openapi")
    schemas_file = base_dir / "schemas" / "schemas.json"

    if not schemas_file.exists():
        return True

    try:
        with open(schemas_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Aplicar todas las correcciones automáticas
        original_data = json.dumps(data, indent=2, ensure_ascii=False)
        fixed_data = validate_and_fix_duplicate_keys(data, str(schemas_file))

        # Verificar si hubo cambios
        fixed_json = json.dumps(fixed_data, indent=2, ensure_ascii=False)
        if original_data != fixed_json:
            print(f"🔧 Corrigiendo problemas en {schemas_file.name}...")

            # Guardar archivo corregido
            with open(schemas_file, "w", encoding="utf-8") as f:
                json.dump(fixed_data, f, indent=2, ensure_ascii=False)

            print(f"✅ {schemas_file.name} corregido automáticamente")
            return True
        else:
            return True

    except json.JSONDecodeError as e:
        print(f"❌ Error de JSON en {schemas_file}: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Error validando schemas: {e}")
        import traceback

        traceback.print_exc()
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
        # Document states
        base_dir / "document-states" / "document-states.json",
        # Cessions
        base_dir / "cessions" / "batch.json",
        # Webhooks
        base_dir / "webhooks" / "webhooks.json",
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
            original_data_str = json.dumps(data, indent=2, ensure_ascii=False)
            data = validate_and_fix_duplicate_keys(data, str(file_path))
            fixed_data_str = json.dumps(data, indent=2, ensure_ascii=False)

            # Si hubo correcciones, guardar el archivo corregido
            if original_data_str != fixed_data_str:
                print(f"🔧 Corrigiendo problemas en {file_path.name}...")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ {file_path.name} corregido automáticamente")

            # Validar estructura (solo reporta, no bloquea)
            if not validate_openapi_structure(data, str(file_path)):
                print(
                    f"⚠️  Advertencia: Problemas detectados en {file_path}, pero continuando..."
                )

            # Combinar paths (combinar métodos si el path ya existe)
            # Agregar prefijo /v1 a todos los paths si no lo tienen
            if "paths" in data:
                for path, methods in data["paths"].items():
                    # Agregar prefijo /v1 si no lo tiene
                    prefixed_path = path
                    if not path.startswith("/v1/"):
                        # Si ya tiene /v1 al inicio pero sin la barra, agregar la barra
                        if path.startswith("/v1"):
                            prefixed_path = path
                        else:
                            prefixed_path = f"/v1{path}"
                    
                    if prefixed_path not in combined["paths"]:
                        combined["paths"][prefixed_path] = {}
                    combined["paths"][prefixed_path].update(methods)

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
    output_path = Path("api-reference/openapi-combined.json")
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
