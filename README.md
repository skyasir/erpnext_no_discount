# ERPNext No Discount

Adds a **No Discount Applicable** checkbox to Item, and to the item rows of every
document that has Additional Discount. Additional Discount skips a flagged row.

- Selling: Quotation, Sales Order, Delivery Note, Sales Invoice, POS Invoice
- Buying: Supplier Quotation, Purchase Order, Purchase Receipt, Purchase Invoice

The Item flag is shared by both sides: a flagged item is exempt on sales and purchases.

Tick it once on the Item (Sales Details, next to Grant Commission) and every new
row for that item is flagged automatically. A row can also be ticked by hand for
an item that is not flagged. The row copies the Item's flag only while the row is
unticked, so a row for a flagged item cannot be unticked -- untick the Item instead.
The flag carries over when one document is made from another (Quotation -> Order ->
Delivery Note / Invoice, Supplier Quotation -> Purchase Order -> Receipt / Invoice).

```
10% Additional Discount, three rows of 10,000:

  Item        No Discount   amount    net_amount   distributed_discount
  Goods A         ☐        10,000.00    9,000.00        1,000.00
  Goods B         ☐        10,000.00    9,000.00        1,000.00
  Special C       ☑        10,000.00   10,000.00            0.00

  discount_amount = 2,000.00     <- 10% of the 20,000 eligible base
```

The flagged row keeps its full value **and** does not inflate the discount the
other rows absorb. Works the same for a flat `discount_amount`.

No Item Price or Price List is required — the logic runs off `net_amount`, never
`price_list_rate`.

## Row discount without an Item Price

ERPNext takes a row's Discount % / Discount Amount from its **Price List Rate**. With no Item
Price that is 0, so the discount is wiped (sales) or the rate drops to 0 (purchase).

This app fixes that in the form. On rows **without an Item Price**, the Price List Rate is
kept equal to the Rate at all times, so a discount always comes off the rate shown and is then
folded straight into it:

```
Rate 10             ->  Price List Rate 10
Discount 2          ->  Rate 8,    Price List Rate 8,    Discount back to 0
Discount 10%        ->  Rate 7.20, Price List Rate 7.20, Discount back to 0
```

The row only ever shows the final rate; prints show no separate discount for these rows.
A quantity change leaves the rate alone. Rows **with** an Item Price, a pricing rule or a
blanket order rate keep standard ERPNext behaviour: every discount is taken from the list price.
Covers all nine documents listed above.

Stock ERPNext also **hides** Discount % and Discount Amount until a row has a Price List Rate.
The app ships Property Setters that show them once the row has a Price List Rate **or** a Rate
(`eval:doc.price_list_rate || doc.rate`), on all nine item tables.
Covers all nine documents listed above.

## Why a class override

ERPNext distributes Additional Discount across every item row and exposes no
hook inside `calculate_taxes_and_totals`. Per-item `discount_percentage` alone is not
a usable alternative: when `price_list_rate` is `0`, `calculate_item_rate()`
calls `remove_discount()` and wipes it (see above for how the form now handles that).

So three methods are subclassed and wired in via `override_doctype_class`, the
same mechanism `india_compliance` and `hrms` use:

| Method | Job |
| --- | --- |
| `set_discount_amount` | 10% means 10% of the eligible rows only |
| `get_total_for_discount_amount` | shrinks the distribution denominator |
| `apply_discount_amount` | hides flagged rows during distribution, then recalculates |

A matching Client Script patches the browser-side calculation so the form shows
what the server will save.

## Install

```bash
bench get-app erpnext_no_discount <repo-url>
bench --site <site> install-app erpnext_no_discount
bench restart
```

## Notes

- Exact for `Apply Discount On = Net Total`. For `Grand Total`, the flagged
  row's own tax is not removed from the discount base.
- One ERPNext class is subclassed. On a major ERPNext upgrade, re-check
  `erpnext/controllers/taxes_and_totals.py` for changes to the three methods.
- Only one app may override a given DocType class. If another app already
  overrides any of the nine doctypes above, the two must be merged.

## Tests

```bash
cd <bench>/sites
../env/bin/python ../apps/erpnext_no_discount/tests/test_no_discount.py [site]
```

Exercises `calculate_taxes_and_totals()` directly rather than saving a document, so
customisations on the site cannot colour the result. Nothing is written.

Covered: the override is actually wired in on all nine doctypes; the discount
maths holds on each of them; a row copies the Item's flag, and can be ticked by
hand for an unflagged item; a flagged row neither absorbs discount nor
enlarges what the others absorb; the flag demonstrably changes the outcome; with no flagged
rows the behaviour is identical to stock ERPNext; all-flagged leaves nothing discountable;
flat `discount_amount` as well as a percentage; and `apply_discount_on = "Grand Total"`,
where the result is approximate by design but the flagged row is still kept whole.
