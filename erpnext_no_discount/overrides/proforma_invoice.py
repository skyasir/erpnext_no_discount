"""Proforma Invoice wired to the No-Discount aware totals calculator.

Kept apart from `selling.py` so that sites without `erpnext_export_tracker`
are not affected by its import. Only loaded through `override_doctype_class`.

Export Tracker's own `calculate_taxes_and_totals` presents the document to
ERPNext as a "Sales Order" while it totals, because ERPNext decides buy or sell
by matching the doctype name against a literal list. The same is done here;
`NoDiscountMixin` is called directly rather than inherited so that swap is not
bypassed.
"""

from erpnext_export_tracker.export_tracker.doctype.proforma_invoice.proforma_invoice import (
	ProformaInvoice as ExportTrackerProformaInvoice,
)

from erpnext_no_discount.overrides.selling import NoDiscountMixin


class ProformaInvoice(ExportTrackerProformaInvoice):
	def calculate_taxes_and_totals(self):
		actual = self.doctype
		self.doctype = "Sales Order"
		try:
			NoDiscountMixin.calculate_taxes_and_totals(self)
		finally:
			self.doctype = actual
