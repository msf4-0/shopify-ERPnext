import requests
import frappe
import json

@frappe.whitelist()
def update_shopify_customer_by_email(shopifyCustomerId, firstName, lastName, mobileNum, emailID, address, addrCity, addrState, addrPostcode, customerNotes, customerTags, shopify_url, access_token):
    # Find Shopify customer by shopify customer id
    
    if not shopifyCustomerId:
        frappe.msgprint("customer not found in shopify")
        return
    
    customer_payload = { 
        "id": shopifyCustomerId,
        "first_name": firstName,
        "last_name": lastName,
        "email": emailID,
        "note": customerNotes,
        "tags": customerTags,
        "currency": "MYR",
    }
    if mobileNum:
        customer_payload["phone"] = "+60" + mobileNum

    if address:
        customer_payload["addresses"] = [{
            "address1": address,
            "city": addrCity,
            "province": addrState,
            "country": "Malaysia",
            "zip": addrPostcode
        }]
    payload = {
        "customer": customer_payload
    }

    endpoint = f'customers/{shopifyCustomerId}.json'
    final_url = shopify_url + endpoint

    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': access_token
    }

    try:
        response = requests.put(final_url, json=payload, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            frappe.msgprint(f"Customer record was updated in Shopify.")
        else:
            error_message = response.text 
            frappe.msgprint(f"Shopify API returned a non-success status code: {response.status_code}. Error message: {error_message}")
    except requests.exceptions.RequestException as e:
        frappe.msgprint(f"An error occurred while making the Shopify API request: {response.text}")

def on_submit(doc, method):
    if doc.flags.in_insert:
        return
    
    shopify_doc = frappe.get_doc("Shopify Access", frappe.get_value("Shopify Access", {}, "name"))

    update_shopify_customer_by_email(
        doc.shopify_customer_id,
        doc.customer_name,
        "", 
        doc.mobile_no if hasattr(doc, "mobile_no") else "",
        doc.email_id if hasattr(doc, "email_id") else "",
        doc.customer_address if hasattr(doc, "customer_address") else "",
        getattr(doc, "city", ""),
        getattr(doc, "state", ""),
        getattr(doc, "postcode", ""),
        getattr(doc, "notes", ""),
        getattr(doc, "customer_tags", ""),
        shopify_doc.shopify_url,
        shopify_doc.access_token
    )

# Ensure the on_submit function is triggered when a Customer document is submitted
frappe.get_doc('DocType', 'Customer').on_submit = on_submit