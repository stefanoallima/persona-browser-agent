import copy


def filter_codeintel_for_visual(codeintel: dict) -> dict:
    """Filter codeintel to visual-relevant fields only.

    Keeps: pages[].elements, pages[].design_tokens, pages[].accessibility, pages[].id, pages[].purpose
    Removes: api_endpoints, auth, data_flows, generated_from, generated_at, version
    Also removes from each page's form elements: api_call, on_success (non-visual fields)

    Returns a deep copy — does not modify the original.
    """
    filtered = copy.deepcopy(codeintel)

    # Remove top-level non-visual fields
    for key in ["api_endpoints", "auth", "data_flows", "generated_from", "generated_at", "version"]:
        filtered.pop(key, None)

    # Remove non-visual fields from page form definitions
    for page in filtered.get("pages", []):
        elements = page.get("elements", {})
        for form in elements.get("forms", []):
            form.pop("api_call", None)
            form.pop("on_success", None)

    return filtered
