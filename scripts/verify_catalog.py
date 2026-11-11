"""Audita o catálogo e a base enriquecida: esquema, `content`, allowlist, links, telefones e idade (`python scripts/verify_catalog.py`)."""

import argparse
import logging
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import (
    CATALOG_DIR_PATH,
    CATALOG_PATH,
    DEFAULT_MAX_AGE_DAYS,
    CatalogFileError,
    catalog_extra_files,
    read_catalog_records,
)
from triage.automation.catalog_audit import (
    LEVEL_ERROR,
    LEVEL_OK,
    AuditOptions,
    Check,
    audit_catalog_files,
    fetch_page_text,
    has_errors,
)
from triage.automation.link_check import build_link_checker
from triage.config import load_settings

EXIT_OK = 0
EXIT_ERRORS = 1
LEVEL_LABELS = {LEVEL_OK: "OK   ", LEVEL_ERROR: "ERRO "}
WARNING_LABEL = "AVISO"

logger = logging.getLogger("triage.verify_catalog")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica o catálogo de serviços públicos (não altera o arquivo).")
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH, help="arquivo do catálogo")
    parser.add_argument("--catalog-dir", type=Path, default=CATALOG_DIR_PATH, help="pasta da base enriquecida (*.json)")
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS, help="idade máxima de verified_on")
    parser.add_argument("--offline", action="store_true", help="pula links e telefones (sem rede)")
    return parser


def _format(check: Check) -> str:
    line = f"{LEVEL_LABELS.get(check.level, WARNING_LABEL)} {check.entry_id} [{check.name}] {check.detail}"
    return line if check.level == LEVEL_OK else f"{line} (arquivo: {check.source})"


def _read_extra_files(directory: Path) -> tuple[list[tuple[str, list]], list[Check]]:
    """Registros de cada arquivo da base enriquecida; arquivo ilegível vira erro apontando o arquivo, sem derrubar os demais."""
    files: list[tuple[str, list]] = []
    failures: list[Check] = []
    for file in catalog_extra_files(directory):
        try:
            files.append((str(file), read_catalog_records(file)))
        except CatalogFileError as error:
            failures.append(Check(file.name, "file", LEVEL_ERROR, str(error), str(file)))
    return files, failures


def main(argv: list[str] | None = None) -> int:
    """Audita o catálogo e devolve o código de saída: 0 sem erro, 1 com erro."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    try:
        main_records = read_catalog_records(args.catalog)
    except CatalogFileError as error:
        logger.error("%s", error)
        return EXIT_ERRORS
    files = [(str(args.catalog), main_records)]
    extra_files, failures = _read_extra_files(args.catalog_dir)
    files.extend(extra_files)
    user_agent = load_settings().link_check_user_agent
    options = AuditOptions(
        link_checker=build_link_checker(user_agent),
        fetch_page_text=partial(fetch_page_text, user_agent=user_agent),
        max_age_days=args.max_age_days,
        offline=args.offline,
    )
    checks = [*audit_catalog_files(files, load_allowed_suffixes(), options), *failures]
    failed = has_errors(checks)
    total = sum(len(records) for _, records in files)
    summary = f"{total} registro(s) verificado(s); {'com erro' if failed else 'sem erro'}."
    sys.stdout.write("\n".join([*(_format(check) for check in checks), summary]) + "\n")
    return EXIT_ERRORS if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
