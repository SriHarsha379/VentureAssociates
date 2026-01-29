from app.core.document_rules import REQUIRED_DOCS

def resolve_status(uploaded_docs: set) -> str:
    if REQUIRED_DOCS.issubset(uploaded_docs):
        return "COMPLETED"
    return "PARTIAL"
