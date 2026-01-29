def merge_fields(base: dict, incoming: dict) -> dict:
    for k, v in incoming.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if not base.get(k):
            base[k] = v
    return base
