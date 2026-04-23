# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountWithholdingTax(models.Model):
    _name = "account.withholding.tax"

    name = fields.Char(string="Tax Name", required=True)

    rate = fields.Float(
        string="Rate", 
        required=True, 
        digits=(16, 4)
    )

    account_id = fields.Many2one(
        "account.account",
        # Remove the deprecated domain filter
        string="Tax Account",
        ondelete="restrict",
        required=True,
    )
    refund_account_id = fields.Many2one(
        "account.account",
        # Remove the deprecated domain filter
        string="Tax Account on Refunds",
        ondelete="restrict",
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company'
    )