"""Buying controllers wired to the No-Discount aware totals calculator.

Same mixin as the selling side; its commission step only runs for selling doctypes.
"""

from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
	PurchaseInvoice as ERPNextPurchaseInvoice,
)
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder as ERPNextPurchaseOrder
from erpnext.buying.doctype.supplier_quotation.supplier_quotation import (
	SupplierQuotation as ERPNextSupplierQuotation,
)
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
	PurchaseReceipt as ERPNextPurchaseReceipt,
)

from erpnext_no_discount.overrides.selling import NoDiscountMixin


class SupplierQuotation(NoDiscountMixin, ERPNextSupplierQuotation):
	pass


class PurchaseOrder(NoDiscountMixin, ERPNextPurchaseOrder):
	pass


class PurchaseReceipt(NoDiscountMixin, ERPNextPurchaseReceipt):
	pass


class PurchaseInvoice(NoDiscountMixin, ERPNextPurchaseInvoice):
	pass
