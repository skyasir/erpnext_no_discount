# ERPNext No Discount

Adds a **No Discount Applicable** checkbox to Quotation Item, Sales Order Item
and Sales Invoice Item. Tick it and Additional Discount skips that row.

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

## Why a class override

ERPNext distributes Additional Discount across every item row and exposes no
hook inside `calculate_taxes_and_totals`. Per-item `discount_percentage` is not
a usable alternative: when `price_list_rate` is `0`, `calculate_item_rate()`
calls `remove_discount()` and wipes it.

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
  overrides Quotation / Sales Order / Sales Invoice, the two must be merged.

## Tests

```bash
cd <bench>/sites
../env/bin/python ../apps/erpnext_no_discount/tests/test_no_discount.py [site]
```

Exercises `calculate_taxes_and_totals()` directly rather than saving a document, so
customisations on the site cannot colour the result. Nothing is written.

Covered: the override is actually wired in; a flagged row neither absorbs discount nor
enlarges what the others absorb; the flag demonstrably changes the outcome; with no flagged
rows the behaviour is identical to stock ERPNext; all-flagged leaves nothing discountable;
flat `discount_amount` as well as a percentage; and `apply_discount_on = "Grand Total"`,
where the result is approximate by design but the flagged row is still kept whole.
