"""Shared HTTP request utilities."""
from fastapi import Request


def wants_html(request: Request) -> bool:
    """True iff the client explicitly accepts text/html.

    `*/*` (the default curl/TestClient Accept) is NOT treated as HTML -- those
    callers want JSON. Pages add Accept: text/html via the browser.
    """
    return "text/html" in request.headers.get("accept", "")
