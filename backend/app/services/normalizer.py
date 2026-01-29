# app/services/normalizer.py

import re
KEY_ALIASES = {
    # ======================
    # Invoice
    # ======================
    "invoice_no": "invoice_no",
    "invoice_number": "invoice_no",
    "invoice_amount": "invoice_amount",
    "invoice_value": "invoice_amount",
    "invoice_total": "invoice_amount",
    "total_invoice_amount": "invoice_amount",
    "total_invoice_value": "invoice_amount",
    "total_amount": "invoice_amount",
    "grand_total": "invoice_amount",
    "net_payable": "invoice_amount",
    "amount_payable": "invoice_amount",
    "total_payable": "invoice_amount",

    # ======================
    # Dates
    # ======================
    "invoice_date": "invoice_date",
    "order_date": "invoice_date",
    "ack_date": "invoice_date",
    "ack_date_time": "invoice_date",
    "date": "invoice_date",

    "lr_date": "lr_date",
    "lr_date_time": "lr_date",

    # ======================
    # Buyer (Bill To)
    # ======================
    "buyer": "buyer_name",
    "buyer_name": "buyer_name",
    "bill_to": "buyer_name",
    "bill_to_party": "buyer_name",
    "billto": "buyer_name",

    # ======================
    # Ship To
    # ======================
    "ship_to": "ship_to_party",
    "ship_to_party": "ship_to_party",
    "ship_to_address": "ship_to_party",
    "shipto": "ship_to_party",

    # ======================
    # Vehicle
    # ======================
    "vehicle_no": "vehicle_no",
    "vehicle_number": "vehicle_no",
    "truck_no": "vehicle_no",
    "truck_number": "vehicle_no",
    "lorry_no": "vehicle_no",

    # ======================
    # LR
    # ======================
    "lr_no": "lr_no",
    "lr_number": "lr_no",
    "lr_receipt_no": "lr_no",

    # ======================
    # Origin / Destination
    # ======================
    "origin": "origin",
    "from": "origin",
    "source": "origin",

    "destination": "destination",
    "to": "destination",
    "delivery_at": "destination",

    # ======================
    # E-Way Bill
    # ======================
    "eway_bill_no": "e_way_bill_no",
    "e_way_bill_no": "e_way_bill_no",
    "e_way_bill_number": "e_way_bill_no",
    "ewaybill_no": "e_way_bill_no",

    # ======================
    # Order
    # ======================
    "order_no": "order_no",
    "order_number": "order_no",

    "order_type": "order_type",
    "dispatch_type": "order_type",

    # ======================
    # Document metadata
    # ======================
    "page": "page_no",
    "page_no": "page_no",
    "page_number": "page_no",

    "doc_type": "doc_type",
    "document_type": "doc_type",

    "principal_company": "principal_company",
    "seller": "principal_company",
    "consignor": "principal_company",

    # ======================
    # Acknowledgement
    # ======================
    "acknowledged": "acknowledged",
    "ack_status": "acknowledged",
    "acknowledgement": "acknowledged",
    "signed": "acknowledged",
}



def _clean_key(key: str) -> str:
    """
    Normalize key names:
    - lowercase
    - remove dots
    - replace spaces with underscores
    """
    key = key.lower()
    key = re.sub(r"[.\s]+", "_", key)
    return key.strip("_")


def normalize_keys(data: dict) -> dict:
    """
    Normalize noisy LLM keys into canonical ERP schema keys.
    This function:
    - NEVER drops data
    - ONLY renames keys
    """
    if not isinstance(data, dict):
        return {}

    normalized = {}

    for key, value in data.items():
        cleaned_key = _clean_key(key)
        canonical_key = KEY_ALIASES.get(cleaned_key, cleaned_key)
        normalized[canonical_key] = value

    return normalized
