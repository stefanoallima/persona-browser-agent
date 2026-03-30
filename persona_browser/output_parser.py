"""
output_parser.py — AgentHistoryList → v3 navigator output JSON

Transforms browser-use's AgentHistoryList + parsed HAR entries + optional
manifest into the v3 navigator output JSON matching
schemas/navigator-output.schema.json.

Works with both the real AgentHistoryList (browser-use) and duck-typed mocks
(for testing without the full async browser-use setup).
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_history(
    history,                        # AgentHistoryList or duck-type compatible
    har_entries: list[dict],        # from har_parser.parse_har()
    manifest: dict | None = None,   # from manifest.json
    persona: str = "",
    url: str = "",
    scope: str = "task",
) -> dict:
    """
    Convert an AgentHistoryList into the v3 navigator output dict.

    Parameters
    ----------
    history     : AgentHistoryList (or mock) from browser-use
    har_entries : list of network-log dicts from har_parser.parse_har()
    manifest    : optional page manifest dict (pages[], auth_flow, etc.)
    persona     : persona identifier string
    url         : root URL used for the session
    scope       : session scope string (e.g. "task", "gate")

    Returns
    -------
    dict matching schemas/navigator-output.schema.json
    """
    # 1. Group steps by URL into page segments
    groups = _group_steps_by_url(history)

    # 2. Assign manifest page IDs (or fallback slugs) to each group
    if manifest:
        groups = _match_to_manifest(groups, manifest)
    else:
        groups = _assign_slug_ids(groups)

    # 3. Build per-page output dicts
    pages = [_build_page_output(g, har_entries) for g in groups]

    # 4. Determine overall status
    status = _determine_status(history)

    # 5. Elapsed time
    elapsed = 0.0
    try:
        elapsed = float(history.total_duration_seconds())
    except Exception:
        pass

    # 6. Collect all screenshot paths
    screenshots = [p["screenshot"] for p in pages if p.get("screenshot")]

    # 7. Manifest coverage
    manifest_coverage = _build_manifest_coverage(groups, manifest)

    # 8. Experience section
    experience = _build_experience(history)

    # 9. agent_result backward-compat field
    agent_result = ""
    try:
        agent_result = history.final_result() or ""
    except Exception:
        pass

    # 10. Root URL — use from args, or fall back to first URL in history
    root_url = url
    if not root_url:
        try:
            urls = history.urls()
            if urls:
                root_url = urls[0] or ""
        except Exception:
            pass

    output: dict[str, Any] = {
        "version": "1.1",
        "status": status,
        "elapsed_seconds": elapsed,
        "persona": persona,
        "url": root_url,
        "scope": scope,
        "agent_result": agent_result,
        "manifest_coverage": manifest_coverage,
        "pages": pages,
        "experience": experience,
        "screenshots": screenshots,
        "video": None,
    }

    return output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _group_steps_by_url(history) -> list[dict]:
    """
    Group consecutive steps with the same URL into page segments.

    Revisiting the same URL creates a new segment (no merging).

    Returns a list of dicts:
      {
        "url": str,
        "steps": [step, ...],   # original step objects
        "step_indices": [int, ...]  # global step numbers (0-based)
      }
    """
    groups: list[dict] = []
    current_group: dict | None = None

    for i, step in enumerate(history.history):
        try:
            step_url = step.state.url or ""
        except Exception:
            step_url = ""

        if current_group is None or step_url != current_group["url"]:
            current_group = {
                "url": step_url,
                "steps": [],
                "step_indices": [],
            }
            groups.append(current_group)

        current_group["steps"].append(step)
        current_group["step_indices"].append(i)

    return groups


def _assign_slug_ids(groups: list[dict]) -> list[dict]:
    """
    Assign simple URL-slug IDs to groups when there is no manifest.
    Duplicate slugs get a '-visit-N' suffix.
    """
    slug_counts: dict[str, int] = {}
    for g in groups:
        slug = _url_to_slug(g["url"])
        slug_counts[slug] = slug_counts.get(slug, 0) + 1

    slug_seen: dict[str, int] = {}
    for g in groups:
        slug = _url_to_slug(g["url"])
        slug_seen[slug] = slug_seen.get(slug, 0) + 1
        if slug_counts[slug] > 1:
            g["page_id"] = f"{slug}-visit-{slug_seen[slug]}"
        else:
            g["page_id"] = slug
    return groups


def _match_to_manifest(groups: list[dict], manifest: dict) -> list[dict]:
    """
    Assign manifest page IDs to groups by URL matching.

    Matching strategy (simple substring, sufficient for v1):
    1. Check if any word from the page's `how_to_reach` hint appears in the URL path.
    2. Fall back to checking if the page `id` appears in the URL path.
    3. If still no match, assign "unexpected-{slug}".

    Duplicate matches get a '-visit-N' suffix.
    """
    manifest_pages = manifest.get("pages", [])

    def _find_manifest_id(url: str) -> str | None:
        path = urlparse(url).path.lower()
        # Try each manifest page
        for page in manifest_pages:
            page_id = page.get("id", "")
            how_to_reach = page.get("how_to_reach", "")
            # Extract path-like tokens from how_to_reach
            tokens = re.findall(r"/[\w\-]+", how_to_reach.lower())
            for token in tokens:
                if token in path:
                    return page_id
            # Fallback: page id directly in path
            if page_id.lower() in path:
                return page_id
        return None

    # Count how many times each manifest id will appear
    id_counts: dict[str, int] = {}
    assigned: list[str | None] = []
    for g in groups:
        mid = _find_manifest_id(g["url"])
        assigned.append(mid)
        if mid:
            id_counts[mid] = id_counts.get(mid, 0) + 1

    id_seen: dict[str, int] = {}
    for g, mid in zip(groups, assigned):
        if mid:
            id_seen[mid] = id_seen.get(mid, 0) + 1
            if id_counts[mid] > 1:
                g["page_id"] = f"{mid}-visit-{id_seen[mid]}"
            else:
                g["page_id"] = mid
        else:
            g["page_id"] = f"unexpected-{_url_to_slug(g['url'])}"

    return groups


def _build_page_output(group: dict, har_entries: list[dict]) -> dict:
    """
    Build a single page output dict from a URL group + HAR entries.
    """
    url = group["url"]
    page_id = group.get("page_id", _url_to_slug(url))
    steps = group["steps"]
    step_indices = group.get("step_indices", list(range(len(steps))))

    # Screenshot: use first step with a non-None screenshot path
    screenshot = None
    for step in steps:
        try:
            sp = step.state.screenshot_path
            if sp:
                screenshot = sp
                break
        except Exception:
            pass

    # Page title: from first step
    title = ""
    try:
        title = steps[0].state.title or ""
    except Exception:
        pass

    # Observations: actions list
    actions = []
    description_parts = []
    for local_idx, (step, global_idx) in enumerate(zip(steps, step_indices)):
        step_num = global_idx + 1  # 1-based

        # Action description from model_output.action
        action_texts = []
        try:
            for act in step.model_output.action:
                try:
                    if hasattr(act, "model_dump"):
                        d = act.model_dump(exclude_none=True, mode="json")
                        # Use first key as action name, rest as params
                        keys = list(d.keys())
                        if keys:
                            action_texts.append(f"{keys[0]}: {d[keys[0]]}")
                    elif isinstance(act, dict):
                        keys = list(act.keys())
                        if keys:
                            action_texts.append(f"{keys[0]}: {act[keys[0]]}")
                    else:
                        action_texts.append(str(act))
                except Exception:
                    action_texts.append(str(act))
        except Exception:
            pass

        action_str = "; ".join(action_texts) if action_texts else f"step {step_num}"

        # Result description from extracted_content
        result_str = ""
        try:
            ec = step.result[0].extracted_content
            result_str = ec or ""
        except Exception:
            pass

        if not result_str:
            result_str = f"Step {step_num} completed"

        actions.append({
            "step": step_num,
            "action": action_str,
            "result": result_str,
        })

        # Collect thinking for description
        try:
            thinking = step.model_output.current_state.thinking
            if thinking:
                description_parts.append(thinking)
        except Exception:
            pass

    # Build description from extracted content if no thinking available
    if not description_parts:
        for step in steps:
            try:
                ec = step.result[0].extracted_content
                if ec:
                    description_parts.append(ec)
            except Exception:
                pass

    description = " ".join(description_parts) if description_parts else (title or url)

    # Forms: detect from extracted content (simple heuristic for v1)
    forms = _detect_forms(steps)

    # Network log: assign HAR entries whose URL matches this page's URL base
    page_network_log = _assign_har_to_page(url, har_entries)

    page: dict[str, Any] = {
        "id": page_id,
        "url_visited": url,
        "observations": {
            "description": description,
            "actions": actions,
            "forms": forms,
        },
        "network_log": page_network_log,
    }

    if screenshot is not None:
        page["screenshot"] = screenshot

    return page


def _detect_forms(steps: list) -> list[dict]:
    """
    Simple v1 form detection: look for form-related extracted content keywords.
    Returns a list of form dicts (may be empty).
    """
    form_keywords = {"form", "input", "field", "submit", "register", "login", "sign"}
    for step in steps:
        try:
            ec = (step.result[0].extracted_content or "").lower()
            if any(kw in ec for kw in form_keywords):
                return [{"fields_seen": [], "submitted": False, "errors_encountered": []}]
        except Exception:
            pass
    return []


def _assign_har_to_page(page_url: str, har_entries: list[dict]) -> list[dict]:
    """
    Assign HAR entries whose URL shares the same scheme+host as page_url.

    Additionally, for non-root paths, only include entries whose URL path
    starts with the same path prefix (first path segment) as the page URL.
    This keeps API calls from leaking to unrelated pages.

    For simple cases (root page or matching host), all entries with same
    host are assigned; when there are multiple distinct page URLs we use
    path matching to scope entries.
    """
    if not har_entries:
        return []

    try:
        parsed_page = urlparse(page_url)
        page_host = parsed_page.netloc
        page_path = parsed_page.path.rstrip("/")
    except Exception:
        return []

    assigned = []
    for entry in har_entries:
        try:
            entry_url = entry.get("url", "")
            parsed_entry = urlparse(entry_url)
            if parsed_entry.netloc != page_host:
                continue
            # If the entry URL path starts with or matches the page path (or root)
            entry_path = parsed_entry.path.rstrip("/")
            if _paths_match(page_path, entry_path):
                assigned.append(entry)
        except Exception:
            continue

    return assigned


def _paths_match(page_path: str, entry_path: str) -> bool:
    """
    Return True when the entry URL belongs to this page.

    Rules:
    - entry_path starts with page_path  (e.g., /register matches /register)
    - OR entry_path starts with /api    (API calls appear on whatever page triggered them)
    - OR page_path is root ("")         (root page gets everything)
    """
    if not page_path:
        return True
    if entry_path.startswith(page_path):
        return True
    return False


def _build_manifest_coverage(groups: list[dict], manifest: dict | None) -> dict:
    """
    Compute manifest coverage from matched groups.
    """
    if not manifest:
        # No manifest: visited = unique page IDs seen
        visited_ids = list(dict.fromkeys(g.get("page_id", "") for g in groups))
        return {
            "expected_pages": [],
            "visited": visited_ids,
            "not_visited": [],
            "unexpected_pages": [],
        }

    manifest_pages = manifest.get("pages", [])
    expected_ids = [p["id"] for p in manifest_pages]

    # Gather visited manifest IDs (strip visit-N suffixes)
    visited_manifest_ids: set[str] = set()
    unexpected_ids: list[str] = []

    for g in groups:
        pid = g.get("page_id", "")
        if pid.startswith("unexpected-"):
            unexpected_ids.append(pid)
        else:
            # Strip -visit-N suffix
            base_id = re.sub(r"-visit-\d+$", "", pid)
            if base_id in expected_ids:
                visited_manifest_ids.add(base_id)
            else:
                unexpected_ids.append(pid)

    visited = [eid for eid in expected_ids if eid in visited_manifest_ids]
    not_visited = [eid for eid in expected_ids if eid not in visited_manifest_ids]

    return {
        "expected_pages": expected_ids,
        "visited": visited,
        "not_visited": not_visited,
        "unexpected_pages": unexpected_ids,
    }


def _build_experience(history) -> dict:
    """
    Build the experience section from history.

    For v1 the experience dict is mostly empty scaffolding — it gets
    populated by a post-processing LLM call in the full pipeline.
    We populate what we can deterministically here.
    """
    final = ""
    try:
        final = history.final_result() or ""
    except Exception:
        pass

    # Extract extracted content as proxy for experience notes
    extracted: list[str] = []
    try:
        extracted = [c for c in history.extracted_content() if c]
    except Exception:
        pass

    experience: dict[str, Any] = {
        "first_impression": final[:300] if final else "",
        "easy": [],
        "hard": [],
        "hesitation_points": [],
        "would_return": None,
        "would_recommend": "",
        "satisfaction": None,
        "satisfaction_reason": "",
    }

    return experience


def _determine_status(history) -> str:
    """
    Determine the DONE/ERROR/PARTIAL status from history flags.
    """
    try:
        if history.is_done() and history.is_successful():
            return "DONE"
        if history.is_done() and not history.is_successful():
            return "ERROR"
    except Exception:
        pass

    try:
        errors = [e for e in history.errors() if e]
        if errors:
            return "PARTIAL"
    except Exception:
        pass

    return "DONE"


def _url_to_slug(url: str) -> str:
    """
    Convert a URL to a kebab-case slug suitable as a page ID.

    Examples:
      http://localhost:3333/register  → register
      http://localhost:3333/          → home
      http://localhost:3333/settings/profile → settings-profile
    """
    try:
        path = urlparse(url).path.strip("/")
        if not path:
            return "home"
        # Replace slashes with dashes and strip non-alphanumeric
        slug = re.sub(r"[^a-z0-9\-]", "", path.lower().replace("/", "-"))
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug or "page"
    except Exception:
        return "page"
