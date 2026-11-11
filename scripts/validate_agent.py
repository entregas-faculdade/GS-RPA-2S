"""Valida os arquivos do agente LLM: `python scripts/validate_agent.py [--agent <id>]`."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.agent import AGENTS_DIR, DEFAULT_AGENT_ID, lint_agent

EXIT_OK = 0
EXIT_ERRORS = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida os arquivos de um agente LLM (não altera nada).")
    parser.add_argument("--agent", default=DEFAULT_AGENT_ID, help="id do agente em data/agents/")
    parser.add_argument("--agents-dir", type=Path, default=AGENTS_DIR, help="pasta dos agentes")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Lista cada problema do agente e devolve o código de saída: 0 sem problema, 1 com problema."""
    args = _build_parser().parse_args(argv)
    problems = lint_agent(args.agent, args.agents_dir)
    lines = [f"ERRO  {problem}" for problem in problems]
    lines.append(f"agente '{args.agent}': {len(problems)} problema(s)." if problems else f"agente '{args.agent}': OK.")
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_ERRORS if problems else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
