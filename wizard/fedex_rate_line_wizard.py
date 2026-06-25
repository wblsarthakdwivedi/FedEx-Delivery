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