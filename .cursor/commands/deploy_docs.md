# deploy_docs

Ejecuta el script de combinación de OpenAPI y hace push de la documentación a main.

## Instrucciones

Cuando se invoca este comando, ejecuta el siguiente proceso:

1. **Ejecutar el script de combinación de OpenAPI:**

   ```bash
   # Ejecutar el script de combinación (ya estamos en el directorio docs)
   python combine_openapi.py
   ```

2. **Verificar si hay cambios para commitear:**

   ```bash
   # Verificar el estado de git
   git status --porcelain
   ```

3. **Si hay cambios, hacer commit y push:**

   ```bash
   if [ -n "$(git status --porcelain)" ]; then
     # Agregar todos los cambios
     git add .

     # Crear commit con mensaje descriptivo
     git commit -m "docs: update API documentation"

     # Hacer push a main
     git push origin main
   else
     echo "No hay cambios para commitear"
   fi
   ```

## Requisitos

- Requiere que Python esté disponible para ejecutar el script `combine_openapi.py`
- Requiere permisos de push al repositorio docs
- El repositorio docs debe tener Git configurado correctamente

## Uso

Menciona `/deploy_docs` en el chat para ejecutar este comando.
