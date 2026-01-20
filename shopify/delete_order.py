import requests
import frappe
import json

@frappe.whitelist()
def delete_shopify_order(orderID, shopify_url,access_token):


    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    response = requests.delete(
        f"{shopify_url}orders/{orderID}.json",
        headers=headers
    )
    if response.status_code == 200:
        frappe.msgprint(f"Customer record was deleted from Shopify.")
    else:
        frappe.msgprint("Failed to delete the customer in Shopify. Error: {response.content}")

# Attach the custom function to the 'Item' doctype's on_submit event
def on_submit(doc, method):
    shopify_doc = frappe.get_doc("Shopify Access", frappe.get_value("Shopify Access", {}, "name"))
    delete_shopify_order(doc.shopify_order_id, shopify_doc.shopify_url, shopify_doc.access_token)

# Ensure the on_submit function is triggered when an 'Item' document is submitted
frappe.get_doc('DocType', 'Sales Order').on_submit = on_submit
