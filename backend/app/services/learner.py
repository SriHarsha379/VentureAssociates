import json
from pathlib import Path

DATA_PATH = Path("app/data/few_shots.json")

def load_examples():
    if not DATA_PATH.exists():
        return []

    text = DATA_PATH.read_text().strip()
    if not text:
        return []

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # corrupted file fallback
        return []


def save_example(raw_text, extracted):
    examples = load_examples()

    if extracted.get("invoice_no") and extracted.get("bill_to_party"):
        examples.append({
            "input": raw_text[:1500],
            "output": extracted
        })

        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        DATA_PATH.write_text(
            json.dumps(examples[-30:], indent=2, ensure_ascii=False)
        )

