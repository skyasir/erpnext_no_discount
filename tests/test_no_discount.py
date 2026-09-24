"""Tests for ERPNext No Discount, run against a live site. Nothing is saved.

The controller maths is exercised directly through `calculate_taxes_and_totals()`
rather than through a document save, so unrelated Before Save customisations on
the site cannot colour the result.

    cd <bench>/sites
    ../env/bin/python ../apps/erpnext_no_discount/tests/test_no_discount.py [site] [item_code]
"""

import pathlib
import sys
import unittest

import frappe


def _default_site():
	current = pathlib.Path("currentsite.txt")
	if current.is_file():
		return current.read_text().strip()
	sites = sorted(p.name for p in pathlib.Path(".").iterdir() if (p / "site_config.json").is_file())
	if len(sites) == 1:
		return sites[0]
	sys.exit(f"Pass the site name as an argument. Found {len(sites)}: {', '.join(sites) or 'none'}")


SITE = sys.argv[1] if len(sys.argv) > 1 else _default_site()
FLAG = "custom_no_discount_applicable"


def setUpModule():
	frappe.init(site=SITE)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.db.rollback()
	frappe.destroy()


class NoDiscountTestCase(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		cls.company = frappe.defaults.get_user_default("Company") or frappe.db.get_value(
			"Company", {}, "name"
		)
		cls.supplier = frappe.db.get_value("Supplier", {"disabled": 0}, "name")
		cls.price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
		cls.buying_price_list = frappe.db.get_value("Price List", {"buying": 1, "enabled": 1}, "name")
		cls.item = frappe.db.get_value("Item", {"is_sales_item": 1, "disabled": 0, "has_variants": 0}, "name")
		cls.uom = frappe.db.get_value("Item", cls.item, "stock_uom") if cls.item else None

	def setUp(self):
		if not (self.customer and self.supplier and self.company and self.item):
			self.skipTest("site has no customer / supplier / company / item to build documents from")

	def quotation(self, rows, pct=None, amount=None, apply_on="Net Total", doctype="Quotation"):
		"""rows: list of (rate, flagged)."""
		doc = self.build(doctype, rows, pct=pct, amount=amount, apply_on=apply_on)
		doc.calculate_taxes_and_totals()
		return doc

	def build(self, doctype, rows, pct=None, amount=None, apply_on="Net Total"):
		currency = frappe.db.get_value("Company", self.company, "default_currency")
		doc = frappe.get_doc(
			{
				"doctype": doctype,
				"company": self.company,
				"currency": currency,
				"conversion_rate": 1,
				"price_list_currency": currency,
				"plc_conversion_rate": 1,
				"apply_discount_on": apply_on,
				"additional_discount_percentage": pct,
				"discount_amount": amount,
				"items": [
					{
						"item_code": self.item,
						"qty": 1,
						"rate": rate,
						"price_list_rate": rate,
						"conversion_factor": 1,
						"uom": self.uom,
						FLAG: flagged,
					}
					for rate, flagged in rows
				],
			}
		)
		date = "transaction_date" if doctype in DATED_BY_TRANSACTION else "posting_date"
		doc.set(date, frappe.utils.nowdate())
		if doctype in BUYING:
			doc.update({"supplier": self.supplier, "buying_price_list": self.buying_price_list})
		elif doctype == "Quotation":
			doc.update(
				{"quotation_to": "Customer", "party_name": self.customer, "selling_price_list": self.price_list}
			)
		else:
			doc.update({"customer": self.customer, "selling_price_list": self.price_list})
		return doc

	def fetch(self, doc):
		"""Run the fetch_from pass a save would, without saving."""
		doc._action = "save"
		doc._validate_links()

	def flagged_net(self, doc):
		return [row.net_amount for row in doc.items if row.get(FLAG)][0]


SELLING = ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice")
BUYING = ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice")
DOCTYPES = SELLING + BUYING
DATED_BY_TRANSACTION = ("Quotation", "Sales Order", "Supplier Quotation", "Purchase Order")


class TestTheOverrideIsWired(NoDiscountTestCase):
	def test_every_doctype_uses_the_subclass(self):
		for doctype in DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(
					type(frappe.get_doc({"doctype": doctype})).__module__,
					"erpnext_no_discount.overrides."
					+ ("buying" if doctype in BUYING else "selling"),
				)


class TestEveryDoctype(NoDiscountTestCase):
	def test_flagged_row_is_untouched_on_every_doctype(self):
		"""Same maths on each doctype: a document made from a flagged one must not
		spread the discount back over the flagged row."""
		for doctype in DOCTYPES:
			with self.subTest(doctype=doctype):
				doc = self.quotation([(10000, 0), (20000, 0), (10000, 1)], pct=10, doctype=doctype)

				self.assertAlmostEqual(doc.discount_amount, 3000, places=2)
				self.assertAlmostEqual(self.flagged_net(doc), 10000, places=2)


class TestItemMasterFlag(NoDiscountTestCase):
	"""The row copies the Item's flag (fetch_from + fetch_if_empty), so a row is
	flagged when either the Item or the row itself is ticked."""

	def test_row_inherits_the_item_flag(self):
		frappe.db.set_value("Item", self.item, FLAG, 1, update_modified=False)
		try:
			for doctype in DOCTYPES:
				with self.subTest(doctype=doctype):
					doc = self.build(doctype, [(10000, 0)])
					self.fetch(doc)
					self.assertEqual(doc.items[0].get(FLAG), 1)
		finally:
			frappe.db.rollback()

	def test_row_can_be_ticked_for_an_unflagged_item(self):
		frappe.db.set_value("Item", self.item, FLAG, 0, update_modified=False)
		try:
			doc = self.build("Quotation", [(10000, 1)])
			self.fetch(doc)
			self.assertEqual(doc.items[0].get(FLAG), 1)
		finally:
			frappe.db.rollback()


class TestPercentageDiscount(NoDiscountTestCase):
	def test_flagged_row_is_untouched_and_shrinks_the_base(self):
		"""10% over 10,000 + 20,000 goods and a 10,000 flagged row.

		Eligible base is 30,000, so 3,000 -- not 4,000. The flagged row neither
		absorbs discount nor enlarges what the others absorb.
		"""
		doc = self.quotation([(10000, 0), (20000, 0), (10000, 1)], pct=10)

		self.assertAlmostEqual(doc.discount_amount, 3000, places=2)
		self.assertAlmostEqual(doc.net_total, 37000, places=2)
		self.assertAlmostEqual(self.flagged_net(doc), 10000, places=2)

	def test_the_flag_actually_changes_the_outcome(self):
		"""Same rows unflagged is plain ERPNext: 10% of 40,000."""
		flagged = self.quotation([(10000, 0), (20000, 0), (10000, 1)], pct=10)
		plain = self.quotation([(10000, 0), (20000, 0), (10000, 0)], pct=10)

		self.assertAlmostEqual(plain.discount_amount, 4000, places=2)
		self.assertAlmostEqual(plain.discount_amount - flagged.discount_amount, 1000, places=2)

	def test_no_flagged_rows_behaves_exactly_like_stock_erpnext(self):
		doc = self.quotation([(10000, 0), (20000, 0)], pct=10)

		self.assertAlmostEqual(doc.discount_amount, 3000, places=2)
		self.assertAlmostEqual(doc.net_total, 27000, places=2)

	def test_every_row_flagged_leaves_nothing_discountable(self):
		doc = self.quotation([(10000, 1)], pct=10)

		self.assertAlmostEqual(doc.discount_amount, 0, places=2)
		self.assertAlmostEqual(doc.net_total, 10000, places=2)


class TestFlatDiscountAmount(NoDiscountTestCase):
	def test_flagged_row_is_untouched(self):
		doc = self.quotation([(10000, 0), (20000, 0), (10000, 1)], amount=3000)

		self.assertAlmostEqual(self.flagged_net(doc), 10000, places=2)
		self.assertAlmostEqual(doc.net_total, 37000, places=2)


class TestApplyDiscountOnGrandTotal(NoDiscountTestCase):
	def test_flagged_row_is_still_kept_whole(self):
		"""Documented as approximate: the flagged row's own tax is not removed
		from the base. Its value must still survive intact."""
		doc = self.quotation([(10000, 0), (20000, 0), (10000, 1)], pct=10, apply_on="Grand Total")

		self.assertAlmostEqual(self.flagged_net(doc), 10000, places=2)


if __name__ == "__main__":
	unittest.main(argv=sys.argv[:1], verbosity=2)
