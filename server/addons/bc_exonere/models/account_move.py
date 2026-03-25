# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import AccessError, UserError, ValidationError

#from server.odoo.tools import file_path



class AccountMove(models.Model):
    _inherit = 'account.move'

    num_exoneration = fields.Char(
        #related='partner_id.num_exoneration',
        compute = '_compute_exoneration',
        string="N° Exonération",
        store=True
    )
    date_debut_exoneration = fields.Date(
        #related='partner_id.date_debut_exoneration',
        compute='_compute_exoneration',

        string="Date Début Exonération",
        store=True
    )
    date_fin_exoneration = fields.Date(
        #related='partner_id.date_fin_exoneration',
        compute='_compute_exoneration',
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
    @api.depends('partner_id')
    def _compute_exoneration(self):
        for move in self:
            move.num_exoneration =''
            move.date_debut_exoneration =''
            move.date_fin_exoneration =''
            if move.partner_id:
                move.num_exoneration = move.partner_id.num_exoneration
                move.date_debut_exoneration = move.partner_id.date_debut_exoneration
                move.date_fin_exoneration = move.partner_id.date_fin_exoneration

    def action_post(self):
        for move in self:
            if move.num_exoneration:
                if move.date_debut_exoneration and move.date_fin_exoneration:
                    #vjjv
                    if (move.date_debut_exoneration > move.invoice_date or
                            move.date_fin_exoneration < move.invoice_date):
                        raise ValidationError(
                            "Il faut vérifier la date de facturation"
                        )
                else: raise ValidationError(
                                "Il faut définir les dates fin et début d'exonération"
                            )
        return super(AccountMove, self).action_post()

    def export_exonerated_invoice(self):
        #sous menu / action -- facture
        file_path = 't1.txt'
        with open(file_path, 'w') as f:
            company = self.env.company
            f.write('EF') #ligne entete
            f.write('\n')
            f.write(company.vat)
            f.write('\n')
            for move in self:
                f.write('DF104355CM000')
                f.write(str(move.invoice_date.year))
#ligne détail

                f.write('\n')
            f.write('fin') #ligne footer totaux
            f.write('\n')

        #return True








