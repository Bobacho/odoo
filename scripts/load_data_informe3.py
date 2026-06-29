#!/usr/bin/env python3
"""Odoo BN - Data population based on Informe 3 (Security Incident Management)"""

import xmlrpc.client
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('odoo_data')

URL = 'http://localhost:8069'
DB = 'odoo_banco_nacion'
USER = 'admin'
PASS = 'admin'

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USER, PASS, {})
if not uid:
    logger.error("Authentication failed")
    exit(1)

models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

def call(model, method, *args):
    return models.execute_kw(DB, uid, PASS, model, method, args)

def call_kw(model, method, args, kwargs):
    return models.execute_kw(DB, uid, PASS, model, method, args, kwargs)

logger.info("=" * 60)
logger.info("CARGA DE DATOS - INFORME 3 (GESTION DE INCIDENTES DE SEGURIDAD TI)")
logger.info("=" * 60)

# ─────────────────────────────────────────────────────
# 1. CATEGORIAS DE PRODUCTOS/SERVICIOS DE SEGURIDAD
# ─────────────────────────────────────────────────────
logger.info("\n[1/6] Creando categorias de seguridad...")

security_categories = [
    'Monitoreo SIEM',
    'Seguridad Perimetral',
    'Proteccion de Datos',
    'Gestion de Identidades',
    'Auditoria y Cumplimiento',
    'Canales Digitales',
    'Core Bancario',
]

categ_ids = {}
for cat in security_categories:
    existing = call('product.category', 'search', [('name', '=', cat)])
    if existing:
        categ_ids[cat] = existing[0]
    else:
        cid = call('product.category', 'create', {'name': cat})
        categ_ids[cat] = cid
        logger.info(f"  Categoria creada: {cat}")

# ─────────────────────────────────────────────────────
# 2. PRODUCTOS/SERVICIOS DE SEGURIDAD
# ─────────────────────────────────────────────────────
logger.info("\n[2/6] Creando servicios de seguridad...")

security_products = [
    ('ISAM - IBM Security Access Manager', 'service', 'SEG-ISAM-001', 'Seguridad Perimetral', 'Control de acceso y autenticacion SSO'),
    ('WAF - Web Application Firewall', 'service', 'SEG-WAF-001', 'Seguridad Perimetral', 'Proteccion de aplicaciones web contra ataques OWASP Top 10'),
    ('Antispam Corporativo', 'service', 'SEG-SPAM-001', 'Seguridad Perimetral', 'Filtrado de correo malicioso y phishing'),
    ('IDS/IPS de Red', 'service', 'SEG-IDS-001', 'Seguridad Perimetral', 'Deteccion y prevencion de intrusiones de red'),
    ('DLP - Data Loss Prevention', 'service', 'SEG-DLP-001', 'Proteccion de Datos', 'Prevencion de fuga de informacion confidencial'),
    ('Antivirus Corporativo', 'service', 'SEG-AV-001', 'Proteccion de Datos', 'Proteccion contra malware en endpoints'),
    ('Wazuh SIEM - Gestion de Eventos', 'service', 'SEG-SIEM-001', 'Monitoreo SIEM', 'Plataforma SIEM open source para correlacion de eventos'),
    ('Core Abside - Nessa RSI', 'service', 'SEG-ABS-001', 'Core Bancario', 'Sistema core bancario para accionar restricciones'),
    ('Multired - Red de Cajeros', 'service', 'SEG-MULT-001', 'Canales Digitales', 'Red de cajeros automaticos y agentes bancarios'),
    ('App Movil BN', 'service', 'SEG-APP-001', 'Canales Digitales', 'Aplicacion movil del Banco de la Nacion'),
    ('Pagalo.pe - Plataforma Pagos', 'service', 'SEG-PAG-001', 'Canales Digitales', 'Plataforma de pagos digitales del Estado'),
    ('RENIEC - Interoperabilidad', 'service', 'SEG-REN-001', 'Gestion de Identidades', 'Consulta biometrica de identidad'),
    ('SUNAT - Interoperabilidad', 'service', 'SEG-SUN-001', 'Gestion de Identidades', 'Consulta tributaria y RUC'),
    ('Auditoria de Accesos - LDAP/AD', 'service', 'SEG-AUD-001', 'Auditoria y Cumplimiento', 'Monitoreo de autenticacion y accesos corporativos'),
    ('Reporte Regulatorio SBS', 'service', 'SEG-SBS-001', 'Auditoria y Cumplimiento', 'Generacion de reportes para la SBS (Res. 504-2021)'),
]

prod_ids = {}
for name, ptype, ref, cat, desc in security_products:
    existing = call('product.product', 'search', [('default_code', '=', ref)])
    if existing:
        prod_ids[ref] = existing[0]
    else:
        pid = call('product.product', 'create', {
            'name': name,
            'type': ptype,
            'default_code': ref,
            'categ_id': categ_ids[cat],
            'description': desc,
            'list_price': 0,
            'standard_price': 0,
        })
        prod_ids[ref] = pid
        logger.info(f"  Servicio creado: {name} [{ref}]")

