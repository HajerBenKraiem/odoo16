# -*- coding: utf-8 -*-
import base64

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
#controle tva
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
#validation facture

    def action_post(self):
        for move in self:
            if move.move_type in ['out_invoice', 'in_invoice']:
                if move.num_exoneration:
                    if move.date_debut_exoneration and move.date_fin_exoneration:
                        if (not move.invoice_date or
                                move.date_debut_exoneration > move.invoice_date or
                                move.date_fin_exoneration < move.invoice_date):
                            raise ValidationError(
                                "Il faut vérifier la date de facturation"
                            )
                    else:
                        raise ValidationError(
                            "Il faut définir les dates fin et début d'exonération"
                        )
        return super(AccountMove, self).action_post()
        # 4. EXPORT TXT (CDC)
        # ========================

    def export_exonerated_invoice(self):
        if self.line_ids:

            str_line = ""
            lines = []

            fac_deb = ""
            fac_deb += "EF"
            if self[0].company_id.vat:
                if len(self[0].company_id.vat) == 12:
                    fac_deb += self[0].company_id.vat
                else:
                    raise ValidationError(_('Votre matricule fiscal doit être au format 0000000AA000.'))
            else:
                raise ValidationError(_('Assurez-vous d\'avoir défini le matricule fiscale de votre entreprise.'))
            if not self[0].partner_id.vat:
                raise ValidationError(_('Assurez-vous d\'avoir défini le matricule fiscale de votre client.'))
            fac_deb += str(self[0].invoice_date.year)

            if (self[0].invoice_date.month - 1) // 3 + 1 == 1:
                fac_deb += "T1"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 2:
                fac_deb += "T2"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 3:
                fac_deb += "T3"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 4:
                fac_deb += "T4"

            fac_deb += self[0].company_id.name.ljust(40)

            if self[0].company_id.street:
                fac_deb += self[0].company_id.city.ljust(40)
                fac_deb += self[0].company_id.street.ljust(72)
                fac_deb += self[0].company_id.street.split(',')[0].zfill(4)
                fac_deb += self[0].company_id.zip.zfill(4)
            else:
                raise ValidationError(_('Assurez-vous d\'avoir défini l\'address de votre entreprise.'))
            fac_deb += "\n"

            str_line += fac_deb

            num_order = 0

            amount_HT_total = 0
            amount_TVA_total = 0
            # amount_fodec_total = 0

            for invoice_line in self:
                # Calculate HT total
                amount_HT_total += invoice_line.amount_untaxed
                # Calculate TVA total
                amount_TVA_total += invoice_line.amount_tax
                # adjustment amount HT
                amount_HT = "%.3f" % invoice_line.amount_untaxed
                amount_HT = amount_HT.replace(".", "")
                # adjustment amount TVA
                amount_TVA = "%.3f" % invoice_line.amount_tax
                amount_TVA = amount_TVA.replace(".", "")

                num_order += 1
                str_line += "DF"
                str_line += invoice_line.company_id.vat
                str_line += str(invoice_line.invoice_date.year)

                if (invoice_line.invoice_date.month - 1) // 3 + 1 == 1:
                    str_line += "T1"
                elif (invoice_line.invoice_date.month - 1) // 3 + 1 == 2:
                    str_line += "T2"
                elif (invoice_line.invoice_date.month - 1) // 3 + 1 == 3:
                    str_line += "T3"
                elif (invoice_line.invoice_date.month - 1) // 3 + 1 == 4:
                    str_line += "T4"
                # Num order
                str_line += str(num_order).zfill(6)
                # Num autorisation
                str_line += (invoice_line.partner_id.num_exoneration or '').ljust(30)
                # Type identifiant du client
                str_line += (invoice_line.partner_id.vat or '').ljust(12)
                # Nom et prénom du client
                str_line += invoice_line.partner_id.name.ljust(40)
                # Num facture
                str_line += invoice_line.name.ljust(30)
                # Date Facture
                list_date_fac = str(invoice_line.invoice_date).split("-")
                str_line += list_date_fac[2] + list_date_fac[1] + list_date_fac[0]

                # Prix de vente (Hors Taxes)
                str_line += amount_HT.zfill(15)
                # Montant TVA
                str_line += amount_TVA.zfill(15)

                str_line += '<'.ljust(320, ' ') + '/>'
                str_line += '\n'

                lines.append(str_line)

            # adjustment amount total HT
            amount_HT_total = "%.3f" % amount_HT_total
            amount_HT_total = amount_HT_total.replace(".", "")
            # adjustment amount total TVA
            amount_TVA_total = "%.3f" % amount_TVA_total
            amount_TVA_total = amount_TVA_total.replace(".", "")

            fac_fin = ""
            fac_fin += "TF"
            fac_fin += self[0].company_id.vat

            fac_fin += str(self[0].invoice_date.year)

            if (self[0].invoice_date.month - 1) // 3 + 1 == 1:
                fac_fin += "T1"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 2:
                fac_fin += "T2"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 3:
                fac_fin += "T3"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 4:
                fac_fin += "T4"

            # NB Factures
            fac_fin += str(len(lines)).zfill(6)
            # Zone reservée
            fac_fin += "".ljust(142)
            # Total prix HT
            fac_fin += amount_HT_total.zfill(15)
            # Total TVA
            fac_fin += amount_TVA_total.zfill(15)

            str_line += fac_fin

            import os.path
            import base64
            year = str(self[0].invoice_date.year)

            if (self[0].invoice_date.month - 1) // 3 + 1 == 1:
                year += "T1"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 2:
                year += "T2"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 3:
                year += "T3"
            elif (self[0].invoice_date.month - 1) // 3 + 1 == 4:
                year += "T4"
            filename = f"FAC_{year}.txt"
            encoded_content = base64.b64encode(str_line.encode('utf-8'))

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': encoded_content,
                'mimetype': 'text/plain',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
