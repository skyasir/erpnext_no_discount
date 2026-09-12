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
		cls.price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
		cls.item = frappe.db.get_value("Item", {"is_sales_item": 1, "disabled": 0, "has_variants": 0}, "name")
		cls.uom = frappe.db.get_value("Item", cls.item, "stock_uom") if cls.item else None

	def setUp(self):
		if not (self.customer and self.company and self.item):
			self.skipTest("site has no customer / company / sales item to build a Quotation from")

	def quotation(self, rows, pct=None, amount=None, apply_on="Net Total"):
		"""rows: list of (rate, flagged)."""
		doc = frappe.get_doc(
			{
				"doctype": "Quotation",
				"party_name": self.customer,
				"company": self.company,
				"currency": frappe.db.get_value("Company", self.company, "default_currency"),
				"conversion_rate": 1,
				"selling_price_list": self.price_list,
				"price_list_currency": frappe.db.get_value("Company", self.company, "default_currency"),
				"plc_conversion_rate": 1,
				"transaction_date": frappe.utils.nowdate(),
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
		doc.calculate_taxes_and_totals()
		return doc

	def flagged_net(self, doc):
		return [row.net_amount for row in doc.items if row.get(FLAG)][0]


class TestTheOverrideIsWired(NoDiscountTestCase):
	def test_quotation_uses_the_subclass(self):
		self.assertEqual(
			type(frappe.get_doc({"doctype": "Quotation"})).__module__,
			"erpnext_no_discount.overrides.selling",
		)


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
