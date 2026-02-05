import frappe
import requests


def retrieve_shopify_product(api_key, password, shopify_url):
    headers = {
        "X-Shopify-Access-Token": password,
        "Content-Type": "application/json",
    }

    frappe.logger().info("Starting full Shopify product sync")

    url = f"{shopify_url}products.json?limit=250"

    while url:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            frappe.log_error(
                f"Shopify fetch failed: {response.status_code} - {response.text}"
            )
            break

        data = response.json()
        products = data.get("products", [])

        for product in products:
            _upsert_item_from_shopify(product)
            frappe.logger().info(
                f"Synced product {product.get('title')} ({product.get('id')})"
            )
        frappe.db.commit()
        # Pagination handling
        link_header = response.headers.get("Link")
        url = None

        if link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip("<> ")
                    break

    frappe.logger().info("Shopify product sync completed")


def _upsert_item_from_shopify(product):
    shopify_product_id = str(product.get("id"))
    title = product.get("title")
    description = product.get("body_html") or ""
    handle = product.get("handle")
    product_type = product.get("product_type")

    # Use the first variant for SKU & inventory
    variant = product.get("variants", [{}])[0]
    item_code = variant.get("sku") or f"SHOPIFY-{shopify_product_id}"

    # Check if Item already exists using Shopify Product ID
    existing_item = frappe.db.get_value(
        "Item", {"shopify_product_id": shopify_product_id}, "name"
    )

    if existing_item:
        #  Update existing item
        frappe.logger().info(f"Updated existing Item: {existing_item}")
        frappe.msgprint(f"Updated existing Item: {existing_item}")
    else:
        #  Create new item
        # Make sure item_code is unique
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.shopify_product_id = shopify_product_id
        item.item_group = "All Item Groups"
        item.stock_uom = "Nos"
        item.is_stock_item = 1
        item.insert(ignore_permissions=True)
        frappe.log_error(f"Created new Item: {title}")



def on_submit():
    
    shopify_doc = frappe.get_doc(
        "Shopify Access",
        frappe.get_value("Shopify Access", {}, "name")
    )
    retrieve_shopify_product(shopify_doc.api_key, shopify_doc.access_token, shopify_doc.shopify_url)
