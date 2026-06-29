from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AlertRule(models.Model):
    _name = 'alert.rule'
    _description = 'Regla de Alerta Regulatoria'
    _rec_name = 'name'
    _order = 'priority, sequence, name'

    name = fields.Char(string='Nombre de la Alerta', required=True)
    description = fields.Text(string='Descripción')
    active = fields.Boolean(string='Activa', default=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    priority = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ], string='Prioridad', default='medium', required=True)

    alert_type = fields.Selection([
        ('regulatory', 'Regulatoria'),
        ('compliance', 'Cumplimiento'),
        ('risk', 'Riesgo'),
        ('fraud', 'Fraude'),
        ('operational', 'Operacional'),
        ('aml', 'PLA/FT'),
        ('financial', 'Financiera'),
        ('security', 'Seguridad'),
        ('system', 'Sistema'),
    ], string='Tipo de Alerta', required=True)

    rule_category = fields.Selection([
        ('sbs_regulatory', 'Regulatoria SBS'),
        ('aml_plaft', 'PLA/FT'),
        ('internal_control', 'Control Interno'),
        ('risk_management', 'Gestión de Riesgos'),
        ('audit', 'Auditoría'),
        ('compliance', 'Cumplimiento'),
    ], string='Categoría Regulatoria', required=True)

    # Condiciones de la alerta
    model_id = fields.Many2one('ir.model', string='Modelo a Monitorear', required=True, ondelete='cascade')
    model_name = fields.Char(string='Nombre Técnico del Modelo', related='model_id.model',
                              store=True)

    condition_domain = fields.Text(string='Dominio de Condición (dominio Odoo)',
                                    default='[]',
                                    help='Dominio en formato Odoo para evaluar la alerta')
    condition_field = fields.Char(string='Campo a Evaluar')
    condition_operator = fields.Selection([
        ('=', 'Igual a'),
        ('!=', 'Diferente de'),
        ('>', 'Mayor que'),
        ('<', 'Menor que'),
        ('>=', 'Mayor o igual'),
        ('<=', 'Menor o igual'),
        ('in', 'En el conjunto'),
        ('not in', 'No en el conjunto'),
        ('between', 'Entre'),
        ('like', 'Contiene'),
    ], string='Operador', default='=')
    condition_value = fields.Char(string='Valor de Comparación')
    condition_value_float = fields.Float(string='Valor Numérico')

    # Notificación
    notify_method = fields.Selection([
        ('email', 'Correo Electrónico'),
        ('notification', 'Notificación Interna'),
        ('both', 'Ambos'),
        ('siem', 'Solo SIEM'),
    ], string='Método de Notificación', required=True, default='both')

    notify_user_ids = fields.Many2many('res.users', string='Notificar a')
    email_template_id = fields.Many2one('mail.template', string='Plantilla de Email')

    # Acción automática al disparar
    auto_action = fields.Selection([
        ('none', 'Ninguna'),
        ('block_transaction', 'Bloquear Transacción'),
        ('flag_record', 'Marcar Registro'),
        ('notify_officer', 'Notificar al Oficial de Cumplimiento'),
        ('create_case', 'Crear Caso de Investigación'),
        ('freeze_account', 'Congelar Cuenta'),
        ('report_sbs', 'Reportar a SBS'),
        ('trigger_workflow', 'Disparar Workflow'),
        ('call_api', 'Llamar API Externa'),
    ], string='Acción Automática', default='none')

    # Control de frecuencia
    throttle_hours = fields.Integer(string='Esperar (horas) entre alertas', default=0,
                                     help='Evita alertas duplicadas en este período')
    max_alerts_per_day = fields.Integer(string='Máx. alertas por día', default=100)
    group_by_field = fields.Char(string='Agrupar por campo',
                                  help='Evita duplicados basado en este campo')

    # Estadísticas
    alert_count = fields.Integer(string='Alertas Generadas', default=0)
    last_alert_date = fields.Datetime(string='Última Alerta')

    # Sistema
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)

    def evaluate_and_alert(self, records=None):
        self.ensure_one()
        if not self.active:
            return False

        if not records:
            records = self._get_records_to_evaluate()

        alerts_generated = 0
        for record in records:
            if self._evaluate_condition(record):
                self._generate_alert(record)
                alerts_generated += 1

        if alerts_generated:
            self.write({
                'alert_count': self.alert_count + alerts_generated,
                'last_alert_date': fields.Datetime.now(),
            })

        return alerts_generated

    def _get_records_to_evaluate(self):
        if not self.model_name:
            return []
        Model = self.env.get(self.model_name)
        if not Model:
            return []
        domain = []
        if self.condition_domain and self.condition_domain != '[]':
            try:
                domain = eval(self.condition_domain)
            except:
                domain = []
        return Model.search(domain)

    def _evaluate_condition(self, record):
        if not self.condition_field:
            return True
        value = record
        for field_part in self.condition_field.split('.'):
            value = getattr(value, field_part, None)
            if value is None:
                return False

        op = self.condition_operator
        cond_val = self.condition_value or self.condition_value_float

        if op == '=':
            return value == cond_val
        elif op == '!=':
            return value != cond_val
        elif op == '>':
            return float(value) > float(cond_val)
        elif op == '<':
            return float(value) < float(cond_val)
        elif op == '>=':
            return float(value) >= float(cond_val)
        elif op == '<=':
            return float(value) <= float(cond_val)
        elif op == 'between':
            try:
                vals = [float(x) for x in cond_val.split(',')]
                return vals[0] <= float(value) <= vals[1]
            except:
                return False
        return False

    def _generate_alert(self, record):
        alert_vals = {
            'rule_id': self.id,
            'alert_type': self.alert_type,
            'priority': self.priority,
            'model_name': self.model_name,
            'record_id': record.id,
            'record_name': record.display_name if hasattr(record, 'display_name') else str(record),
            'description': f"Alerta: {self.name} en {record}",
            'company_id': self.env.company.id,
        }

        alert = self.env['alert.rule.instance'].create(alert_vals)
        alert._send_notifications()

        # Registrar en auditoría
        self.env['audit.trail.entry'].create({
            'model_name': 'alert.rule',
            'record_id': self.id,
            'action_type': 'alert',
            'description': f"Alerta {self.name} disparada en {record}",
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
        })

        # Reenviar a Wazuh SIEM
        alert_data = {
            'type': 'regulatory_alert',
            'rule': self.name,
            'alert_type': self.alert_type,
            'priority': self.priority,
            'record_model': self.model_name,
            'record_id': record.id,
        }
        _logger.info("SIEM ALERT: %s", json.dumps(alert_data))

        return alert


