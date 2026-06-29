# Tutorial del Módulo Odoo — Banco de la Nación (SBS Regulatorio)

## Tabla de Contenidos

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Módulo](#2-arquitectura-del-módulo)
3. [Instalación](#3-instalación)
4. [Configuración Inicial](#4-configuración-inicial)
5. [Módulo de Ventas](#5-módulo-de-ventas)
6. [Módulo de Compras](#6-módulo-de-compras)
7. [Módulo de Inventario](#7-módulo-de-inventario)
8. [Módulo de Contabilidad](#8-módulo-de-contabilidad)
9. [Reportes Regulatorios SBS](#9-reportes-regulatorios-sbs)
10. [Automatizaciones](#10-automatizaciones)
11. [Alertas Regulatorias](#11-alertas-regulatorias)
12. [Auditoría y Trazabilidad](#12-auditoría-y-trazabilidad)
13. [Integración con Wazuh SIEM](#13-integración-con-wazuh-siem)
14. [Referencia Técnica](#14-referencia-técnica)

---

## 1. Descripción General

El módulo **Banco de la Nación — SBS Regulatorio** es una extensión de Odoo 17 diseñada para la gestión regulatoria bancaria peruana. Integra los módulos core de Odoo (Ventas, Compras, Inventario, Contabilidad) con funcionalidades especializadas para cumplir con las exigencias de la **Superintendencia de Banca, Seguros y AFP (SBS)**.

### Funcionalidades Clave

| Funcionalidad | Descripción |
|--------------|-------------|
| Reportes SBS | Generación de reportes regulatorios en XML, CSV, XLSX y TXT |
| Automatizaciones | Reglas automatizadas para conciliación, reporting y compliance |
| Alertas | Monitoreo de transacciones, cumplimiento PLA/FT y riesgos |
| Auditoría | Trazabilidad con encadenamiento hash (SHA-256) para integridad |
| SIEM | Integración con Wazuh para seguridad y logging centralizado |
| Localización Peruana | Plan Contable PCGE, IGV, detracciones, facturación electrónica |

### Dependencias

```
base, web, account, account_audit_trail, sale, purchase, stock, mail, board, l10n_pe
```

---

## 2. Arquitectura del Módulo

```
banco_nacion/
├── __init__.py                  # Punto de entrada
├── __manifest__.py              # Declaración del módulo
├── controllers/
│   └── __init__.py              # (vacío - sin controladores HTTP)
├── data/
│   ├── automated_actions.xml    # 7 reglas de automatización predefinidas
│   ├── email_templates.xml      # 3 plantillas de correo
│   └── sbs_regulatory_data.xml  # 1 reporte demo: Estados Financieros
├── models/
│   ├── __init__.py              # Importa los 6 modelos
│   ├── sbs_report.py            # SBSRegulatoryReport, SBSReportLine
│   ├── audit_trail.py           # AuditTrailEntry (hash-chained)
│   ├── automated_action.py      # AutomatedActionLog, AutomatedActionRule
│   ├── alert_rule.py            # AlertRule, AlertRuleInstance
│   ├── wazuh_siem.py            # WazuhSIEMEvent, WazuhIntegrationConfig
│   └── bank_config.py           # BankConfigParams (configuración del sistema)
├── reports/
│   ├── sbs_reports.xml          # 3 acciones de reporte (PDF/HTML)
│   └── report_templates.xml     # Plantillas QWeb
├── security/
│   ├── ir.model.access.csv      # 15 entradas de control de acceso
│   └── security.xml             # 5 grupos + 3 reglas de registro
├── static/
│   └── description/.gitkeep
├── views/
│   ├── menu_views.xml           # Jerarquía completa del menú
│   ├── sbs_report_views.xml     # Vistas tree/form/search/graph/pivot
│   ├── audit_trail_views.xml    # Vistas de trazabilidad
│   └── automated_action_views.xml  # Vistas de automatización
└── wizard/
    ├── __init__.py              # Importa el wizard
    ├── sbs_report_wizard.py     # SBSReportWizard (TransientModel)
    └── sbs_report_wizard.xml    # Formulario del wizard + secuencia
```

### Modelos de Datos (6 modelos, 9 clases)

| Modelo Técnico | Clase Python | Propósito |
|---------------|-------------|-----------|
| `sbs.regulatory.report` | `SBSRegulatoryReport` | Reporte regulatorio maestro |
| `sbs.report.line` | `SBSReportLine` | Líneas de detalle del reporte |
| `audit.trail.entry` | `AuditTrailEntry` | Entrada de auditoría encadenada |
| `automated.action.rule` | `AutomatedActionRule` | Regla de automatización |
| `automated.action.log` | `AutomatedActionLog` | Registro de ejecución |
| `alert.rule` | `AlertRule` | Regla de alerta |
| `alert.rule.instance` | `AlertRuleInstance` | Instancia de alerta disparada |
| `wazuh.siem.event` | `WazuhSIEMEvent` | Evento de seguridad SIEM |
| `wazuh.integration.config` | `WazuhIntegrationConfig` | Configuración Wazuh |

---

## 3. Instalación

### 3.1 Desde Docker (Entorno del Proyecto)

```bash
# Posicionarse en el directorio del proyecto
cd /home/luciano/odoo

# Construir la imagen personalizada
docker compose build odoo

# Iniciar todos los servicios
docker compose up -d

# Verificar que todo esté corriendo
docker ps
```

### 3.2 Instalar el Módulo vía Web

1. Acceder a `http://localhost:8069/web`
2. Ir a **Aplicaciones** → buscar `banco_nacion`
3. Hacer clic en **Instalar**

### 3.3 Instalar vía Línea de Comandos

```bash
docker exec -u odoo banco_nacion_odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d odoo_banco_nacion \
  -i banco_nacion \
  --stop-after-init
```

Para instalar todos los módulos core junto con el banco:

```bash
docker exec -u odoo banco_nacion_odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d odoo_banco_nacion \
  -i sale_management,purchase,stock,account,l10n_pe,banco_nacion \
  --stop-after-init
```

### 3.4 Verificar Instalación

```sql
-- Desde el contenedor de BD
docker exec banco_nacion_db psql -U odoo -d odoo_banco_nacion \
  -c "SELECT name, state FROM ir_module_module WHERE name='banco_nacion';"
```

---

## 4. Configuración Inicial

### 4.1 Configuración General del Banco

Ir a: **SBS Regulatorio → Configuración**

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| Código de Entidad SBS | `0001` | Código asignado por SBS |
| Email de Notificaciones SBS | `sbs-reportes@banconacion.pe` | Correo para envío de reportes |
| Wazuh Manager IP | `wazuh.manager.local` | Dirección del servidor Wazuh |
| Wazuh Agente | `odoo-banco-nacion` | Nombre del agente en Wazuh |
| Intentos máx. de login | `5` | Política de seguridad |
| Timeout de sesión | `30` minutos | Sesión autogestionada |

### 4.2 Grupos de Usuarios

El módulo define 5 grupos de seguridad con permisos jerárquicos:

```
base.group_user
  └── SBS - Analista Regulatorio
       └── Oficial de Cumplimiento
SBS - Auditor
SBS - Administrador Regulatorio (acceso total)
Administrador de Automatizaciones (base.group_system)
```

Para asignar un usuario a un grupo:
1. Ir a **Ajustes → Usuarios y Compañías → Usuarios**
2. Seleccionar el usuario
3. En la pestaña **Permisos de Acceso**, activar el grupo correspondiente

---

## 5. Módulo de Ventas

### 5.1 Acceso

**Ventas → Configuración → Ajustes**

### 5.2 Parámetros Configurados

| Parámetro | Valor | Efecto |
|-----------|-------|--------|
| Bloquear pedidos confirmados | Activado | Evita modificaciones en pedidos confirmados |
| Política de facturación | Cantidades pedidas | Factura al confirmar el pedido |
| Advertencias en pedidos | Activado | Alerta sobre clientes con deuda pendiente |
| Firma electrónica | Activado | Aprobación digital de cotizaciones |
| Listas de precios | Activado | Precios diferenciados por cliente |
| Descuentos en línea | Activado | Descuentos por producto en líneas |
| Márgenes en pedidos | Activado | Muestra rentabilidad por línea |

### 5.3 Crear un Pedido de Venta

```python
# Ejemplo vía API XML-RPC
import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo_banco_nacion'
uid = 2  # admin user ID

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Crear pedido
order_id = models.execute_kw(db, uid, 'demo', 'sale.order', 'create', [{
    'partner_id': partner_id,
    'partner_invoice_id': partner_id,
    'partner_shipping_id': partner_id,
}])

# Agregar líneas
models.execute_kw(db, uid, 'demo', 'sale.order.line', 'create', [{
    'order_id': order_id,
    'product_id': product_id,
    'product_uom_qty': 50,
    'price_unit': 12.50,
}])

# Confirmar pedido
models.execute_kw(db, uid, 'demo', 'sale.order', 'action_confirm', [[order_id]])
```

### 5.4 Flujo de Ventas

```
Cotización → Confirmar → Entrega (Picking) → Facturar → Contabilizar
    1             2             3              4            5
```

---

## 6. Módulo de Compras

### 6.1 Acceso

**Compras → Configuración → Ajustes**

### 6.2 Parámetros Configurados

| Parámetro | Valor | Efecto |
|-----------|-------|--------|
| Bloquear órdenes confirmadas | Activado | Evita modificaciones |
| Política de factura | Cantidades recibidas | Factura al recibir mercancía |
| Advertencias de proveedor | Activado | Alertas sobre proveedores |
| Aprobación de órdenes | Activado si monto > S/. 10,000 | Control presupuestal |
| Método de costo | PEPS (FIFO) | Primero en entrar, primero en salir |

### 6.3 Crear una Orden de Compra

1. Ir a **Compras → Órdenes → Nueva orden**
2. Seleccionar proveedor
3. Agregar productos con cantidades y precios
4. La confirmación genera automáticamente una recepción

---

## 7. Módulo de Inventario

### 7.1 Acceso

**Inventario → Configuración → Ajustes**

### 7.2 Parámetros Configurados

| Parámetro | Valor | Efecto |
|-----------|-------|--------|
| Ubicaciones de almacenamiento | Activado | Múltiples almacenes/ubicaciones |
| Rutas en múltiples pasos | Activado | Recepción/despacho en 2 pasos |
| Números de lote y serie | Activado | Trazabilidad de productos |
| Fechas de vencimiento | Activado | Control de caducidad |
| Reglas de reordenamiento | Activado | Stock mínimo automático |

### 7.3 Almacén Central

Configuración del almacén principal:

| Campo | Valor |
|-------|-------|
| Nombre corto | `BN` |
| Nombre | Almacén Central Banco de la Nación |
| Recepciones | Recibir en 2 pasos (recibir + control calidad) |
| Envíos | Enviar en 2 pasos (empacar + enviar) |

### 7.4 Categorías de Producto

| Categoría | Método de Valoración |
|-----------|---------------------|
| Material de Oficina | Precio promedio (AVCO) |
| Equipos Informáticos | PEPS (FIFO) |
| Insumos de Seguridad | Precio promedio (AVCO) |
| Bienes de Activo Fijo | Precio estándar |

---

## 8. Módulo de Contabilidad

### 8.1 Configuración Fiscal

- **País fiscal**: Perú
- **Moneda**: PEN — Sol Peruano (S/.)
- **Plan contable**: PCGE (Plan Contable General Empresarial)
- **Tipo de cambio**: Diario (vinculado con SBS)

### 8.2 Impuestos Configurados

| Impuesto | Tipo | Porcentaje |
|----------|------|-----------|
| IGV | Porcentaje del precio | 18% |
| Retención SUNAT | Porcentaje del precio | 3% |
| Detracción (Servicios > S/. 700) | Porcentaje del precio | 12% |

### 8.3 Diarios Contables

| Diario | Tipo |
|--------|------|
| Ventas | Facturas de cliente (PEN) |
| Compras | Facturas de proveedor (PEN) |
| Banco | Cuenta corriente principal |
| Caja | Caja chica operaciones |
| Ajuste | Asientos de apertura y ajuste |

---

## 9. Reportes Regulatorios SBS

Este es el componente central del módulo. Permite generar, validar y enviar reportes a la SBS.

### 9.1 Acceso

**SBS Regulatorio → Reportes SBS → Reportes Regulatorios**

### 9.2 Tipos de Reporte

| Tipo | Código | Descripción |
|------|--------|-------------|
| Estados Financieros | `SBS-FIN` | Balance general, EE.FF. |
| Gestión de Riesgos | `SBS-RISK` | Riesgo crediticio, mercado, liquidez |
| Cartera Crediticia | `SBS-CRED` | Portafolio de préstamos |
| PLA/FT | `SBS-AML` | Prevención de lavado de activos |
| Liquidez | `SBS-LIQ` | Ratio de liquidez |
| Capital | `SBS-CAP` | Patrimonio efectivo |
| Provisiones | `SBS-PROV` | Provisiones crediticias |
| Tesorería | `SBS-TREA` | Operaciones de tesorería |

### 9.3 Estados del Reporte

```
Borrador → Generado → Validado → Enviado a SBS → Acusado Recibo
                                        ↓
                                   Rechazado (→ Borrador)
                                        ↓
                                   Cancelado
```

### 9.4 Generar un Reporte (Wizard)

1. Ir a **SBS Regulatorio → Reportes SBS → Reportes Regulatorios**
2. Hacer clic en **Generar Reporte**
3. Completar el wizard:

   | Campo | Valor Ejemplo |
   |-------|--------------|
   | Tipo de reporte | Estados Financieros |
   | Tipo de período | Mensual |
   | Fecha desde | 2026-06-01 |
   | Fecha hasta | 2026-06-30 |
   | Formato de archivo | XML |
   | Generar automáticamente | Activado |

4. Hacer clic en **Generar Reporte**

### 9.5 Añadir Líneas al Reporte

Una vez creado el reporte en estado **Borrador**:

1. Ir a la pestaña **Líneas del Reporte**
2. Hacer clic en **Añadir una línea**
3. Completar:

   | Campo | Valor |
   |-------|-------|
   | Código | `FIN-001` |
   | Descripción | Activo Corriente - Efectivo |
   | Monto | 1500000.00 |
   | Cuenta Contable | 10101 |
   | Es Anomalía | (desactivado) |

### 9.6 Validar y Enviar

1. **Validar**: Hacer clic en **Validar** → verifica integridad de datos
2. **Enviar a SBS**: Hacer clic en **Enviar a SBS** → registra fecha de envío
3. **Acusar Recibo**: Simula la recepción por parte de SBS

### 9.7 Formatos de Exportación

El módulo soporta 4 formatos de archivo:

```python
# XML - Estructura del archivo generado
<SBSReport>
  <EntityCode>0001</EntityCode>
  <ReportCode>SBS-FIN-0001</ReportCode>
  <Period>2026-06</Period>
  <ReportLines>
    <Line>
      <Code>FIN-001</Code>
      <Description>Activo Corriente</Description>
      <Amount>1500000.00</Amount>
      <AccountCode>10101</AccountCode>
    </Line>
  </ReportLines>
</SBSReport>

# CSV - Encabezados
# Codigo,Descripcion,Monto,Cuenta Contable,Es Anomalia,Notas

# XLSX - Libro Excel con openpyxl

# TXT - Texto plano delimitado
```

### 9.8 Hash de Integridad

Cada reporte genera un hash SHA-256 para verificar su integridad:

```python
hash_input = f"{report.code}|{report.date_from}|{report.date_to}|{total_amount}"
audit_hash = hashlib.sha256(hash_input.encode()).hexdigest()
```

---

## 10. Automatizaciones

### 10.1 Acceso

**SBS Regulatorio → Automatizaciones → Reglas de Automatización**

### 10.2 Reglas Predefinidas

El módulo instala 7 reglas de automatización:

| Regla | Tipo de Acción | Disparador | Descripción |
|-------|---------------|------------|-------------|
| Conciliación Bancaria Diaria | `reconciliation` | Programado (cron) | Concilia movimientos bancarios |
| Reporte SBS Mensual | `sbs_report` | Programado | Genera reporte SBS automático |
| Verificación PLA/FT | `aml_check` | Al guardar (`account.move`) | Revisa transacciones > S/. 10,000 |
| Cumplimiento Normativo SBS | `compliance_check` | Programado | Verifica cumplimiento regulatorio |
| Cálculo de Provisiones | `provision_calc` | Programado | Calcula provisiones crediticias |
| Alerta de Tesorería | `treasury_alert` | Por condición | Monitorea límite de liquidez |
| Reporte Diario Operaciones | `sbs_report` | Programado | Reporte diario de operaciones |

### 10.3 Configurar una Regla

1. Seleccionar una regla existente o crear nueva
2. Configurar:

   | Sección | Campos |
   |---------|--------|
   | **General** | Nombre, tipo de acción, tipo de disparador |
   | **Condiciones** | Modelo, campo, operador, valor |
   | **Ejecución** | Código Python o acción del servidor |
   | **Notificaciones** | Usuarios a notificar en éxito/fallo |
   | **Control** | Reintentos, timeout, ejecución concurrente |

### 10.4 Ejecutar Manualmente

Desde el formulario de la regla, hacer clic en **Ejecutar Ahora** para probar la regla sin esperar el disparador programado.

### 10.5 Historial de Ejecución

**SBS Regulatorio → Automatizaciones → Historial de Ejecución**

Muestra el registro de todas las ejecuciones con estado, duración, errores y trazabilidad.

---

## 11. Alertas Regulatorias

### 11.1 Acceso

**SBS Regulatorio → Alertas Regulatorias**

(Solo visible para el grupo **Oficial de Cumplimiento**)

### 11.2 Tipos de Alerta

| Tipo | Ejemplo de Uso |
|------|---------------|
| Regulatoria | Cambio en normativa SBS |
| Compliance | Incumplimiento de políticas internas |
| Riesgo | Concentración de crédito excesiva |
| Fraude | Transacción sospechosa |
| AML/PLA/FT | Posible lavado de activos |
| Financiera | Variación atípica en estados financieros |
| Seguridad | Intento de acceso no autorizado |
| Operacional | Error en proceso batch |

### 11.3 Estados de una Alerta

```
Nueva → Reconocida → Investigando → Resuelta
  ↓                                  ↓
  └→ Falso Positivo           Escalada
```

### 11.4 Ciclo de Vida de una Alerta

1. **Se dispara** automáticamente por una regla o manualmente
2. **Notifica** a los usuarios asignados vía correo/notificación interna
3. **Se investiga** por el Oficial de Cumplimiento
4. **Se resuelve** o **escala** según la gravedad

### 11.5 Crear una Regla de Alerta Personalizada

```python
# Ejemplo: Alerta para transacciones > S/. 50,000
{
    'name': 'Transacciones Mayoristas > S/. 50,000',
    'alert_type': 'aml',
    'model_id': modelo_account_move,
    'condition_domain': "[('amount_total', '>', 50000)]",
    'condition_field': 'amount_total',
    'condition_operator': '>',
    'condition_value_float': 50000.0,
    'priority': 'high',
    'notify_method': 'both',  # email + notification
    'auto_action': 'flag_record',
}
```

---

## 12. Auditoría y Trazabilidad

### 12.1 Acceso

**SBS Regulatorio → Auditoría → Trazabilidad**

(Solo visible para **SBS - Auditor** y **SBS - Administrador Regulatorio**)

### 12.2 ¿Qué se Audita?

Cada acción crítica del sistema genera una entrada de auditoría:

| Tipo de Acción | Cuándo se Dispara |
|---------------|-------------------|
| `create` | Creación de registros críticos |
| `write` | Modificación de registros |
| `unlink` | Eliminación de registros |
| `validate` | Validación de reportes SBS |
| `submit` | Envío a SBS |
| `sbs_submission` | Confirmación de recepción SBS |
| `config_change` | Cambio en configuración del banco |
| `alert` | Generación de alerta |
| `automation` | Ejecución de automatización |
| `login` / `logout` | Inicio/cierre de sesión |

### 12.3 Hash Chain (Encadenamiento)

El módulo implementa un sistema de integridad mediante encadenamiento de hashes SHA-256:

```
Entrada 1: hash(prev_hash="0" + id=1 + action="create" + desc + fecha)
     ↓
Entrada 2: hash(prev_hash=hash_1 + id=2 + action="validate" + desc + fecha)
     ↓
Entrada 3: hash(prev_hash=hash_2 + id=3 + action="submit" + desc + fecha)
     ↓
    ...
```

**Verificar la integridad de la cadena:**
1. Abrir cualquier entrada de auditoría
2. Hacer clic en **Verificar Integridad**
3. El sistema recalcula toda la cadena y muestra si ha sido alterada

### 12.4 Estructura de una Entrada

| Campo | Descripción |
|-------|-------------|
| Fecha/Hora | Marca de tiempo automática |
| Tipo de Acción | Categoría de la acción (ver lista arriba) |
| Modelo | Nombre técnico del modelo afectado |
| ID de Registro | ID del registro en el modelo |
| Descripción | Texto legible de lo ocurrido |
| Usuario | Quién realizó la acción |
| IP | Dirección IP del usuario |
| Valor Anterior | Snapshot antes del cambio |
| Valor Nuevo | Snapshot después del cambio |
| Hash SHA-256 | Hash de integridad encadenado |
| Entrada Anterior | ID de la entrada previa en la cadena |

---

## 13. Integración con Wazuh SIEM

### 13.1 Arquitectura

```
Odoo ──log──> Wazuh Agent ──> Wazuh Manager ──> Wazuh Dashboard
  │                                                  │
  └── Eventos SIEM (wazuh.siem.event) ──────────────┘
```

### 13.2 Configuración

1. Ir a **SBS Regulatorio → Configuración**
2. Sección **Wazuh SIEM**:

   | Campo | Valor |
   |-------|-------|
   | Wazuh Manager IP | IP del servidor Wazuh |
   | Agente | Nombre identificador del agente |
   | Habilitado | Activado/Desactivado |

3. Seleccionar qué eventos forwardear:

   - Logs de auditoría
   - Acciones automatizadas
   - Alertas generadas
   - Errores del sistema
   - Reportes SBS
   - Intentos de login

### 13.3 Tipos de Eventos SIEM

| Tipo | Severidad | Descripción |
|------|-----------|-------------|
| `alert` | 3 (Warning) | Alerta regulatoria disparada |
| `audit` | 4 (Warning) | Cambio en configuración de auditoría |
| `automation` | 5 (Notice) | Ejecución de automatización |
| `system` | 5 (Notice) | Evento del sistema |
| `security` | 3 (Warning) | Intento de acceso no autorizado |
| `regulatory` | 4 (Warning) | Reporte SBS generado/enviado |
| `compliance` | 4 (Warning) | Verificación de cumplimiento |
| `error` | 2 (Critical) | Error en proceso crítico |

---

## 14. Referencia Técnica

### 14.1 API XML-RPC

**Endpoint**: `http://localhost:8069/xmlrpc/2/object`

Ejemplo: Listar reportes SBS:

```python
import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo_banco_nacion'
username = 'admin'
password = 'demo'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

reports = models.execute_kw(db, uid, password,
    'sbs.regulatory.report', 'search_read',
    [[('state', '=', 'validated')]],
    {'fields': ['name', 'code', 'total_amount', 'state'], 'limit': 10})
```

Ejemplo: Generar reporte vía wizard:

```python
wizard_id = models.execute_kw(db, uid, password,
    'sbs.report.wizard', 'create', [{
        'report_type': 'financial_statements',
        'period_type': 'monthly',
        'date_from': '2026-06-01',
        'date_to': '2026-06-30',
        'file_format': 'xml',
        'generate_automatically': True,
    }])

result = models.execute_kw(db, uid, password,
    'sbs.report.wizard', 'action_generate_report', [[wizard_id]])
```

### 14.2 Comandos Docker Útiles

```bash
# Ver logs en tiempo real
docker compose logs -f odoo

# Reiniciar solo Odoo
docker compose restart odoo

# Backup de base de datos
docker exec banco_nacion_db pg_dump -U odoo odoo_banco_nacion \
  > backup_$(date +%Y%m%d_%H%M).sql

# Restaurar backup
docker exec -i banco_nacion_db psql -U odoo odoo_banco_nacion \
  < backup_20260614_1200.sql

# Actualizar módulo banco_nacion
docker exec -u odoo banco_nacion_odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d odoo_banco_nacion \
  -u banco_nacion \
  --stop-after-init

# Acceder a la consola de Odoo
docker exec -u odoo -it banco_nacion_odoo odoo shell \
  -c /etc/odoo/odoo.conf -d odoo_banco_nacion --no-http
```

### 14.3 Verificación del Sistema

```
 Servicio          Puerto   Estado
 PostgreSQL        5432     Healthy
 Odoo              8069     Running
 Odoo Longpolling  8072     Running
 Nginx HTTP        80       Running
 Nginx HTTPS       443      Running
 Redis             6379     Healthy
```

**Checklist de verificación:**

- [ ] Todos los contenedores en estado `healthy`
- [ ] `http://localhost:8069` carga la página de login de Odoo
- [ ] Módulo `banco_nacion` instalado (Aplicaciones → Módulos instalados)
- [ ] Menú **SBS Regulatorio** visible en la barra lateral
- [ ] Contactos demo cargados (Clientes + Proveedores)
- [ ] Productos demo cargados con precios
- [ ] Pedido de venta confirmado con picking generado
- [ ] Orden de compra confirmada con recepción pendiente
- [ ] Reporte SBS demo visible en **SBS Regulatorio → Reportes Regulatorios**
- [ ] Reglas de automatización cargadas (7 reglas)
- [ ] Grupos de seguridad asignados correctamente

---

### 14.4 Archivos Clave del Proyecto

```
/home/luciano/odoo/
├── docker-compose.yml          # Orquestación de servicios
├── Dockerfile                  # Imagen Odoo personalizada
├── .env                        # Variables de entorno
├── odoo/config/odoo.conf       # Configuración de Odoo
├── odoo/custom_addons/         # Módulos personalizados
│   └── banco_nacion/           # ← Este módulo
├── nginx/nginx.conf            # Proxy reverso SSL
├── scripts/
│   ├── entrypoint.sh           # Punto de entrada del contenedor
│   ├── init_db.sh              # Inicialización de BD
│   ├── configure_odoo.py       # Script de parametrización
│   └── setup_wazuh.sh          # Configuración Wazuh
├── volumes/
│   ├── postgres_data/          # Datos persistentes PostgreSQL
│   ├── odoo_data/              # Filestore de Odoo
│   └── odoo_logs/              # Logs de Odoo
└── wazuh/
    ├── agent/ossec.conf        # Configuración Wazuh agent
    ├── decoders/               # Decoders personalizados
    └── rules/                  # Reglas de correlación
```

---

## Resumen

El módulo **Banco de la Nación — SBS Regulatorio** transforma Odoo 17 en un sistema ERP bancario preparado para cumplir con las exigencias regulatorias peruanas. Sus pilares fundamentales son:

1. **Reportes SBS**: Generación, validación y envío de reportes regulatorios en múltiples formatos
2. **Automatizaciones**: Reglas inteligentes que ejecutan tareas críticas sin intervención manual
3. **Alertas**: Monitoreo proactivo de transacciones, riesgos y cumplimiento normativo
4. **Auditoría**: Trazabilidad inmutable con hash chain para integridad forense
5. **SIEM**: Integración con Wazuh para seguridad centralizada y correlación de eventos
6. **Localización**: Adaptación completa al marco contable y tributario peruano (PCGE, IGV, SUNAT)

> **Nota**: Este tutorial asume que el sistema está desplegado con Docker Compose según el Informe 4 del proyecto. Para entornos de producción, se recomienda revisar las configuraciones de seguridad (SSL, rate limiting, backups) y escalabilidad (workers, conexiones concurrentes).
