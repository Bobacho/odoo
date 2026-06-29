from odoo import api, fields, models, _
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class AuditTrailEntry(models.Model):
    _name = 'audit.trail.entry'
    _description = 'Entrada de Trazabilidad de Auditoría'
    _rec_name = 'display_name'
    _order = 'create_date desc'

    display_name = fields.Char(string='Descripción', compute='_compute_display_name', store=True)
    model_name = fields.Char(string='Modelo', required=True, index=True)
    record_id = fields.Integer(string='ID del Registro', required=True, index=True)
    action_type = fields.Selection([
        ('create', 'Creación'),
        ('write', 'Modificación'),
        ('unlink', 'Eliminación'),
        ('generate', 'Generación'),
        ('validate', 'Validación'),
        ('submit', 'Envío'),
        ('acknowledge', 'Acuse'),
        ('reject', 'Rechazo'),
        ('cancel', 'Anulación'),
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('export', 'Exportación'),
        ('print', 'Impresión'),
        ('automation', 'Acción Automatizada'),
        ('alert', 'Alerta'),
        ('sbs_submission', 'Envío a SBS'),
        ('config_change', 'Cambio de Configuración'),
        ('user_action', 'Acción de Usuario'),
    ], string='Tipo de Acción', required=True, index=True)

    description = fields.Text(string='Descripción Detallada', required=True)
    user_id = fields.Many2one('res.users', string='Usuario', required=True,
                               default=lambda self: self.env.user, index=True)
    user_login = fields.Char(string='Login de Usuario', related='user_id.login', store=True)
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company, required=True)
    ip_address = fields.Char(string='Dirección IP')
    user_agent = fields.Text(string='User Agent')
    session_id = fields.Char(string='ID de Sesión')

    # Datos de cambios
    old_value = fields.Text(string='Valor Anterior')
    new_value = fields.Text(string='Valor Nuevo')
    changes_json = fields.Text(string='Cambios (JSON)')
    changes_summary = fields.Text(string='Resumen de Cambios', compute='_compute_changes_summary')

    # Integridad
    hash_chain = fields.Char(string='Hash de Integridad', readonly=True)
    previous_entry_id = fields.Many2one('audit.trail.entry', string='Entrada Anterior',
                                         readonly=True)
    signed = fields.Boolean(string='Firmado', default=False, readonly=True)

    _sql_constraints = [
        ('check_previous_entry',
         'UNIQUE(previous_entry_id)',
         'Cada entrada solo puede tener una predecesora.'),
    ]

    @api.depends('action_type', 'description', 'create_date')
    def _compute_display_name(self):
        for entry in self:
            entry.display_name = f"[{entry.action_type}] {entry.description[:50]}"

    @api.depends('changes_json')
    def _compute_changes_summary(self):
        for entry in self:
            if entry.changes_json:
                try:
                    changes = json.loads(entry.changes_json)
                    summary_parts = []
                    for field, vals in changes.items():
                        summary_parts.append(f"{field}: {vals.get('old', '')} -> {vals.get('new', '')}")
                    entry.changes_summary = ' | '.join(summary_parts[:5])
                except (json.JSONDecodeError, TypeError):
                    entry.changes_summary = entry.changes_json[:100]
            else:
                entry.changes_summary = ''

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Encadenar hashes para integridad
        last_entry = self.search([], order='create_date desc', limit=1)
        if len(last_entry) > 1:
            record._chain_hash(last_entry[1] if last_entry[0].id == record.id else last_entry[0])
        return record

    def _chain_hash(self, previous_entry):
        self.ensure_one()
        import hashlib
        prev_hash = previous_entry.hash_chain or '0' * 64
        content = f"{prev_hash}{self.id}{self.action_type}{self.description}{self.create_date}"
        self.hash_chain = hashlib.sha256(content.encode()).hexdigest()
        self.previous_entry_id = previous_entry.id

    def action_verify_integrity(self):
        self.ensure_one()
        if not self.previous_entry_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Integridad Verificada'),
                    'message': _('Entrada raíz - no hay entrada anterior para verificar.'),
                    'type': 'success',
                }
            }

        import hashlib
        prev = self.previous_entry_id
        expected_content = f"{prev.hash_chain}{self.id}{self.action_type}{self.description}{self.create_date}"
        expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()

        if self.hash_chain == expected_hash:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Integridad Verificada'),
                    'message': _('La cadena de auditoría es íntegra y no ha sido alterada.'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('¡ALERTA DE INTEGRIDAD!'),
                    'message': _('La cadena de auditoría ha sido alterada o es inválida.'),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _get_client_ip(self):
        try:
            from odoo.http import request
            if request and request.httprequest:
                return request.httprequest.remote_addr
        except Exception:
            pass
        return None

    @api.model
    def log_action(self, model_name, record_id, action_type, description,
                   old_value=None, new_value=None, changes=None):
        vals = {
            'model_name': model_name,
            'record_id': record_id,
            'action_type': action_type,
            'description': description,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'ip_address': self._get_client_ip(),
        }
        if old_value:
            vals['old_value'] = str(old_value)[:10000]
        if new_value:
            vals['new_value'] = str(new_value)[:10000]
        if changes:
            vals['changes_json'] = json.dumps(changes)[:10000]
        return self.create(vals)
