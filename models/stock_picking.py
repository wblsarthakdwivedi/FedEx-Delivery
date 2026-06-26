import base64
import requests
from odoo import fields, models, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fedex_rate_id = fields.Char("FedEx Rate ID")
    fedex_service_name = fields.Char()
    fedex_tracking_url = fields.Char("FedEx Tracking URL")
    fedex_rate_amount = fields.Float("FedEx Rate Amount")
    fedex_label_url = fields.Char("FedEx Label URL")
    fedex_label_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Shipping Label"
    )

    def button_validate(self):

        self.ensure_one()

        if self.carrier_id.delivery_type != "fedex":
            return result

        carrier = self.carrier_id

        if not carrier.fedex_api_key:
            raise UserError("FedEx API Key missing.")

        token = carrier.fedex_auth_token()

        if not self.sale_id.fedex_service_code:
            raise UserError("No FedEx service selected.")

        url = f"{carrier.fedex_base_url}/ship/v1/shipments"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        sender = self.company_id.partner_id
        recipient = self.partner_id

        # Total shipment weight
        weight = sum(
            move.product_id.weight * move.quantity
            for move in self.move_ids
        )
        weight = max(weight, 0.1)

        payload = {
            "labelResponseOptions": "LABEL",
            "accountNumber": {
                "value": carrier.fedex_account,
            },
            "requestedShipment": {
                "shipDateStamp": fields.Date.context_today(self).strftime("%Y-%m-%d"),

                "pickupType": "DROPOFF_AT_FEDEX_LOCATION",

                # Selected by customer during rate request
                "serviceType": self.sale_id.fedex_service_code,

                "packagingType": "YOUR_PACKAGING",

                "shippingChargesPayment": {
                    "paymentType": "SENDER",
                },

                "shipper": {
                    "contact": {
                        "personName": sender.name,
                        "companyName": sender.commercial_company_name or sender.name,
                        "phoneNumber": sender.phone or sender.mobile or "",
                        "emailAddress": sender.email or "",
                    },
                    "address": {
                        "streetLines": list(filter(None, [
                            sender.street,
                            sender.street2,
                        ])),
                        "city": sender.city or "",
                        "stateOrProvinceCode": sender.state_id.code or "",
                        "postalCode": sender.zip or "",
                        "countryCode": sender.country_id.code or "",
                    },
                },

                "recipients": [
                    {
                        "contact": {
                            "personName": recipient.name,
                            "companyName": recipient.commercial_company_name or recipient.name,
                            "phoneNumber": recipient.phone or recipient.mobile or "",
                            "emailAddress": recipient.email or "",
                        },
                        "address": {
                            "streetLines": list(filter(None, [
                                recipient.street,
                                recipient.street2,
                            ])),
                            "city": recipient.city or "",
                            "stateOrProvinceCode": recipient.state_id.code or "",
                            "postalCode": recipient.zip or "",
                            "countryCode": recipient.country_id.code or "",
                        },
                    }
                ],

                "labelSpecification": {
                    "imageType": "PDF",
                    "labelStockType": "PAPER_4X6",
                },

                "requestedPackageLineItems": [
                    {
                        "weight": {
                            "units": "LB",
                            "value": weight,
                        },
                    }
                ],
            },
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60,
        )

        data = response.json()

        print("Shipment Response:", data)

        if response.status_code not in (200, 201):
            raise UserError(str(data))

        shipment = data["output"]["transactionShipments"][0]
        piece = shipment["pieceResponses"][0]

        tracking = piece["trackingNumber"]

        encoded_label = piece["packageDocuments"][0]["encodedLabel"]

        self.write({
            "carrier_tracking_ref": tracking,
        })

        attachment = self.env["ir.attachment"].create({
            "name": f"{tracking}.pdf",
            "datas": encoded_label,
            "mimetype": "application/pdf",
            "res_model": "stock.picking",
            "res_id": self.id,
        })

        self.message_post(
            body=f"""
                FedEx Label Generated
        
                Service : {self.sale_id.fedex_service_name}
        
                Tracking : {tracking}
        
                Amount : {self.sale_id.fedex_rate_amount:.2f} {self.sale_id.currency_id.name}
                """,
                    attachment_ids=[attachment.id],
                )

        result = super().button_validate()

        return result
