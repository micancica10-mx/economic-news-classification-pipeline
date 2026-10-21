from __future__ import annotations

import re


def clean_spaces(t: str) -> str:
    """Colapsa espacios/saltos y recorta."""
    return re.sub(r"\s+", " ", (t or "")).strip()


def ensure_final_period(text: str) -> str:
    """
    Asegura que el texto termine en punto.
    - Quita signos finales comunes (. ! ? …) y vuelve a poner '.'
    - Si viene vacío, devuelve ""
    """
    if not text:
        return ""
    t = text.strip().rstrip(" .!?…")
    return t + "."


def join_blocks(blocks: list[str]) -> str:
    """
    Une bloques con doble salto, limpiando espacios y eliminando vacíos.
    """
    blocks = [clean_spaces(b) for b in blocks]
    blocks = [b for b in blocks if b]
    return "\n\n".join(blocks).strip()


def make_bad_prefix_checker(prefixes: list[str] | tuple[str, ...]):
    """
    Devuelve una función is_bad(text) que filtra por prefijos (case-insensitive),
    útil para 'Lea también', 'Te puede interesar', etc.
    """
    pref = tuple(clean_spaces(p).lower() for p in prefixes if clean_spaces(p))

    def is_bad(txt: str) -> bool:
        t = clean_spaces(txt).lower()
        if not t:
            return True
        return t.startswith(pref)

    return is_bad