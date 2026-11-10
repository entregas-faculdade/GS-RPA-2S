"""Ponto de entrada do robô de triagem (`python run.py`)."""

import argparse
import dataclasses
import logging
import sys
from pathlib import Path
from threading import Event

sys.path.insert(0, str(Path(__file__).parent / "src"))

from triage.config import DEFAULT_OUTPUT_DIR, Settings, load_settings
from triage.logging_setup import configure_logging, shutdown_logging
from triage.pipeline import build_deps, run_batch, watch
from triage.storage import StorageError

DEFAULT_INPUT_DIR = "data/samples"
DEFAULT_DB_FILENAME = "triage.db"
DEFAULT_INTERVAL_SECONDS = 60.0
EXIT_OK = 0
EXIT_INFRASTRUCTURE_FAILURE = 1
EXIT_INVALID_INPUT = 2

logger = logging.getLogger("triage.run")


def _positive_seconds(raw_value: str) -> float:
    try:
        value = float(raw_value)
    except ValueError:
        value = 0.0
    if value <= 0:
        raise argparse.ArgumentTypeError("o intervalo deve ser um número maior que zero")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Robô de triagem de pedidos de serviços públicos.")
    parser.add_argument("--input", default=DEFAULT_INPUT_DIR, help="pasta com os pedidos (txt/csv/json)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="pasta de saída (logs, relatórios e banco)")
    parser.add_argument("--db", default=None, help=f"arquivo SQLite (padrão: <output>/{DEFAULT_DB_FILENAME})")
    parser.add_argument("--watch", action="store_true", help="reexecuta periodicamente até Ctrl+C")
    parser.add_argument("--interval", type=_positive_seconds, default=DEFAULT_INTERVAL_SECONDS, help="segundos entre as rodadas do --watch")
    parser.add_argument(
        "--llm", action=argparse.BooleanOptionalAction, default=None, help="liga ou desliga o LLM (padrão: LLM_ENABLED do .env)"
    )
    return parser


def _settings_from(args: argparse.Namespace) -> Settings:
    settings = dataclasses.replace(load_settings(), output_dir=args.output)
    if args.llm is not None:
        settings = dataclasses.replace(settings, llm_enabled=args.llm)
    return settings


def _execute(args: argparse.Namespace, settings: Settings) -> int:
    """Roda uma vez (ou em laço, com `--watch`); falha de banco ou de disco é falha de infraestrutura."""
    db_path = args.db or str(Path(settings.output_dir) / DEFAULT_DB_FILENAME)
    try:
        deps = build_deps(settings, db_path)
        if args.watch:
            watch(args.input, args.interval, deps, Event())
        else:
            run_batch(args.input, deps)
    except (StorageError, OSError) as error:
        logger.error("Falha de infraestrutura; a execução não foi concluída (%s)", type(error).__name__)
        return EXIT_INFRASTRUCTURE_FAILURE
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Valida os argumentos, executa o robô e devolve o código de saída (0 ok, 1 infraestrutura, 2 argumento)."""
    args = _build_parser().parse_args(argv)
    settings = _settings_from(args)
    configure_logging(settings)
    try:
        if not Path(args.input).is_dir():
            logger.error("Pasta de entrada não encontrada: %s", args.input)
            return EXIT_INVALID_INPUT
        return _execute(args, settings)
    finally:
        shutdown_logging()


if __name__ == "__main__":
    sys.exit(main())
