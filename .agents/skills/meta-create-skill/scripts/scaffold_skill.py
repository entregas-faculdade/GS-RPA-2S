"""
scaffold_skill.py — gera o esqueleto determinístico de uma skill nova no padrão de 3 camadas.

Uso:
    python scaffold_skill.py <skill-name> [--dir <destino>] [--with-script]

Argumentos:
    skill-name      Nome da skill em kebab-case com prefixo de área (ex.: code-review).
    --dir           Diretório onde a pasta da skill será criada. Padrão: diretório atual.
    --with-script   Também cria scripts/<skill-name>.py (stub). Por padrão scripts/ não é criado.

Retorno:
    Imprime um JSON com {"skill": <nome>, "path": <caminho>, "created": [arquivos criados]}.
    Sai com código != 0 (e mensagem em stderr) se o nome for inválido ou a pasta já existir.

Regras (padrao-escrita): zero hardcoded (nome e destino vêm de argumentos), zero segredos,
responsabilidade única (só gera estrutura — não valida conteúdo nem escreve lógica de skill).
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Padrão de nome exigido pela skill meta-create-skill: kebab-case com prefixo de área.
# Vocabulário FECHADO de prefixos — fonte única em references/nomenclatura.md (Camada 3 desta
# skill). Mantenha esta tupla em sincronia com aquele arquivo; amplie os dois quando a área ganhar
# tração. (Achado ao escrever nomenclatura.md: esta tupla tinha 'api-', que nenhuma skill usa mais
# — a skill que a exemplificava é hoje 'test-api-contrato' — e não tinha 'spec-', que 4 skills usam.)
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_PREFIX = "skill-"
VALID_PREFIXES = (
    "padrao-",
    "code-",
    "spec-",
    "test-",
    "db-",
    "deploy-",
    "docker-",
    "otimizacao-",
    "obs-",
    "site-",
    "git-",
    "cyber-",
    "maquina-",
    "meta-",
)


def validate_name(name: str) -> None:
    """Garante kebab-case com prefixo de área válido. Levanta ValueError com a razão se inválido."""
    if not NAME_PATTERN.match(name):
        raise ValueError(
            f"invalid name: '{name}'. Use lowercase kebab-case "
            f"(e.g. 'code-review') — no uppercase, spaces or underscores."
        )
    if name.startswith(FORBIDDEN_PREFIX):
        raise ValueError(
            f"invalid name: '{name}'. Do not use the redundant prefix '{FORBIDDEN_PREFIX}' "
            f"— choose an area prefix: {', '.join(VALID_PREFIXES)}."
        )
    if not name.startswith(VALID_PREFIXES):
        raise ValueError(
            f"invalid name: '{name}'. Missing a valid area prefix "
            f"({', '.join(VALID_PREFIXES)}) — e.g. 'code-review'."
        )


def skill_md_content(name: str) -> str:
    """Stub do SKILL.md denso (Camada 2) com as seções-padrão e placeholders."""
    return f"""---
name: {name}
description: [O QUE faz, 1 frase] + [QUANDO/gatilhos: "Use ao…"]. [SE sob demanda: "Use APENAS quando o usuário solicitar explicitamente. NÃO acione proativamente."]
---

# Skill: [Nome Descritivo]

[1–2 linhas: o que a skill faz e o que a diferencia.]

> Padrões globais em `padrao-escrita`; estrutura/contratos de módulo no catálogo `04-regras.md` do template. Referencie, não duplique.

## Quando usar
- [Situação que dispara o uso]
- [Como é acionada: proativa ao detectar X / sob demanda / por command]

## Workflow
Trate **um [item] por vez**.

1. **[Passo]** — [ferramenta + ação + output/critério].
2. **[Passo]** — [ação]. _(detalhe em `references/workflow.md`)_
3. **[Passo HITL]** — se modifica algo, apresente o Plano de Execução e aguarde confirmação.