# ─────────────────────────────────────────────────────
# 3. CONTACTOS (AREAS Y SISTEMAS DEL BANCO)
# ─────────────────────────────────────────────────────
logger.info("\n[3/6] Creando contactos del ecosistema BN...")

contacts = [
    ('Wazuh SIEM - Nodo Activo', 'system', 'Proveedor de alertas SIEM'),
    ('Wazuh SIEM - Nodo Pasivo', 'system', 'Respaldo del SIEM'),
    ('Core Abside - Nessa RSI', 'system', 'Sistema core bancario'),
    ('Middleware API Gateway', 'system', 'Capa de integracion REST'),
    ('Red Multired - Cajeros', 'system', 'Red de cajeros automaticos'),
    ('App Movil BN - Canales', 'system', 'Aplicacion movil'),
    ('Plataforma Pagalo.pe', 'system', 'Pagos digitales del Estado'),
    ('ISAM - Access Manager', 'system', 'Control de accesos'),
    ('Balanceador de Carga - HA', 'system', 'Infraestructura de red'),
    ('RENIEC - Servicio Externo', 'system', 'Consulta biometrica'),
    ('SUNAT - Servicio Externo', 'system', 'Consulta tributaria'),
]

contact_ids = {}
for name, ptype, desc in contacts:
    existing = call('res.partner', 'search', [('name', '=', name)])
    if existing:
        contact_ids[name] = existing[0]
    else:
        cid = call('res.partner', 'create', {
            'name': name,
            'company_type': 'company',
            'is_company': True,
            'comment': desc,
        })
        contact_ids[name] = cid
        logger.info(f"  Contacto creado: {name}")

# ─────────────────────────────────────────────────────
# 4. INCIDENTES DE SEGURIDAD DEMO
# ─────────────────────────────────────────────────────
logger.info("\n[4/6] Creando incidentes de seguridad demo...")

# We use sale.order to represent security incidents (adapted for Odoo core)
# Each incident is mapped as an order with lines representing affected services

incidents = [
    {
        'name': 'INC-2026-001 - Intento de Acceso No Autorizado a Core',
        'partner': 'ISAM - Access Manager',
        'source': 'ISAM',
        'severity': 'critical',
        'detection': '2026-06-27 14:32:00',
        'description': 'Multiple intentos de autenticacion fallidos contra el core Abside desde IP externa. 15 intentos en 3 minutos.',
        'affected': ['SEG-ISAM-001', 'SEG-ABS-001'],
        'status': 'open',
    },
    {
        'name': 'INC-2026-002 - Ataque XSS en Plataforma Pagalo.pe',
        'partner': 'WAF - Web Application Firewall',
        'source': 'WAF',
        'severity': 'high',
        'detection': '2026-06-26 09:15:00',
        'description': 'El WAF detecto y bloqueo un intento de inyeccion XSS contra el formulario de pago de Pagalo.pe. Origen: 190.x.x.x (Lima).',
        'affected': ['SEG-WAF-001', 'SEG-PAG-001'],
        'status': 'in_progress',
    },
    {
        'name': 'INC-2026-003 - Campana de Phishing dirigida a Funcionarios',
        'partner': 'Antispam Corporativo',
        'source': 'Antispam',
        'severity': 'high',
        'detection': '2026-06-25 11:45:00',
        'description': 'El filtro antispam detecto una campana de phishing con plantilla del BID. 85 correos bloqueados, 3 llegaron a bandeja de entrada.',
        'affected': ['SEG-SPAM-001'],
        'status': 'open',
    },
    {
        'name': 'INC-2026-004 - Alerta DLP - Transferencia No Autorizada',
        'partner': 'DLP - Data Loss Prevention',
        'source': 'DLP',
        'severity': 'critical',
        'detection': '2026-06-24 16:20:00',
        'description': 'DLP detecto transferencia de archivo con datos de clientes (RUCs y saldos) via USB a dispositivo no autorizado. Usuario: rquiroz@bn.pe.',
        'affected': ['SEG-DLP-001'],
        'status': 'investigating',
    },
    {
        'name': 'INC-2026-005 - Malware detectado en Estacion de Trabajo',
        'partner': 'Antivirus Corporativo',
        'source': 'Antivirus',
        'severity': 'medium',
        'detection': '2026-06-23 08:10:00',
        'description': 'Antivirus detecto Trojan.Generic.123 en estacion de trabajo del area de Operaciones. Equipo aislado de la red.',
        'affected': ['SEG-AV-001'],
        'status': 'resolved',
    },
    {
        'name': 'INC-2026-006 - Intrusion IDS/IPS - Escaneo de Puertos',
        'partner': 'IDS/IPS de Red',
        'source': 'IDS/IPS',
        'severity': 'medium',
        'detection': '2026-06-22 02:30:00',
        'description': 'El IDS detecto escaneo de puertos en el rango 1-1024 contra servidores de aplicaciones. Origen: 10.x.x.x (red interna).',
        'affected': ['SEG-IDS-001'],
        'status': 'resolved',
    },
    {
        'name': 'INC-2026-007 - Falla en Servicio de Autenticacion Multired',
        'partner': 'Red Multired - Cajeros',
        'source': 'ISAM',
        'severity': 'critical',
        'detection': '2026-06-21 10:00:00',
        'description': 'Caida del servicio de autenticacion ISAM afectando a 150 cajeros Multired a nivel nacional. Tiempo de caida: 45 minutos.',
        'affected': ['SEG-ISAM-001', 'SEG-MULT-001'],
        'status': 'resolved',
    },
    {
        'name': 'INC-2026-008 - Consulta Masiva a RENIEC (Posible Fraude)',
        'partner': 'RENIEC - Servicio Externo',
        'source': 'Core Abside',
        'severity': 'high',
        'detection': '2026-06-20 15:00:00',
        'description': 'El core Abside detecto 500 consultas biometricas a RENIEC en 10 minutos desde una misma session. Posible suplantacion de identidad.',
        'affected': ['SEG-REN-001', 'SEG-ABS-001'],
        'status': 'investigating',
    },
]

