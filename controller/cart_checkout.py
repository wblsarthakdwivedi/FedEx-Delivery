import requests

from odoo import http, fields
from odoo.http import route, request
import logging

from odoo.tools import format_amount

_logger = logging.getLogger(__name__)


class CartCheckout(http.Controller):

    @http.route("/fedex/rates", type="json", auth="public", website=True)
    def fedex_rates(self, carrier_id):

        sale_order_id = request.session.get("sale_order_id")
        if not sale_order_id:
            return []

        order = request.env["sale.order"].sudo().browse(sale_order_id)

        if not order.exists():
            return []

        carrier = request.env["delivery.carrier"].sudo().browse(carrier_id)

        token = carrier.fedex_auth_token()

        picking = order.picking_ids[:1]

        if picking:
            weight = sum(
                move.product_id.weight * move.product_uom_qty
                for move in picking.move_ids
            )
        else:
            weight = sum(
                line.product_id.weight * line.product_uom_qty
                for line in order.order_line
            )

        weight = max(weight, 0.1)

        payload = {
            "accountNumber": {
                "value": carrier.fedex_account,
            },
            "requestedShipment": {
                "shipDateStamp": fields.Date.today().strftime("%Y-%m-%d"),
                "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
                "rateRequestType": ["LIST"],
                "shipper": {
                    "address": {
                        "countryCode": order.company_id.country_id.code,
                        "postalCode": order.company_id.zip or "",
                    }
                },
                "recipient": {
                    "address": {
                        "countryCode": order.partner_shipping_id.country_id.code,
                        "postalCode": order.partner_shipping_id.zip or "",
                    }
                },
                "requestedPackageLineItems": [{
                    "weight": {
                        "units": "KG",
                        "value": weight,
                    }
                }],
            },
        }

        response = requests.post(
            f"{carrier.fedex_base_url}/rate/v1/rates/quotes",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )

        data = response.json()

        print("controller Response", data)

        if response.status_code >= 400:
            return []

        rates = []

        for service in data.get("output", {}).get("rateReplyDetails", []):
            rate = service.get("ratedShipmentDetails", [{}])[0]

            rates.append({
                "service_name": service.get("serviceName"),
                "service_code": service.get("serviceType"),
                "amount": rate.get("totalNetCharge"),
                "currency": order.currency_id.name,
                "delivery_days": 0,
            })

        request.session["fedex_rates"] = rates

        print("Saved Rates:", request.session["fedex_rates"])


        return rates

    @route('/fedex/select_rate', type='json', auth='public', methods=['POST'], website=True)
    def fedex_select_rate(self, carrier_id=None, service_code=None, **kwargs):

        order = request.cart

        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))

        rates = request.session.get('fedex_rates', [])

        print("rates",rates)

        rate = next(
            (
                r for r in rates
                if r.get('service_code') == service_code
            ),
            False,
        )

        if not rate:
            return {
                'success': False,
                'message': 'FedEx service not found.',
            }

        # Update delivery amount
        order.set_delivery_line(
            carrier,
            float(rate['amount']),
        )

        delivery_line = order.order_line.filtered(
            lambda l: l.is_delivery
        )

        if delivery_line:
            delivery_line.name = (
                f"{carrier.name}\n"
                f"{rate['service_name']}"
            )

        order.write({
            'fedex_service_code': rate.get('service_code'),
            'fedex_service_name': rate.get('service_name'),
            'fedex_rate_amount': float(rate.get('amount', 0.0)),
        })

        return {
            'success': True,
            'service_name': rate.get('service_name'),
            'service_code': rate.get('service_code'),
            'is_service_selected': True,
            'is_free_delivery': float(rate['amount']) == 0,
            'compute_price_after_delivery': False,

            'amount_delivery':
                f'$ <span class="oe_currency_value">{order.amount_delivery:.2f}</span>',

            'amount_untaxed':
                f'$ <span class="oe_currency_value">{order.amount_untaxed:.2f}</span>',

            'amount_tax':
                f'$ <span class="oe_currency_value">{order.amount_tax:.2f}</span>',

            'amount_total':
                f'$ <span class="oe_currency_value">{order.amount_total:.2f}</span>',
        }
