from odoo import api, fields, models, _
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class WazuhSIEMEvent(models.Model):
    _name = 'wazuh.siem.event'
    _description = 'Evento Wazuh SIEM'
    _rec_name = 'display_name'
    _order = 'create_date desc'

    display_name = fields.Char(string='Evento', compute='_compute_display_name', store=True)

    # Identificación del evento
    event_id = fields.Char(string='ID del Evento', index=True, required=True)
    event_type = fields.Selection([
        ('alert', 'Alerta'),
        ('audit', 'Auditoría'),
        ('automation', 'Automatización'),
        ('system', 'Sistema'),
        ('security', 'Seguridad'),
        ('regulatory', 'Regulatorio'),
        ('compliance', 'Cumplimiento'),
        ('error', 'Error'),
        ('warning', 'Advertencia'),
        ('info', 'Informativo'),
    ], string='Tipo de Evento', required=True, index=True)

    # Contenido del evento
    event_data = fields.Text(string='Datos del Evento (JSON)')
    event_summary = fields.Text(string='Resumen del Evento')
    severity = fields.Selection([
        ('0', 'Emergencia'),
        ('1', 'Alerta'),
        ('2', 'Crítico'),
        ('3', 'Error'),
        ('4', 'Advertencia'),
        ('5', 'Notificación'),
        ('6', 'Informativo'),
        ('7', 'Depuración'),
    ], string='Severidad', default='6')

    # Origen
    source_model = fields.Char(string='Modelo de Origen')
    source_record_id = fields.Integer(string='ID del Registro Origen')
    source_user_id = fields.Many2one('res.users', string='Usuario Origen')
    ip_address = fields.Char(string='Dirección IP')
    hostname = fields.Char(string='Hostname')

    # Integración Odoo
    odoo_model = fields.Char(string='Modelo Odoo Relacionado')
    odoo_record_id = fields.Integer(string='ID Registro Odoo')
    odoo_action = fields.Char(string='Acción Odoo')

    # Metadata
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    acknowledged = fields.Boolean(string='Reconocido', default=False)
    acknowledged_by = fields.Many2one('res.users', string='Reconocido por')
    acknowledged_date = fields.Datetime(string='Fecha de Reconocimiento')

    _sql_constraints = [
        ('unique_event_id', 'UNIQUE(event_id)', 'El ID del evento SIEM debe ser único.'),
    ]

    @api.depends('event_id', 'event_type', 'event_summary')
    def _compute_display_name(self):
        for event in self:
            summary = event.event_summary[:50] if event.event_summary else 'Sin resumen'
            event.display_name = f"[{event.event_type}] {event.event_id}: {summary}"

    @api.model
    def ingest_event(self, event_type, event_id, event_data, severity='6',
                     source_model=None, source_record_id=None, summary=None):
        if not summary:
            summary = f"Evento {event_type}: {event_id}"

        domain = [('event_id', '=', event_id)]
        existing = self.search(domain, limit=1)
        if existing:
            _logger.debug(f"Evento SIEM duplicado: {event_id}")
            return existing

        event = self.create({
            'event_id': event_id,
            'event_type': event_type,
            'event_data': json.dumps(event_data) if isinstance(event_data, dict) else str(event_data),
            'event_summary': str(summary)[:500],
            'severity': severity,
            'source_model': source_model,
            'source_record_id': source_record_id,
            'source_user_id': self.env.user.id,
            'company_id': self.env.company.id,
        })
        _logger.info(f"Evento SIEM ingerido: {event_id} ({event_type})")
        return event

    def action_acknowledge(self):
        self.ensure_one()
        self.write({
            'acknowledged': True,
            'acknowledged_by': self.env.user.id,
            'acknowledged_date': fields.Datetime.now(),
        })
        return True

    @api.model
    def _forward_to_wazuh(self, event_type, event_data):
        # Punto de integración: envía el evento al archivo de log de Odoo
        # para que Wazuh agent lo capture y lo envíe al manager
        log_entry = {
            'wazuh': {
                'integration': 'odoo',
                'event_type': event_type,
                'timestamp': datetime.now().isoformat(),
                'data': event_data,
            }
        }
        _logger.info(f"WAZUH_FORWARD: {json.dumps(log_entry)}")
        return True


class WazuhIntegrationConfig(models.Model):
    _name = 'wazuh.integration.config'
    _description = 'Configuración de Integración Wazuh'
    _rec_name = 'name'

    name = fields.Char(string='Nombre', default='Configuración Wazuh BDN')
    active = fields.Boolean(string='Activo', default=True)

    # Configuración de conexión
    manager_address = fields.Char(string='Dirección del Manager Wazuh',
                                   default='wazuh.manager.local')
    manager_port = fields.Integer(string='Puerto del Manager', default=1514)
    agent_name = fields.Char(string='Nombre del Agente', default='odoo-banco-nacion')

    # Tipos de eventos a enviar
    forward_audit_logs = fields.Boolean(string='Enviar Logs de Auditoría', default=True)
    forward_automated_actions = fields.Boolean(string='Enviar Acciones Automatizadas', default=True)
    forward_alerts = fields.Boolean(string='Enviar Alertas', default=True)
    forward_errors = fields.Boolean(string='Enviar Errores', default=True)
    forward_sbs_reports = fields.Boolean(string='Enviar Reportes SBS', default=True)
    forward_login_attempts = fields.Boolean(string='Enviar Intentos de Login', default=True)

    # Filtros
    min_severity = fields.Selection([
        ('0', 'Emergencia'), ('1', 'Alerta'), ('2', 'Crítico'),
        ('3', 'Error'), ('4', 'Advertencia'), ('5', 'Notificación'),
    ], string='Severidad Mínima', default='4')

    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
