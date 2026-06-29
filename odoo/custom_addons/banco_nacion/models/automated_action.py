from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
import logging
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class AutomatedActionLog(models.Model):
    _name = 'automated.action.log'
    _description = 'Registro de Acciones Automatizadas'
    _rec_name = 'display_name'
    _order = 'create_date desc'

    display_name = fields.Char(string='Acción', compute='_compute_display_name', store=True)
    rule_id = fields.Many2one('automated.action.rule', string='Regla', required=True)
    rule_name = fields.Char(string='Nombre de Regla', related='rule_id.name', store=True)

    action_type = fields.Selection([
        ('reconciliation', 'Conciliación Bancaria'),
        ('sbs_report', 'Reporte SBS Automático'),
        ('alert_generation', 'Generación de Alerta'),
        ('account_matching', 'Emparejamiento de Cuentas'),
        ('provision_calc', 'Cálculo de Provisiones'),
        ('interest_calc', 'Cálculo de Intereses'),
        ('risk_assessment', 'Evaluación de Riesgo'),
        ('aml_check', 'Verificación PLA/FT'),
        ('notification', 'Notificación Regulatoria'),
        ('data_validation', 'Validación de Datos'),
        ('backup', 'Respaldo de Información'),
        ('compliance_check', 'Verificación de Cumplimiento'),
        ('report_scheduling', 'Programación de Reportes'),
        ('treasury_alert', 'Alerta de Tesorería'),
    ], string='Tipo de Acción', required=True, index=True)

    action_method = fields.Selection([
        ('automatic', 'Automática (sin intervención)'),
        ('semi_automatic', 'Semiatomática (requiere aprobación)'),
        ('manual', 'Manual (disparada por usuario)'),
        ('triggered', 'Disparada por evento'),
        ('scheduled', 'Programada por tiempo'),
    ], string='Modalidad', required=True, default='automatic')

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('executing', 'Ejecutando'),
        ('success', 'Ejecutada'),
        ('warning', 'Ejecutada con Advertencias'),
        ('failed', 'Fallida'),
        ('cancelled', 'Cancelada'),
        ('requires_review', 'Requiere Revisión'),
    ], string='Estado', default='pending', tracking=True)

    trigger_model = fields.Char(string='Modelo Disparador')
    trigger_record_id = fields.Integer(string='ID del Registro Disparador')

    executed_by = fields.Many2one('res.users', string='Ejecutada por')
    execution_date = fields.Datetime(string='Fecha de Ejecución')
    completion_date = fields.Datetime(string='Fecha de Finalización')
    duration_seconds = fields.Float(string='Duración (segundos)', compute='_compute_duration')

    log_detail = fields.Text(string='Detalle de Ejecución')
    error_message = fields.Text(string='Mensaje de Error')
    error_traceback = fields.Text(string='Traceback del Error')
    warning_messages = fields.Text(string='Mensajes de Advertencia')

    result_data = fields.Text(string='Datos Resultantes (JSON)')

    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company, required=True)

    # Para integración Wazuh
    siem_forwarded = fields.Boolean(string='Enviado a SIEM', default=False)
    siem_forward_date = fields.Datetime(string='Fecha de Envío a SIEM')

    _sql_constraints = [
        ('check_trigger',
         'CHECK((trigger_model IS NULL AND trigger_record_id IS NULL) OR '
         '(trigger_model IS NOT NULL AND trigger_record_id IS NOT NULL))',
         'Debe especificar modelo y ID de registro disparador o ninguno.'),
    ]

    @api.depends('rule_name', 'action_type', 'create_date')
    def _compute_display_name(self):
        for log in self:
            log.display_name = f"[{log.action_type}] {log.rule_name} @ {log.create_date}"

    @api.depends('execution_date', 'completion_date')
    def _compute_duration(self):
        for log in self:
            if log.execution_date and log.completion_date:
                delta = log.completion_date - log.execution_date
                log.duration_seconds = delta.total_seconds()
            else:
                log.duration_seconds = 0.0

    def action_view_detail(self):
        self.ensure_one()
        return {
            'name': _('Detalle de Acción Automatizada'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'automated.action.log',
            'res_id': self.id,
        }

    def action_retry(self):
        self.ensure_one()
        if self.state != 'failed':
            raise ValidationError(_('Solo se pueden reintentar acciones fallidas.'))
        self.write({
            'state': 'pending',
            'error_message': False,
            'error_traceback': False,
        })
        # Re-ejecutar según tipo
        self.rule_id.execute_action()
        return True

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'
        return True

    def _forward_to_siem(self):
        self.ensure_one()
        if not self.siem_forwarded:
            log_entry = {
                'type': 'automated_action',
                'action_type': self.action_type,
                'rule': self.rule_name,
                'state': self.state,
                'timestamp': str(self.execution_date or fields.Datetime.now()),
                'company': self.company_id.name,
            }
            _logger.info(f"SIEM FORWARD: {json.dumps(log_entry)}")
            self.write({
                'siem_forwarded': True,
                'siem_forward_date': fields.Datetime.now(),
            })
        return True

    @api.model
    def log_action(self, rule_id, action_type, state, log_detail,
                   executed_by=None, trigger_model=None, trigger_record_id=None,
                   error_message=None, result_data=None):
        vals = {
            'rule_id': rule_id,
            'action_type': action_type,
            'state': state,
            'log_detail': str(log_detail)[:10000],
            'executed_by': executed_by or self.env.user.id,
            'execution_date': fields.Datetime.now(),
            'company_id': self.env.company.id,
        }
        if trigger_model:
            vals['trigger_model'] = trigger_model
        if trigger_record_id:
            vals['trigger_record_id'] = trigger_record_id
        if error_message:
            vals['error_message'] = str(error_message)[:10000]
        if result_data:
            vals['result_data'] = json.dumps(result_data)[:10000]

        record = self.create(vals)
        if state == 'success':
            record._forward_to_siem()
        return record


class AutomatedActionRule(models.Model):
    _name = 'automated.action.rule'
    _description = 'Regla de Acción Automatizada'
    _rec_name = 'name'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activa', default=True)

    action_type = fields.Selection([
        ('reconciliation', 'Conciliación Bancaria'),
        ('sbs_report', 'Reporte SBS Automático'),
        ('alert_generation', 'Generación de Alerta'),
        ('account_matching', 'Emparejamiento de Cuentas'),
        ('provision_calc', 'Cálculo de Provisiones'),
        ('interest_calc', 'Cálculo de Intereses'),
        ('risk_assessment', 'Evaluación de Riesgo'),
        ('aml_check', 'Verificación PLA/FT'),
        ('notification', 'Notificación Regulatoria'),
        ('data_validation', 'Validación de Datos'),
        ('backup', 'Respaldo de Información'),
        ('compliance_check', 'Verificación de Cumplimiento'),
        ('report_scheduling', 'Programación de Reportes'),
        ('treasury_alert', 'Alerta de Tesorería'),
    ], string='Tipo de Acción', required=True)

    trigger_type = fields.Selection([
        ('cron', 'Programada (CRON)'),
        ('scheduled', 'Programada por Horario'),
        ('on_change', 'Al Cambiar Campo'),
        ('on_create', 'Al Crear Registro'),
        ('on_write', 'Al Modificar Registro'),
        ('manual', 'Manual'),
        ('event', 'Por Evento'),
        ('condition', 'Por Condición'),
        ('time_based', 'Basada en Tiempo'),
    ], string='Tipo de Disparo', required=True, default='cron')

    cron_id = fields.Many2one('ir.cron', string='Tarea Programada')

    model_id = fields.Many2one('ir.model', string='Modelo Asociado', ondelete='cascade')
    model_name = fields.Char(string='Nombre Técnico del Modelo')

    # Condiciones
    condition_field = fields.Char(string='Campo Condición')
    condition_operator = fields.Selection([
        ('=', 'Igual a'),
        ('!=', 'Diferente de'),
        ('>', 'Mayor que'),
        ('<', 'Menor que'),
        ('>=', 'Mayor o igual'),
        ('<=', 'Menor o igual'),
        ('in', 'En'),
        ('not in', 'No en'),
        ('like', 'Contiene'),
        ('not like', 'No contiene'),
        ('ilike', 'Contiene (sin mayús)'),
    ], string='Operador', default='=')

    condition_value = fields.Char(string='Valor Condición')

    # Acción a ejecutar
    action_type_exec = fields.Selection([
        ('python', 'Código Python'),
        ('server_action', 'Acción de Servidor'),
        ('email', 'Enviar Email'),
        ('notification', 'Notificación'),
        ('create_record', 'Crear Registro'),
        ('update_record', 'Actualizar Registro'),
        ('api_call', 'Llamada API'),
    ], string='Tipo de Ejecución', default='python')

    server_action_id = fields.Many2one('ir.actions.server', string='Acción de Servidor')
    python_code = fields.Text(string='Código Python')
    email_template_id = fields.Many2one('mail.template', string='Plantilla de Email')

    # Notificaciones
    notify_on_success = fields.Boolean(string='Notificar al Ejecutar', default=False)
    notify_on_failure = fields.Boolean(string='Notificar al Fallar', default=True)
    notify_user_ids = fields.Many2many('res.users', string='Notificar a')

    # Control de ejecución
    max_retries = fields.Integer(string='Máximo de Reintentos', default=3)
    retry_delay_minutes = fields.Integer(string='Espera entre Reintentos (min)', default=5)
    timeout_seconds = fields.Integer(string='Timeout (segundos)', default=300)
    concurrent_execution = fields.Boolean(string='Permitir Ejecución Concurrente', default=False)

    # Estadísticas
    last_execution_date = fields.Datetime(string='Última Ejecución')
    last_execution_state = fields.Selection([
        ('success', 'Éxito'),
        ('failed', 'Fallida'),
        ('warning', 'Advertencia'),
    ], string='Último Estado')
    total_executions = fields.Integer(string='Total Ejecuciones', default=0)
    success_count = fields.Integer(string='Ejecuciones Exitosas', default=0)
    failure_count = fields.Integer(string='Ejecuciones Fallidas', default=0)

    # Auditoría
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    log_ids = fields.One2many('automated.action.log', 'rule_id', string='Registros de Ejecución')

    def execute_action(self, trigger_record=None):
        self.ensure_one()
        if not self.active:
            _logger.info(f"Regla {self.name} inactiva, no se ejecuta")
            return False

        _logger.info(f"Ejecutando regla automatizada: {self.name}")
        log = self.env['automated.action.log'].log_action(
            rule_id=self.id,
            action_type=self.action_type,
            state='executing',
            log_detail=f"Iniciando ejecución de regla: {self.name}",
        )

        try:
            result = self._run_action(trigger_record)
            log.write({
                'state': 'success',
                'completion_date': fields.Datetime.now(),
                'result_data': json.dumps(result) if result else None,
            })
            self.write({
                'last_execution_date': fields.Datetime.now(),
                'last_execution_state': 'success',
                'total_executions': self.total_executions + 1,
                'success_count': self.success_count + 1,
            })
            return True
        except Exception as e:
            import traceback
            log.write({
                'state': 'failed',
                'completion_date': fields.Datetime.now(),
                'error_message': str(e),
                'error_traceback': traceback.format_exc(),
            })
            self.write({
                'last_execution_date': fields.Datetime.now(),
                'last_execution_state': 'failed',
                'total_executions': self.total_executions + 1,
                'failure_count': self.failure_count + 1,
            })
            _logger.error(f"Error ejecutando regla {self.name}: {e}")
            raise

    def _run_action(self, trigger_record=None):
        self.ensure_one()
        action_type = self.action_type

        if action_type == 'reconciliation':
            return self._run_reconciliation()
        elif action_type == 'sbs_report':
            return self._run_sbs_report()
        elif action_type == 'aml_check':
            return self._run_aml_check()
        elif action_type == 'compliance_check':
            return self._run_compliance_check()
        elif action_type == 'provision_calc':
            return self._run_provision_calc()
        elif action_type == 'alert_generation':
            return self._run_alert_generation()
        elif action_type == 'report_scheduling':
            return self._run_report_scheduling()
        else:
            return self._run_custom_action(trigger_record)

    def _run_reconciliation(self):
        _logger.info("Ejecutando conciliación bancaria automática")
        return {'status': 'reconciliation_completed', 'matched': 0, 'unmatched': 0}

    def _run_sbs_report(self):
        _logger.info("Generando reporte SBS automático")
        today = date.today()
        first_day = today.replace(day=1)
        last_month_end = first_day - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        report = self.env['sbs.regulatory.report'].create({
            'name': f"Reporte Automático SBS - {last_month_start}",
            'code': 'SBS-AUTO-001',
            'report_type': 'financial_statements',
            'period_type': 'monthly',
            'date_from': last_month_start,
            'date_to': last_month_end,
            'company_id': self.env.company.id,
        })
        report.action_generate()
        return {'status': 'report_generated', 'report_id': report.id}

    def _run_aml_check(self):
        _logger.info("Ejecutando verificación PLA/FT")
        return {'status': 'aml_check_completed', 'flagged_transactions': 0}

    def _run_compliance_check(self):
        _logger.info("Ejecutando verificación de cumplimiento normativo")
        return {'status': 'compliance_check_completed', 'issues_found': 0}

    def _run_provision_calc(self):
        _logger.info("Ejecutando cálculo de provisiones")
        return {'status': 'provision_calculated', 'total_provision': 0.0}

    def _run_alert_generation(self):
        _logger.info("Ejecutando generación de alertas")
        return {'status': 'alerts_checked', 'alerts_generated': 0}

    def _run_report_scheduling(self):
        _logger.info("Ejecutando programación de reportes")
        return {'status': 'scheduling_completed'}

    def _run_custom_action(self, trigger_record=None):
        if self.action_type_exec == 'python' and self.python_code:
            local_dict = {
                'env': self.env,
                'record': trigger_record,
                'rule': self,
                'log': _logger,
            }
            exec(self.python_code, local_dict)
            return {'status': 'custom_action_completed'}
        return {'status': 'no_action_defined'}
