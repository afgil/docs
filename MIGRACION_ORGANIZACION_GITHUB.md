# Migración de Repositorios a la Organización Tu-Pana

## Repositorios Actuales

Los siguientes repositorios están actualmente bajo el usuario `afgil` y necesitan migrarse a la organización `Tu-Pana`:

1. **pana-backend**: `git@github.com:afgil/pana-backend.git`
2. **pana-frontend**: `git@github.com:afgil/pana-frontend.git`
3. **docs**: `git@github.com:afgil/docs.git`

## Requisitos Previos

### 1. Permisos en la Organización Tu-Pana

Asegúrate de tener los siguientes permisos en la organización `Tu-Pana`:

- **Owner** o **Admin** de la organización
- Permisos para crear/transferir repositorios
- Permisos para configurar GitHub Actions y Secrets

### 2. Acceso SSH a GitHub

Verifica que tu clave SSH esté configurada correctamente:

```bash
ssh -T git@github.com
```

Deberías ver un mensaje como: `Hi Tu-Pana! You've successfully authenticated...`

### 3. Verificar Membresía en la Organización

1. Ve a: <https://github.com/orgs/Tu-Pana/people>
2. Confirma que tu usuario (`afgil`) está en la organización
3. Verifica que tengas el rol adecuado (Owner/Admin)

## Opción 1: Transferir Repositorios (Recomendado)

Esta opción mantiene todo el historial, issues, PRs, releases, etc.

### Pasos para Transferir

1. **Para cada repositorio, ve a Settings → General → Danger Zone → Transfer ownership**

   - **pana-backend**: <https://github.com/afgil/pana-backend/settings>
   - **pana-frontend**: <https://github.com/afgil/pana-frontend/settings>
   - **docs**: <https://github.com/afgil/docs/settings>

2. **Ingresa el nombre de la organización**: `Tu-Pana`

3. **Confirma la transferencia** (se pedirá el nombre completo del repositorio)

4. **Espera la confirmación por email**

### Después de la Transferencia

Los repositorios quedarán en:

- `git@github.com:Tu-Pana/pana-backend.git`
- `git@github.com:Tu-Pana/pana-frontend.git`
- `git@github.com:Tu-Pana/docs.git`

## Opción 2: Crear Nuevos Repositorios y Migrar

Si prefieres crear repositorios nuevos en la organización:

### Pasos

1. **Crear repositorios en la organización**:
   - Ve a: <https://github.com/organizations/Tu-Pana/repositories/new>
   - Crea: `pana-backend`, `pana-frontend`, `docs`
   - **NO inicialices con README, .gitignore o licencia** (ya tienes el código)

2. **Agregar remotes y hacer push**:

```bash
# Para pana-backend
cd /Users/antoniogil/dev/tupana/pana-backend
git remote add tu-pana git@github.com:Tu-Pana/pana-backend.git
git push tu-pana master --all
git push tu-pana --tags

# Para pana-frontend
cd /Users/antoniogil/dev/tupana/pana-frontend
git remote add tu-pana git@github.com:Tu-Pana/pana-frontend.git
git push tu-pana master --all
git push tu-pana --tags

# Para docs
cd /Users/antoniogil/dev/tupana/docs
git remote add tu-pana git@github.com:Tu-Pana/docs.git
git push tu-pana master --all
git push tu-pana --tags
```

## Actualizar Remotes Locales

Después de la transferencia o migración, actualiza los remotes en cada repositorio:

### Script de Actualización

```bash
# pana-backend
cd /Users/antoniogil/dev/tupana/pana-backend
git remote set-url origin git@github.com:Tu-Pana/pana-backend.git
git remote -v  # Verificar

# pana-frontend
cd /Users/antoniogil/dev/tupana/pana-frontend
git remote set-url origin git@github.com:Tu-Pana/pana-frontend.git
git remote -v  # Verificar

# docs
cd /Users/antoniogil/dev/tupana/docs
git remote set-url origin git@github.com:Tu-Pana/docs.git
git remote -v  # Verificar
```

## Actualizar GitHub Actions

### 1. Verificar Secrets en la Organización

Los secrets deben estar configurados a nivel de organización:

1. Ve a: <https://github.com/organizations/Tu-Pana/settings/secrets/actions>
2. Asegúrate de que todos los secrets necesarios estén configurados:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `RESEND_API_KEY`
   - Cualquier otro secret que uses

### 2. Actualizar Referencias en Workflows (si es necesario)

Los workflows de GitHub Actions deberían funcionar automáticamente, pero verifica:

- **`.github/workflows/deploy.yml`**: No debería necesitar cambios
- **`.github/workflows/test.yml`**: No debería necesitar cambios

### 3. Verificar Permisos de GitHub Actions

1. Ve a: <https://github.com/organizations/Tu-Pana/settings/actions>
2. Configura:
   - **Actions permissions**: Permitir todas las acciones
   - **Workflow permissions**: Read and write permissions (si es necesario para deployments)

## Configurar Branch Protections (CRÍTICO)

**⚠️ IMPORTANTE**: Las branch protections NO se transfieren automáticamente. Debes configurarlas manualmente después de la migración.

### ¿Por qué son importantes?

Las branch protections garantizan que:

- Los tests pasen antes de mergear PRs
- Se requieran reviews de código
- No se pueda hacer force push a la rama principal
- No se pueda eliminar la rama principal accidentalmente
- Solo se pueda hacer deploy desde la rama protegida

### Configuración para cada repositorio

#### 1. pana-backend

