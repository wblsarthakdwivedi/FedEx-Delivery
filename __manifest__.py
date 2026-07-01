# -*- coding: utf-8 -*-
#
#################################################################################
# Author      : Weblytic Labs Pvt. Ltd. (<https://store.weblyticlabs.com/>)
# Copyright(c): 2023-Present Weblytic Labs Pvt. Ltd.
# All Rights Reserved.
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
##################################################################################
{
    'name': 'FedEx Delivery',
    'version': '19.0.1.0.0',
    'description': """""",
    'summary': """""",
    'category': 'eCommerce',
    'author': 'Weblytic Labs',
    'company': 'Weblytic Labs',
    'website': 'https://store.weblyticlabs.com',
    'price': '50.00',
    'currency': 'USD',
    'depends': ['base', 'mail', 'website', 'delivery', 'sale', 'website_sale', 'payment', 'sale_management',
                'stock'],
    'data': [
            "security/ir.model.access.csv",
            "data/fedex_package_type.xml",
            "views/delivery_method_credentials.xml",
            "wizard/choose_delivery_carrier_view.xml",
            "views/website_delivery_template.xml",
            "views/delivery_order_package_view.xml",
            "views/fedex_shipping_view.xml",
            "views/fedex_label_view.xml",
            "views/fedex_menu.xml",
    ],
    'assets': {
        'web.assets_frontend_lazy': [

            "wbl_fedex_delivery/static/src/fedex_checkout.js",

        ],

        'web.assets_backend': [
            "wbl_fedex_delivery/static/src/js/fedex_dashboard.js",
            "wbl_fedex_delivery/static/src/xml/fedex_dashboard.xml",
            "wbl_fedex_delivery/static/src/scss/fedex_dashboard.scss",
        ],
    },
    'images': ['static/description/banner.gif'],
    'live_test_url': 'https://youtu.be/vgeP_Ga1u7Y',
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
}
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
##################################################################################
