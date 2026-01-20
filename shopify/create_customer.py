import requests
import frappe
import json

@frappe.whitelist()
def create_shopify_customer(firstName, lastName, mobileNum, emailID, address, addrCity, addrState, addrPostcode, shopify_url, access_token):

    # Prepare payload
    customer_payload = {
        "email": emailID,
        "accepts_marketing": True,
        "first_name": firstName,
        "last_name": lastName,
        "orders_count": 0,
        "note": "",
        "tax_exempt": False,
        "tags": "",
        "currency": "MYR",
        "phone": "+60" + mobileNum if mobileNum else "",
        "addresses": [
            {
                "address1": address,
                "city": addrCity,
                "province": addrState,
                "country": "Malaysia",
                "zip": addrPostcode,
                "default": True,
            }
        ],
    }

    payload = {
        "customer": customer_payload
    }

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    final_url = f"{shopify_url}customers.json"
    response = requests.post(
        final_url,
        json=payload,
        headers=headers
    )

    if response.status_code != 201:
        frappe.log_error(
            title="Shopify Customer Creation Failed",
            message=response.text
        )
        frappe.throw("Failed to create customer in Shopify")

    customer = response.json()["customer"]

    return customer["id"]

def on_submit(doc, method):

    if doc.shopify_customer_id:
        return

    shopify_doc = frappe.get_doc(
        "Shopify Access",
        frappe.get_value("Shopify Access", {}, "name")
    )
    customer = create_shopify_customer(
        doc.customer_name,  # firstName
        "",  
        doc.mobile_no if hasattr(doc, "mobile_no") else "",
        doc.email_id if hasattr(doc, "email_id") else "",
        doc.customer_address if hasattr(doc, "customer_address") else "",
        "",  # addrCity
        "",  # addrState
        "",  # addrPostcode
        shopify_doc.shopify_url,
        shopify_doc.access_token
    )

    if customer:
        doc.db_set("shopify_customer_id", customer)

# Ensure the on_submit function is triggered when a Customer document is submitted
frappe.get_doc('DocType', 'Customer').on_submit = on_submit