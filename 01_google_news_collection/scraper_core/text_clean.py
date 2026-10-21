from __future__ import annotations

import re
import html as ihtml

_RE_IMG = re.compile(r"<img\b[^>]*\/?>", flags=re.IGNORECASE)
_RE_B_OPEN = re.compile(r"<\s*b\s*>", flags=re.IGNORECASE)
_RE_B_CLOSE = re.compile(r"<\s*/\s*b\s*>", flags=re.IGNORECASE)

_RE_H3_OPEN = re.compile(r"<\s*h3\b[^>]*>", flags=re.IGNORECASE)
_RE_H3_CLOSE = re.compile(r"<\s*/\s*h3\s*>", flags=re.IGNORECASE)

_RE_P_OPEN = re.compile(r"<\s*p\b[^>]*>", flags=re.IGNORECASE)
_RE_P_CLOSE = re.compile(r"<\s*/\s*p\s*>", flags=re.IGNORECASE)


def limpiar_texto_completo(html_text: str) -> str:
    """
    Convierte HTML (content:encoded) a texto legible con saltos.
    """
    if not html_text:
        return ""

    s = html_text

    s = _RE_IMG.sub("", s)

    s = _RE_B_OPEN.sub("", s)
    s = _RE_B_CLOSE.sub("", s)

    s = _RE_P_CLOSE.sub("\n\n", s)
    s = _RE_P_OPEN.sub("", s)

    s = _RE_H3_CLOSE.sub("\n\n", s)
    s = _RE_H3_OPEN.sub("\n\n", s)

    s = re.sub(r"<\s*br\s*/?\s*>", "\n", s, flags=re.IGNORECASE)

    s = re.sub(r"<[^>]+>", "", s)

    s = ihtml.unescape(s)

    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s).strip()

    return s
