from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class BankConfigParams(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuración SBS Regulatorio
    sbs_entity_code = fields.Char(string='Código de Entidad SBS', default='0001',
                                   config_parameter='sbs_entity_code')
    sbs_api_endpoint = fields.Char(string='Endpoint API SBS',
                                    default='https://api.sbs.gob.pe/reportes',
                                    config_parameter='sbs_api_endpoint')
    sbs_api_key = fields.Char(string='API Key SBS', config_parameter='sbs_api_key')
    sbs_notification_email = fields.Char(string='Email de Notificaciones SBS',
                                          default='sbs-reportes@banconacion.pe',
                                          config_parameter='sbs_notification_email')

    # Configuración Wazuh SIEM
    wazuh_manager_ip = fields.Char(string='IP del Manager Wazuh',
                                    default='wazuh.manager.local',
                                    config_parameter='wazuh_manager_ip')
    wazuh_agent_name = fields.Char(string='Nombre del Agente Wazuh',
                                    default='odoo-banco-nacion',
                                    config_parameter='wazuh_agent_name')
    wazuh_enabled = fields.Boolean(string='Wazuh SIEM Habilitado', default=True,
                                    config_parameter='wazuh_enabled')

    # Configuración de Automatizaciones
    automation_enabled = fields.Boolean(string='Automatizaciones Habilitadas', default=True,
                                         config_parameter='automation_enabled')
    auto_reconciliation = fields.Boolean(string='Conciliación Automática', default=True,
                                          config_parameter='auto_reconciliation')
    auto_sbs_reports = fields.Boolean(string='Reportes SBS Automáticos', default=True,
                                       config_parameter='auto_sbs_reports')
    auto_aml_checks = fields.Boolean(string='Verificaciones PLA/FT Automáticas', default=True,
                                      config_parameter='auto_aml_checks')

    # Configuración de Seguridad Bancaria
    max_login_attempts = fields.Integer(string='Máx. Intentos de Login', default=5,
                                        config_parameter='max_login_attempts')
    session_timeout_minutes = fields.Integer(string='Timeout de Sesión (min)', default=30,
                                              config_parameter='session_timeout_minutes')
    two_factor_auth = fields.Boolean(string='Autenticación de Doble Factor', default=True,
                                      config_parameter='two_factor_auth')
    ip_whitelist = fields.Text(string='Lista Blanca de IPs',
                                config_parameter='ip_whitelist')

    # Módulos del banco
    module_sale = fields.Boolean(string='Módulo de Ventas', default=True)
    module_purchase = fields.Boolean(string='Módulo de Compras', default=True)
    module_stock = fields.Boolean(string='Módulo de Inventarios', default=True)
    module_account = fields.Boolean(string='Módulo de Finanzas/Contabilidad', default=True)

    def set_values(self):
        super().set_values()
        # Log de configuración
        _logger.info("Configuración bancaria actualizada")
        self.env['audit.trail.entry'].create({
            'model_name': 'res.config.settings',
            'record_id': self.id,
            'action_type': 'config_change',
            'description': 'Configuración general del banco actualizada',
            'user_id': self.env.user.id,
        })

    def action_install_bank_modules(self):
        modules_to_install = []
        if self.module_sale:
            modules_to_install.append('sale')
        if self.module_purchase:
            modules_to_install.append('purchase')
        if self.module_stock:
            modules_to_install.append('stock')
        if self.module_account:
            modules_to_install.append('account')
            modules_to_install.append('account_accountant')

        if modules_to_install:
            module_obj = self.env['ir.module.module']
            for module_name in modules_to_install:
                module = module_obj.search([('name', '=', module_name)], limit=1)
                if module and module.state != 'installed':
                    module.button_install()
                    _logger.info(f"Módulo {module_name} instalado")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Módulos Instalados'),
                'message': _('Módulos bancarios instalados correctamente: %s') %
                           ', '.join(modules_to_install),
                'type': 'success',
                'sticky': True,
            }
        }
