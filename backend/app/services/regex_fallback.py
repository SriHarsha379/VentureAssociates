import re

def normalize(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


# ---------------- VEHICLE ----------------
def extract_vehicle_no(text: str) -> str:
    if not text:
        return ""

    text = text.upper().replace(".", "").replace("-", "")

    candidates = re.findall(r"[A-Z0-9]{8,12}", text)

    for c in candidates:
        c = normalize(c)
        if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z]{2}\d{4}", c):
            return c

    return ""


# ---------------- LR ----------------
def extract_lr_no(text: str) -> str:
    if not text:
        return ""

    patterns = [
        r"\bLR\s*NO\.?\s*[:\-]?\s*([A-Z0-9\/\-]{6,25})",
        r"\bSP\/DR\/LR\/\d{2}-\d{2}\/\d+"
    ]

    text = text.upper()

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            # ✅ SAFE handling
            if m.lastindex:          # has capture group
                return m.group(1).strip()
            else:                    # no capture group
                return m.group(0).strip()

    return ""



# ---------------- E-WAY ----------------
def extract_eway_bill_no(text: str) -> str:
    if not text:
        return ""

    m = re.search(r"\b(\d{12})\b", text)
    return m.group(1) if m else ""


# ---------------- ORDER ----------------
def extract_order_no(text: str) -> str:
    if not text:
        return ""

    patterns = [
        r"\b(SO|S0|2S)[\:\/\-]?\d{2}-\d{2}\/\d+",
        r"\bORDER\s*NO\.?\s*[:\-]?\s*([A-Z0-9\/\-]+)"
    ]

    for pat in patterns:
        m = re.search(pat, text.upper())
        if m:
            return m.group(0)

    return ""


# ---------------- INVOICE AMOUNT ----------------
def extract_invoice_amount(text: str) -> str:
    """
    Try to extract the final invoice amount / grand total.
    Returns a string number (e.g. "12345.67") or "" if not found.
    """
    if not text:
        return ""

    t = text.upper()

    # Prefer totals/grand total style lines
    patterns = [
        r"\bGRAND\s*TOTAL\b[^\d]{0,20}([0-9][0-9,]*\.?[0-9]{0,2})",
        r"\bINVOICE\s*AMOUNT\b[^\d]{0,20}([0-9][0-9,]*\.?[0-9]{0,2})",
        r"\bTOTAL\s*(?:AMOUNT|VALUE|INVOICE\s*VALUE)?\b[^\d]{0,20}([0-9][0-9,]*\.?[0-9]{0,2})",
        r"\bNET\s*(?:AMOUNT|PAYABLE)\b[^\d]{0,20}([0-9][0-9,]*\.?[0-9]{0,2})",
        r"(?:₹|RS\.?|INR)\s*([0-9][0-9,]*\.?[0-9]{0,2})\b",
    ]

    candidates = []
    for pat in patterns:
        for m in re.finditer(pat, t):
            amt = (m.group(1) or "").replace(",", "").strip()
            try:
                candidates.append(float(amt))
            except ValueError:
                continue

    if not candidates:
        return ""

    # Usually the largest candidate is the grand total.
    best = max(candidates)
    return f"{best:.2f}".rstrip("0").rstrip(".")