## Regras e limites
- **NÃO** [proibição] — [justificativa].
- **NUNCA** [proibição] — [justificativa].
- **NÃO** saia do escopo: ao detectar problema do tipo [X], registre e passe para `[skill]`.

## Checklist "pronta"
- [ ] A `description` tem o quê + quando/gatilhos (+ trava, se sob demanda)?
- [ ] Cada passo é acionável (ferramenta + ação + critério)?
- [ ] [Item verificável]

## Referências (Camada 3 — leia sob demanda)
- `references/workflow.md` — workflow detalhado com antes/depois.
- `references/templates.md` — templates de preenchimento. *(remova se não houver)*
- `references/examples.md` — exemplo bom e ruim. *(remova se não houver)*
"""


def workflow_md_content(name: str) -> str:
    return f"""# Workflow Detalhado: {name}

Versão expandida do workflow do `SKILL.md`. Leia quando precisar do detalhe de um passo.
Trate **um [item] por vez**.

## Passo 1: [Nome]
**Objetivo:** [o que alcança]
1. [Ação atômica com ferramenta declarada]

**O que detectar:**
- [Sintoma]

**Como corrigir:**
1. [Ação concreta]

**Antes:**
```
[estado com problema]
```

**Depois:**
```
[estado corrigido]
```
"""


def templates_md_content(name: str) -> str:
    return f"""# Templates de Preenchimento: {name}

[Blocos copiáveis dos outputs que esta skill produz. Placeholders em [colchetes].
Remova este arquivo (e seu ponteiro no SKILL.md) se a skill não produz output.]
"""


def examples_md_content(name: str) -> str:
    return f"""# Exemplos: {name}

## Exemplo bom
### Cenário
[contexto]
### Antes
[com problema]
### Depois
[corrigido]

## Exemplo ruim
### Estado incorreto
[errado]
**Por que é ruim:**
| Problema | Impacto |
|----------|---------|
| [violação] | [impacto] |
"""


def script_stub_content(name: str) -> str:
    return f'''"""
{name}.py — [o que faz em uma frase].

Uso:
    python {name}.py <target> [--config config.json]

Retorno:
    [o que imprime/gera].

Regras (padrao-escrita): zero hardcoded, zero segredos, responsabilidade única.
"""
import argparse
import json
from pathlib import Path


def execute(target: Path) -> list:
    """Faz UMA coisa. Retorna estrutura clara para o agente consumir."""
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="[descrição]")
    parser.add_argument("target", help="Caminho a processar")
    args = parser.parse_args()
    print(json.dumps(execute(Path(args.target)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
'''


def create_skill(name: str, dest_dir: Path, with_script: bool) -> dict:
    """Cria a estrutura da skill. Levanta FileExistsError se a pasta-alvo já existir."""
    root = dest_dir / name
    if root.exists():
        raise FileExistsError(f"the folder already exists: {root}")

    files = {
        root / "SKILL.md": skill_md_content(name),
        root / "references" / "workflow.md": workflow_md_content(name),
        root / "references" / "templates.md": templates_md_content(name),
        root / "references" / "examples.md": examples_md_content(name),
    }
    if with_script:
        files[root / "scripts" / f"{name}.py"] = script_stub_content(name)

    created = []
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(str(path))

    return {"skill": name, "path": str(root), "created": created}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generates the skeleton of a new skill in the 3-layer pattern."
    )
    parser.add_argument(
        "skill_name", help="Name in kebab-case with an area prefix (e.g. code-review)"
    )
    parser.add_argument(
        "--dir", default=".", help="Destination directory (default: current)"
    )
    parser.add_argument(
        "--with-script",
        action="store_true",
        help="Also creates scripts/<name>.py (stub)",
    )
    args = parser.parse_args()

    try:
        validate_name(args.skill_name)
        result = create_skill(args.skill_name, Path(args.dir), args.with_script)
    except (ValueError, FileExistsError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
