from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class SBSReportWizard(models.TransientModel):
    _name = 'sbs.report.wizard'
    _description = 'Asistente de Generación de Reporte SBS'

    report_type = fields.Selection([
        ('financial_statements', 'Estados Financieros'),
        ('risk_management', 'Gestión de Riesgos'),
        ('credit_portfolio', 'Cartera Crediticia'),
        ('aml_ctf', 'PLA/FT - Prevención Lavado de Activos'),
        ('liquidity', 'Liquidez'),
        ('capital', 'Adecuación de Capital'),
        ('market_risk', 'Riesgo de Mercado'),
        ('operational_risk', 'Riesgo Operacional'),
        ('provisions', 'Provisiones'),
        ('treasury', 'Tesorería'),
    ], string='Tipo de Reporte', required=True)

    period_type = fields.Selection([
        ('daily', 'Diario'),
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('annual', 'Anual'),
    ], string='Periodicidad', required=True, default='monthly')

    date_from = fields.Date(string='Fecha Inicio', required=True)
    date_to = fields.Date(string='Fecha Fin', required=True)
    file_format = fields.Selection([
        ('xml', 'XML SBS'),
        ('csv', 'CSV'),
        ('xlsx', 'Excel (XLSX)'),
        ('pdf', 'PDF'),
    ], string='Formato de Archivo', default='xml')

    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    generate_automatically = fields.Boolean(string='Generar automáticamente', default=True)
    notify_users = fields.Boolean(string='Notificar a usuarios', default=True)

    @api.onchange('period_type')
    def _onchange_period_type(self):
        today = date.today()
        if self.period_type == 'daily':
            self.date_from = today
            self.date_to = today
        elif self.period_type == 'monthly':
            self.date_from = today.replace(day=1)
            self.date_to = today
        elif self.period_type == 'quarterly':
            quarter = (today.month - 1) // 3
            self.date_from = date(today.year, quarter * 3 + 1, 1)
            self.date_to = today
        elif self.period_type == 'annual':
            self.date_from = date(today.year, 1, 1)
            self.date_to = today

    def action_generate_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise ValidationError(_('La fecha de inicio debe ser anterior a la fecha de fin.'))

        report = self.env['sbs.regulatory.report'].create({
            'name': f"Reporte {dict(self._fields['report_type'].selection).get(self.report_type)} - {self.date_from}",
            'code': self._generate_report_code(),
            'report_type': self.report_type,
            'period_type': self.period_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'file_format': self.file_format,
            'company_id': self.company_id.id,
        })

        if self.generate_automatically:
            report.action_generate()

        if self.notify_users:
            report.message_post(
                body=_("Reporte generado correctamente."),
                subject=_("Reporte SBS Generado"),
            )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sbs.regulatory.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _generate_report_code(self):
        prefix_map = {
            'financial_statements': 'SBS-FIN',
            'risk_management': 'SBS-RSK',
            'credit_portfolio': 'SBS-CRD',
            'aml_ctf': 'SBS-AML',
            'liquidity': 'SBS-LIQ',
            'capital': 'SBS-CAP',
            'market_risk': 'SBS-MRK',
            'operational_risk': 'SBS-OPS',
            'provisions': 'SBS-PRO',
            'treasury': 'SBS-TRS',
        }
        prefix = prefix_map.get(self.report_type, 'SBS-GEN')
        seq = self.env['ir.sequence'].next_by_code('sbs.report.code') or '0001'
        return f"{prefix}-{seq}"
