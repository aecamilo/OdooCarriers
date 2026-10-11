# -*- coding: utf-8 -*-
{
    'name': 'Shipping Hub Connector - European Logistics',
    'version': '1.0.16',
    'category': 'Inventory/Delivery',
    'summary': 'Integração oficial com DPD, DHL, GLS e transportadoras europeias via Shipping Hub SaaS',
    'description': """
Shipping Hub Connector — European carrier labels via SaaS Gateway (HMAC).
    """,
    'author': 'Shipping Hub Europe',
    'website': 'https://shippingconnector.eu',
    'license': 'OPL-1',
    'depends': ['delivery', 'stock_delivery', 'iap'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/shipping_hub_batch_labels_wizard_views.xml',
        'wizard/shipping_hub_provision_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
