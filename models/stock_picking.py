import base64
import requests
from odoo import fields, models, api
from odoo.exceptions import UserError
import json as pyjson


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

    package_type_id = fields.Many2one(
        "stock.package.type",
        string="Package Type",
        help="Package used for this shipment."
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

        package = self.package_type_id

        if not package:
            raise UserError("Please select a Package Type.")

        if not package.fedex_packaging_type:
            raise UserError(
                "Please configure the FedEx Packaging Type on the selected Package Type."
            )

        # if not package.packaging_length or not package.width or not package.height:
        #     raise UserError(
        #         "Please configure the package dimensions."
        #     )

        sender = self.company_id.partner_id
        recipient = self.partner_id

        # Total shipment weight
        weight = sum(
            move.product_id.weight * move.quantity
            for move in self.move_ids
        )
        weight += package.base_weight or 0.1

        weight_lb = round(weight * 2.20462, 2)

        length = max(1, round(package.packaging_length / 25.4))
        width = max(1, round(package.width / 25.4))
        height = max(1, round(package.height / 25.4))

        phone = recipient.phone or getattr(recipient, "mobile", "") or ""
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

                "packagingType": package.fedex_packaging_type,

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
                            "value": weight_lb,
                        },
                        "dimensions": {
                            "length": int(length),
                            "width": int(width),
                            "height": int(height),
                            "units": "IN",
                        },
                    }
                ],
            },
        }

        is_international = (
                sender.country_id
                and recipient.country_id
                and sender.country_id.id != recipient.country_id.id
        )

        if is_international:

            commodities = []
            total_customs_value = 0.0

            for move in self.move_ids:
                product = move.product_id

                qty = move.quantity or 1

                unit_price = (
                    move.sale_line_id.price_unit
                    if move.sale_line_id
                    else product.lst_price
                )

                customs_value = qty * unit_price
                total_customs_value += customs_value

                commodities.append({
                    "description": product.name[:35],
                    "countryOfManufacture": (
                        sender.country_id.code
                    ),
                    "quantity": qty,
                    "quantityUnits": "EA",

                    "unitPrice": {
                        "amount": round(unit_price, 2),
                        "currency": self.company_id.currency_id.name,
                    },

                    "customsValue": {
                        "amount": round(customs_value, 2),
                        "currency": self.company_id.currency_id.name,
                    },

                    "weight": {
                        "units": "LB",
                        "value": max(product.weight * qty, 0.1),
                    },

                    "numberOfPieces": int(qty),
                })

            payload["requestedShipment"]["customsClearanceDetail"] = {

                "dutiesPayment": {
                    "paymentType": "SENDER",
                },

                "documentContent": "NON_DOCUMENTS",

                "commercialInvoice": {
                    "shipmentPurpose": "SOLD",
                },

                "customsValue": {
                    "amount": round(total_customs_value, 2),
                    "currency": self.company_id.currency_id.name,
                },

                "commodities": commodities,
            }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60,
        )

        data = response.json()

        print("response: ", data)

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
            "name": f"FedEX_{self.name}.pdf",
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

        shipping = self.env["fedex.shipping"].create({
            "name": f"SHIP-{self.sale_id.name or self.name}",
            "picking_id": self.id,
            "sale_id": self.sale_id.id,
            "partner_id": self.partner_id.id,
            "carrier_id": self.carrier_id.id,
            "package_type_id": self.package_type_id.id,
            "service_name": self.sale_id.fedex_service_name,
            "shipping_charge": self.sale_id.fedex_rate_amount,
            "tracking_number": tracking,
            "state": "shipped",
        })

        print("Shipping Order Created:", shipping)

        self.env["fedex.label"].create({
            "picking_id": self.id,
            "sale_ids": self.sale_id.id,
            "tracking_number": tracking,
            "service_type": self.sale_id.fedex_service_code,
            "attachment_id": attachment.id,
            "shipment_response": pyjson.dumps(data, indent=4),
        })

        result = super().button_validate()

        return result

    def open_website_url(self):
        self.ensure_one()

        if not self.carrier_tracking_ref:
            raise UserError("No tracking number available.")

        # Sandbox
        if not self.carrier_id.prod_environment:
            raise UserError(
                "FedEx sandbox shipments cannot be tracked on the public FedEx website."
            )

        # Production
        return {
            "type": "ir.actions.act_url",
            "url": f"https://www.fedex.com/fedextrack/?trknbr={self.carrier_tracking_ref}",
            "target": "new",
        }
