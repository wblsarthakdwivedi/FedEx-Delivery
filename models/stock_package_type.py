from odoo import fields, models, api


class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    is_selectable = fields.Boolean(default=True)

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


    @api.onchange("fedex_packaging_type")
    def _onchange_fedex_packaging_type(self):
        dimensions = {
            "YOUR_PACKAGING": {
                "packaging_length": 300,
                "width": 200,
                "height": 150,
                "base_weight": 5,
                "max_weight": 150,
            },
            "FEDEX_ENVELOPE": {
                "packaging_length": 381,
                "width": 305,
                "height": 10,
                "base_weight": 0.5,
                "max_weight": 1,
            },
            "FEDEX_BOX": {
                "packaging_length": 305,
                "width": 254,
                "height": 102,
                "base_weight": 2,
                "max_weight": 20,
            },
            "FEDEX_EXTRA_SMALL_BOX": {
                "packaging_length": 279,
                "width": 32,
                "height": 216,
                "base_weight": 1,
                "max_weight": 10,
            },
            "FEDEX_SMALL_BOX": {
                "packaging_length": 305,
                "width": 254,
                "height": 38,
                "base_weight": 2,
                "max_weight": 20,
            },
            "FEDEX_MEDIUM_BOX": {
                "packaging_length": 356,
                "width": 279,
                "height": 76,
                "base_weight": 3,
                "max_weight": 20,
            },
            "FEDEX_LARGE_BOX": {
                "packaging_length": 432,
                "width": 305,
                "height": 102,
                "base_weight": 5,
                "max_weight": 30,
            },
            "FEDEX_EXTRA_LARGE_BOX": {
                "packaging_length": 559,
                "width": 381,
                "height": 152,
                "base_weight": 8,
                "max_weight": 50,
            },
            "FEDEX_10KG_BOX": {
                "packaging_length": 400,
                "width": 310,
                "height": 270,
                "base_weight": 10,
                "max_weight": 22,
            },
            "FEDEX_25KG_BOX": {
                "packaging_length": 540,
                "width": 420,
                "height": 335,
                "base_weight": 25,
                "max_weight": 55,
            },
            "FEDEX_PAK": {
                "packaging_length": 394,
                "width": 305,
                "height": 25,
                "base_weight": 1,
                "max_weight": 5,
            },
            "FEDEX_TUBE": {
                "packaging_length": 965,
                "width": 152,
                "height": 152,
                "base_weight": 2,
                "max_weight": 20,
            },
        }

        vals = dimensions.get(self.fedex_packaging_type)
        if vals:
            self.update(vals)
