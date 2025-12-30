#!/usr/bin/env python3
"""
Script para verificar que la documentación Mintlify funcione correctamente
con los archivos OpenAPI divididos.
"""

import json
import requests
import subprocess
import time
import sys

def start_mintlify():
    """Iniciar Mintlify en background"""
    print("🚀 Iniciando Mintlify...")
    process = subprocess.Popen(
        ["npx", "mintlify", "dev", "--no-open", "--port", "4000"],
        cwd="/Users/antoniogil/dev/tupana/docs",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(10)  # Esperar que se inicie
    return process

def check_docs_loading():
    """Verificar que la documentación cargue correctamente"""
    try:
        response = requests.get("http://localhost:4000", timeout=5)
        if response.status_code == 200:
            print("✅ Documentación cargando correctamente")
            return True
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return False

def check_api_reference():
    """Verificar que la referencia de API funcione"""
    try:
        response = requests.get("http://localhost:4000/api-reference", timeout=5)
        if response.status_code == 200:
            print("✅ Referencia de API cargando correctamente")
            return True
        else:
            print(f"❌ Error en API reference: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión en API reference: {e}")
        return False

def main():
    # Verificar archivos JSON
    print("📋 Verificando archivos OpenAPI...")
    files = [
        'api-reference/openapi/base.json',
        'api-reference/openapi/documents.json',
        'api-reference/openapi/master-entities.json', 
        'api-reference/openapi/credentials.json',
        'api-reference/openapi/scheduled-documents.json',
        'api-reference/openapi/schemas.json'
    ]
    
    for file in files:
        try:
            with open(f"/Users/antoniogil/dev/tupana/docs/{file}", 'r') as f:
                json.load(f)
            print(f"✅ {file}: JSON válido")
        except Exception as e:
            print(f"❌ {file}: Error - {e}")
            return False
    
    # Iniciar Mintlify
    mintlify_process = start_mintlify()
    
    try:
        # Verificar carga de documentación
        docs_ok = check_docs_loading()
        api_ok = check_api_reference()
        
        if docs_ok and api_ok:
            print("\n🎉 ¡ÉXITO! La documentación funciona correctamente con archivos OpenAPI divididos")
            print("📖 Los ejemplos de curl deberían estar disponibles en la documentación")
            return True
        else:
            print("\n❌ Hay problemas con la carga de la documentación")
            return False
            
    finally:
        # Detener Mintlify
        print("🛑 Deteniendo Mintlify...")
        mintlify_process.terminate()
        mintlify_process.wait()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