1. Ve a: <https://github.com/Tu-Pana/pana-backend/settings/branches>
2. Haz clic en **"Add branch protection rule"**
3. En **"Branch name pattern"**, ingresa: `master`
4. Configura las siguientes opciones:

   **✅ Require a pull request before merging**
   - ✅ Require approvals: **1** (mínimo)
   - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require review from Code Owners (si tienes CODEOWNERS configurado)

   **✅ Require status checks to pass before merging**
   - ✅ Require branches to be up to date before merging
   - En **"Status checks that are required"**, agrega:
     - `validate` (del workflow deploy.yml)
     - `test` (del workflow deploy.yml)
     - `prepare_deploy` (del workflow deploy.yml)
     - `deploy` (del workflow deploy.yml)

   **✅ Require conversation resolution before merging**
   - ✅ Require all conversations on code to be resolved

   **✅ Include administrators**
   - ✅ Incluir administradores en estas reglas

   **✅ Restrict who can push to matching branches**
   - Dejar vacío (todos los miembros con permisos pueden crear PRs)

   **✅ Do not allow bypassing the above settings**
   - ✅ No permitir bypass (incluso para admins)

   **✅ Allow force pushes**
   - ❌ NO permitir force pushes

   **✅ Allow deletions**
   - ❌ NO permitir eliminar la rama

5. Haz clic en **"Create"**

#### 2. pana-frontend

1. Ve a: <https://github.com/Tu-Pana/pana-frontend/settings/branches>
2. Configura similar a pana-backend:
   - Branch pattern: `master` o `main` (según tu rama principal)
   - Require PR before merging: **Sí**
   - Require approvals: **1**
   - Require status checks: **Sí** (si tienes workflows configurados)
   - No permitir force pushes
   - No permitir eliminaciones

#### 3. docs

1. Ve a: <https://github.com/Tu-Pana/docs/settings/branches>
2. Configura similar, pero puede ser menos estricto:
   - Branch pattern: `main` o `master`
   - Require PR before merging: **Sí** (recomendado)
   - Require approvals: **1** (opcional, pero recomendado)
   - No permitir force pushes
   - No permitir eliminaciones

### Verificar que las Branch Protections funcionen

Después de configurar:

1. **Crear una PR de prueba**:

   ```bash
   git checkout -b test/branch-protection
   git commit --allow-empty -m "test: verificar branch protection"
   git push origin test/branch-protection
   ```

2. **Verificar que**:
   - ✅ No puedes mergear sin que pasen los tests
   - ✅ No puedes mergear sin aprobación
   - ✅ No puedes hacer force push a master
   - ✅ No puedes eliminar la rama master

3. **Eliminar la rama de prueba**:

   ```bash
   git checkout master
   git branch -D test/branch-protection
   git push origin --delete test/branch-protection
   ```

### Troubleshooting

Si los status checks no aparecen en la lista:

1. **Ejecuta el workflow manualmente**:
   - Ve a Actions → Selecciona el workflow → Run workflow
   - Esto creará el primer status check

2. **Verifica que los jobs tengan el mismo nombre**:
   - Los nombres en `deploy.yml` deben coincidir con los que configuraste
   - Ejemplo: `validate`, `test`, `prepare_deploy`, `deploy`

3. **Espera a que se ejecute al menos una vez**:
   - Los status checks aparecen después de la primera ejecución exitosa

## Actualizar Webhooks (si aplica)

Si tienes webhooks configurados:

1. Ve a cada repositorio → Settings → Webhooks
2. Verifica que las URLs sigan siendo válidas
3. Actualiza si es necesario

## Verificar Integraciones

### 1. Verificar Integraciones de Terceros

- **Vercel** (si usas para frontend): Actualizar el repositorio conectado
- **AWS**: Verificar que las credenciales funcionen
- **Resend**: Verificar que la API key funcione
- **Cualquier otro servicio**: Actualizar referencias al nuevo repositorio

### 2. Actualizar Documentación

Busca y actualiza referencias a los repositorios antiguos en:

- README.md
- Documentación
- Scripts
- Configuraciones

## Checklist Final

- [ ] Repositorios transferidos/creados en Tu-Pana
- [ ] Remotes locales actualizados
- [ ] GitHub Actions secrets configurados en la organización
- [ ] Permisos de GitHub Actions verificados
- [ ] **Branch protections configuradas para `master` en cada repositorio** ⚠️ CRÍTICO
  - [ ] pana-backend: Branch protection configurada
  - [ ] pana-frontend: Branch protection configurada
  - [ ] docs: Branch protection configurada
- [ ] Status checks requeridos configurados en branch protections
- [ ] PR de prueba creada para verificar branch protections
- [ ] Webhooks verificados (si aplica)
- [ ] Integraciones de terceros actualizadas
- [ ] Documentación actualizada
- [ ] Tests ejecutados para verificar que todo funciona
- [ ] Deployments verificados

## Comandos de Verificación

```bash
# Verificar remotes
cd /Users/antoniogil/dev/tupana/pana-backend && git remote -v
cd /Users/antoniogil/dev/tupana/pana-frontend && git remote -v
cd /Users/antoniogil/dev/tupana/docs && git remote -v

# Verificar que puedes hacer push
cd /Users/antoniogil/dev/tupana/pana-backend
git push origin master --dry-run

# Verificar acceso SSH
ssh -T git@github.com
```

## Notas Importantes

1. **Historial de Git**: Se mantiene completo con ambas opciones
2. **Issues y PRs**: Se mantienen solo con la Opción 1 (Transfer)
3. **Releases**: Se mantienen solo con la Opción 1 (Transfer)
4. **Stars y Forks**: Se pierden con ambas opciones (son específicos del repositorio original)
5. **GitHub Actions**: Deben reconfigurarse los secrets a nivel de organización

## Soporte

Si encuentras problemas durante la migración:

1. Verifica los permisos en la organización
2. Revisa los logs de GitHub Actions
3. Consulta la documentación de GitHub sobre transferencia de repositorios:
   - <https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository>
