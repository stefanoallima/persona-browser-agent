"""
har_parser.py — HAR file → v3 network_log entries

Pure Python, no browser-use dependency.
Reads HAR JSON and returns entries matching the network-log-entry.schema.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Schema-allowed fields (additionalProperties: false in schema)
# ---------------------------------------------------------------------------
_ALLOWED_FIELDS = {
    "method",
    "url",
    "status",
    "timing_ms",
    "trigger",
    "request_content_type",
    "request_body",
    "response_summary",
    "set_cookie",
    "request_headers_note",
}

_RESPONSE_SUMMARY_MAX = 500


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_header(headers: list[dict], name: str) -> Optional[str]:
    """Case-insensitive header lookup. Returns first match or None."""
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return h.get("value")
    return None


def _domain_matches(url: str, domains: list[str]) -> bool:
    """Return True if the URL's host:port (or host) matches any domain in the list."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port
        # Build host:port string if port present
        if port:
            host_port = f"{host}:{port}"
        else:
            host_port = host
        for domain in domains:
            # Match against both bare host and host:port
            if domain == host_port or domain == host:
                return True
        return False
    except Exception:
        return False


def _build_response_summary(content: dict) -> Optional[str]:
    """
    Build a response_summary string.
    - HTML bodies → "HTML page (N bytes)"
    - JSON bodies → body text truncated to 500 chars
    - Other → None
    """
    mime = content.get("mimeType", "")
    text = content.get("text", "")
    size = content.get("size", 0)

    if "html" in mime:
        return f"HTML page ({size} bytes)"

    if text:
        # JSON or other text — truncate to 500 chars
        summary = text[:_RESPONSE_SUMMARY_MAX]
        return summary

    return None


def _parse_entry(entry: dict) -> dict:
    """Convert a single HAR entry dict to a network_log entry dict."""
    request = entry.get("request", {})
    response = entry.get("response", {})

    result: dict = {}

    # Required fields
    result["method"] = request.get("method", "GET").upper()
    result["url"] = request.get("url", "")
    result["status"] = int(response.get("status", 0))

    # timing_ms — HAR stores total time in entry["time"] (milliseconds)
    raw_time = entry.get("time")
    if raw_time is not None:
        result["timing_ms"] = float(raw_time)

    # request_content_type
    req_content_type = _get_header(request.get("headers", []), "content-type")
    if req_content_type:
        result["request_content_type"] = req_content_type

    # request_body (POST data)
    post_data = request.get("postData")
    if post_data and isinstance(post_data, dict):
        body_text = post_data.get("text")
        if body_text:
            result["request_body"] = body_text

    # response_summary
    content = response.get("content", {})
    summary = _build_response_summary(content)
    if summary:
        result["response_summary"] = summary

    # set_cookie
    set_cookie = _get_header(response.get("headers", []), "set-cookie")
    if set_cookie:
        result["set_cookie"] = set_cookie

    # request_headers_note — note if cookie or authorization header was sent
    req_headers = request.get("headers", [])
    req_cookies = request.get("cookies", [])
    notes = []
    if req_cookies:
        notes.append("Cookie sent")
    elif _get_header(req_headers, "cookie"):
        notes.append("Cookie sent")
    if _get_header(req_headers, "authorization"):
        notes.append("Authorization present")
    if notes:
        result["request_headers_note"] = "; ".join(notes)

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_har(
    har_path: str,
    app_domains: list[str] | None = None,
) -> list[dict]:
    """
    Read a HAR file and return a list of network_log entries.

    Parameters
    ----------
    har_path:
        Path to the HAR JSON file.
    app_domains:
        Optional list of domain strings (e.g. ["localhost:3333"]).
        None or [] means return all entries.

    Returns
    -------
    list[dict]
        Each dict matches network-log-entry.schema.json.
        None-valued fields are omitted.

    Raises
    ------
    FileNotFoundError
        If har_path does not exist.
    """
    if not os.path.exists(har_path):
        raise FileNotFoundError(f"HAR file not found: {har_path}")

    with open(har_path, encoding="utf-8") as f:
        har = json.load(f)

    raw_entries = har.get("log", {}).get("entries", [])

    # Apply domain filter if specified and non-empty
    if app_domains:
        raw_entries = [
            e for e in raw_entries
            if _domain_matches(e.get("request", {}).get("url", ""), app_domains)
        ]

    return [_parse_entry(e) for e in raw_entries]


def correlate_with_steps(
    entries: list[dict],
    step_timestamps: list[tuple[float, float]],
    session_start: datetime | None = None,
) -> list[dict]:
    """
    Return a new list with a `trigger` field added to each entry.

    Maps entries to steps using proportional chronological distribution:
    the session is divided into equal time-slices, one per step, and
    each network entry is assigned to the step whose slice it falls in.

    Parameters
    ----------
    entries:
        Network log entries (as returned by parse_har).
    step_timestamps:
        List of (start_offset_s, end_offset_s) tuples — one per step.
        Offset is seconds from session start.
        If empty, all triggers become None.
    session_start:
        Optional reference datetime. Currently unused; offsets are relative.

    Returns
    -------
    list[dict]
        New list with `trigger` field added (or set to None).
    """
    if not step_timestamps:
        return [{**e, "trigger": None} for e in entries]

    n = len(entries)
    n_steps = len(step_timestamps)

    result = []
    for i, entry in enumerate(entries):
        # Proportional distribution: assign step by index fraction
        step_index = int(i * n_steps / n) if n > 0 else 0
        step_index = min(step_index, n_steps - 1)
        trigger = f"step {step_index + 1}"
        result.append({**entry, "trigger": trigger})

    return result


def parse_har_raw_timestamps(
    har_path: str,
) -> list[tuple[dict, datetime]]:
    """
    Return (entry_dict, started_datetime) pairs for precise correlation.

    Parameters
    ----------
    har_path:
        Path to the HAR JSON file.

    Returns
    -------
    list[tuple[dict, datetime]]
        Each tuple contains the parsed entry dict and its startedDateTime
        as a timezone-aware datetime object.

    Raises
    ------
    FileNotFoundError
        If har_path does not exist.
    """
    if not os.path.exists(har_path):
        raise FileNotFoundError(f"HAR file not found: {har_path}")

    with open(har_path, encoding="utf-8") as f:
        har = json.load(f)

    raw_entries = har.get("log", {}).get("entries", [])
    result = []
    for raw_entry in raw_entries:
        entry_dict = _parse_entry(raw_entry)
        started_str = raw_entry.get("startedDateTime", "")
        try:
            # HAR uses ISO 8601 with Z suffix
            dt = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            dt = datetime.now(timezone.utc)
        result.append((entry_dict, dt))

    return result
