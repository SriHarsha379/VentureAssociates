"""
Self-Learning Invoice Extraction System
Uses AI to extract data and learns from corrections automatically
No regex patterns needed - the AI learns from examples
"""

import re
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FIELDS = [
    "invoice_no",
    "invoice_date",
    "eway_bill_no",
    "bill_to_party",
    "ship_to_party",
    "destination",
    "vehicle_no",
    "lr_no",
    "lr_date"
]

# File paths
TRAINING_DATA_PATH = os.path.join(BASE_DIR, "training_data.json")
VALIDATION_LOG_PATH = os.path.join(BASE_DIR, "validation_log.json")


class SelfLearningExtractor:
    """AI-based extractor that learns from corrections"""

    def __init__(self):
        self.training_examples = self._load_json(TRAINING_DATA_PATH, [])
        self.validation_log = self._load_json(VALIDATION_LOG_PATH, [])

    def _load_json(self, filepath, default):
        """Load JSON file or return default"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default
        return default

    def _save_json(self, filepath, data):
        """Save data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _build_training_prompt(self):
        """Build few-shot examples from training data"""
        if not self.training_examples:
            return ""

        # Use last 3 examples to avoid token limits
        recent = self.training_examples[-3:]

        prompt = "\n### LEARNING FROM PAST CORRECTIONS ###\n"
        prompt += "Here are examples of correctly extracted invoice data:\n\n"

        for i, ex in enumerate(recent, 1):
            # Truncate invoice text for brevity
            text_preview = ex['invoice_text'][:400].replace('\n', ' ')
            prompt += f"Example {i}:\n"
            prompt += f"Invoice snippet: ...{text_preview}...\n"
            prompt += f"Correct extraction:\n{json.dumps(ex['correct_data'], indent=2)}\n\n"

        return prompt

    def extract(self, invoice_text):
        """
        Extract invoice data using AI
        Returns: dict with extracted_data, confidence, and metadata
        """

        training_context = self._build_training_prompt()

        system_prompt = """You are an expert invoice data extraction AI.
Your job is to extract specific fields from invoice text with high accuracy.
Learn from the examples provided and apply similar patterns to new invoices.

Handle OCR errors gracefully:
- "chicle" might mean "vehicle"
- Missing spaces or extra characters
- Formatting issues

Be precise and consistent."""

        user_prompt = f"""{training_context}

### FIELDS TO EXTRACT ###
Extract these fields from the invoice below:
{json.dumps(FIELDS, indent=2)}

### EXTRACTION GUIDELINES ###
1. **invoice_no**: Invoice number (e.g., "MHSI/25-26/1286")
2. **invoice_date**: Date in DD/MM/YYYY format
3. **eway_bill_no**: E-Way bill number (usually 12 digits)
4. **bill_to_party**: Company name after "BILL TO:"
5. **ship_to_party**: Shipping location/address after "SHIP TO:"
6. **destination**: Full destination address
7. **vehicle_no**: Vehicle registration (e.g., "MH46CL0081")
8. **lr_no**: LR/Lorry Receipt number
9. **lr_date**: LR date (use CPO date if LR date not found)

### IMPORTANT ###
- Return empty string "" if field is not found
- Be consistent with date formats (DD/MM/YYYY)
- Extract exact values, don't modify or clean them
- For company names, get the complete name
- Handle OCR errors intelligently

### INVOICE TEXT ###
{invoice_text}

### OUTPUT FORMAT ###
Return ONLY a valid JSON object with the extracted fields. No explanations, no markdown formatting, just pure JSON."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Ensure all fields are present
            extracted_data = {field: result.get(field, "") for field in FIELDS}

            # Calculate confidence
            fields_found = sum(1 for v in extracted_data.values() if v)
            confidence_pct = round((fields_found / len(FIELDS)) * 100, 2)

            return {
                "success": True,
                "extracted_data": extracted_data,
                "confidence": {
                    "fields_found": fields_found,
                    "total_fields": len(FIELDS),
                    "percentage": confidence_pct
                },
                "training_examples_count": len(self.training_examples),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_data": {field: "" for field in FIELDS}
            }

    def learn(self, invoice_text, correct_data):
        """
        Teach the system with correct data
        This is called after manual verification/correction
        """

        # Validate correct_data has all fields
        validated_data = {field: correct_data.get(field, "") for field in FIELDS}

        # Create training example
        example = {
            "id": len(self.training_examples) + 1,
            "timestamp": datetime.now().isoformat(),
            "invoice_text": invoice_text,
            "correct_data": validated_data
        }

        # Add to training examples
        self.training_examples.append(example)

        # Keep only last 50 examples to manage size
        if len(self.training_examples) > 50:
            self.training_examples = self.training_examples[-50:]

        # Save to disk
        self._save_json(TRAINING_DATA_PATH, self.training_examples)

        return {
            "success": True,
            "message": f"Learned from example #{example['id']}",
            "total_examples": len(self.training_examples)
        }

    def validate_and_learn(self, invoice_text, extracted_data, correct_data):
        """
        Compare extracted data with correct data and learn from differences
        """

        differences = {}
        for field in FIELDS:
            extracted_val = extracted_data.get(field, "")
            correct_val = correct_data.get(field, "")

            if extracted_val != correct_val:
                differences[field] = {
                    "extracted": extracted_val,
                    "correct": correct_val
                }

        # Log validation
        validation_entry = {
            "timestamp": datetime.now().isoformat(),
            "differences_count": len(differences),
            "differences": differences,
            "accuracy": round((1 - len(differences) / len(FIELDS)) * 100, 2)
        }

        self.validation_log.append(validation_entry)
        self._save_json(VALIDATION_LOG_PATH, self.validation_log[-100:])  # Keep last 100

        # If there are differences, learn from them
        if differences:
            self.learn(invoice_text, correct_data)

            return {
                "success": True,
                "needs_learning": True,
                "differences": differences,
                "accuracy": validation_entry["accuracy"],
                "message": f"Found {len(differences)} differences. System has learned from this."
            }
        else:
            return {
                "success": True,
                "needs_learning": False,
                "accuracy": 100.0,
                "message": "Perfect extraction! No learning needed."
            }

    def get_stats(self):
        """Get statistics about the learning system"""

        total_validations = len(self.validation_log)

        if total_validations == 0:
            avg_accuracy = 0
        else:
            avg_accuracy = sum(v['accuracy'] for v in self.validation_log) / total_validations

        return {
            "training_examples": len(self.training_examples),
            "total_validations": total_validations,
            "average_accuracy": round(avg_accuracy, 2),
            "last_trained": self.training_examples[-1]['timestamp'] if self.training_examples else None
        }


# ============== EASY-TO-USE FUNCTIONS ==============

def extract_invoice(invoice_text):
    """
    Main function to extract data from invoice
    Usage: result = extract_invoice(your_invoice_text)
    """
    extractor = SelfLearningExtractor()
    return extractor.extract(invoice_text)


def correct_and_teach(invoice_text, extracted_data, correct_data):
    """
    Provide correct data to teach the system
    Usage: correct_and_teach(invoice_text, extracted, correct_data)
    """
    extractor = SelfLearningExtractor()
    return extractor.validate_and_learn(invoice_text, extracted_data, correct_data)


def get_system_stats():
    """Get learning system statistics"""
    extractor = SelfLearningExtractor()
    return extractor.get_stats()


# ============== EXAMPLE USAGE ==============

if __name__ == "__main__":
    # Sample invoice text
    sample_invoice = """TAX INVOICE

