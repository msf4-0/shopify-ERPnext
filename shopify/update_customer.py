import requests
import frappe
import json

@frappe.whitelist()
def update_shopify_customer(customerID, firstName, lastName, mobileNum, emailID, address, addrCity, addrState, addrPostcode, customerNotes, customerTags, shopify_url,access_token):
    print(f"Received arguments - productID: {customerID}, fName: {firstName}, lName: {lastName}, mobile: {mobileNum}, email: {emailID}, address: {address}, city: {addrCity}, state: {addrState}, zip: {addrPostcode}, notes: {customerNotes}, tags: {customerTags}, shopify_url: {shopify_url}")
    customer_payload = { 
            "email": emailID,
            "first_name": firstName,
            "last_name": lastName,
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
    # Construct the API payload
    payload = {
        "customer": customer_payload
    }

    endpoint = 'customers/' + str(customerID) + '.json'
    final_url = shopify_url + endpoint

    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': access_token
    }

    try:
        # Send the PUT request to create the product
        response = requests.put(final_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx, 5xx)
        
        if response.status_code == 200:
            frappe.msgprint(f"Customer record was updated in Shopify.")
        else:
            error_message = response.text 
            frappe.msgprint(f"Shopify API returned a non-success status code: {response.status_code}. Error message: {error_message}")
    
    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        frappe.msgprint(f"An error occurred while making the Shopify API request: {response.text}")


# Attach the custom function to the 'Item' doctype's on_submit event
def on_submit(doc, method):
    if doc.flags.in_insert:
        return
    
    shopify_doc = frappe.get_doc("Shopify Access", frappe.get_value("Shopify Access", {}, "name"))
    email = doc.email_id if hasattr(doc, "email_id") and doc.email_id else "noemail@example.com"

    update_shopify_customer(
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
# Ensure the on_submit function is triggered when an 'Item' document is submitted
frappe.get_doc('DocType', 'Customer').on_submit = on_submit
