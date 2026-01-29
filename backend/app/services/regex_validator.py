import re

def validate(data: dict):
    if not isinstance(data, dict):
        return {}

    invoice_date = data.get("invoice_date", "")
    vehicle_no = data.get("vehicle_no", "")

    if invoice_date and not re.match(r"\d{2}/\d{2}/\d{4}", invoice_date):
        data["invoice_date"] = ""
    else:
        data.setdefault("invoice_date", invoice_date)

    if vehicle_no and not re.match(r"[A-Z]{2}\d{2}[A-Z]{2}\d{4}", vehicle_no):
        data["vehicle_no"] = ""
    else:
        data.setdefault("vehicle_no", vehicle_no)

    return data
