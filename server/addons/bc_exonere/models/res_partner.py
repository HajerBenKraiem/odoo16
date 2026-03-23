# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import AccessError, UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    num_exoneration = fields.Char(string="N° Exonération")
    date_debut_exoneration = fields.Date(string="Date Début Exonération")
    date_fin_exoneration = fields.Date(string="Date Fin Exonération")

    @api.onchange('num_exoneration', 'date_debut_exoneration', 'date_fin_exoneration')
    def _onchange_num_exoneration(self):
        if self.num_exoneration:
            pos_fiscal = self.env['account.fiscal.position'].search([
                ('name', 'ilike', 'Exonérée')
            ], limit=1)
            if pos_fiscal:
                self.property_account_position_id = pos_fiscal.id
        else:
            self.property_account_position_id = False

    def _cron_check_exoneration_expiry(self):
        today = date.today()

        pos_exo = self.env['account.fiscal.position'].search([('name', 'ilike', 'Exonérée')], limit=1)
        if pos_exo:
            partners_to_update = self.search([
                ('date_fin_exoneration', '<', today),
            ])
            partners_to_update.write({
                'property_account_position_id': False
            })
            for partner in partners_to_update:
                partner.message_post(body="L'exonération de TVA a expiré. La position fiscale a été réinitialisée.")

    @api.onchange('vat')
    def _onchange_vat_tunisie(self):
        if not self.vat:
            return

        val = self.vat.upper().replace(" ", "").strip()
        self.vat = val

        if len(val) != 12:
            return {'warning': {
                'title': _("Format Invalide"),
                'message': _("Le matricule fiscal tunisien doit comporter exactement 12 caractères.")
            }}

        numero_matricule = val[:7]
        if not numero_matricule.isdigit():
            return {'warning': {
                'title': _("Erreur Numéro Matricule"),
                'message': _("Les 7 premiers caractères doivent être des chiffres.")
            }}

        cle_matricule = val[7:8]
        if not cle_matricule.isalpha():
            return {'warning': {
                'title': _("Erreur Clé"),
                'message': _("Le 8ème caractère doit être une lettre (Clé du matricule).")
            }}

        code_categorie = val[8:9]
        if not code_categorie.isalpha():
            return {'warning': {
                'title': _("Erreur Catégorie"),
                'message': _("Le 9ème caractère doit être une lettre (Code Catégorie : M, P, C, N, E).")
            }}

        etablissement = val[9:]
        if etablissement != "000":
            return {'warning': {
                'title': _("Établissement Secondaire"),
                'message': _("Le numéro d'établissement doit être '000'")
            }}