# Build a map from system partner names to their IDs
partner_map = {
    'ISAM': 'ISAM - Access Manager',
    'WAF': 'Wazuh SIEM - Nodo Activo',
    'Antispam': 'Wazuh SIEM - Nodo Activo',
    'DLP': 'Wazuh SIEM - Nodo Activo',
    'Antivirus': 'Wazuh SIEM - Nodo Activo',
    'IDS/IPS': 'Wazuh SIEM - Nodo Activo',
    'Core Abside': 'Core Abside - Nessa RSI',
    'RENIEC': 'RENIEC - Servicio Externo',
    'App BN': 'App Movil BN - Canales',
    'Pagalo.pe': 'Plataforma Pagalo.pe',
}

for inc in incidents:
    partner_name = partner_map.get(inc['source'])
    partner_id = contact_ids.get(partner_name or inc['partner'])
    if not partner_id:
        logger.warning(f"  Partner no encontrado: {inc.get('partner')} (source: {inc['source']})")
        continue
    
    order_vals = {
        'name': inc['name'],
        'partner_id': partner_id,
        'note': inc['description'],
        'date_order': inc['detection'],
        'state': 'sale' if inc['status'] == 'confirmed' else 'draft',
    }
    
    try:
        order_id = call('sale.order', 'create', order_vals)
        
        # Add affected services as order lines
        for prod_ref in inc['affected']:
            prod_id = prod_ids.get(prod_ref)
            if prod_id:
                call('sale.order.line', 'create', {
                    'order_id': order_id,
                    'product_id': prod_id,
                    'product_uom_qty': 1,
                    'price_unit': 0,
                })
        
        logger.info(f"  Incidente creado: {inc['name']} (ID {order_id})")
        
        # Add a message/note to the order
        call_kw('sale.order', 'message_post', [[order_id]], {
            'body': f"<strong>Fuente:</strong> {inc['source']}<br/><strong>Severidad:</strong> {inc['severity'].upper()}<br/><strong>Descripcion:</strong> {inc['description']}"
        })
        
    except Exception as e:
        logger.error(f"  Error creando incidente {inc['name']}: {e}")

# ─────────────────────────────────────────────────────
# 5. CONFIGURACION DEL SISTEMA
# ─────────────────────────────────────────────────────
logger.info("\n[5/6] Configurando parametros del sistema...")

config_params = {
    'sbs_entity_code': '0001',
    'sbs_notification_email': 'sbs-reportes@banconacion.pe',
    'wazuh_manager_ip': 'wazuh.manager.local',
    'wazuh_agent_name': 'odoo-banco-nacion',
    'wazuh_enabled': 'True',
    'automation_enabled': 'True',
    'auto_reconciliation': 'True',
    'auto_sbs_reports': 'True',
    'auto_aml_checks': 'True',
    'max_login_attempts': '5',
    'session_timeout_minutes': '30',
    'two_factor_auth': 'True',
}

for key, value in config_params.items():
    try:
        call('ir.config_parameter', 'set_param', key, value)
        logger.info(f"  config {key} = {value}")
    except Exception as e:
        logger.warning(f"  Error setting {key}: {e}")

# ─────────────────────────────────────────────────────
# 6. VERIFICACION FINAL
# ─────────────────────────────────────────────────────
logger.info("\n[6/6] Verificando datos cargados...")

total_products = call('product.product', 'search_count', [])
total_partners = call('res.partner', 'search_count', [])
total_orders = call('sale.order', 'search_count', [])
total_categories = call('product.category', 'search_count', [])

logger.info(f"  Categorias de seguridad: {total_categories}")
logger.info(f"  Servicios/productos: {total_products}")
logger.info(f"  Contactos del ecosistema: {total_partners}")
logger.info(f"  Incidentes de seguridad: {total_orders}")

logger.info("\n" + "=" * 60)
logger.info("CARGA DE DATOS COMPLETADA - CONTEXTO INFORME 3")
logger.info("=" * 60)
