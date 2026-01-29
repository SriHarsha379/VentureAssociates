import re
import os
import json
import io
import cv2
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract

# ---------------- CONFIG ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

FIELDS = [
    "invoice_no","invoice_date","eway_bill_no",
    "bill_to_party","ship_to_party","destination",
    "vehicle_no","lr_no","lr_date"
]

# ---------------- OCR ---------------- #

def extract_text(file_bytes):

    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img = np.array(image)

    img = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    thresh = cv2.adaptiveThreshold(
        denoised,255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,21,10
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(1,1))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    config = "--oem 3 --psm 4 -c preserve_interword_spaces=1"
    text = pytesseract.image_to_string(cleaned, config=config)

    return text


# ---------------- REGEX ---------------- #

def regex_extract(text):

    data = {k:"" for k in FIELDS}

    # Invoice
    m = re.search(r"Invoice\s*No\s*[:\-]?\s*([A-Z0-9\/\-]+)",text,re.I)
    if m: data["invoice_no"]=m.group(1)

    m = re.search(r"Invoice\s*Date\s*[:\-]?\s*([\d\/\-]{10})",text,re.I)
    if m: data["invoice_date"]=m.group(1)

    m = re.search(r"E[-\s]?Way\s*bill\s*No\s*[:\-]?\s*(\d{10,15})",text,re.I)
    if m: data["eway_bill_no"]=m.group(1)

    # Vehicle
    veh = re.search(r"\b(MH|AP|TS|KA|TN|DL)\s*\d{2}\s*[A-Z]{1,2}\s*\d{4}\b",text,re.I)
    if veh:
        data["vehicle_no"]=re.sub(r"\s+","",veh.group(0))

    # LR
    lr = re.search(r"(?:LR|L\.R)\s*No\s*[:\-]?\s*(\d+)",text,re.I)
    if lr: data["lr_no"]=lr.group(1)

    # Bill To
    bill = re.search(r"BILL\s*TO\s*:([\s\S]{0,200})",text,re.I)
    if bill:
        names=re.findall(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b",bill.group(1))
        if names: data["bill_to_party"]=names[-1]

    # Ship To
    if "GHOSALWADI" in text.upper():
        data["ship_to_party"]="GHOSALWADI-PANVEL"

    # Destination
    dest = re.search(r"Near[:\s]*Dandfata.*?Panvel",text,re.I)
    if dest: data["destination"]=dest.group(0)

    return data


# ---------------- GPT ---------------- #

def parse_with_gpt(raw_text, regex_data):

    prompt=f"""
Use regex as truth.
DO NOT guess.

RAW:
{raw_text}

REGEX:
{regex_data}

Return ONLY JSON.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0
    )

    txt=res.choices[0].message.content.strip()

    try:
        json.loads(txt)
        return txt
    except:
        return json.dumps(regex_data)


# ---------------- FASTAPI ---------------- #

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/ocr")
async def ocr_api(file: UploadFile = File(...)):

    file_bytes = await file.read()

    if len(file_bytes) < 1000:
        return {"error":"Empty file"}

    raw_text = extract_text(file_bytes)
    regex_data = regex_extract(raw_text)
    gpt_fixed = parse_with_gpt(raw_text, regex_data)

    try:
        final_json=json.loads(gpt_fixed)
    except:
        final_json=regex_data

    return {
        "raw_text": raw_text,
        "regex_result": regex_data,
        "final_result": final_json,
        "confidence":{
            "regex_fields_found":sum(1 for v in regex_data.values() if v),
            "total_fields":len(FIELDS)
        }
    }
