from fastapi import APIRouter, UploadFile, File, Form, Query, Body
from fastapi.responses import FileResponse
from typing import List
from datetime import datetime
from pathlib import Path
import shutil
from app.services.image_preprocessor import enhance_image
from app.services.ocr_service import run_ocr
from app.services.llm_extractor import extract_with_llm
from app.services.normalizer import normalize_keys
from app.services.aggregator import merge_fields
from app.services.regex_validator import validate
from app.services.confidence import add_confidence
from app.services.regex_fallback import (
    extract_vehicle_no,
    extract_lr_no,
    extract_eway_bill_no,
    extract_order_no,
    extract_invoice_amount
)
from db import invoice_col

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def normalize_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


@router.post("/api/extract")
async def extract_invoice(
        invoice_no: str = Form(...),
        files: List[UploadFile] = File(...),
        doc_types: List[str] = Form(...)
):
    # Get existing invoice from MongoDB
    existing = await invoice_col.find_one({"_id": invoice_no}) or {}
    final_data = existing.get("data", {})
    uploaded_docs = set(existing.get("uploaded_docs", []))
    uploaded_docs.update(doc_types)

    # Store document metadata
    documents = existing.get("documents", {})

    for file, doc_type in zip(files, doc_types):
        raw = await file.read()

        # Save file to disk - sanitize invoice number for filesystem
        safe_invoice_no = invoice_no.replace("/", "_").replace("\\", "_")
        invoice_dir = UPLOAD_DIR / safe_invoice_no
        invoice_dir.mkdir(parents=True, exist_ok=True)

        file_path = invoice_dir / f"{doc_type}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(raw)

        # Store document metadata
        documents[doc_type] = {
            "filename": file.filename,
            "filepath": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat()
        }

        # Process for OCR
        enhanced = enhance_image(raw)
        text = run_ocr(enhanced, file.filename)

        extracted = normalize_keys(extract_with_llm(text))

        extracted["vehicle_no"] = extract_vehicle_no(text) or extracted.get("vehicle_no")
        extracted["lr_no"] = extract_lr_no(text) or extracted.get("lr_no")
        extracted["e_way_bill_no"] = extract_eway_bill_no(text) or extracted.get("e_way_bill_no")
        extracted["order_no"] = extract_order_no(text) or extracted.get("order_no")
        extracted["invoice_amount"] = extract_invoice_amount(text) or extracted.get("invoice_amount")

        final_data = merge_fields(final_data, extracted)

    final_data = validate(final_data)
    confidence = add_confidence(final_data)
    final_data["invoice_date"] = normalize_date(final_data.get("invoice_date"))
    final_data["lr_date"] = normalize_date(final_data.get("lr_date"))

    required = {"invoice", "lr", "party_weighment", "site_weighment"}
    status = "COMPLETED" if required.issubset(uploaded_docs) else "PARTIAL"

    # Save to MongoDB with document metadata
    await invoice_col.update_one(
        {"_id": invoice_no},
        {
            "$set": {
                "data": final_data,
                "confidence": confidence,
                "status": status,
                "uploaded_docs": list(uploaded_docs),
                "documents": documents,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return {"data": final_data, "status": status, "confidence": confidence}


@router.post("/api/extract-from-stored")
async def extract_from_stored(invoice_no: str = Form(...)):
    """
    Run extraction using documents already uploaded and stored on disk.
    This is needed because browsers don't keep <input type=file> selections
    when the user comes back later to a saved draft.
    """
    existing = await invoice_col.find_one({"_id": invoice_no}) or {}
    documents = existing.get("documents", {}) or {}
    if not documents:
        return {"error": "No documents available for this invoice"}

    final_data = existing.get("data", {}) or {}
    uploaded_docs = set(existing.get("uploaded_docs", [])) or set(documents.keys())
    uploaded_docs.update(documents.keys())

    for doc_type, meta in documents.items():
        file_path = Path(meta.get("filepath", ""))
        if not file_path.exists():
            continue

        raw = file_path.read_bytes()
        enhanced = enhance_image(raw)
        text = run_ocr(enhanced, meta.get("filename", str(file_path.name)))

        extracted = normalize_keys(extract_with_llm(text))
        extracted["vehicle_no"] = extract_vehicle_no(text) or extracted.get("vehicle_no")
        extracted["lr_no"] = extract_lr_no(text) or extracted.get("lr_no")
        extracted["e_way_bill_no"] = extract_eway_bill_no(text) or extracted.get("e_way_bill_no")
        extracted["order_no"] = extract_order_no(text) or extracted.get("order_no")
        extracted["invoice_amount"] = extract_invoice_amount(text) or extracted.get("invoice_amount")

        final_data = merge_fields(final_data, extracted)

    final_data = validate(final_data)
    confidence = add_confidence(final_data)
    final_data["invoice_date"] = normalize_date(final_data.get("invoice_date"))
    final_data["lr_date"] = normalize_date(final_data.get("lr_date"))

    required = {"invoice", "lr", "party_weighment", "site_weighment"}
    status = "COMPLETED" if required.issubset(uploaded_docs) else "PARTIAL"

    await invoice_col.update_one(
        {"_id": invoice_no},
        {
            "$set": {
                "data": final_data,
                "confidence": confidence,
                "status": status,
                "uploaded_docs": list(uploaded_docs),
                "documents": documents,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )

    return {"data": final_data, "status": status, "confidence": confidence}


@router.post("/api/upload-documents")
async def upload_documents(
        invoice_no: str = Form(...),
        files: List[UploadFile] = File(...),
        doc_types: List[str] = Form(...)
):
    """
    Upload and persist document images WITHOUT running OCR/LLM extraction.
    This enables saving a draft now and extracting later from Manage Invoices.
    """
    existing = await invoice_col.find_one({"_id": invoice_no}) or {}
    uploaded_docs = set(existing.get("uploaded_docs", []))
    uploaded_docs.update(doc_types)

    documents = existing.get("documents", {})

    for file, doc_type in zip(files, doc_types):
        raw = await file.read()

        safe_invoice_no = invoice_no.replace("/", "_").replace("\\", "_")
        invoice_dir = UPLOAD_DIR / safe_invoice_no
        invoice_dir.mkdir(parents=True, exist_ok=True)

        file_path = invoice_dir / f"{doc_type}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(raw)

        documents[doc_type] = {
            "filename": file.filename,
            "filepath": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat()
        }

    required = {"invoice", "lr", "party_weighment", "site_weighment"}
    status = "COMPLETED" if required.issubset(uploaded_docs) else "PARTIAL"

    await invoice_col.update_one(
        {"_id": invoice_no},
        {
            "$set": {
                "documents": documents,
                "uploaded_docs": list(uploaded_docs),
                # Keep existing extracted data/confidence if already present
                "data": existing.get("data", {}),
                "confidence": existing.get("confidence", {}),
                # Drafts with partial docs should remain PARTIAL
                "status": existing.get("status", status) if existing.get("data") else status,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return {"ok": True, "uploaded_docs": list(uploaded_docs), "documents": documents, "status": status}


@router.get("/api/document")
async def get_document(invoice_no: str = Query(...), doc_type: str = Query(...)):
    """Serve uploaded document images"""
    invoice = await invoice_col.find_one({"_id": invoice_no})

    if not invoice or "documents" not in invoice:
        return {"error": "Document not found"}

    doc_info = invoice["documents"].get(doc_type)
    if not doc_info:
        return {"error": "Document type not found"}

    file_path = Path(doc_info["filepath"])
    if not file_path.exists():
        return {"error": "File not found on disk"}

    return FileResponse(file_path)


@router.post("/api/invoice/save")
async def save_invoice_data(payload: dict = Body(...)):
    invoice_no = payload.get("invoice_no")
    if not invoice_no:
        return {"error": "invoice_no required"}

    existing = await invoice_col.find_one({"_id": invoice_no}) or {}

    await invoice_col.update_one(
        {"_id": invoice_no},
        {
            "$set": {
                "data": payload,
                "confidence": existing.get("confidence", {}),
                "status": payload.get("status", "DRAFT"),
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow(),
                "uploaded_docs": []
            }
        },
        upsert=True
    )

    return {"message": "saved"}


@router.get("/api/invoice")
async def get_invoice(invoice_no: str = Query(...)):
    invoice = await invoice_col.find_one({"_id": invoice_no})
    if not invoice:
        return {
            "data": {},
            "confidence": {},
            "status": "NEW",
            "uploaded_docs": [],
            "documents": {}
        }
    invoice["_id"] = str(invoice["_id"])
    return invoice


@router.get("/api/invoices")
async def list_invoices():
    DOCS_REQUIRED = 4
    invoices = []

    async for doc in invoice_col.find():
        invoices.append({
            "invoice_no": str(doc["_id"]),
            "status": doc.get("status"),
            "documents": doc.get("documents", {}),
            "docs_uploaded": len(doc.get("uploaded_docs", [])),
            "docs_required": DOCS_REQUIRED,
            "data": doc.get("data", {})
        })

    return invoices


@router.post("/api/invoice")
async def save_invoice(payload: dict):
    invoice_no = payload["invoice_no"]

    # Get existing invoice to preserve documents and uploaded_docs
    existing = await invoice_col.find_one({"_id": invoice_no}) or {}

    # Only update documents if new documents are provided, otherwise keep existing
    documents_to_save = payload.get("documents")
    if documents_to_save is None or (isinstance(documents_to_save, dict) and not documents_to_save):
        # If no documents provided or empty dict, keep existing documents
        documents_to_save = existing.get("documents", {})

    # Preserve existing payments
    payments = existing.get("payments", [])
    total_paid = existing.get("total_paid", 0)
    balance_due = existing.get("balance_due", 0)
    payment_status = existing.get("payment_status", "Unpaid")

    # Get invoice amount from payload
    invoice_amount = float(payload.get("invoice_amount", 0))

    # Recalculate if invoice amount changed
    if invoice_amount > 0 and payments:
        total_paid = sum(p.get("amount", 0) for p in payments)
        balance_due = invoice_amount - total_paid
        payment_status = "Paid" if balance_due <= 0 else "Partial" if total_paid > 0 else "Unpaid"

    await invoice_col.update_one(
        {"_id": invoice_no},
        {
            "$set": {
                "data": payload["data"],
                "documents": documents_to_save,
                "uploaded_docs": existing.get("uploaded_docs", []),
                "status": payload["status"],
                "invoice_amount": invoice_amount,
                "payments": payments,
                "total_paid": total_paid,
                "balance_due": balance_due,
                "payment_status": payment_status,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return {"ok": True}


@router.get("/api/debug/invoice/{invoice_no}")
async def debug_invoice(invoice_no: str):
    """Debug endpoint to see raw MongoDB data"""
    invoice = await invoice_col.find_one({"_id": invoice_no})
    if invoice:
        invoice["_id"] = str(invoice["_id"])
    return invoice


@router.delete("/api/invoice")
async def delete_invoice(invoice_no: str = Query(...)):
    """Delete an invoice and its uploaded files"""
    # Get invoice to find file paths
    invoice = await invoice_col.find_one({"_id": invoice_no})

    if invoice:
        # Delete uploaded files from disk
        documents = invoice.get("documents", {})
        for doc_type, doc_info in documents.items():
            file_path = Path(doc_info.get("filepath", ""))
            if file_path.exists():
                file_path.unlink()

        # Delete the directory if empty
        safe_invoice_no = invoice_no.replace("/", "_").replace("\\", "_")
        invoice_dir = UPLOAD_DIR / safe_invoice_no
        if invoice_dir.exists():
            try:
                invoice_dir.rmdir()  # Only removes if empty
            except:
                pass  # Directory not empty, leave it

    # Delete from MongoDB
    result = await invoice_col.delete_one({"_id": invoice_no})

    if result.deleted_count > 0:
        return {"ok": True, "message": "Invoice deleted successfully"}
    else:
        return {"ok": False, "message": "Invoice not found"}


# ==================== PAYMENT/LEDGER ENDPOINTS ====================

@router.post("/api/payment")
async def add_payment(payload: dict = Body(...)):
    """Add a payment record for an invoice"""
    invoice_no = payload.get("invoice_no")
    if not invoice_no:
        return {"error": "invoice_no required"}

    payment_record = {
        "amount": float(payload.get("amount", 0)),
        "payment_date": payload.get("payment_date"),
        "payment_mode": payload.get("payment_mode", ""),  # Cash, Cheque, UPI, NEFT, etc.
        "reference_no": payload.get("reference_no", ""),
        "remarks": payload.get("remarks", ""),
        "recorded_at": datetime.utcnow().isoformat(),
        "recorded_by": payload.get("recorded_by", "System")
    }

    # Add payment to invoice
    result = await invoice_col.update_one(
        {"_id": invoice_no},
        {
            "$push": {"payments": payment_record},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    if result.modified_count > 0:
        # Calculate totals
        invoice = await invoice_col.find_one({"_id": invoice_no})
        payments = invoice.get("payments", [])
        total_paid = sum(p.get("amount", 0) for p in payments)
        invoice_amount = float(invoice.get("invoice_amount", 0))
        balance = invoice_amount - total_paid
        payment_status = "Paid" if balance <= 0 else "Partial" if total_paid > 0 else "Unpaid"

        # Update payment status
        await invoice_col.update_one(
            {"_id": invoice_no},
            {
                "$set": {
                    "total_paid": total_paid,
                    "balance_due": balance,
                    "payment_status": payment_status
                }
            }
        )

        return {"ok": True, "message": "Payment added successfully"}
    else:
        return {"ok": False, "message": "Failed to add payment"}


@router.get("/api/payments")
async def get_all_payments():
    """Get payment summary for all invoices"""
    invoices = []

    async for doc in invoice_col.find({"status": "COMPLETED"}):
        invoice_amount = float(doc.get("invoice_amount", 0))
        payments = doc.get("payments", [])
        total_paid = sum(p.get("amount", 0) for p in payments)
        balance = invoice_amount - total_paid

        invoices.append({
            "invoice_no": str(doc["_id"]),
            "invoice_date": doc.get("data", {}).get("invoice_date"),
            "buyer_name": doc.get("data", {}).get("buyer_name"),
            "invoice_amount": invoice_amount,
            "total_paid": total_paid,
            "balance_due": balance,
            "payment_status": doc.get("payment_status", "Unpaid"),
            "payments": payments
        })

    # Sort by balance due (highest first)
    invoices.sort(key=lambda x: x["balance_due"], reverse=True)

    return invoices


@router.get("/api/payment-summary")
async def get_payment_summary():
    """Get overall payment summary statistics"""
    invoices = await invoice_col.find({"status": "COMPLETED"}).to_list(None)

    total_invoices = len(invoices)
    total_invoice_amount = sum(float(inv.get("invoice_amount", 0)) for inv in invoices)
    total_paid = sum(float(inv.get("total_paid", 0)) for inv in invoices)
    total_outstanding = total_invoice_amount - total_paid

    paid_count = sum(1 for inv in invoices if inv.get("payment_status") == "Paid")
    partial_count = sum(1 for inv in invoices if inv.get("payment_status") == "Partial")
    unpaid_count = sum(1 for inv in invoices if inv.get("payment_status") == "Unpaid")

    return {
        "total_invoices": total_invoices,
        "total_invoice_amount": total_invoice_amount,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "paid_count": paid_count,
        "partial_count": partial_count,
        "unpaid_count": unpaid_count
    }