from __future__ import annotations

from datetime import date, datetime
from typing import Optional


def parse_lastmod_to_date(s: str) -> Optional[date]:
    """
    lastmod suele venir como:
    - 2026-01-07T21:32:21-05:00
    - 2026-01-07T21:32:21+00:00
    - 2026-01-07
    - 2026-01-07T21:32:21Z
    """
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None
