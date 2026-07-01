from odoo import api, fields, models
from odoo.exceptions import UserError


class FedexShipping(models.Model):
    _name = "fedex.shipping"
    _description = "FedEx Shipping Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Shipping Order",
        default="New",
        readonly=True,
        copy=False,
        tracking=True,
    )

    state = fields.Selection([
        ("draft", "Draft"),
        ("shipped", "Shipped"),
        ("cancel", "Cancelled"),
    ], default="draft", tracking=True)

    sale_id = fields.Many2one(
        "sale.order",
        string="Sales Order",
        tracking=True,
    )

    picking_id = fields.Many2one(
        "stock.picking",
        string="Delivery Order",
        required=True,
        tracking=True,
    )

    carrier_id = fields.Many2one(
        "delivery.carrier",
        string="Delivery Carrier",
        tracking=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        related="sale_id.partner_id",
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        related="sale_id.company_id",
        store=True,
    )

    package_type_id = fields.Many2one(
        "stock.package.type",
        string="Package Type",
    )

    service_name = fields.Char("FedEx Service")

    # service_code = fields.Char("Service Code")

    shipping_charge = fields.Monetary(
        string="Shipping Charge",
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    tracking_number = fields.Char(
        tracking=True,
    )

    shipment_date = fields.Datetime(
        default=fields.Datetime.now,
    )


    weight = fields.Float()

    notes = fields.Text()