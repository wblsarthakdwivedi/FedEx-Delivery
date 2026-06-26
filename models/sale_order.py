from odoo import api,fields,models



class SaleOrder(models.Model):
    _inherit = "sale.order"

    fedex_rate_id = fields.Char(string="FedEx Rate ID")
    fedex_rate_amount = fields.Float(string="FedEx Rate Amount")
    fedex_service_name = fields.Char(string="FedEx Service")
    fedex_service_code = fields.Char(string="FedEx Service Code")
    fedex_tracking_number = fields.Char(string="FedEx Tracking Number")
