import requests
import frappe
import json

@frappe.whitelist()
def create_shopify_customer(firstName, lastName, mobileNum, emailID, address, addrCity, addrState, addrPostcode, shopify_url,access_token,customer_name=None):

    customer_payload = {"email": emailID,
            "accepts_marketing": True,
            "first_name": firstName,
            "last_name": lastName,
            "orders_count": 0,
            "note": "",
            "tax_exempt": False,
            "tags": "",
            "currency": "MYR",
            "phone": mobileNum,
            "addresses": [
                {
                "address1": address,
                "city": addrCity,
                "province": addrState,
                "country": "Malaysia",
                "zip": addrPostcode,
                "default": True,}
            ]
        }
    
    if mobileNum:
        customer_payload["phone"] = "+60" + mobileNum
    # Construct the API payload
    payload = {
        "customer": customer_payload
    }

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    final_url = f"{shopify_url}customers.json"
    try:
        # Send the POST request to create the product
        response = requests.post(final_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx, 5xx)
        
        if response.status_code == 201:
            frappe.msgprint(f"Customer was created in Shopify.")

            customer_data = response.json().get("customer")
            if customer_data:
                shopify_customer_id = customer_data.get("id")
                # Optionally, you can store the Shopify customer ID in ERPNext
                frappe.db.set_value("Customer", customer_name, "shopify_customer_id", shopify_customer_id)
        else:
            frappe.msgprint(f"Shopify API returned a non-success status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        frappe.msgprint(f"An error occurred while making the Shopify API request: {str(e)}")

# Attach the custom function to the 'Item' doctype's on_submit event
def on_submit(doc, method):
    shopify_doc = frappe.get_doc(
        "Shopify Access",
        frappe.get_value("Shopify Access", {}, "name")  # first Shopify Access record
    )
    create_shopify_customer(
        doc.customer_name,  # firstName
        "",  # lastName
        doc.mobile_no if hasattr(doc, "mobile_no") else "",
        doc.email_id if hasattr(doc, "email_id") else "",
        doc.customer_address if hasattr(doc, "customer_address") else "",
        "",  # addrCity
        "",  # addrState
        "",  # addrPostcode
        shopify_doc.shopify_url,
        shopify_doc.access_token,
        customer_name=doc.customer_name,
    )
# Ensure the on_submit function is triggered when an 'Item' document is submitted
frappe.get_doc('DocType', 'Customer').on_submit = on_submit
