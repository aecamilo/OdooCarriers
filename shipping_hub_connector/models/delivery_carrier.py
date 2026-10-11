# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# Public carrier tracking URL templates (%s = tracking number)
TRACKING_URL_BY_CODE = {
    'dhl': 'https://www.dhl.com/global-en/home/tracking.html?tracking-id=%s',
    'dhl_express': 'https://www.dhl.com/global-en/home/tracking.html?tracking-id=%s',
    'dpd': 'https://tracking.dpd.de/status/en_US/parcel/%s',
    'gls': 'https://gls-group.eu/GROUP/en/parcel-tracking?match=%s',
    'ups': 'https://www.ups.com/track?tracknum=%s',
    'fedex': 'https://www.fedex.com/fedextrack/?trknbr=%s',
    'postnl': 'https://jouw.postnl.nl/track-and-trace/%s',
    'ctt': 'https://apps.ctt.pt/CustomerArea/PublicArea_Detail?ObjectCodeInput=%s',
    'brt': 'https://www.mybrt.it/it/mybrt/my-parcels/incoming?parcelNumber=%s',
    'inpost': 'https://inpost.pl/sledzenie-przesylek?number=%s',
    'tnt': 'https://www.fedex.com/fedextrack/?trknbr=%s',
    'hermes': 'https://www.evri.com/track-a-parcel/%s',
    'evri': 'https://www.evri.com/track-a-parcel/%s',
}

# Keys match saas-gateway carrier_code (sent as-is in create_shipment payload).
SHIPPING_HUB_CARRIER_SELECTION = [
    ('dhl_express', 'DHL Express (Europe)'),
    ('dhl', 'DHL Express'),
    ('dpd', 'DPD'),
    ('gls', 'GLS EuroBusiness'),
    ('ups', 'UPS'),
    ('fedex', 'FedEx'),
    ('tnt', 'TNT (FedEx)'),
    ('inpost', 'InPost'),
    ('postnl', 'PostNL'),
    ('evri', 'Evri'),
    ('hermes', 'Hermes / Evri'),
    ('poste_italiane', 'Poste Italiane'),
    ('brt', 'BRT Bartolini'),
    ('correos', 'Correos'),
    ('ctt', 'CTT Expresso'),
    ('post_at', 'Österreichische Post'),
    ('post_ch', 'Swiss Post'),
]


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('shipping_hub', 'Shipping Hub Europe')],
        ondelete={'shipping_hub': 'set default'},
    )
    shipping_hub_carrier_code = fields.Selection(
        selection=SHIPPING_HUB_CARRIER_SELECTION,
        string='Carrier service',
        default='dhl_express',
        help=(
            'Carrier registered in your Shipping Hub portal. The technical code is sent '
            'automatically to the Gateway (same value as in the SaaS carrier list, e.g. dpd, dhl_express).'
        ),
    )
    shipping_hub_service_level = fields.Char(
        string='Service level',
        default='standard',
        help='Service level for the Gateway API (default: standard). Change only if your Hub plan defines other levels.',
    )

    @api.onchange('delivery_type')
    def _onchange_delivery_type_shipping_hub(self):
        if self.delivery_type == 'shipping_hub' and not self.shipping_hub_carrier_code:
            self.shipping_hub_carrier_code = 'dhl_express'

    @api.constrains('delivery_type', 'shipping_hub_carrier_code')
    def _check_shipping_hub_carrier_code(self):
        for carrier in self:
            if carrier.delivery_type == 'shipping_hub' and not carrier.shipping_hub_carrier_code:
                raise ValidationError(
                    _('Carrier service is required for Shipping Hub delivery methods.')
                )

    def _shipping_hub_tracking_url(self, tracking_number):
        self.ensure_one()
        if not tracking_number:
            return False
        code = (self.shipping_hub_carrier_code or '').lower().strip()
        template = TRACKING_URL_BY_CODE.get(code)
        if not template:
            return False
        return template % tracking_number
