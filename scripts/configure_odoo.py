#!/usr/bin/env python3
"""Odoo BN - Configuration Script for Ventas, Compras, Inventario, Finanzas"""

import xmlrpc.client
import logging
import sys

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('odoo_config')

URL = 'http://localhost:8069'
DB = 'odoo_banco_nacion'
USER = 'admin'
PASS = 'demo'

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USER, PASS, {})
if not uid:
    logger.error("Authentication failed")
    sys.exit(1)
logger.info(f"Authenticated as UID {uid}")

models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

def call(model, method, *args):
    return models.execute_kw(DB, uid, PASS, model, method, args)

def call_kw(model, method, args, kwargs):
    return models.execute_kw(DB, uid, PASS, model, method, args, kwargs)

PERU_COUNTRY_ID = None

def get_peru_country():
    global PERU_COUNTRY_ID
    if PERU_COUNTRY_ID is None:
        res = call_kw('res.country', 'search_read', [[('code', '=', 'PE')]], {'fields': ['id'], 'limit': 1})
        PERU_COUNTRY_ID = res[0]['id'] if res else 604
    return PERU_COUNTRY_ID

def set_config(params):
    """Set multiple config parameters via res.config.settings"""
    for key, value in params.items():
        existing = call('ir.config_parameter', 'get_param', key)
        call('ir.config_parameter', 'set_param', key, str(value))
        logger.info(f"  config {key} = {value} (was: {existing})")

def create_partner(name, ptype, ruc, email, phone, street, payment_term=None):
    vals = {
        'name': name,
        'company_type': 'company',
        'company_registry': ruc,
        'email': email,
        'phone': phone,
        'street': street,
        'country_id': get_peru_country(),
        'is_company': True,
    }
    if ptype == 'customer':
        vals['customer_rank'] = 1
    elif ptype == 'supplier':
        vals['supplier_rank'] = 1
    if payment_term:
        term = call('account.payment.term', 'search', [('name', '=', payment_term)])
        if term:
            vals['property_payment_term_id'] = term[0]
    pid = call('res.partner', 'create', vals)
    logger.info(f"  Created {ptype}: {name} (ID {pid})")
    return pid

def create_product(name, ptype, sale_price, cost_price, ref, categ_name, tax_name='IGV 18%', tracking='none'):
    categ = call('product.category', 'search', [('name', '=', categ_name)])
    if not categ:
        categ = call('product.category', 'create', {'name': categ_name})
        logger.info(f"  Created category: {categ_name}")
        categ = [categ]
    tax = call('account.tax', 'search', [('name', '=', tax_name)])
    pid = call('product.product', 'create', {
        'name': name,
        'type': ptype,
        'list_price': sale_price,
        'standard_price': cost_price,
        'default_code': ref,
        'categ_id': categ[0],
        'taxes_id': [(6, 0, tax)] if tax else [],
        'tracking': tracking,
    })
    logger.info(f"  Created product: {name} (ID {pid})")
    return pid

def create_sale_order(partner_id, lines):
    order_vals = {
        'partner_id': partner_id,
        'partner_invoice_id': partner_id,
        'partner_shipping_id': partner_id,
    }
    order_id = call('sale.order', 'create', order_vals)
    for product_id, qty, price in lines:
        call('sale.order.line', 'create', {
            'order_id': order_id,
            'product_id': product_id,
            'product_uom_qty': qty,
            'price_unit': price,
        })
    call('sale.order', 'action_confirm', [order_id])
    logger.info(f"  Sale order {order_id} created and confirmed")
    return order_id

def create_purchase_order(partner_id, lines):
    order_vals = {
        'partner_id': partner_id,
    }
    order_id = call('purchase.order', 'create', order_vals)
    for product_id, qty, price in lines:
        call('purchase.order.line', 'create', {
            'order_id': order_id,
            'product_id': product_id,
            'product_qty': qty,
            'price_unit': price,
        })
    call('purchase.order', 'button_confirm', [order_id])
    logger.info(f"  Purchase order {order_id} created and confirmed")
    return order_id

logger.info("=" * 60)
logger.info("CONFIGURACIÓN DE MÓDULOS - ODOO BANCO DE LA NACIÓN")
logger.info("=" * 60)

# ─────────────────────────────────────────────
# 1. VENTAS (sale_management)
# ─────────────────────────────────────────────
logger.info("\n[1/6] Configurando Módulo de Ventas...")

set_config({
    'sale.block_confirm': 'True',
    'sale.invoice_policy': 'order',
    'sale.warning': 'True',
    'sale.signature': 'True',
    'sale.pricelist': 'True',
    'sale.discount': 'True',
    'sale.margin': 'True',
})

