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
import requests
import logging

import xml.etree.ElementTree as ET

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[('fedex', 'FedEx')],
        ondelete={'fedex': 'set default'},
    )

    fedex_api_key = fields.Char("API Key", required=True)

    fedex_secret_key = fields.Char("Secret Key", required=True)

    fedex_account = fields.Char(string="Account ID")

    fedex_base_url = fields.Char(
        compute="_compute_fedex_base_url", store=True
    )
    prod_environment = fields.Boolean(
        string="Production Environment",
        default=False
    )

    def toggle_prod_environment(self):
        for c in self:
            c.prod_environment = not c.prod_environment

    @api.depends('prod_environment')
    def _compute_fedex_base_url(self):
        for record in self:
            if record.prod_environment:
                record.fedex_base_url = "https://apis.fedex.com"
            else:
                record.fedex_base_url = "https://apis-sandbox.fedex.com"

    def fedex_auth_token(self):

        self.ensure_one()

        url = f"{self.fedex_base_url}/oauth/token"

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.fedex_api_key,
            "client_secret": self.fedex_secret_key,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)

            response.raise_for_status()

            data = response.json()

            token = data.get("access_token")

            expires_in = data.get("expires_in")

            if not token:
                raise UserError("FedEx token not received from API.")

            _logger.info("FedEx token generated successfully")

            return token

        except requests.exceptions.RequestException as e:
            _logger.error("FedEx Auth Error: %s", str(e))
            raise UserError(f"FedEx Authentication Failed: {e}")


    def fedex_rate_shipment(self, order):
        delivery_line = order.order_line.filtered(lambda l: l.is_delivery)

        return {
            'success': True,
            'price': delivery_line.price_unit if delivery_line else 0.0,
            'error_message': False,
            'warning_message': False,
        }

    def fedex_send_shipping(self, pickings):
        result = []


        for picking in pickings:
            result.append({
                "exact_price": picking.sale_id.fedex_rate_amount or 0.0,
                "tracking_number": picking.carrier_tracking_ref or "",
            })

        return result
