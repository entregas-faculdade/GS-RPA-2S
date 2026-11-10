"""Allowlist de domínios: o robô só responde com link cujo host pertence a um sufixo permitido."""

import json
import logging
import re
from collections.abc import Collection
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_DOMAINS_PATH = Path("data") / "allowed_domains.json"
REQUIRED_SCHEME = "https"
HOST_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")

logger = logging.getLogger("triage.automation")


@lru_cache(maxsize=None)
def load_allowed_suffixes(path: Path = ALLOWED_DOMAINS_PATH) -> frozenset[str]:
    """Lê os sufixos permitidos; falha segura: arquivo ausente ou inválido devolve conjunto vazio (nada é permitido)."""
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        logger.error("Allowlist indisponível (%s): %s", path, error)
        return frozenset()
    if not isinstance(records, list):
        logger.error("Allowlist inválida (esperava uma lista): %s", path)
        return frozenset()
    suffixes = {
        record["suffix"].strip().lower().strip(".")
        for record in records
        if isinstance(record, dict) and isinstance(record.get("suffix"), str) and record["suffix"].strip(".")
    }
    return frozenset(suffixes)


def _extract_host(url: str) -> str | None:
    """Devolve o host em minúsculas se a URL for `https` bem formada e sem credenciais; senão `None`."""
    if not isinstance(url, str) or any(char.isspace() or ord(char) < 32 for char in url):
        return None
    try:
        parts = urlsplit(url)
        parts.port  # noqa: B018 - levanta ValueError se a porta for inválida
    except ValueError:
        return None
    if parts.scheme != REQUIRED_SCHEME or parts.username is not None or parts.password is not None:
        return None
    host = (parts.hostname or "").rstrip(".")
    return host if HOST_PATTERN.fullmatch(host) else None


def is_allowed(url: str, suffixes: Collection[str] | None = None) -> bool:
    """Diz se a URL é `https`, sem credenciais, e o host é um sufixo permitido ou subdomínio dele.

    A comparação é pelo sufixo de domínio completo, com o ponto como fronteira:
    `servicos.gov.br` casa `gov.br`; `gov.br.evil.com` e `evilgov.br` não.
    """
    host = _extract_host(url)
    if host is None:
        return False
    allowed = load_allowed_suffixes() if suffixes is None else suffixes
    return any(host == suffix or host.endswith("." + suffix) for suffix in allowed)
