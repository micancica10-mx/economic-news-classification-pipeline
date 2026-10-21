from urllib.parse import urlparse, unquote


def title_from_slug(link: str) -> str:
    try:
        path = unquote(urlparse(link).path).strip("/")
        parts = [p for p in path.split("/") if p]
        slug = parts[-1] if parts else ""
        return slug.replace("-", " ").strip()
    except Exception:
        return ""
