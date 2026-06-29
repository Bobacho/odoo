{
    'name': 'Banco de la Nación - Módulo SBS Regulatorio',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Regulatory',
    'summary': 'Configuración regulatoria SBS para Banco de la Nación',
    'description': """
Módulo regulatorio para Banco de la Nación
===========================================
- Reportes regulatorios SBS (Superintendencia de Banca, Seguros y AFP)
- Automatizaciones de compliance bancario
- Integración con Wazuh SIEM para auditoría
- Gestión de alertas automáticas
- Trazabilidad de acciones automatizadas
- Reportes financieros según normativa peruana
- Conciliación bancaria automatizada
- Gestión de riesgos operativos
- Prevención de lavado de activos (PLA/FT)
- Reporting de estados financieros SBS
    """,
    'author': 'Banco de la Nación - Dirección de TI',
    'website': 'https://www.banconacion.pe',
    'depends': [
        'base',
        'web',
        'account',
        'account_audit_trail',
        'sale',
        'purchase',
        'stock',
        'mail',
        'board',
        'l10n_pe',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/automated_actions.xml',
        'data/sbs_regulatory_data.xml',
        'data/email_templates.xml',
        'wizard/sbs_report_wizard.xml',
        'views/sbs_report_views.xml',
        'views/audit_trail_views.xml',
        'views/automated_action_views.xml',
        'views/menu_views.xml',
        'reports/sbs_reports.xml',
        'reports/report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'assets': {
        'web.assets_backend': [
            'banco_nacion/static/src/**/*',
        ],
    },
}
