"""Ponto de entrada do robô de triagem (`python run.py`)."""

import argparse
import dataclasses
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from triage.config import DEFAULT_OUTPUT_DIR, load_settings
from triage.logging_setup import configure_logging, shutdown_logging

DEFAULT_INPUT_DIR = "data/samples"
EXIT_OK = 0
EXIT_INVALID_INPUT = 2

logger = logging.getLogger("triage.run")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Robô de triagem de pedidos de serviços públicos.")
    parser.add_argument("--input", default=DEFAULT_INPUT_DIR, help="pasta com os pedidos (txt/csv/json)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="pasta de saída (logs e relatórios)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Valida os argumentos e devolve o código de saída."""
    args = _build_parser().parse_args(argv)
    settings = dataclasses.replace(load_settings(), output_dir=args.output)
    configure_logging(settings)
    try:
        if not Path(args.input).is_dir():
            logger.error("Pasta de entrada não encontrada: %s", args.input)
            return EXIT_INVALID_INPUT
        logger.warning("Pipeline ainda não implementado; nada foi processado.")
        return EXIT_OK
    finally:
        shutdown_logging()


if __name__ == "__main__":
    sys.exit(main())
