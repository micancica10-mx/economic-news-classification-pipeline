from __future__ import annotations

import requests
import time
import random
from typing import Optional, Dict
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/123.0 Safari/537.36"),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
}


def make_session(headers: Optional[Dict[str, str]] = None) -> requests.Session:
    s = requests.Session()
    s.verify = False

    h = dict(DEFAULT_HEADERS)
    if headers:
        h.update(headers)

    s.headers.update(h)
    return s


# Códigos 5xx que vale la pena reintentar (errores transitorios de servidor)
_RETRYABLE_5XX = {500, 502, 503, 504, 520, 521, 522, 524}


def get_text(
    s: requests.Session,
    url: str,
    *,
    timeout=(10, 60),
    max_tries: int = 4
) -> str:
    """
    Descarga HTML con reintentos para:
    - Errores de conexión (RemoteDisconnected, Timeout, etc.)
    - Errores 5xx transitorios del servidor (502, 503, 504, etc.)
    Los errores 4xx (403, 404, etc.) fallan inmediatamente sin reintentar.
    """
    last_err = None

    for i in range(max_tries):
        try:
            r = s.get(url, timeout=timeout)
            r.raise_for_status()
            return r.text

        except requests.exceptions.HTTPError as e:
            # 4xx → error permanente, no reintentar
            if e.response is not None and e.response.status_code < 500:
                raise
            # 5xx → transitorio, reintentar
            last_err = e

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as e:
            last_err = e

        # backoff exponencial + jitter (2s, 4s, 8s...)
        sleep_s = (2 ** i) + random.uniform(0, 0.6)
        time.sleep(sleep_s)

    raise last_err