BILL TO:
OM ASHTAVINAYAK ENTERPRISES

E-Way bill No > 222037782861

Invoice No. : MHSI/25-26/1286
Invoice Date: 16/09/2025
Vehicle No =: MH46CL0081
LRNo. =: 1430
CPO Date: 15/08/2025

SHIP TO:
GHOSALWADI-PANVEL

Near Dandfata,Old Mumbai-Pune Highway,Panvel"""

    print("=" * 60)
    print("INVOICE EXTRACTION TEST")
    print("=" * 60)

    # Step 1: Extract
    result = extract_invoice(sample_invoice)
    print("\n1. EXTRACTION RESULT:")
    print(json.dumps(result, indent=2))

    # Step 2: Provide correct data (simulate user correction)
    correct_data = {
        "invoice_no": "MHSI/25-26/1286",
        "invoice_date": "16/09/2025",
        "eway_bill_no": "222037782861",
        "bill_to_party": "OM ASHTAVINAYAK ENTERPRISES",
        "ship_to_party": "GHOSALWADI-PANVEL",
        "destination": "Near Dandfata,Old Mumbai-Pune Highway,Panvel",
        "vehicle_no": "MH46CL0081",
        "lr_no": "1430",
        "lr_date": "15/08/2025"
    }

    print("\n2. TEACHING THE SYSTEM:")
    validation = correct_and_teach(
        sample_invoice,
        result['extracted_data'],
        correct_data
    )
    print(json.dumps(validation, indent=2))

    # Step 3: Check stats
    print("\n3. SYSTEM STATISTICS:")
    stats = get_system_stats()
    print(json.dumps(stats, indent=2))

    print("\n" + "=" * 60)
    print("✓ System is now smarter for future invoices!")
    print("=" * 60)