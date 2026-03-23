# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import AccessError, UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('order_line')
    def _check_tax_exonerated_sale(self):
        for order in self:
            if order.fiscal_position_id and 'Exonérée' in order.fiscal_position_id.name:
                for line in order.order_line:
                    for tax in line.tax_id:
                        if tax.amount > 0:
                            raise ValidationError(_(
                                "Action Bloquée (Vente) :\n"
                                "Le client est exonéré (Position Fiscale : %s).\n"
                                "La taxe '%s' (%s%%) est interdite sur la ligne '%s'."
                            ) % (order.fiscal_position_id.name, tax.name, tax.amount, line.name))
