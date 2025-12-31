#!/usr/bin/env python3
"""
Script para analizar y detectar problemas de claves duplicadas en archivos OpenAPI.
Especialmente útil para detectar problemas que Mintlify reporta pero que JSON estándar ignora.
"""

import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path


class OpenAPIAnalyzer:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.content = None
        self.lines = None
        self.data = None
        
    def load_file(self):
        """Cargar el archivo"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            self.lines = self.content.split('\n')
            print(f"✅ Archivo cargado: {self.file_path}")
            print(f"   Total de líneas: {len(self.lines)}")
            return True
        except FileNotFoundError:
            print(f"❌ Archivo no encontrado: {self.file_path}")
            return False
        except Exception as e:
            print(f"❌ Error al cargar archivo: {e}")
            return False
    
    def parse_json(self):
        """Parsear como JSON"""
        try:
            self.data = json.loads(self.content)
            print("✅ JSON válido según parser estándar de Python")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Error al parsear JSON: {e}")
            print(f"   Línea {e.lineno}, columna {e.colno}")
            return False
    
    def find_duplicate_keys_in_objects(self):
        """Encontrar claves duplicadas en objetos usando análisis de texto"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DE CLAVES DUPLICADAS EN OBJETOS")
        print("=" * 70)
        
        duplicates = []
        stack = []  # Stack para rastrear objetos anidados
        object_keys = defaultdict(list)  # Claves por objeto
        object_starts = {}  # Línea de inicio de cada objeto
        
        for i, line in enumerate(self.lines, 1):
            # Contar llaves abiertas y cerradas
            open_braces = line.count('{')
            close_braces = line.count('}')
            
            # Procesar llaves abiertas
            for _ in range(open_braces):
                stack.append(i)
                object_keys[i] = []
                object_starts[i] = i
            
            # Buscar claves en esta línea
            # Patrón: "clave": (con posibles espacios)
            key_pattern = r'"([^"]+)"\s*:'
            key_matches = re.findall(key_pattern, line)
            
            for key in key_matches:
                if stack:
                    obj_line = stack[-1]
                    if key in object_keys[obj_line]:
                        # ¡Duplicado encontrado!
                        first_occurrence_line = None
                        # Buscar la primera ocurrencia
                        for j in range(object_starts[obj_line], i):
                            if f'"{key}"' in self.lines[j-1]:
                                first_occurrence_line = j
                                break
                        
                        duplicates.append({
                            'line': i,
                            'key': key,
                            'object_start': object_starts[obj_line],
                            'first_occurrence': first_occurrence_line or object_starts[obj_line],
                            'context': self._get_context(i, 5)
                        })
                    object_keys[obj_line].append(key)
            
            # Procesar llaves cerradas
            for _ in range(close_braces):
                if stack:
                    obj_line = stack.pop()
                    # Limpiar cuando se cierra el objeto
                    if obj_line in object_keys:
                        del object_keys[obj_line]
                    if obj_line in object_starts:
                        del object_starts[obj_line]
        
        return duplicates
    
    def _get_context(self, line_num, context_lines=5):
        """Obtener contexto alrededor de una línea"""
        start = max(0, line_num - context_lines - 1)
        end = min(len(self.lines), line_num + context_lines)
        return [(i+1, self.lines[i]) for i in range(start, end)]
    
    def find_specific_key_duplicates(self, key_name):
        """Buscar duplicaciones específicas de una clave"""
        print(f"\n" + "=" * 70)
        print(f"BUSCANDO DUPLICACIONES ESPECÍFICAS DE '{key_name}'")
        print("=" * 70)
        
        occurrences = []
        for i, line in enumerate(self.lines, 1):
            if f'"{key_name}"' in line:
                occurrences.append({
                    'line': i,
                    'content': line.strip(),
                    'context': self._get_context(i, 3)
                })
        
        print(f"   Encontradas {len(occurrences)} ocurrencias de '{key_name}':")
        for occ in occurrences:
            print(f"\n   📍 Línea {occ['line']}:")
            print(f"      {occ['content'][:100]}")
        
        # Verificar si hay duplicados en el mismo objeto
        duplicates_in_same_object = []
        for i, occ1 in enumerate(occurrences):
            for occ2 in occurrences[i+1:]:
                # Verificar si están en el mismo objeto
                if self._are_in_same_object(occ1['line'], occ2['line']):
                    duplicates_in_same_object.append({
                        'key': key_name,
                        'line1': occ1['line'],
                        'line2': occ2['line']
                    })
        
        if duplicates_in_same_object:
            print(f"\n   ⚠️ DUPLICADOS EN EL MISMO OBJETO:")
            for dup in duplicates_in_same_object:
                print(f"      Línea {dup['line1']} y línea {dup['line2']}")
        else:
            print(f"\n   ✅ No hay duplicados de '{key_name}' en el mismo objeto")
        
        return occurrences, duplicates_in_same_object
    
    def _are_in_same_object(self, line1, line2):
        """Verificar si dos líneas están en el mismo objeto JSON"""
        # Encontrar el objeto más cercano que contiene ambas líneas
        start = min(line1, line2) - 1
        end = max(line1, line2)
        
        brace_count = 0
        object_start = None
        
        for i in range(start, -1, -1):
            brace_count += self.lines[i].count('}') - self.lines[i].count('{')
            if brace_count < 0:
                object_start = i
                break
        
        if object_start is None:
            return False
        
        # Verificar que ambas líneas estén dentro del mismo objeto
        brace_count = 0
        for i in range(object_start, end):
            brace_count += self.lines[i].count('{') - self.lines[i].count('}')
            if brace_count == 0 and i < end - 1:
                return False
        
        return True
    
    def analyze_schema_structure(self):
        """Analizar la estructura de los schemas"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DE ESTRUCTURA DE SCHEMAS")
        print("=" * 70)
        
        if not self.data or 'components' not in self.data:
            print("   ⚠️ No se encontró 'components' en el archivo")
            return
        
        schemas = self.data.get('components', {}).get('schemas', {})
        print(f"\n   Total de schemas: {len(schemas)}")
        
        # Analizar ReferenceItem específicamente
        if 'ReferenceItem' in schemas:
            print("\n   📋 ReferenceItem:")
            ref_item = schemas['ReferenceItem']
            if 'properties' in ref_item:
                props = ref_item['properties']
                print(f"      Propiedades: {list(props.keys())}")
                if 'dte_type_code' in props:
                    print(f"      ✅ Tiene 'dte_type_code'")
                if 'reference_type' in props:
                    print(f"      ⚠️ Tiene 'reference_type' (debería eliminarse)")
        
        # Analizar DocumentDetailWithFiles
        if 'DocumentDetailWithFiles' in schemas:
            print("\n   📋 DocumentDetailWithFiles:")
            doc_detail = schemas['DocumentDetailWithFiles']
            if 'allOf' in doc_detail:
                print(f"      Usa allOf con {len(doc_detail['allOf'])} elementos")
                for i, item in enumerate(doc_detail['allOf']):
                    if '$ref' in item:
                        print(f"         [{i}] $ref: {item['$ref']}")
                    elif 'properties' in item:
                        props = list(item['properties'].keys())
                        print(f"         [{i}] Propiedades: {props}")
                        if 'dte_type_code' in props:
                            print(f"            ⚠️ Tiene 'dte_type_code' directamente")
    
    def check_line_specific(self, line_num):
        """Verificar una línea específica y su contexto"""
        print(f"\n" + "=" * 70)
        print(f"ANÁLISIS DE LÍNEA ESPECÍFICA: {line_num}")
        print("=" * 70)
        
        if line_num < 1 or line_num > len(self.lines):
            print(f"   ❌ Línea {line_num} fuera de rango")
            return
        
        line = self.lines[line_num - 1]
        print(f"\n   Contenido de la línea {line_num}:")
        print(f"   '{line}'")
        
        # Buscar claves en esta línea
        key_matches = re.findall(r'"([^"]+)"\s*:', line)
        if key_matches:
            print(f"\n   Claves encontradas en esta línea: {key_matches}")
        
        # Contexto amplio
        print(f"\n   Contexto (10 líneas antes y después):")
        context = self._get_context(line_num, 10)
        for line_no, line_content in context:
            marker = ">>>" if line_no == line_num else "   "
            print(f"   {marker} {line_no:4d}: {line_content}")
        
        # Buscar el objeto que contiene esta línea
        print(f"\n   Objeto que contiene esta línea:")
        obj_info = self._find_containing_object(line_num)
        if obj_info:
            print(f"      Inicia en línea: {obj_info['start']}")
            print(f"      Termina en línea: {obj_info['end']}")
            print(f"      Tipo: {obj_info.get('type', 'desconocido')}")
            print(f"      Claves en el objeto: {obj_info.get('keys', [])}")
    
    def _find_containing_object(self, line_num):
        """Encontrar el objeto JSON que contiene una línea específica"""
        # Buscar hacia atrás para encontrar el inicio del objeto
        brace_count = 0
        start = None
        
        for i in range(line_num - 1, -1, -1):
            brace_count += self.lines[i].count('}') - self.lines[i].count('{')
            if brace_count < 0:
                start = i + 1
                break
        
        if start is None:
            return None
        
        # Buscar hacia adelante para encontrar el final
        brace_count = 0
        end = None
        
        for i in range(start - 1, len(self.lines)):
            brace_count += self.lines[i].count('{') - self.lines[i].count('}')
            if brace_count == 0:
                end = i + 1
                break
        
        # Extraer información del objeto
        obj_lines = self.lines[start-1:end] if end else self.lines[start-1:start+50]
        obj_text = '\n'.join(obj_lines)
        
        # Buscar tipo y claves
        obj_type = None
        keys = []
        
        if '"type"' in obj_text:
            type_match = re.search(r'"type"\s*:\s*"([^"]+)"', obj_text)
            if type_match:
                obj_type = type_match.group(1)
        
        key_matches = re.findall(r'"([^"]+)"\s*:', obj_text)
        keys = list(set(key_matches))  # Eliminar duplicados
        
        return {
            'start': start,
            'end': end,
            'type': obj_type,
            'keys': keys
        }
    
    def generate_report(self):
        """Generar reporte completo"""
        print("\n" + "=" * 70)
        print("REPORTE COMPLETO")
        print("=" * 70)
        
        # 1. Duplicados generales
        duplicates = self.find_duplicate_keys_in_objects()
        if duplicates:
            print(f"\n⚠️ Encontradas {len(duplicates)} claves duplicadas:")
            for dup in duplicates[:10]:  # Mostrar solo las primeras 10
                print(f"\n   Línea {dup['line']}: clave '{dup['key']}' duplicada")
                print(f"      Primera ocurrencia: línea {dup['first_occurrence']}")
                print(f"      Objeto iniciado en: línea {dup['object_start']}")
        else:
            print("\n✅ No se encontraron claves duplicadas en objetos")
        
        # 2. Buscar específicamente dte_type_code
        self.find_specific_key_duplicates('dte_type_code')
        
        # 3. Analizar estructura
        self.analyze_schema_structure()
        
        # 4. Verificar línea problemática (1695)
        self.check_line_specific(1695)
        
        return duplicates


def main():
    """Función principal"""
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = 'api-reference/openapi-complete.json'
    
    print("=" * 70)
    print("ANALIZADOR DE OPENAPI - DETECCIÓN DE DUPLICADOS")
    print("=" * 70)
    print(f"\nArchivo a analizar: {file_path}")
    
    analyzer = OpenAPIAnalyzer(file_path)
    
    if not analyzer.load_file():
        sys.exit(1)
    
    if not analyzer.parse_json():
        print("\n⚠️ Continuando con análisis de texto aunque JSON tenga errores...")
    
    # Generar reporte completo
    duplicates = analyzer.generate_report()
    
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    if duplicates:
        print(f"⚠️ Se encontraron {len(duplicates)} claves duplicadas")
        print("   Revisa el reporte anterior para más detalles")
    else:
        print("✅ No se encontraron claves duplicadas obvias")
        print("   El problema podría ser:")
        print("   - Mintlify parseando JSON como YAML (más estricto)")
        print("   - Problema de caché de Mintlify")
        print("   - Conflicto entre schemas con allOf")


if __name__ == '__main__':
    main()

