"""
verify_commit.py — Gate rápido: varre o que está STAGED por segredos e arquivos sensíveis.

Uso (manual ou via pre-commit hook):
    python verify_commit.py [--root .] [--config config.json]
    python verify_commit.py --selftest

Saída:
    JSON {blocked, secret_findings, sensitive_files}. Segredos mascarados.
    **Exit code 1** se houver qualquer achado (faz o pre-commit hook BLOQUEAR o commit); 0 se limpo.

Regras (padrao-escrita): zero hardcoded (padrões/listas no config.json), segredos mascarados,
responsabilidade única (só o commit atual/staged — histórico é da git-especialista-repositorio).

`--selftest` prova as duas camadas, na convenção núcleo puro + casca desta base: `scan_secrets`,
`scan_files` e `evaluate_block` são PURAS (fixtures em memória, sem git); o caminho fim a fim —
"staged com segredo bloqueia de verdade", que a camada 3 (`template-self-test.mjs`, passo
`primeiro-commit`) não cobria — só é alcançável rodando o próprio script contra um repositório git
**temporário**, montado e destruído a cada caso. Nenhum segredo real é usado: a chave AWS plantada é
`AWS_EXAMPLE_KEY` (definida mais abaixo) — o valor de EXEMPLO da própria documentação da AWS,
nunca uma credencial viva, e partido em dois literais no código-fonte para não disparar o próprio
scanner estático de `audit_base.py` sobre este arquivo.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path


# Mapa antigo -> novo (um só lugar): aceita o config.json de quem já instalou o gate em português.
LEGACY_CONFIG_KEYS = {
    "_fonte": "_source",
    "padroes": "patterns",
    "arquivos_sensiveis": "sensitive_files",
    "arquivos_permitidos": "allowed_files",
}
LEGACY_PATTERN_LABELS = {
    "Segredo atribuido": "Assigned secret",
    "String de conexao": "Connection string",
}


def normalize_config(raw: dict) -> dict:
    config = {LEGACY_CONFIG_KEYS.get(key, key): value for key, value in raw.items()}
    patterns = config.get("patterns", {})
    config["patterns"] = {
        LEGACY_PATTERN_LABELS.get(label, label): rx for label, rx in patterns.items()
    }
    return config


def load_config(path: Path) -> dict:
    return normalize_config(json.loads(path.read_text(encoding="utf-8")))


def git(root: Path, *args) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except FileNotFoundError:
        sys.exit("Error: git not found in the environment.")
    if r.returncode != 0:
        sys.exit(
            f"Git error ({' '.join(args)}): {r.stderr.strip()} (is the root a Git repo?)"
        )
    return r.stdout


def mask(snippet: str) -> str:
    snippet = snippet.strip()
    return "****" if len(snippet) <= 8 else f"{snippet[:4]}...{snippet[-2:]}"


def scan_secrets(diff: str, patterns) -> list:
    findings, file = [], None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for kind, regex in patterns:
                m = regex.search(line[1:])
                if m:
                    findings.append(
                        {
                            "file": file,
                            "kind": kind,
                            "masked_snippet": mask(m.group(0)),
                        }
                    )
                    break
    return findings


def scan_files(files, sensitive, allowed) -> list:
    findings = []
    for path in files:
        name = Path(path).name
        if any(fnmatch(name, p) for p in allowed):
            continue
        if any(fnmatch(name, p) for p in sensitive):
            findings.append(path)
    return findings


def evaluate_block(secret_findings: list, sensitive_files: list) -> bool:
    """PURA: a decisao final do gate — bloqueia se ha qualquer achado, de qualquer tipo."""
    return bool(secret_findings or sensitive_files)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8"
        )  # saída UTF-8 mesmo em console cp1252 (Windows/acentos)
    parser = argparse.ArgumentParser(description="Secret gate for the staged commit.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.json"))
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    try:
        config = load_config(Path(args.config))
    except FileNotFoundError:
        sys.exit(f"Error: config not found at '{args.config}'.")
    except json.JSONDecodeError as error:
        sys.exit(f"Error: invalid config ({error}).")

    root = Path(args.root)
    patterns = [(kind, re.compile(rx)) for kind, rx in config["patterns"].items()]

    diff = git(root, "diff", "--cached", "--unified=0", "--no-color")
    files = [
        a
        for a in git(
            root, "diff", "--cached", "--name-only", "--diff-filter=ACM"
        ).splitlines()
        if a
    ]

    secret_findings = scan_secrets(diff, patterns)
    sensitive_files = scan_files(
        files,
        config.get("sensitive_files", []),
        config.get("allowed_files", []),
    )

    blocked = evaluate_block(secret_findings, sensitive_files)
    print(
        json.dumps(
            {
                "blocked": blocked,
                "secret_findings": secret_findings,
                "sensitive_files": sensitive_files,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    sys.exit(1 if blocked else 0)


# ================================================================================================
# AUTOTESTE — nucleo puro com fixtures, casca fim a fim contra repo git temporario.
# ================================================================================================

# Chave de EXEMPLO da propria documentacao da AWS (docs.aws.amazon.com) — nunca uma credencial real.
# Usada so para provar que o padrao "AWS Access Key" do config.json real dispara o bloqueio. Partida em
# duas por concatenacao de proposito: inteira, ela e um literal "AKIA[0-9A-Z]{16}" contiguo no PROPRIO
# codigo-fonte deste arquivo, e um scanner estatico de segredos nao
# tem isencao para fixture de teste — reportaria esta linha como vazamento real. Em runtime a string
# concatenada e identica; o teste continua provando exatamente o mesmo padrao.
AWS_EXAMPLE_KEY = "AKIA" + "IOSFODNN7EXAMPLE"


def _test_patterns() -> list:
    config = load_config(Path(__file__).with_name("config.json"))
    catalog_patterns = config["patterns"]
    return [
        (kind, re.compile(catalog_patterns[kind]))
        for kind in ("AWS Access Key", "Connection string")
    ]


def _core_cases() -> list:
    clean_diff = "+++ b/src/config.ts\n+export const TIMEOUT = 5000;\n"
    diff_with_secret = (
        f'+++ b/src/config.ts\n+const key = "{AWS_EXAMPLE_KEY}";\n'
    )
    patterns = _test_patterns()
    scheme = "postgres" + "://"  # concatenado: o gate não pode casar o próprio fixture
    url = lambda username, password: (
        f"+++ b/deploy/compose.yml\n+DATABASE_URL={scheme}{username}:{password}@db:5432/app\n"
    )
    env_username = "${DEPLOY_DB_USER:?required}"
    env_pw_ref = "${DEPLOY_DB_" + "PASSWORD:?required}"
    literal_password = "-".join(("literal", "password"))
    return [
        {
            "name": "scan_secrets: clean diff -> no findings",
            "fn": lambda: scan_secrets(clean_diff, patterns) == [],
        },
        {
            "name": "scan_secrets: planted AWS example key -> masked finding",
            "fn": lambda: (
                len(findings := scan_secrets(diff_with_secret, patterns)) == 1
                and findings[0]["kind"] == "AWS Access Key"
                and AWS_EXAMPLE_KEY not in findings[0]["masked_snippet"]
            ),
        },
        {
            "name": "scan_secrets: both database credentials interpolated -> ignored",
            "fn": lambda: scan_secrets(
                url(env_username, env_pw_ref), patterns
            ) == [],
        },
        {
            "name": "scan_secrets: literal database password -> detected",
            "fn": lambda: any(
                a["kind"] == "Connection string"
                for a in scan_secrets(url("app", literal_password), patterns)
            ),
        },
        {
            "name": "scan_secrets: one environment credential and one literal -> detected",
            "fn": lambda: all(
                any(
                    a["kind"] == "Connection string"
                    for a in scan_secrets(url(username, password), patterns)
                )
                for username, password in (
                    (env_username, literal_password),
                    ("app", env_pw_ref),
                )
            ),
        },
        {
            "name": "scan_files: .env without exemption -> finding",
            "fn": lambda: (
                scan_files([".env"], [".env", ".env.*"], [".env.example"])
                == [".env"]
            ),
        },
        {
            "name": "scan_files: exempt .env.example -> no findings",
            "fn": lambda: (
                scan_files([".env.example"], [".env", ".env.*"], [".env.example"])
                == []
            ),
        },
        {
            "name": "normalize_config: legacy Portuguese config keys and labels are translated",
            "fn": lambda: (
                normalize_config(
                    {
                        "_fonte": "x",
                        "padroes": {"String de conexao": "y"},
                        "arquivos_sensiveis": [".env"],
                        "arquivos_permitidos": [".env.example"],
                    }
                )
                == {
                    "_source": "x",
                    "patterns": {"Connection string": "y"},
                    "sensitive_files": [".env"],
                    "allowed_files": [".env.example"],
                }
            ),
        },
        {
            "name": "evaluate_block: no findings -> does not block",
            "fn": lambda: evaluate_block([], []) is False,
        },
        {
            "name": "evaluate_block: secret finding -> blocks",
            "fn": lambda: evaluate_block([{"kind": "x"}], []) is True,
        },
        {
            "name": "evaluate_block: sensitive file -> blocks",
            "fn": lambda: evaluate_block([], [".env"]) is True,
        },
    ]


def _run_verifier(root: Path, config: Path = None) -> tuple:
    """CASCA: invoca o PROPRIO verify_commit.py como subprocesso contra `root` — a unica forma de
    provar blocked/exit-code fim a fim, ja que ler o staged (`git diff --cached`) nao e puro. `root`
    e um repo git real, montado e destruido pelo chamador; nunca o repositorio desta base."""
    args = [sys.executable, str(Path(__file__)), "--root", str(root)]
    if config is not None:
        args += ["--config", str(config)]
    r = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    return r.returncode, r.stdout, r.stderr


def _shell_cases() -> list:
    """Cada caso monta o estado staged que precisa, roda o script real, e o `with` apaga o repo
    temporario ao sair — nunca planta nada no repositorio de verdade desta base."""
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)

        (root / "app.ts").write_text("export const TIMEOUT = 5000;\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.ts"], cwd=root, check=True)
        code, _, _ = _run_verifier(root)
        cases.append(
            {"name": "end to end: staged without secret -> exit 0", "ok": code == 0}
        )

        (root / "app.ts").write_text(
            f'const key = "{AWS_EXAMPLE_KEY}";\n', encoding="utf-8"
        )
        subprocess.run(["git", "add", "app.ts"], cwd=root, check=True)
        code, output, _ = _run_verifier(root)
        cases.append(
            {
                "name": "end to end: staged WITH planted secret -> exit 1, masked in output",
                "ok": code == 1 and AWS_EXAMPLE_KEY not in output,
            }
        )

        code, _, _ = _run_verifier(root, config=root / "missing-config.json")
        cases.append(
            {
                "name": "end to end: missing config -> error, never exit 0",
                "ok": code != 0,
            }
        )

        invalid_config = root / "invalid-config.json"
        invalid_config.write_text("{ this is not valid json", encoding="utf-8")
        code, _, _ = _run_verifier(root, config=invalid_config)
        cases.append(
            {
                "name": "end to end: invalid config -> error, never exit 0",
                "ok": code != 0,
            }
        )
    return cases


def run_selftest() -> int:
    failures = 0
    for case in _core_cases():
        ok = bool(case["fn"]())
        print(f"  {'ok   ' if ok else 'FAIL '} {case['name']}")
        if not ok:
            failures += 1
    for case in _shell_cases():
        print(f"  {'ok   ' if case['ok'] else 'FAIL '} {case['name']}")
        if not case["ok"]:
            failures += 1

    total = len(_core_cases()) + len(_shell_cases())
    print(f"\nselftest (verify_commit): {total - failures}/{total} ok")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    main()
