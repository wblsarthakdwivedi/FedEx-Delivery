# -*- coding: utf-8 -*-
#
#################################################################################
# Author      : Weblytic Labs Pvt. Ltd. (<https://store.weblyticlabs.com/>)
# Copyright(c): 2023-Present Weblytic Labs Pvt. Ltd.
# All Rights Reserved.
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
##################################################################################
from odoo import models, fields
from odoo.exceptions import UserError


class fedexRateLineWizard(models.TransientModel):
    _name = "fedex.rate.line.wizard"

    wizard_id = fields.Many2one("choose.delivery.carrier", ondelete="cascade")

    selected = fields.Boolean(string="Select")

    carrier_name = fields.Char()
    service_name = fields.Char()
    service_code = fields.Char()

    delivery_days = fields.Integer()

    amount = fields.Float()
    currency_id = fields.Many2one("res.currency")

    def action_select_rate(self):
        self.ensure_one()

        wizard = self.wizard_id
        order = wizard.order_id

        if not order:
            raise UserError("No Sales Order found.")

        # Create the delivery line with the selected price
        order.set_delivery_line(
            wizard.carrier_id,
            self.amount,
            )

        # Remove existing delivery line if there is one
        delivery_lines = order.order_line.filtered(
            lambda l: l.is_delivery
        )

        print(delivery_lines)
        print(delivery_lines.name)

        if delivery_lines:
            delivery_lines.name = f"{wizard.carrier_id.name}\n{self.service_name}"

        # (Optional) Store the selected FedEx service
        order.write({
            "fedex_service_code": self.service_code,
            "fedex_service_name": self.service_name,
            "fedex_rate_amount" : self.amount,
        })

        return {
            "type": "ir.actions.act_window_close",
            "tag": "reload",
        }
