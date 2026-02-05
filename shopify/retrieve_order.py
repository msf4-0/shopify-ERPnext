from time import time
import requests
import base64
import frappe
from frappe.utils import now
@frappe.whitelist()
def retrieve_shopify_orders(api_key, api_password, shopify_store_url):
    # Construct the Shopify API endpoint for fetching orders
    order_items = []
    api_endpoint = f"{shopify_store_url}orders.json"
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
            orders_data = response.json().get("orders", [])

            # Process the retrieved orders
            if orders_data:
                for shopify_order in orders_data:
                    create_sales_order(shopify_order)  # Create order records in ERPNext

                frappe.logger().info("Shopify orders retrieved and new Sales Orders created in ERPNext.")
                frappe.log_error("Shopify orders retrieved and new Sales Orders created in ERPNext.", "Shopify Order Retrieval")
            else:
                frappe.logger().info("No orders retrieved from Shopify.")
                frappe.log_error("No orders retrieved from Shopify.", "Shopify Order Retrieval")
        else:
            frappe.logger().error(f"Failed to fetch data from Shopify. Status code: {response.status_code}")
            frappe.log_error(f"Failed to fetch data from Shopify. Status code: {response.status_code}", "Shopify Order Retrieval")

    except Exception as e:
        frappe.log_error(
            title="Shopify Order Sync Failed",
            message=(
                f"Error: {str(e)}\n"
                f"Shopify Order ID: {shopify_order.get('id') if 'shopify_order' in locals() else 'N/A'}"
            )
        )
        frappe.logger().exception("Shopify sync exception")

def create_sales_order(shopify_order):
    order_name = shopify_order["name"]
    shopify_order_id = str(shopify_order["id"])

    # Prevent duplicates
    existing_order = frappe.db.get_value(
        "Sales Order",
        {"shopify_order_id": shopify_order_id},
        "name"
    )

    customer_data = shopify_order.get("customer")
    email = customer_data.get("email")
    shopify_customer_id = str(customer_data.get("id"))
    customer_name = frappe.db.get_value(
        "Customer",
        {"shopify_customer_id": shopify_customer_id},
        "name"
    )
    
    if not existing_order:
        new_sales_order = frappe.new_doc("Sales Order")
        new_sales_order.delivery_date = now()
        new_sales_order.shopify_order_id = shopify_order_id
        if not customer_name:
            new_customer_name = create_customer(customer_data)
            new_sales_order.customer = new_customer_name
        else:
            new_sales_order.customer = customer_name
        new_sales_order.status = map_workflow_state(shopify_order)

        for line_item in shopify_order["line_items"]:
            create_sales_order_item(new_sales_order, line_item)

        if not new_sales_order.get("items"):
            frappe.logger().warning(
                f"Sales Order {order_name} has no valid items. Skipping creation."
            )
            return
        new_sales_order.insert(ignore_permissions=True)  # Insert Sales Order record
        frappe.db.commit()
        frappe.msgprint(f"Sales Order {new_sales_order.name} created in ERPNext.")
    else:
        frappe.msgprint(f"Sales Order already exists in ERPNext.")

def map_workflow_state(shopify_order):
    if shopify_order["fulfillment_status"] == "unfulfilled" or shopify_order["fulfillment_status"] is None:
        if shopify_order["financial_status"] == "pending":
            return "Draft"
        if shopify_order["financial_status"] == "paid":
            return "To Deliver"
    else:
        if shopify_order["financial_status"] == "pending":
            return "To Deliver"
        if shopify_order["financial_status"] == "paid":
            return "Completed"
    

def create_sales_order_item(sales_order, line_item):
    item_code = line_item.get("sku")
    title = line_item.get("title")
    shopify_product_id = str(line_item.get("product_id"))

    if not item_code:
        frappe.logger().warning(
            f"Skipping item without SKU (Shopify line_item_id={line_item.get('id')})"
        )
        return

    # Get or create Item
    if not frappe.db.exists("Item", item_code):
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.item_name = title or item_code
        item.item_group = "Products"
        item.stock_uom = "Nos"
        item.is_stock_item = 1
        item.shopify_product_id = shopify_product_id
        item.insert(ignore_permissions=True)
        frappe.db.commit()

    # 🔐 SAFE numeric values
    qty = line_item.get("quantity")
    price = line_item.get("price")

    qty = int(qty) if qty is not None else 1
    rate = float(price) if price is not None else 0.0

    frappe.logger().info(
        f"SO Item -> SKU={item_code}, qty={qty}, rate={rate}, order={sales_order.shopify_order_id}"
    )
    so_item = sales_order.append("items")
    so_item.item_code = item_code
    so_item.qty = qty
    so_item.rate = rate
    so_item.conversion_factor = 1


def create_customer(shopify_customer):

    shopify_customer_id = str(shopify_customer["id"])
    customer_email = shopify_customer.get("email")
    existing_customer = frappe.db.get_value(
        "Customer",
        {"shopify_customer_id": shopify_customer_id},
        "name"
    )

    if not existing_customer:
        new_customer = frappe.new_doc("Customer")
        new_customer.customer_name = f"{shopify_customer.get('first_name', '')} {shopify_customer.get('last_name', '')}".strip() or "shopify Customer"
        new_customer.email_id = customer_email
        new_customer.shopify_customer_id = shopify_customer_id
        new_customer.insert(ignore_permissions=True)
        frappe.db.commit()
        return new_customer.name
    else:
        return existing_customer.name


# Attach the custom function to the 'Sales Order' doctype's on_submit event
def scheduled_retrieve_shopify_orders():
    shopify_doc = frappe.get_doc(
        "Shopify Access",
        frappe.get_value("Shopify Access", {}, "name")
    )
    retrieve_shopify_orders(shopify_doc.api_key, shopify_doc.access_token, shopify_doc.shopify_url)

@frappe.whitelist()
def test_scheduler_event():
    # This is a test function to verify that the scheduler event is working
    #log a message to the Frappe log
    frappe.log_error("Scheduler event is working!", "Shopify Scheduler Test")
