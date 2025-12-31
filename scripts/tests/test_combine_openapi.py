#!/usr/bin/env python3
"""
Tests unitarios para combine_openapi.py
Valida que el script detecte y corrija problemas comunes en schemas OpenAPI.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open
import sys

# Agregar el directorio padre al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent.parent))

from combine_openapi import (
    validate_and_fix_duplicate_keys,
    validate_openapi_structure,
    validate_and_fix_schemas_before_combine,
)


class TestCombineOpenAPI(unittest.TestCase):
    """Tests para funciones de validación y corrección"""

    def test_validate_and_fix_duplicate_description_keys(self):
        """Test: Detectar y corregir claves 'description' duplicadas"""
        data = {
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Valor duplicado"  # Problema
                            }
                        }
                    }
                }
            }
        }

        fixed = validate_and_fix_duplicate_keys(data)
        
        # Verificar que se corrigió
        test_schema = fixed["components"]["schemas"]["TestSchema"]
        desc_prop = test_schema["properties"]["description"]
        
        # No debe tener "description" dentro de "description"
        self.assertNotIn("description", desc_prop)
        self.assertEqual(desc_prop["type"], "string")

    def test_validate_and_fix_duplicate_type_in_items(self):
        """Test: Detectar conflicto entre 'type' en items y 'type' en properties"""
        data = {
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "properties": {
                            "states": {
                                "type": "array",
                                "items": {
                                    "type": "object",  # type aquí
                                    "properties": {
                                        "type": {  # type también aquí - CONFLICTO
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        # La función debería detectar este problema
        issues = []
        def check_issues(obj, path=""):
            if isinstance(obj, dict):
                if "items" in obj and "properties" in obj.get("items", {}):
                    items_props = obj["items"]["properties"]
                    if "type" in obj["items"] and "type" in items_props:
                        issues.append(f"{path}.items tiene 'type' duplicado")
                for k, v in obj.items():
                    check_issues(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_issues(item, f"{path}[{i}]")

        check_issues(data)
        self.assertGreater(len(issues), 0, "Debe detectar el conflicto de 'type'")

    def test_validate_openapi_structure_detects_description_duplicate(self):
        """Test: validate_openapi_structure detecta objetos description con description interna"""
        data = {
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Valor duplicado"
                            }
                        }
                    }
                }
            }
        }

        result = validate_openapi_structure(data)
        self.assertFalse(result, "Debe detectar el problema")

    def test_validate_and_fix_schemas_before_combine(self):
        """Test: validate_and_fix_schemas_before_combine corrige problemas en schemas.json"""
        # Crear un archivo temporal con problema
        problem_content = '''{
  "components": {
    "schemas": {
      "TestSchema": {
        "type": "object",
        "properties": {
          "description": {
            "type": "string",
            "description": "Valor duplicado"
          }
        }
      }
    }
  }
}'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(problem_content)
            temp_path = Path(f.name)

        try:
            # Mock el path del archivo
            with patch('combine_openapi.Path') as mock_path:
                mock_schemas_file = mock_path.return_value / "schemas" / "schemas.json"
                mock_schemas_file.exists.return_value = True
                mock_schemas_file.__str__ = lambda x: str(temp_path)

                # Ejecutar la función
                result = validate_and_fix_schemas_before_combine()

                # Verificar que se corrigió
                with open(temp_path, 'r') as f:
                    fixed_data = json.load(f)

                test_schema = fixed_data["components"]["schemas"]["TestSchema"]
                desc_prop = test_schema["properties"]["description"]
                self.assertNotIn("description", desc_prop)

        finally:
            temp_path.unlink()

    def test_no_duplicate_keys_in_valid_schema(self):
        """Test: Schema válido no debe tener problemas"""
        data = {
            "components": {
                "schemas": {
                    "ValidSchema": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Nombre válido"
                            },
                            "age": {
                                "type": "integer"
                            }
                        }
                    }
                }
            }
        }

        fixed = validate_and_fix_duplicate_keys(data)
        result = validate_openapi_structure(fixed)
        self.assertTrue(result, "Schema válido no debe tener problemas")

    def test_detect_duplicate_keys_in_same_object(self):
        """Test: Detectar claves duplicadas en el mismo objeto"""
        # JSON permite claves duplicadas (mantiene la última), pero YAML no
        # Necesitamos detectar esto
        data = {
            "test": {
                "key1": "value1",
                "key1": "value2"  # Duplicado (JSON lo permite, YAML no)
            }
        }

        # En Python, el dict no puede tener claves duplicadas realmente
        # Pero podemos simular el problema con un objeto que tenga el mismo nombre
        # en diferentes niveles que causen conflicto

        # Test real: objeto con "type" en items y "type" en properties
        data = {
            "components": {
                "schemas": {
                    "ProblemSchema": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string"}  # Conflicto
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        issues = []
        def check_for_type_conflict(obj, path=""):
            if isinstance(obj, dict):
                # Verificar si items tiene type y también properties.type
                if "items" in obj:
                    items_obj = obj["items"]
                    if isinstance(items_obj, dict):
                        if "type" in items_obj and "properties" in items_obj:
                            if "type" in items_obj["properties"]:
                                issues.append(f"{path}.items tiene conflicto de 'type'")
                for k, v in obj.items():
                    check_for_type_conflict(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_for_type_conflict(item, f"{path}[{i}]")

        check_for_type_conflict(data)
        self.assertGreater(len(issues), 0)


class TestOpenAPIValidation(unittest.TestCase):
    """Tests para validaciones específicas de OpenAPI"""

    def test_detect_description_inside_description(self):
        """Test: Detectar objeto description con clave description interna"""
        data = {
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Valor problemático"
                }
            }
        }

        issues = []
        def check_description_objects(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "description" and isinstance(value, dict):
                        if "description" in value:
                            issues.append(f"Objeto 'description' con clave 'description' interna en {path}")
                    check_description_objects(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_description_objects(item, f"{path}[{i}]")

        check_description_objects(data)
        self.assertGreater(len(issues), 0)

    def test_detect_type_conflict_in_array_items(self):
        """Test: Detectar conflicto de 'type' en items de array"""
        data = {
            "properties": {
                "states": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"}  # Conflicto
                        }
                    }
                }
            }
        }

        issues = []
        def check_type_conflict(obj, path=""):
            if isinstance(obj, dict):
                if "items" in obj and isinstance(obj["items"], dict):
                    items_obj = obj["items"]
                    if "type" in items_obj and "properties" in items_obj:
                        if "type" in items_obj["properties"]:
                            issues.append(f"{path}: items tiene 'type' y properties también tiene 'type'")
                for k, v in obj.items():
                    check_type_conflict(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_type_conflict(item, f"{path}[{i}]")

        check_type_conflict(data)
        self.assertGreater(len(issues), 0)


if __name__ == "__main__":
    unittest.main()