# ─────────────────────────────────────────────
# 2. COMPRAS (purchase)
# ─────────────────────────────────────────────
logger.info("\n[2/6] Configurando Módulo de Compras...")

set_config({
    'purchase.block_confirm': 'True',
    'purchase.invoice_policy': 'picking',
    'purchase.warning': 'True',
    'purchase.approval': 'True',
    'purchase.approval_amount': '10000',
})

# ─────────────────────────────────────────────
# 3. INVENTARIO (stock)
# ─────────────────────────────────────────────
logger.info("\n[3/6] Configurando Módulo de Inventario...")

set_config({
    'stock.location': 'True',
    'stock.multi_step': 'True',
    'stock.lot': 'True',
    'stock.expiry': 'True',
    'stock.reordering': 'True',
    'stock.mto': 'True',
    'stock.mto_rule': 'buy',
})

# ─────────────────────────────────────────────
# 4. CONTABILIDAD (account)
# ─────────────────────────────────────────────
logger.info("\n[4/6] Configurando Módulo de Contabilidad...")

pe_country = get_peru_country()
set_config({
    'country_id': str(pe_country),
    'tax_calculation_rounding_method': 'round_per_line',
})

logger.info("\n  Instalando Plan Contable PCGE...")
l10n_pe = call('ir.module.module', 'search', [('name', '=', 'l10n_pe'), ('state', '=', 'uninstalled')])
if l10n_pe:
    call('ir.module.module', 'button_install', l10n_pe)
    logger.info("  l10n_pe module installed")

# ─────────────────────────────────────────────
# 5. DATOS DEMO - CONTACTOS
# ─────────────────────────────────────────────
logger.info("\n[5/6] Cargando Contactos Demo...")

cliente1 = create_partner(
    'Corporación Lima S.A.C.', 'customer',
    '20501123456', 'pagos@corplima.com', '+51 1 234-5678',
    'Av. Javier Prado Este 1234, Lima', '30 días'
)

cliente2 = create_partner(
    'Ministerio de Economía y Finanzas', 'customer',
    '20131370645', 'contacto@mef.gob.pe', '+51 1 311-3000',
    'Jr. Junín 319, Lima', '30 días'
)

proveedor1 = create_partner(
    'Suministros Andinos S.A.', 'supplier',
    '20456789012', 'ventas@sandinos.com', '+51 1 456-7890',
    'Av. Argentina 3456, Lima', '15 días'
)

proveedor2 = create_partner(
    'Tecnología Perú E.I.R.L.', 'supplier',
    '20612345678', 'info@tecnologiaperu.pe', '+51 1 789-0123',
    'Av. La Marina 2500, Lima', '30 días'
)

# ─────────────────────────────────────────────
# 6. DATOS DEMO - PRODUCTOS
# ─────────────────────────────────────────────
logger.info("\n[6/6] Cargando Productos Demo...")

categories = ['Material de Oficina', 'Equipos Informáticos', 'Insumos de Seguridad', 'Bienes de Activo Fijo']
for cat in categories:
    existing = call('product.category', 'search', [('name', '=', cat)])
    if not existing:
        call('product.category', 'create', {'name': cat})
        logger.info(f"  Created category: {cat}")

prod1 = create_product('Resma de Papel A4 80gr', 'consu', 12.50, 9.80, 'PP-A4-001', 'Material de Oficina')
prod2 = create_product('Laptop Dell Latitude 5540', 'product', 4500.00, 3800.00, 'EQ-DELL-5540', 'Equipos Informáticos', tracking='serial')
prod3 = create_product('Tóner HP LaserJet CF283A', 'consu', 185.00, 142.00, 'IN-TONER-001', 'Material de Oficina')
prod4 = create_product('Monitor Dell 27" P2723DE', 'product', 1250.00, 980.00, 'EQ-DELL-MON27', 'Equipos Informáticos')
prod5 = create_product('Cámara de Seguridad IP', 'product', 320.00, 245.00, 'SEG-CAM-001', 'Insumos de Seguridad')

# ─────────────────────────────────────────────
# 7. PEDIDO DE VENTA DEMO
# ─────────────────────────────────────────────
logger.info("\n  Creando Pedido de Venta Demo...")
sale_order = create_sale_order(cliente1, [
    (prod1, 50, 12.50),
    (prod2, 5, 4500.00),
])

# ─────────────────────────────────────────────
# 8. ORDEN DE COMPRA DEMO
# ─────────────────────────────────────────────
logger.info("\n  Creando Orden de Compra Demo...")
purchase_order = create_purchase_order(proveedor1, [
    (prod1, 200, 9.80),
    (prod3, 30, 142.00),
])

logger.info("\n" + "=" * 60)
logger.info("CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
logger.info("=" * 60)
