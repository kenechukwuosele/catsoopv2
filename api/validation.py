"""
Path/identifier validators. All user-supplied path segments must pass these
before being joined into filesystem paths or interpolated into generated
.catsoop / .py files.
"""

import os
import re
import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)

SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SAFE_QNAME = re.compile(r"^q_[A-Za-z0-9]{1,32}$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

# Characters that must never appear in a value written to a generated .py file
# even inside a repr()-quoted string — prevents accidental shell/format issues
# in downstream consumers.
_DANGEROUS_PY_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _ensure(rx: re.Pattern, value: str, kind: str) -> str:
    if not isinstance(value, str) or not rx.match(value):
        logger.info("Rejected unsafe %s: %r", kind, value)
        raise HTTPException(status_code=422, detail=f"Invalid {kind}")
    return value


def safe_course(value: str) -> str:
    return _ensure(SAFE_ID, value, "course id")


def safe_week(value: str) -> str:
    return _ensure(SAFE_ID, value, "week id")


def safe_qname(value: str) -> str:
    return _ensure(SAFE_QNAME, value, "question name")


def safe_filename(value: str) -> str:
    if value in (".", "..") or "/" in value or "\\" in value:
        raise HTTPException(status_code=422, detail="Invalid filename")
    return _ensure(SAFE_FILENAME, value, "filename")


def safe_text_for_pyfile(value: str, max_len: int = 1024) -> str:
    """Reject control characters in values destined for repr()-quoted .py output."""
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail="Invalid text")
    if len(value) > max_len:
        raise HTTPException(status_code=422, detail="Value too long")
    if _DANGEROUS_PY_CHARS.search(value):
        raise HTTPException(status_code=422, detail="Value contains control characters")
    return value


def ensure_within(base: str, candidate: str) -> str:
    """Return the realpath of `candidate` after asserting it lives under `base`."""
    base_real = os.path.realpath(base)
    cand_real = os.path.realpath(candidate)
    if cand_real != base_real and not cand_real.startswith(base_real + os.sep):
        logger.warning("Path traversal blocked: base=%s candidate=%s", base, candidate)
        raise HTTPException(status_code=422, detail="Path traversal blocked")
    return cand_real
