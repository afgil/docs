#!/usr/bin/env python3
"""
Script para verificar que los ejemplos de curl se estén mostrando
en la documentación de Mintlify.
"""

import webbrowser
import time
import subprocess

def open_documentation():
    """Abrir la documentación en el navegador"""
    
    url = "http://localhost:3003/api-reference/documents-batch"
    
    print("🌐 Abriendo documentación en el navegador...")
    print(f"📍 URL: {url}")
    print("")
    print("🔍 Verifica que puedas ver:")
    print("  ✅ Los ejemplos de curl/request")
    print("  ✅ Los botones interactivos para diferentes lenguajes")
    print("  ✅ La documentación del endpoint POST /documents/batch")
    print("")
    
    # Intentar abrir en el navegador
    try:
        webbrowser.open(url)
        print("✅ Navegador abierto automáticamente")
    except:
        print("⚠️  No se pudo abrir automáticamente. Copia esta URL en tu navegador:")
        print(f"   {url}")
    
    print("")
    print("💡 Si los ejemplos de curl NO aparecen:")
    print("   1. Verifica que Mintlify esté ejecutándose")
    print("   2. Recarga la página (Ctrl+F5)")
    print("   3. Revisa la consola del navegador por errores")
    
    # Mantener el script ejecutándose
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Script terminado")

if __name__ == "__main__":
    open_documentation()
