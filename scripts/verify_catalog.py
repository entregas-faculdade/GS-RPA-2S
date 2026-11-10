"""Audita o catálogo de serviços: esquema, allowlist, links, telefones e idade (`python scripts/verify_catalog.py`)."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import (
    CATALOG_PATH,
    CatalogFileError,
    read_catalog_records,
)
from triage.automation.catalog_audit import (
    DEFAULT_MAX_AGE_DAYS,
    LEVEL_ERROR,
    LEVEL_OK,
    AuditOptions,
    Check,
    audit_catalog,
    fetch_page_text,
    has_errors,
)
from triage.automation.link_check import check_link

EXIT_OK = 0
EXIT_ERRORS = 1
LEVEL_LABELS = {LEVEL_OK: "OK   ", LEVEL_ERROR: "ERRO "}
WARNING_LABEL = "AVISO"

logger = logging.getLogger("triage.verify_catalog")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica o catálogo de serviços públicos (não altera o arquivo).")
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH, help="arquivo do catálogo")
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS, help="idade máxima de verified_on")
    parser.add_argument("--offline", action="store_true", help="pula links e telefones (sem rede)")
    return parser


def _format(check: Check) -> str:
    return f"{LEVEL_LABELS.get(check.level, WARNING_LABEL)} {check.entry_id} [{check.name}] {check.detail}"


def main(argv: list[str] | None = None) -> int:
    """Audita o catálogo e devolve o código de saída: 0 sem erro, 1 com erro."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    try:
        records = read_catalog_records(args.catalog)
    except CatalogFileError as error:
        logger.error("%s", error)
        return EXIT_ERRORS
    options = AuditOptions(
        link_checker=check_link,
        fetch_page_text=fetch_page_text,
        max_age_days=args.max_age_days,
        offline=args.offline,
    )
    checks = audit_catalog(records, load_allowed_suffixes(), options)
    failed = has_errors(checks)
    summary = f"{len(records)} registro(s) verificado(s); {'com erro' if failed else 'sem erro'}."
    sys.stdout.write("\n".join([*(_format(check) for check in checks), summary]) + "\n")
    return EXIT_ERRORS if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
