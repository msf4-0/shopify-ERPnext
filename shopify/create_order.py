import requests
import frappe
import json

@frappe.whitelist()
def create_shopify_order(customer_email, items, shopify_url, access_token, sales_order_name=None):
    
    items = json.loads(items)
    print(items)
    line_items = []

    for item in items:
        line_item = {
            "title": item.get("title"),
            "price": item.get("price"),
            "quantity": item.get("quantity"),
            "product_id": item.get("product_id"),
            "sku": item.get("sku"),
            "tax_lines": [
                {
                    "price": item.get("price") / 10,
                    "rate": 0.1,
                    "title": "SST",
                }
            ],
        }
        line_items.append(line_item)
    
    print(line_items)
    # Construct the API payload
    payload = {
        "order": {
            "email": customer_email,
            "financial_status": "pending",
            "fulfillment_status": "unfulfilled",
            "line_items": line_items,
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    final_url = f"{shopify_url}orders.json"

    response = requests.post(final_url, json=payload, headers=headers)

    if response.status_code == 201:
        frappe.msgprint("Order created in Shopify.")
        shopify_order = response.json().get("order")
        if shopify_order and sales_order_name:
            # Save Shopify order ID to Sales Order
            frappe.db.set_value("Sales Order", sales_order_name, "shopify_order_id", shopify_order.get("id"))
    else:
        frappe.msgprint(f"Failed to create the order in Shopify. Error: {response.content}")

    return shopify_order.get("id")

def on_submit(doc, method):

    if doc.shopify_order_id:
        return
    
    customer_doc = frappe.get_doc("Customer", doc.customer)
    customer_email = customer_doc.email_id
    items = []
    for item in doc.items:
        item_dict = {
            "title": item.name,
            "price": float(item.rate),
            "quantity": int(item.qty),
            "product_id": getattr(item, "shopify_product_id", ""),
            "sku": item.item_code
        }
        items.append(item_dict)
    
    shopify_doc = frappe.get_doc(
        "Shopify Access",
        frappe.get_value("Shopify Access", {}, "name")  # first Shopify Access record
    )
    
    shopify_order_id= create_shopify_order(customer_email, json.dumps(items), shopify_doc.shopify_url, shopify_doc.access_token,sales_order_name=doc.name)

    doc.db_set("shopify_order_id", shopify_order_id)