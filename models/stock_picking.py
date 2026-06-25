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


    