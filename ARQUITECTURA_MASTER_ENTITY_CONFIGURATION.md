# Arquitectura: MasterEntityConfiguration - Configuración Genérica y Escalable

## 1. Endpoints Existentes de Configuración

| Endpoint | Uso | Modelo |
|----------|-----|--------|
| `companies/<id>/configuration` | Config cliente (address, activity, etc.) | EntityConfiguration |
| `master-entities/<id>/invoice-auto-emails-settings/` | Correos post-emisión | MasterEntity (campos directos) |
| `master-entities/<id>/conciliation-configuration/` | Conciliación automática | EntityConciliationConfiguration |
| `master-entities/<id>/certificate-config/` | Certificado digital | - |
| `master-entities/<id>/shopify-shop-configurations/` | Shopify | ShopifyShopConfiguration |

**Problema actual:** `invoice-auto-emails-settings` es específico y la data vive en MasterEntity. No hay un patrón genérico reutilizable.

---

## 2. Propuesta: API REST Genérica por Tipo de Configuración

### 2.1 Endpoint Unificado

```
GET    /master-entities/<id>/configurations/
       → Lista tipos de configuración disponibles (y/o sus valores)

GET    /master-entities/<id>/configurations/<config_type>/
       → Obtiene la configuración de un tipo

PATCH  /master-entities/<id>/configurations/<config_type>/
       → Actualiza la configuración de un tipo
```

**Tipos iniciales:**

| `config_type` | Descripción |
|---------------|-------------|
| `auto_emails` | Correos automáticos post-emisión (antes invoice-auto-emails) |
| `conciliation` | Conciliación automática (ya existe como endpoint separado) |
| `emission` | Timeout, batch, etc. (ya existe EmissionConfiguration) |

**Ventaja:** Un solo patrón REST. Agregar nuevos tipos = registrar nuevo `config_type` sin cambiar URLs.

---

## 3. Modelo MasterEntityConfiguration

### 3.1 Enfoque: Tabla por Tipo (recomendado)

Similar a `EntityConciliationConfiguration` y `EmissionConfiguration`: **un modelo por tipo de configuración**, pero todos bajo el mismo endpoint genérico.

```
MasterEntityConfiguration (abstracto / interfaz)
    ├── AutoEmailsConfiguration   (master_entity OneToOne)
    ├── EntityConciliationConfiguration (existente)
    └── EmissionConfiguration (existente)
```

**Nuevo modelo `AutoEmailsConfiguration`** (reemplaza campos en MasterEntity):

```python
class AutoEmailsConfiguration(BasePanaModel):
    master_entity = models.OneToOneField(
        "master_entities.MasterEntity",
        on_delete=models.CASCADE,
        related_name="auto_emails_configuration",
    )
    enabled = models.BooleanField(default=False)
    to_emails = models.JSONField(default=list)   # emails globales (todos usuarios empresa)
    cc_emails = models.JSONField(default=list)
    bcc_emails = models.JSONField(default=list)
    body_template = models.TextField(null=True, blank=True)
    include_bank_info = models.BooleanField(default=False)
```

### 3.2 Alternativa: EAV (Entity-Attribute-Value)

```python
class MasterEntityConfiguration(BasePanaModel):
    master_entity = models.ForeignKey(MasterEntity, on_delete=models.CASCADE)
    config_type = models.CharField(max_length=50)  # 'auto_emails', 'custom_xyz'
    config_data = models.JSONField(default=dict)
    class Meta:
        unique_together = ['master_entity', 'config_type']
```

**Pros EAV:** muy flexible, un solo modelo.  
**Contras:** menos tipado, validaciones por tipo en código.

Para cumplir *Fat Models* y escalabilidad, se recomienda **tabla por tipo** con view genérica que enruta por `config_type`.

---

## 4. Lógica de Destinatarios (Auto Emails)

### 4.1 Reglas

1. **Contactos del cliente (receiver):** siempre se envían por defecto.
2. **Configuración por contacto:** si un contacto está configurado en la config como To/CC/BCC, va en ese rol.
3. **To, CC, BCC globales:** son correos adicionales para **todos los usuarios de la empresa** (emisora), no solo contactos del cliente.

### 4.2 Modelo de datos para destino por contacto

Para poder configurar "este contacto va en CC" o "este contacto va en BCC", se necesita una tabla de mapeo:

```python
class AutoEmailsContactDestination(BasePanaModel):
    """Override por contacto: si está configurado, el contacto va en ese rol en lugar de To por defecto."""
    auto_emails_config = models.ForeignKey(AutoEmailsConfiguration, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)  # o MasterEntity si el contacto es la entidad
    destination_type = models.CharField(max_length=10)  # 'to', 'cc', 'bcc', 'exclude'
    class Meta:
        unique_together = ['auto_emails_config', 'contact']
```

**Regla:** si un contacto tiene `destination_type` en la config, se usa ese. Si no, va en To por defecto.

### 4.3 Flujo de envío

```
1. Contactos del receiver → por defecto To
2. Para cada contacto: si existe AutoEmailsContactDestination → usar ese destination_type
3. Agregar to_emails, cc_emails, bcc_emails de la config (globales empresa)
4. Enviar
```

---

## 5. Implementación Propuesta (Fase 1)

### 5.1 Crear modelo y migrar datos

1. Crear `AutoEmailsConfiguration` en `apps/master_entities/app_models/`.
2. Migración: crear tabla + migrar datos desde `MasterEntity.invoice_auto_emails_*`.
3. Nuevo modelo opcional: `AutoEmailsContactDestination` si se quiere override por contacto.

### 5.2 View genérica

```python
# MasterEntityConfigurationView: GET/PATCH por config_type
# Registry: config_type -> (ModelClass, SerializerClass)
CONFIG_REGISTRY = {
    'auto_emails': (AutoEmailsConfiguration, AutoEmailsConfigurationSerializer),
    'conciliation': (EntityConciliationConfiguration, EntityConciliationConfigurationSerializer),
    # ...
}
```

### 5.3 URLs

```
path('master-entities/<int:pk>/configurations/', MasterEntityConfigurationListView.as_view()),
path('master-entities/<int:pk>/configurations/<str:config_type>/', MasterEntityConfigurationView.as_view()),
```

### 5.4 Compatibilidad

- Mantener `/invoice-auto-emails-settings/` como alias que redirige a `/configurations/auto_emails/` durante un tiempo.
- Frontend: cambiar a `/configurations/auto_emails/`.

---

## 6. Resumen de Cambios

| Componente | Antes | Después |
|-----------|-------|---------|
| Modelo | MasterEntity.invoice_auto_emails_* | AutoEmailsConfiguration |
| Endpoint | `/invoice-auto-emails-settings/` | `/configurations/auto_emails/` |
| To/CC/BCC | "Deben estar en Contactos" | Globales (todos usuarios empresa) |
| Contactos | Validación restrictiva | Siempre se envían; override opcional por config |

---

## 7. Checklist de Implementación

- [ ] Crear `AutoEmailsConfiguration` y migración
- [ ] Migrar datos desde MasterEntity
- [ ] Crear `MasterEntityConfigurationView` genérica
- [ ] Registrar `auto_emails` en CONFIG_REGISTRY
- [ ] Actualizar lógica de envío post-issue
- [ ] Frontend: cambiar endpoint a `/configurations/auto_emails/`
- [ ] (Opcional) `AutoEmailsContactDestination` para override por contacto
- [ ] Deprecar campos en MasterEntity (migración posterior)
