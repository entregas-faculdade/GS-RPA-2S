"""Treina o classificador com `split=train` do CSV rotulado e grava o modelo (`python scripts/train_model.py`)."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.classification.model import DEFAULT_MODEL_PATH, save, train

DEFAULT_CSV_PATH = Path("data/labeled/requests_labeled.csv")
EXIT_OK = 0
EXIT_INVALID_INPUT = 2

logger = logging.getLogger("triage.train_model")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Treina o classificador TF-IDF + regressão logística.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="CSV rotulado sintético")
    parser.add_argument("--output", type=Path, default=DEFAULT_MODEL_PATH, help="arquivo do modelo treinado")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Treina e grava o modelo; devolve o código de saída."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    if not args.csv.is_file():
        logger.error("CSV rotulado não encontrado: %s", args.csv)
        return EXIT_INVALID_INPUT
    save(train(args.csv), args.output)
    logger.info("Modelo gravado em %s", args.output)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
