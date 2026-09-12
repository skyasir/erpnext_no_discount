"""Selling controllers wired to the No-Discount aware totals calculator.

Mirrors `AccountsController.calculate_taxes_and_totals` exactly, swapping in the
subclass from `erpnext_no_discount.overrides.taxes_and_totals`.
"""

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	SalesInvoice as ERPNextSalesInvoice,
)
from erpnext.selling.doctype.quotation.quotation import Quotation as ERPNextQuotation
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder as ERPNextSalesOrder

from erpnext_no_discount.overrides.taxes_and_totals import CalculateTaxesAndTotals


class NoDiscountMixin:
	def calculate_taxes_and_totals(self):
		CalculateTaxesAndTotals(self)

		if self.doctype in (
			"Sales Order",
			"Delivery Note",
			"Sales Invoice",
			"POS Invoice",
		):
			self.calculate_commission()
			self.calculate_contribution()


class Quotation(NoDiscountMixin, ERPNextQuotation):
	pass


class SalesOrder(NoDiscountMixin, ERPNextSalesOrder):
	pass


class SalesInvoice(NoDiscountMixin, ERPNextSalesInvoice):
	pass
