import requests
import base64
import frappe

@frappe.whitelist()
def retrieve_shopify_customers(api_key, api_password, shopify_store_url):
    # Construct the Shopify API endpoint for fetching customers
    api_endpoint = f"{shopify_store_url}customers.json"

    # Set up the request headers with basic authentication
    headers = {
        "X-Shopify-Access-Token": api_password,
        "Content-Type": "application/json",
    }

    # Make the GET request to Shopify API
    try:
        response = requests.get(api_endpoint, headers=headers)

        # Check the response status code
        if response.status_code == 200:
            customers_data = response.json().get("customers", [])
            # Process the retrieved customers
            if customers_data:
                for shopify_customer in customers_data:
                    create_customer([shopify_customer])  # Create customer records in ERPNext

                frappe.log_error("Shopify customers retrieved and created in ERPNext.")
            else:
                frappe.log_error("No customers retrieved from Shopify.")
        else:
            frappe.log_error(f"Failed to fetch data from Shopify. Status code: {response.status_code}")

    except Exception as e:
        frappe.log_error(
            title="Shopify Customer Debugging",

            message={"error": str(e), "shopify_customer_id": shopify_customer.get("id") if 'shopify_customer' in locals() else 'N/A'}
        )
        

def create_customer(shopify_customers):
    for shopify_customer in shopify_customers:
        shopify_customer_id = str(shopify_customer.get("id"))

        existing_customer = frappe.db.get_value(
            "Customer",
            {"shopify_customer_id": shopify_customer_id},
            "name"
        )

        if existing_customer:
            continue  # Skip if customer already exists

        contact = create_contact(shopify_customer)

        customer = frappe.new_doc("Customer")
        customer.customer_name = contact.first_name + " " + contact.last_name
        customer.email_id = contact.email_id
        customer.shopify_customer_id = shopify_customer_id

        # Address (safe)
        addresses = shopify_customer.get("addresses") or []
        if addresses and addresses[0].get("address1"):
            customer.primary_address = addresses[0].get("address1")
        else:
            customer.primary_address = "No address provided"

        customer.default_currency = "MYR"
        customer.default_price_list = "Standard Selling"
        customer.customer_group = "All Customer Groups"
        customer.customer_type = "Individual"
        customer.territory = "All Territories"

        customer.insert(ignore_permissions=True)

        contact.append("links", {
            "link_doctype": "Customer",
            "link_name": customer.name
        })
        contact.save(ignore_permissions=True)

        frappe.db.commit()

        frappe.log_error(
            title="Customer Created",
            message=f"Customer {customer.name} linked to Contact {contact.name}"
        )



def create_contact(shopify_customer):
    contact = frappe.new_doc("Contact")

    contact.first_name = shopify_customer.get("first_name") or "Shopify"
    contact.last_name = shopify_customer.get("last_name") or "Customer"
    contact.is_primary_contact = 1

    email = shopify_customer.get("email")
    phone = shopify_customer.get("phone")

    if email:
        contact.append("email_ids", {
            "email_id": email,
            "is_primary": 1
        })

    if phone:
        contact.append("phone_nos", {
            "phone": phone,
            "is_primary_mobile_no": 1
        })

    contact.insert(ignore_permissions=True)
    return contact

# Attach the custom function to the 'Item' doctype's on_submit event
def on_submit():

    shopify_doc = frappe.get_doc(
        "Shopify Access",
        frappe.get_value("Shopify Access", {}, "name")
    )
    retrieve_shopify_customers(shopify_doc.api_key, shopify_doc.access_token, shopify_doc.shopify_url)

# Ensure the on_submit function is triggered when an 'Item' document is submitted
frappe.get_doc('DocType', 'Customer').on_submit = on_submit
