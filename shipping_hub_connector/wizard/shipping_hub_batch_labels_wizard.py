# -*- coding: utf-8 -*-

import base64
import io

from odoo import _, fields, models
from odoo.exceptions import UserError

try:
    from pypdf import PdfWriter, PdfReader
except ImportError:
    PdfWriter = PdfReader = None


class ShippingHubBatchLabelsWizard(models.TransientModel):
    _name = 'shipping.hub.batch.labels.wizard'
    _description = 'Batch merged Shipping Hub label PDF'

    label_pdf = fields.Binary(string='Merged labels PDF', readonly=True, attachment=False)
    filename = fields.Char(string='Filename', readonly=True, default='shipping_hub_labels_batch.pdf')
    errors_summary = fields.Text(string='Errors', readonly=True)

    def set_merged_pdf(self, pdf_byte_list):
        self.ensure_one()
        if not pdf_byte_list:
            return
        if PdfWriter is None or PdfReader is None:
            raise UserError(_('Python package pypdf is required for batch PDF merge.'))
        writer = PdfWriter()
        for raw in pdf_byte_list:
            reader = PdfReader(io.BytesIO(raw))
            for page in reader.pages:
                writer.add_page(page)
        buffer = io.BytesIO()
        writer.write(buffer)
        self.label_pdf = base64.b64encode(buffer.getvalue())
        self.filename = 'shipping_hub_labels_batch.pdf'

    def action_download_merged_pdf(self):
        self.ensure_one()
        if not self.label_pdf:
            raise UserError(_('No merged PDF available. Check the error summary.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=%s&id=%s&field=label_pdf&filename=%s&download=true'
            % (self._name, self.id, self.filename),
            'target': 'self',
        }
