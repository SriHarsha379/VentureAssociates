REQUIRED_DOCS = {
    "invoice",
    "lr",
    "party_weighment",
    "site_weighment"
}

OPTIONAL_DOCS = {"toll_gate"}


def resolve_status(uploaded_docs: set) -> str:
    """
    Toll gate is optional.
    """
    if REQUIRED_DOCS.issubset(uploaded_docs):
        return "COMPLETED"
    return "PARTIAL"
