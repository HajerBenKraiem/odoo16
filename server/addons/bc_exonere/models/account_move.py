# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import AccessError, UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_num_exoneration = fields.Char(
        related='partner_id.num_exoneration',
        string="N° Exonération",
        store=True
    )
    partner_date_debut_exoneration = fields.Date(
        related='partner_id.date_debut_exoneration',
        string="Date Début Exonération",
        store=True
    )
    partner_date_fin_exoneration = fields.Date(
        related='partner_id.date_fin_exoneration',
        string="Date Fin Exonération",
        store=True
    )

    @api.constrains('invoice_line_ids', 'fiscal_position_id')
    def _check_tax_exonerated_invoice(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            if move.fiscal_position_id and 'Exonérée' in move.fiscal_position_id.name:
                for line in move.invoice_line_ids:
                    for tax in line.tax_ids:
                        if tax.amount > 0:
                            raise ValidationError(_(
                                "Action Bloquée (Facturation) :\n"
                                "Ce partenaire est sous régime d'exonération.\n"
                                "Vous ne pouvez pas valider de taxe positive (%s%%) sur la ligne '%s'."
                            ) % (tax.amount, line.name))