class AlertRuleInstance(models.Model):
    _name = 'alert.rule.instance'
    _description = 'Instancia de Alerta'
    _rec_name = 'description'
    _order = 'create_date desc'

    rule_id = fields.Many2one('alert.rule', string='Regla de Alerta', required=True)
    alert_type = fields.Selection([
        ('regulatory', 'Regulatoria'), ('compliance', 'Cumplimiento'),
        ('risk', 'Riesgo'), ('fraud', 'Fraude'),
        ('operational', 'Operacional'), ('aml', 'PLA/FT'),
        ('financial', 'Financiera'), ('security', 'Seguridad'),
        ('system', 'Sistema'),
    ], string='Tipo de Alerta', required=True)
    priority = fields.Selection([
        ('low', 'Baja'), ('medium', 'Media'),
        ('high', 'Alta'), ('critical', 'Crítica'),
    ], string='Prioridad', required=True)
    state = fields.Selection([
        ('new', 'Nueva'),
        ('acknowledged', 'Reconocida'),
        ('investigating', 'En Investigación'),
        ('resolved', 'Resuelta'),
        ('escalated', 'Escalada'),
        ('false_positive', 'Falso Positivo'),
    ], string='Estado', default='new', tracking=True)
    model_name = fields.Char(string='Modelo Asociado')
    record_id = fields.Integer(string='ID del Registro')
    record_name = fields.Char(string='Nombre del Registro')
    description = fields.Text(string='Descripción', required=True)
    assigned_to = fields.Many2one('res.users', string='Asignado a')
    resolution = fields.Text(string='Resolución')
    resolved_by = fields.Many2one('res.users', string='Resuelto por')
    resolved_date = fields.Datetime(string='Fecha de Resolución')
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)

    def _send_notifications(self):
        self.ensure_one()
        if self.rule_id.notify_method in ('email', 'both'):
            self._send_email_notification()
        if self.rule_id.notify_method in ('notification', 'both'):
            self._send_internal_notification()

    def _send_email_notification(self):
        # Enviar notificación por email
        _logger.info(f"Notificación email enviada para alerta: {self.description}")

    def _send_internal_notification(self):
        # Crear notificación interna en Odoo
        users = self.rule_id.notify_user_ids
        for user in users:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_alert').id,
                'summary': self.description[:100],
                'note': self.description,
                'user_id': user.id,
                'res_model_id': self.env['ir.model']._get(self.model_name).id if self.model_name else False,
                'res_id': self.record_id,
            })

    def action_acknowledge(self):
        self.state = 'acknowledged'
        return True

    def action_investigate(self):
        self.state = 'investigating'
        return True

    def action_resolve(self):
        self.state = 'resolved'
        self.resolved_by = self.env.user.id
        self.resolved_date = fields.Datetime.now()
        return True

    def action_escalate(self):
        self.state = 'escalated'
        return True

    def action_false_positive(self):
        self.state = 'false_positive'
        self.resolved_by = self.env.user.id
        self.resolved_date = fields.Datetime.now()
        return True
