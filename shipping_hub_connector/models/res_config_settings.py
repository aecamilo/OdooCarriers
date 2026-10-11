# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .shipping_hub_client import ShippingHubClient

DEFAULT_SANDBOX_URL = 'https://stip.pt/hub-test'
DEFAULT_PRODUCTION_URL = 'https://stip.pt/hub-test'
DEFAULT_IAP_SERVICE_NAME = 'odoocarriers_shipping_labels'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    shipping_hub_api_token = fields.Char(
        string='Shipping Hub API Token',
        config_parameter='shipping_hub_connector.api_token',
    )
    shipping_hub_environment = fields.Selection(
        [
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        string='Environment',
        default='sandbox',
        config_parameter='shipping_hub_connector.environment',
    )
    shipping_hub_auto_generate = fields.Boolean(
        string='Generate label on picking validation',
        default=True,
        config_parameter='shipping_hub_connector.auto_generate',
    )
    shipping_hub_auto_attach = fields.Boolean(
        string='Attach label PDF to Chatter',
        default=True,
        config_parameter='shipping_hub_connector.auto_attach',
    )
    shipping_hub_gateway_base_url = fields.Char(
        string='Gateway base URL (override)',
        config_parameter='shipping_hub_connector.gateway_base_url',
        help='Leave empty to use the default URL for the selected environment.',
    )
    shipping_hub_iap_service_name = fields.Char(
        string='IAP service name',
        config_parameter='shipping_hub_connector.iap_service_name',
        default=DEFAULT_IAP_SERVICE_NAME,
    )
    shipping_hub_skip_iap_charge = fields.Boolean(
        string='Skip IAP charge (sandbox only)',
        config_parameter='shipping_hub_connector.skip_iap_charge',
        help='When enabled, labels are not debited via Odoo IAP (local tests without iap.odoo.com).',
    )

    @api.model
    def _shipping_hub_resolve_base_url(self, environment=None, override=None):
        icp = self.env['ir.config_parameter'].sudo()
        env_name = environment or icp.get_param(
            'shipping_hub_connector.environment', 'sandbox'
        )
        url = (override or icp.get_param('shipping_hub_connector.gateway_base_url') or '').strip()
        if url:
            return url.rstrip('/')
        if env_name == 'production':
            return DEFAULT_PRODUCTION_URL
        import os
        if os.environ.get('SHIPPING_HUB_GATEWAY_URL'):
            return os.environ['SHIPPING_HUB_GATEWAY_URL'].rstrip('/')
        return DEFAULT_SANDBOX_URL

    @api.model
    def _shipping_hub_get_api_token(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('shipping_hub_connector.api_token', '')
            or ''
        )

    @api.model
    def _shipping_hub_auto_generate_enabled(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('shipping_hub_connector.auto_generate', 'True')
            == 'True'
        )

    @api.model
    def _shipping_hub_auto_attach_enabled(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('shipping_hub_connector.auto_attach', 'True')
            == 'True'
        )

    def action_open_shipping_hub_provision(self):
        return self.env.ref(
            'shipping_hub_connector.action_shipping_hub_provision_wizard'
        ).read()[0]

    def action_test_shipping_hub_connection(self):
        self.ensure_one()
        base_url = self._shipping_hub_resolve_base_url(
            self.shipping_hub_environment,
            self.shipping_hub_gateway_base_url,
        )
        token = self.shipping_hub_api_token or self._shipping_hub_get_api_token()
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid') or ''
        ShippingHubClient(base_url, token, database_uuid=db_uuid).test_connection()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shipping Hub'),
                'message': _('Connection successful. Token and gateway are reachable.'),
                'type': 'success',
                'sticky': False,
            },
        }
