import json
from openai import OpenAI

from app.core.config import OPENAI_API_KEY
from app.core.prompts import SYSTEM_PROMPT
from app.services.learner import load_examples


# ✅ Create LLM client HERE (v2-correct)
client = OpenAI(api_key=OPENAI_API_KEY)


def extract_with_llm(raw_text: str) -> dict:
    if not raw_text:
        return {}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # ---- few-shot examples ----
    for ex in load_examples():
        messages.append({
            "role": "user",
            "content": f"OCR TEXT:\n{ex['input']}"
        })
        messages.append({
            "role": "assistant",
            "content": json.dumps(ex["output"])
        })

    # ---- actual input ----
    messages.append({
        "role": "user",
        "content": f"OCR TEXT:\n{raw_text}\n\nExtract invoice data."
    })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0
    )

    raw_output = response.choices[0].message.content.strip()

    print("LLM RAW OUTPUT ↓↓↓")
    print(raw_output)
    print("LLM RAW OUTPUT ↑↑↑")

    if not raw_output:
        return {}

    # ---- handle ```json blocks ----
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        raw_output = raw_output.replace("json", "", 1).strip()

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        print("⚠️ Invalid JSON from LLM, returning empty dict")
        return {}
