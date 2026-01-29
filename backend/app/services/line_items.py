import json
from app.core.config import client

LINE_ITEM_PROMPT = """
Extract invoice line items.

Return ONLY a valid JSON array.
If no line items are found, return [].

Fields:
- item_name
- hsn_sac
- quantity
- uom
- rate
- taxable_value
- cgst
- sgst
- igst
- line_total

Do not include explanations or markdown.
"""



def extract_line_items(raw_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": LINE_ITEM_PROMPT},
            {"role": "user", "content": raw_text}
        ]
    )

    raw_output = response.choices[0].message.content.strip()

    print("LINE ITEMS RAW OUTPUT ↓↓↓")
    print(raw_output)
    print("LINE ITEMS RAW OUTPUT ↑↑↑")

    if not raw_output:
        return []

    # Handle markdown ```json blocks
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        raw_output = raw_output.replace("json", "", 1).strip()

    try:
        data = json.loads(raw_output)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        print("⚠️ Invalid JSON for line items, returning empty list")
        return []
