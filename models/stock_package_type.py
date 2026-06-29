from odoo import fields, models, api


class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    fedex_packaging_type = fields.Selection([
        ('YOUR_PACKAGING', 'Your Packaging'),
        ('FEDEX_ENVELOPE', 'FedEx Envelope'),
        ('FEDEX_BOX', 'FedEx Box'),
        ('FEDEX_EXTRA_SMALL_BOX', 'FedEx Extra Small Box'),
        ('FEDEX_SMALL_BOX', 'FedEx Small Box'),
        ('FEDEX_MEDIUM_BOX', 'FedEx Medium Box'),
        ('FEDEX_LARGE_BOX', 'FedEx Large Box'),
        ('FEDEX_EXTRA_LARGE_BOX', 'FedEx Extra Large Box'),
        ('FEDEX_10KG_BOX', 'FedEx 10kg Box'),
        ('FEDEX_25KG_BOX', 'FedEx 25kg Box'),
        ('FEDEX_PAK', 'FedEx Pak'),
        ('FEDEX_TUBE', 'FedEx Tube'),
    ], string="FedEx Packaging")

    # fedex_package_weight = fields.Float(
    #     string="Package Weight (LB)",
    #     help="Empty package weight in pounds."
    # )
    #
    # fedex_max_weight = fields.Float(
    #     string="Maximum Weight (LB)",
    #     help="Maximum supported package weight in pounds."
    # )