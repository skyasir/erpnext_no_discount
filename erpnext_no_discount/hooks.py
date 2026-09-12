from . import __version__ as app_version  # noqa: F401

app_name = "erpnext_no_discount"
app_title = "ERPNext No Discount"
app_publisher = "Yasir Shaikh"
app_description = (
	"Per-item 'No Discount Applicable' flag. Additional Discount is never applied "
	"to a flagged row, and the flagged row does not enlarge the discount absorbed "
	"by the other rows."
)
app_email = "erp.yasirshaikh@gmail.com"
app_license = "MIT"
required_apps = ["erpnext"]

override_doctype_class = {
	"Quotation": "erpnext_no_discount.overrides.selling.Quotation",
	"Sales Order": "erpnext_no_discount.overrides.selling.SalesOrder",
	"Sales Invoice": "erpnext_no_discount.overrides.selling.SalesInvoice",
}

fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Quotation Item-custom_no_discount_applicable",
					"Sales Order Item-custom_no_discount_applicable",
					"Sales Invoice Item-custom_no_discount_applicable",
				],
			]
		],
	},
	{
		"doctype": "Client Script",
		"filters": [
			[
				"name",
				"in",
				[
					"Quotation - No Discount Applicable",
					"Sales Order - No Discount Applicable",
					"Sales Invoice - No Discount Applicable",
				],
			]
		],
	},
]
