import requests
import base64
import frappe

@frappe.whitelist()
def retrieve_shopify_customers(api_key, api_password, shopify_store_url):
    # Construct the Shopify API endpoint for fetching customers
    api_endpoint = f"{shopify_store_url}customers.json?limit=250"

    # Set up the request headers with basic authentication
    headers = {
        "X-Shopify-Access-Token": api_password,
        "Content-Type": "application/json",
    }

    # Make the GET request to Shopify API
    while api_endpoint:
        response = requests.get(api_endpoint, headers=headers)

        # Check the response status code
        if response.status_code == 200:
            customers_data = response.json().get("customers", [])
            # Process the retrieved customers
            if customers_data:
                for shopify_customer in customers_data:
                    create_customer([shopify_customer])  # Create customer records in ERPNext

                frappe.log_error(f"Shopify customers retrieved {len(customers_data)} and created in ERPNext.")
            else:
                frappe.log_error("No customers retrieved from Shopify.")
        else:
            frappe.log_error(f"Failed to fetch data from Shopify. Status code: {response.status_code}")

        link_header = response.headers.get("Link")
        url = None

        if link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip("<> ")
                    break

    frappe.logger().info("Shopify product sync completed")
        

def create_customer(shopify_customers):
    for shopify_customer in shopify_customers:
        shopify_customer_id = str(shopify_customer.get("id"))
        addresses = shopify_customer.get("addresses") or []
        first_name = shopify_customer.get("first_name") or ""
        last_name = shopify_customer.get("last_name") or ""
        email = shopify_customer.get("email") or ""
        phone = shopify_customer.get("phone") or ""

        full_name = (first_name + " " + last_name).strip() or "Shopify Customer"
        existing_customer = frappe.db.get_value(
            "Customer",
            {"shopify_customer_id": shopify_customer_id},
            "name"
        )
        if existing_customer:
            customer = frappe.get_doc("Customer", existing_customer)
            customer.customer_name = full_name
            customer.email_id = email
            customer.mobile_no = phone
            customer.primary_address = (
                addresses[0].get("address1")
                if addresses and addresses[0].get("address1")
                else "No address provided"
            )
            customer.flags.ignore_shopify_update = True
            customer.save(ignore_permissions=True)

            frappe.db.commit()
            continue 
        
        customer = frappe.new_doc("Customer")
        customer.customer_name = full_name
        customer.email_id = email
        customer.shopify_customer_id = shopify_customer_id
        customer.mobile_no = phone
        customer.primary_address = (
            addresses[0].get("address1")
            if addresses and addresses[0].get("address1")
            else "No address provided"
        )

        customer.default_currency = "MYR"
        customer.default_price_list = "Standard Selling"
        customer.customer_group = "All Customer Groups"
        customer.customer_type = "Individual"
        customer.territory = "All Territories"
        customer.flags.ignore_shopify_update = True

        customer.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.log_error(
            title="Customer Created",
            message=f"Customer {customer.name} created"
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