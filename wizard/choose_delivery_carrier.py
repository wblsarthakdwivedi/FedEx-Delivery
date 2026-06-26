import requests

import json
import time
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"

    fedex_rate_line_ids = fields.One2many(
        "fedex.rate.line.wizard",
        "wizard_id",
        string="Available Rates",
    )

    selected_rate_id = fields.Many2one(
        "fedex.rate.line.wizard",
        string="Selected FedEx Rate",
    )

    delivery_type = fields.Selection(related='carrier_id.delivery_type')

    def update_price(self):
        self.ensure_one()

        if self.carrier_id.delivery_type != 'fedex':
            return super().update_price()

        token = self.carrier_id.fedex_auth_token()

        url = f"{self.carrier_id.fedex_base_url}/rate/v1/rates/quotes"

        order = self.order_id

        if not order:
            raise UserError("No picking found for this order.")

        picking = self.order_id.picking_ids[:1]

        if picking:
            weight = sum(
                move.product_id.weight * move.product_uom_qty
                for move in picking.move_ids
            )
        else:
            weight = sum(
                line.product_id.weight * line.product_uom_qty
                for line in self.order_id.order_line
            )

        weight = max(weight, 0.1)

        payload = {
            "accountNumber": {
                "value": str(self.carrier_id.fedex_account)
            },
            "requestedShipment": {
                "shipDateStamp": fields.Date.today().strftime("%Y-%m-%d"),

                "pickupType": "DROPOFF_AT_FEDEX_LOCATION",

                "rateRequestType": ["LIST"],

                "shipper": {
                    "address": {
                        "countryCode": self.company_id.country_id.code,
                        "postalCode": self.company_id.zip or "",
                    }
                },

                "recipient": {
                    "address": {
                        "countryCode": self.partner_id.country_id.code,
                        "postalCode": self.partner_id.zip or "",
                    }
                },

                "requestedPackageLineItems": [
                    {
                        "weight": {
                            "units": "LB",
                            "value": weight
                        }
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()

        print("FedEx Rate Response:", data)

        if response.status_code >= 400:
            raise UserError(
                data.get("errors", [{}])[0].get("message", "FedEx Rate Request Failed")
            )

        self.fedex_rate_line_ids = [(5, 0, 0)]

        lines = []

        for service in data.get("output", {}).get("rateReplyDetails", []):
            # take FIRST available rate (LIST)
            rate = service.get("ratedShipmentDetails", [{}])[0]

            lines.append((0, 0, {
                "carrier_name": "FedEx",
                "service_name": service.get("serviceName"),
                "service_code": service.get("serviceType"),
                "amount": rate.get("totalNetCharge"),
                "currency_id": self.env.company.currency_id.id,
                "delivery_days": 0,
            }))

        self.fedex_rate_line_ids = lines

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
