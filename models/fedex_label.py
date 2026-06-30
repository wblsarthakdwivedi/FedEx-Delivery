from odoo import models, fields, api


class FedexLabel(models.Model):
    _name = "fedex.label"
    _description = "FedEx Shipping Labels"
    _order = "id desc"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Delivery Order",
        required=True,
        ondelete="cascade",
    )

    sale_ids = fields.Many2one(
        "sale.order",
        string="Sales Order",
        required=True,
        tracking=True,
    )

    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Shipping Label",
        required=True,
        ondelete="cascade",
    )

    tracking_number = fields.Char(
        string="Tracking Number",
        readonly=True,
    )

    shipment_id = fields.Char(
        string="Shipment ID",
        readonly=True,
        help="FedEx Shipment Identifier",
    )

    service_type = fields.Char(
        string="Service",
        readonly=True,
    )

    package_count = fields.Integer(
        string="Packages",
        default=1,
        readonly=True,
    )

    shipment_response = fields.Text(
        string="Shipment Response",
        readonly=True,
    )

    # shipping_id = fields.Many2one(
    #     "fedex.shipping",
    #     string="Shipping Order",
    #     compute="_compute_shipping_id",
    #     store=True,
    # )
    #
    # @api.depends("picking_id")
    # def _compute_shipping_id(self):
    #     for rec in self:
    #         rec.shipping_id = getattr(rec.picking_id, "fedex_shipping_id", False)

    def action_open_label(self):
        self.ensure_one()

        if not self.attachment_id:
            raise UserError("No shipping label found.")

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=false" % self.attachment_id.id,
            "target": "new",
        }