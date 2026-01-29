import re

FIELD_RULES = {
    "invoice_no": r"[A-Z0-9\/\-]{6,}",
    "invoice_date": r"\d{2}/\d{2}/\d{4}",
    "eway_bill_no": r"\d{10,15}",
    "vehicle_no": r"[A-Z]{2}\d{2}[A-Z]{2}\d{4}",
    "lr_no": r"\d+"
}

def score_field(field, value):
    if not value:
        return 0.0
    rule = FIELD_RULES.get(field)
    if not rule:
        return 0.8
    return 0.95 if re.match(rule, value) else 0.5


def add_confidence(data):
    confidence = {}
    for k, v in data.items():
        confidence[k] = score_field(k, v)
    return confidence
