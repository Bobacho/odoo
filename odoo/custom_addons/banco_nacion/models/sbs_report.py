from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta
import base64
import json
import logging

_logger = logging.getLogger(__name__)


class SBSRegulatoryReport(models.Model):
    _name = 'sbs.regulatory.report'
    _description = 'Reporte Regulatorio SBS'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'

    name = fields.Char(string='Nombre del Reporte', required=True, tracking=True)
    display_name = fields.Char(string='Nombre Mostrado', compute='_compute_display_name', store=True)
    code = fields.Char(string='Código SBS', required=True, tracking=True,
                       help='Código del reporte según normativa SBS')
    report_type = fields.Selection([
        ('financial_statements', 'Estados Financieros'),
        ('risk_management', 'Gestión de Riesgos'),
        ('credit_portfolio', 'Cartera Crediticia'),
        ('aml_ctf', 'PLA/FT - Prevención Lavado de Activos'),
        ('liquidity', 'Liquidez'),
        ('capital', 'Adecuación de Capital'),
        ('market_risk', 'Riesgo de Mercado'),
        ('operational_risk', 'Riesgo Operacional'),
        ('interest_rates', 'Tasas de Interés'),
        ('provisions', 'Provisiones'),
        ('treasury', 'Tesorería'),
        ('sbs_especific', 'Reporte Específico SBS'),
    ], string='Tipo de Reporte', required=True, tracking=True)

    period_type = fields.Selection([
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('semiannual', 'Semestral'),
        ('annual', 'Anual'),
        ('on_demand', 'Bajo Demanda'),
    ], string='Periodicidad', required=True, default='monthly', tracking=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('validated', 'Validado'),
        ('submitted', 'Enviado a SBS'),
        ('acknowledged', 'Acusado por SBS'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Anulado'),
    ], string='Estado', default='draft', tracking=True)

    date_from = fields.Date(string='Fecha Inicio', required=True, tracking=True)
    date_to = fields.Date(string='Fecha Fin', required=True, tracking=True)
    generation_date = fields.Datetime(string='Fecha de Generación', readonly=True)
    submission_date = fields.Datetime(string='Fecha de Envío a SBS', readonly=True)
    validation_date = fields.Datetime(string='Fecha de Validación', readonly=True)
    validated_by = fields.Many2one('res.users', string='Validado por', readonly=True)

    company_id = fields.Many2one('res.company', string='Compañía', required=True,
                                  default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)

    report_lines = fields.One2many('sbs.report.line', 'report_id',
                                    string='Líneas del Reporte')

    total_lines = fields.Integer(string='Total Líneas', compute='_compute_totals')
    total_amount = fields.Monetary(string='Monto Total', compute='_compute_totals',
                                    currency_field='currency_id')

    notes = fields.Text(string='Notas y Observaciones')
    regulatory_basis = fields.Text(string='Base Legal/Normativa',
                                    help='Artículo o normativa SBS que respalda este reporte')

    file_generated = fields.Binary(string='Archivo Generado', attachment=True)
    file_filename = fields.Char(string='Nombre del Archivo')
    file_format = fields.Selection([
        ('xml', 'XML SBS'),
        ('csv', 'CSV'),
        ('xlsx', 'Excel (XLSX)'),
        ('pdf', 'PDF'),
        ('txt', 'TXT'),
    ], string='Formato de Archivo', default='xml')

    # Control de versiones
    version = fields.Integer(string='Versión', default=1, readonly=True)
    previous_version_id = fields.Many2one('sbs.regulatory.report',
                                           string='Versión Anterior', readonly=True)

    # Alertas y notificaciones
    alert_ids = fields.Many2many('alert.rule', string='Alertas Disparadas')
    has_anomalies = fields.Boolean(string='Tiene Anomalías', compute='_check_anomalies')

    # Metadatos de auditoría
    audit_hash = fields.Char(string='Hash de Integridad', readonly=True,
                              help='SHA-256 del contenido del reporte para verificación')

    _sql_constraints = [
        ('unique_code_period',
         'UNIQUE(code, date_from, date_to, company_id)',
         'Ya existe un reporte con este código SBS para el período seleccionado.'),
    ]

    @api.depends('name', 'code', 'date_from', 'date_to')
    def _compute_display_name(self):
        for r in self:
            r.display_name = f"[{r.code}] {r.name} ({r.date_from} - {r.date_to})"

    @api.depends('report_lines')
    def _compute_totals(self):
        for r in self:
            lines = r.report_lines
            r.total_lines = len(lines)
            r.total_amount = sum(lines.mapped('amount'))

    def _check_anomalies(self):
        for r in self:
            r.has_anomalies = any(line.is_anomaly for line in r.report_lines)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for r in self:
            if r.date_from > r.date_to:
                raise ValidationError(_('La fecha de inicio debe ser anterior a la fecha de fin.'))

    def action_generate(self):
        self.ensure_one()
        self.write({
            'state': 'generated',
            'generation_date': fields.Datetime.now(),
            'version': self.version + 1 if self.state != 'draft' else 1,
        })
        self._generate_report_file()
        self._log_audit('generate', f'Reporte {self.code} generado')
        return True

    def action_validate(self):
        self.ensure_one()
        validation_errors = self._validate_report()
        if validation_errors:
            raise ValidationError('\n'.join(validation_errors))
        self.write({
            'state': 'validated',
            'validation_date': fields.Datetime.now(),
            'validated_by': self.env.user.id,
        })
        self._log_audit('validate', f'Reporte {self.code} validado por {self.env.user.name}')
        return True

    def action_submit_to_sbs(self):
        self.ensure_one()
        if self.state != 'validated':
            raise UserError(_('Debe validar el reporte antes de enviarlo a SBS.'))
        self.write({
            'state': 'submitted',
            'submission_date': fields.Datetime.now(),
        })
        self._send_to_sbs()
        self._log_audit('submit', f'Reporte {self.code} enviado a SBS')
        return True

    def action_acknowledge(self):
        self.ensure_one()
        self.state = 'acknowledged'
        self._log_audit('acknowledge', f'SBS acusó recibo del reporte {self.code}')
        return True

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'
        self._log_audit('reject', f'Reporte {self.code} rechazado')
        return True

    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'
        return True

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'
        self._log_audit('cancel', f'Reporte {self.code} anulado')
        return True

    def _generate_report_file(self):
        self.ensure_one()
        if self.file_format == 'xml':
            content = self._generate_xml()
            filename = f"SBS_{self.code}_{self.date_from}_{self.date_to}.xml"
        elif self.file_format == 'csv':
            content = self._generate_csv()
            filename = f"SBS_{self.code}_{self.date_from}_{self.date_to}.csv"
        elif self.file_format == 'xlsx':
            content = self._generate_xlsx()
            filename = f"SBS_{self.code}_{self.date_from}_{self.date_to}.xlsx"
        else:
            content = self._generate_txt()
            filename = f"SBS_{self.code}_{self.date_from}_{self.date_to}.txt"

        self.write({
            'file_generated': base64.b64encode(content.encode('utf-8')) if isinstance(content, str) else content,
            'file_filename': filename,
        })

    def _generate_xml(self):
        import xml.etree.ElementTree as ET
        root = ET.Element('SBSReport')
        ET.SubElement(root, 'EntityCode').text = self.env['ir.config_parameter'].get_param(
            'sbs_entity_code', '0001')
        ET.SubElement(root, 'ReportCode').text = self.code
        ET.SubElement(root, 'ReportDate').text = date.today().isoformat()
        ET.SubElement(root, 'PeriodFrom').text = str(self.date_from)
        ET.SubElement(root, 'PeriodTo').text = str(self.date_to)
        ET.SubElement(root, 'Currency').text = self.currency_id.name if self.currency_id else 'PEN'
        ET.SubElement(root, 'Version').text = str(self.version)

        lines_root = ET.SubElement(root, 'ReportLines')
        for line in self.report_lines:
            line_elem = ET.SubElement(lines_root, 'Line')
            ET.SubElement(line_elem, 'Code').text = line.code
            ET.SubElement(line_elem, 'Description').text = line.description
            ET.SubElement(line_elem, 'Amount').text = str(round(line.amount, 2))
            ET.SubElement(line_elem, 'AccountCode').text = line.account_code or ''

        return ET.tostring(root, encoding='unicode', method='xml')

    def _generate_csv(self):
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Código', 'Descripción', 'Monto', 'Cuenta Contable',
                         'Es Anomalía', 'Notas'])
        for line in self.report_lines:
            writer.writerow([
                line.code, line.description, line.amount,
                line.account_code, 'SÍ' if line.is_anomaly else 'NO', line.notes or ''
            ])
        return output.getvalue()

    def _generate_xlsx(self):
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"SBS {self.code}"
            headers = ['Código', 'Descripción', 'Monto', 'Cuenta Contable',
                       'Es Anomalía', 'Notas']
            ws.append(headers)
            for line in self.report_lines:
                ws.append([line.code, line.description, line.amount,
                           line.account_code, 'SÍ' if line.is_anomaly else 'NO',
                           line.notes or ''])
            import io
            output = io.BytesIO()
            wb.save(output)
            return base64.b64encode(output.getvalue())
        except ImportError:
            _logger.warning("openpyxl no disponible, usando CSV como fallback")
            return base64.b64encode(self._generate_csv().encode('utf-8'))

    def _generate_txt(self):
        lines = [
            f"SBS Regulatory Report - {self.code}",
            f"Entity: Banco de la Nación",
            f"Period: {self.date_from} to {self.date_to}",
            f"Generated: {fields.Datetime.now()}",
            "=" * 80,
        ]
        for line in self.report_lines:
            lines.append(f"{line.code:10s} {line.description:50s} {line.amount:15.2f}")
        return '\n'.join(lines)

    def _validate_report(self):
        errors = []
        if not self.report_lines:
            errors.append(_('El reporte debe contener al menos una línea.'))
        if self.total_lines > 10000:
            errors.append(_('El reporte excede el máximo de 10,000 líneas.'))
        unbalanced = any(
            line.amount != 0 and not line.account_code
            for line in self.report_lines
        )
        if unbalanced:
            errors.append(_('Todas las líneas con monto deben tener código de cuenta contable.'))
        return errors

    def _send_to_sbs(self):
        # Simula el envío al sistema SBS
        _logger.info(f"Reporte {self.code} preparado para envío a SBS")
        self.message_post(
            body=_("Reporte preparado para envío al sistema SBS. "
                   "El acuse será procesado cuando SBS responda."),
            subject=_("Envío a SBS"),
        )

    def _log_audit(self, action_type, description):
        self.env['audit.trail.entry'].create({
            'model_name': self._name,
            'record_id': self.id,
            'action_type': action_type,
            'description': description,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
        })

    def action_view_lines(self):
        self.ensure_one()
        return {
            'name': _('Líneas del Reporte'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'sbs.report.line',
            'domain': [('report_id', '=', self.id)],
            'context': {'default_report_id': self.id},
        }

    def action_generate_hash(self):
        self.ensure_one()
        import hashlib
        content = f"{self.code}{self.date_from}{self.date_to}{self.total_amount}{self.version}"
        self.audit_hash = hashlib.sha256(content.encode()).hexdigest()
        return True


class SBSReportLine(models.Model):
    _name = 'sbs.report.line'
    _description = 'Línea de Reporte SBS'
    _order = 'sequence, id'

    report_id = fields.Many2one('sbs.regulatory.report', string='Reporte',
                                 required=True, ondelete='cascade')
    sequence = fields.Integer(string='Secuencia', default=10)
    code = fields.Char(string='Código SBS', required=True)
    description = fields.Text(string='Descripción', required=True)
    amount = fields.Float(string='Monto', digits=(16, 2), required=True, default=0.0)
    account_code = fields.Char(string='Código de Cuenta Contable')
    account_id = fields.Many2one('account.account', string='Cuenta Contable')
    is_anomaly = fields.Boolean(string='Es Anomalía', default=False,
                                 help='Marcar si este valor es anómalo y requiere revisión')
    notes = fields.Text(string='Notas')
    company_id = fields.Many2one('res.company', string='Compañía',
                                  related='report_id.company_id', store=True)

    _sql_constraints = [
        ('unique_report_code',
         'UNIQUE(report_id, code)',
         'El código SBS debe ser único dentro del reporte.'),
    ]
