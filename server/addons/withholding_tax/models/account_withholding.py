# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError
import json

_logger = logging.getLogger(__name__)


class AccountWithholding(models.Model):
    _name = "account.withholding"

    @api.model
    def create(self, vals_list):
        """
        Override create method to generate sequence number
        """
        if isinstance(vals_list, list):
            for vals in vals_list:
                if vals.get('name', _('New')) == _('New'):
                    vals['name'] = self.env["ir.sequence"].next_by_code("account.withholding") or _('New')
        else:
            # Handle single dictionary (shouldn't happen in Odoo 15+ but just in case)
            if vals_list.get('name', _('New')) == _('New'):
                vals_list['name'] = self.env["ir.sequence"].next_by_code("account.withholding") or _('New')

        return super(AccountWithholding, self).create(vals_list)

    def _compute_currency_id(self):
        self.currency_id = self.journal_id.company_id.currency_id

    @api.model
    def _default_journal_id(self):
        return self.env["account.journal"].search([("type", "=", "general")], limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal_id()
        return (
                journal.currency_id
                or journal.company_id.currency_id
                or self.env.user.company_id.currency_id
        )

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default=lambda self: _('New'),
        copy=False
    )

    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")],
        string="Withholding Tax Status",
        default="draft",

    )

    type = fields.Selection(
        [
            ("out_withholding", "Customer Withholding"),
            ("in_withholding", "Vendor Withholding"),
        ],
        readonly=True,
    )

    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)

    journal_id = fields.Many2one(
        "account.journal", string="Journal", default=_default_journal_id, required=True
    )

    partner_id = fields.Many2one("res.partner", required=True)

    account_invoice_ids = fields.One2many(
        "account.move", inverse_name="withholding_id", string="Invoices"
    )

    account_withholding_tax_ids = fields.Many2many(
        "account.withholding.tax", string="Withholding Type", required=True
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        readonly=True,
        default=_default_currency,
        track_visibility="always",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        change_default=True,
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )

    amount = fields.Float(
        string="Withholding Tax", digits=(16, 2)
    )

    account_move_id = fields.Many2one("account.move")

    def unlink(self):
        for rec in self:
            if rec.state == 'draft':
                return super(AccountWithholding, rec).unlink()
            else:
                raise UserError(_("You cannot delete this Document !"))

    @api.onchange("partner_id")
    def _partner_id_onchange(self):
        for invoice in self.account_invoice_ids:
            invoice.write({"withholding_id": False})
        self.account_invoice_ids = []

    @api.depends("account_invoice_ids", "account_withholding_tax_ids")
    @api.onchange("account_invoice_ids", "account_withholding_tax_ids")
    def _compute_amount(self):
        for record in self:
            sum = 0.0
            for tax in record.account_withholding_tax_ids:
                invoice_sum = 0.0
                stamp_tax = self.env["account.tax"].search(
                    [("name", "like", "Timbre Fiscal Vente")], limit=1
                )
                for invoice in record.account_invoice_ids:
                    t = invoice
                    if stamp_tax:
                        if record.type == "in_withholding":
                            invoice_sum += abs(
                                invoice.amount_total_signed + stamp_tax.amount
                            )
                        elif record.type == "out_withholding":

                            invoice_sum += abs(
                                invoice.amount_total_signed - stamp_tax.amount
                            )
                    else:
                        invoice_sum += abs(invoice.amount_total_signed)
                sum += (invoice_sum * tax.rate) / 100
            record.amount = sum

    def button_validate_withholding(self):
        vals = {
            "ref": self.name,
            "journal_id": self.journal_id.id,
            "narration": False,
            "date": self.date,
            "partner_id": self.partner_id.id,
            "line_ids": [],
        }
        # vals for move
        partner_account_id = (
                self.type == "in_withholding"
                and self.partner_id.property_account_payable_id.id
                or self.partner_id.property_account_receivable_id.id
        )
        debit = self.type == "in_withholding" and self.amount or 0.0
        credit = self.type == "out_withholding" and self.amount or 0.0

        partner = {
            "name": self.name,
            "journal_id": self.journal_id.id,
            "company_id": self.journal_id.company_id.id,
            "credit": credit,
            "debit": debit,
            "date": self.date,
            "partner_id": self.partner_id.id,
            "account_id": partner_account_id,
        }

        vals["line_ids"].append([0, False, partner])

        for l in self.account_withholding_tax_ids:
            deb = self.type == "in_withholding" and self.amount or 0.0
            cred = self.type == "out_withholding" and self.amount or 0.0
            withholding = {
                "name": self.name,
                "journal_id": self.journal_id.id,
                "company_id": self.journal_id.company_id.id,
                "credit": deb,
                "debit": cred,
                "date": self.date,
                "partner_id": self.partner_id.id,
                "account_id": l.account_id.id,
            }
            vals["line_ids"].append([0, False, withholding])

        self.account_move_id = self.env["account.move"].create(vals)
        # customer
        withholding_entry = self.account_move_id.line_ids.filtered(
            lambda line: line.account_id.id == partner_account_id
        )
        first_invoice_id = (
                self.account_invoice_ids and self.account_invoice_ids[0] or False
        )

        if first_invoice_id:
            invoice_entry = first_invoice_id.line_ids.filtered(
                lambda line: line.account_id.id == partner_account_id
            )
            _logger.info("receivable_invoice_entry %s", invoice_entry)

            if self.type == "out_withholding":
                self.env["account.partial.reconcile"].create(
                    {
                        "credit_move_id": withholding_entry.id,
                        "debit_move_id": invoice_entry.id,
                        "debit_amount_currency": self.amount,
                        "credit_amount_currency": self.amount,
                        "amount": self.amount,
                        "credit_currency_id": self.currency_id.id,
                        "debit_currency_id": self.currency_id.id,
                    }
                )
            # supplier

            elif self.type == "in_withholding":
                self.env["account.partial.reconcile"].create(
                    {
                        "credit_move_id": invoice_entry.id,
                        "debit_move_id": withholding_entry.id,
                        "debit_amount_currency": self.amount,
                        "credit_amount_currency": self.amount,
                        "amount": self.amount,
                        "credit_currency_id": self.currency_id.id,
                        "debit_currency_id": self.currency_id.id,
                    }
                )

        self.account_move_id.action_post()

        self.state = "done"

    def button_reset_to_draft_withholding(self):
        self.account_move_id.line_ids.remove_move_reconcile()
        self.account_move_id.button_cancel()
        self.account_move_id.line_ids.unlink()
        self.account_move_id.with_context(force_delete=True).unlink()
        self.state = "draft"

    def button_account_move(self):
        return {
            "name": "Journal Items",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "res_id": self.account_move_id.id,
        }

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "withholding_tax.action_withholding_report"
        ).report_action(self)

    # def generate_function_delete_ras(self):
    #     rec_ids = self.env['account.withholding'].sudo().search([('type','=','out_withholding'),('name', '=', 'WI/032')])
    #     if len(rec_ids.ids) > 0 :
    #         for r in rec_ids:
    #             r.write({'account_invoice_ids': False})
    #             r.write({'state': 'draft'})
    #     rec_ids = self.env['account.withholding'].sudo().search([('type','=','out_withholding'),('name', '=', 'WI/033')])
    #     if len(rec_ids.ids) > 0 :
    #         for r in rec_ids:
    #             r.write({'account_invoice_ids': False})
    #             r.write({'state': 'draft'})
