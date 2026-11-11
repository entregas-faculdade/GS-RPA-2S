"""Gera `data/catalog.d/sp_expanded.json` a partir da planilha da base enriquecida (`python scripts/import_catalog_xlsx.py`)."""

import argparse
import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import CATALOG_DIR_PATH, load_catalog
from triage.automation.catalog_import import (
    IMPORT_CONFIG_PATH,
    CatalogImportError,
    ImportOptions,
    find_pairs,
    format_report,
    import_xlsx,
    load_import_config,
    write_catalog_json,
)

EXIT_OK = 0
EXIT_ERROR = 1
DEFAULT_XLSX = Path("docs") / "catalogo_servicos_publicos_expandido_rpa.xlsx"
DEFAULT_OUT = CATALOG_DIR_PATH / "sp_expanded.json"

logger = logging.getLogger("triage.import_catalog_xlsx")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Converte a planilha da base enriquecida em registros do catálogo.")
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX, help="planilha de origem (somente leitura)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="arquivo JSON de saída")
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="verified_on (AAAA-MM-DD); padrão: hoje em UTC")
    parser.add_argument("--config", type=Path, default=IMPORT_CONFIG_PATH, help="tabelas de mapeamento")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Importa a planilha, grava o JSON e imprime o relatório; devolve 0, ou 1 se a planilha não pôde ser lida."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    verified_on = (args.date or datetime.now(UTC).date()).isoformat()
    options = ImportOptions(verified_on, load_allowed_suffixes(), args.xlsx.name)
    try:
        report = import_xlsx(args.xlsx, load_import_config(args.config), options)
    except CatalogImportError as error:
        logger.error("%s", error)
        return EXIT_ERROR
    write_catalog_json(report.records, args.out)
    # O catálogo atual é só o versionado: o arquivo gerado não pode contar como "par" de si mesmo.
    pairs = find_pairs(report.records, load_catalog(extra_dir=None))
    sys.stdout.write(format_report(report, pairs, args.out) + "\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
