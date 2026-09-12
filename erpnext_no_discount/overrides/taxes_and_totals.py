"""Keep Additional Discount off item rows flagged "No Discount Applicable".

ERPNext distributes Additional Discount proportionally across *every* item row.
A row with `custom_no_discount_applicable` ticked must keep its full value, and
must not inflate the discount that lands on the other rows either.

ERPNext exposes no hook inside `calculate_taxes_and_totals`, so three methods
are subclassed here and wired in through `override_doctype_class` -- the same
mechanism india_compliance and hrms use.

Note this works off `net_amount`, never `price_list_rate`, so it is unaffected
by items priced directly on the row with no Item Price record.
"""

from erpnext.controllers.taxes_and_totals import (
	calculate_taxes_and_totals as ERPNextCalculateTaxesAndTotals,
)
from frappe import scrub
from frappe.utils import flt

NO_DISCOUNT_FLAG = "custom_no_discount_applicable"


class CalculateTaxesAndTotals(ERPNextCalculateTaxesAndTotals):
	def no_discount_rows(self):
		"""Rows excluded from Additional Discount.

		Read from `doc.items` rather than `self._items` so the result stays
		stable while `apply_discount_amount` temporarily narrows `self._items`.
		"""
		return [
			row
			for row in (self.doc.get("items") or [])
			if row.get(NO_DISCOUNT_FLAG) and not row.get("is_alternative")
		]

	def set_discount_amount(self):
		"""Derive `discount_amount` from a base that excludes the flagged rows.

		Without this, 10% across 30,000 of items where 10,000 is flagged gives
		3,000 -- the flagged row escapes the discount but still enlarges what
		the other rows absorb. The eligible base here is 20,000, so 2,000.

		Exact for `apply_discount_on = "Net Total"`. For "Grand Total" the
		flagged row's own tax is not removed from the base.
		"""
		flagged = self.no_discount_rows()
		percentage = self.doc.get("additional_discount_percentage")

		if not flagged or not percentage or not self.doc.get("apply_discount_on"):
			return super().set_discount_amount()

		base = flt(self.doc.get(scrub(self.doc.apply_discount_on)))
		for row in flagged:
			base -= flt(row.net_amount)

		self.doc.discount_amount = flt(
			base * percentage / 100, self.doc.precision("discount_amount")
		)

		# hide the percentage so super() keeps the amount just computed
		self.doc.additional_discount_percentage = None
		try:
			super().set_discount_amount()
		finally:
			self.doc.additional_discount_percentage = percentage

	def get_total_for_discount_amount(self):
		"""Shrink the distribution denominator by the flagged rows."""
		total = super().get_total_for_discount_amount()

		for row in self.no_discount_rows():
			total -= flt(row.net_amount)

		return flt(total)

	def apply_discount_amount(self):
		flagged = self.no_discount_rows()

		if not flagged or not self.doc.get("discount_amount"):
			return super().apply_discount_amount()

		original_items = self._items
		self._items = [row for row in original_items if not row.get(NO_DISCOUNT_FLAG)]

		try:
			super().apply_discount_amount()
		finally:
			self._items = original_items

		# `discount_amount_applied` is now True, so the distributed net amounts
		# survive. Recalculate with the flagged rows back in scope so net_total,
		# taxes and grand_total include them at full value.
		self._calculate()
