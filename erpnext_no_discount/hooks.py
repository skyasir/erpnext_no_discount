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
	"Delivery Note": "erpnext_no_discount.overrides.selling.DeliveryNote",
	"POS Invoice": "erpnext_no_discount.overrides.selling.POSInvoice",
	"Supplier Quotation": "erpnext_no_discount.overrides.buying.SupplierQuotation",
	"Purchase Order": "erpnext_no_discount.overrides.buying.PurchaseOrder",
	"Purchase Receipt": "erpnext_no_discount.overrides.buying.PurchaseReceipt",
	"Purchase Invoice": "erpnext_no_discount.overrides.buying.PurchaseInvoice",
}

fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Item-custom_no_discount_applicable",
					"Quotation Item-custom_no_discount_applicable",
					"Sales Order Item-custom_no_discount_applicable",
					"Sales Invoice Item-custom_no_discount_applicable",
					"Delivery Note Item-custom_no_discount_applicable",
					"POS Invoice Item-custom_no_discount_applicable",
					"Supplier Quotation Item-custom_no_discount_applicable",
					"Purchase Order Item-custom_no_discount_applicable",
					"Purchase Receipt Item-custom_no_discount_applicable",
					"Purchase Invoice Item-custom_no_discount_applicable",
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
					"Delivery Note - No Discount Applicable",
					"POS Invoice - No Discount Applicable",
					"Supplier Quotation - No Discount Applicable",
					"Purchase Order - No Discount Applicable",
					"Purchase Receipt - No Discount Applicable",
					"Purchase Invoice - No Discount Applicable",
				],
			]
		],
	},
]
