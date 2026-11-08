# Templates de Preenchimento

Copie e preencha estes templates ao criar uma skill nova. Cada bloco corresponde a um arquivo da
estrutura. Placeholders entre `[colchetes]` — substitua todos. Para gerar o esqueleto automaticamente,
use `scripts/scaffold_skill.py`.

---

## Template: `SKILL.md` *(Camada 2 — denso, auto-suficiente)*

```markdown
---
name: [nome-em-kebab-case-sem-prefixo]
description: [O QUE faz, em 1 frase] + [QUANDO usar / gatilhos: "Use ao…", "ao mencionar…"]. [SE sob demanda: "Use APENAS quando o usuário solicitar explicitamente. NÃO acione proativamente."]
---

# Skill: [Nome Descritivo]

[1–2 linhas: o que a skill faz e o que a diferencia.]

> Padrões globais em `padrao-escrita`; estrutura/contratos de módulo no catálogo `04-regras.md` do template. Referencie, não duplique.

## Quando usar
- [Situação específica que dispara o uso]
- [Como é acionada: proativa ao detectar X / sob demanda / por command]

## Workflow
Trate **um [item] por vez**.

1. **[Passo]** — [ação acionável: ferramenta + ação + output/critério].
2. **[Passo]** — [ação]. _(detalhe com antes/depois em `references/workflow.md`)_
3. **[Passo HITL]** — antes de qualquer alteração, apresente o Plano de Execução e aguarde confirmação.
N. **[Passo final]** — [ação].

## Regras e limites
- **NÃO** [proibição] — [justificativa curta].
- **NUNCA** [proibição] — [justificativa].
- **NÃO** saia do escopo: se detectar problema do tipo [X], registre e passe para `[skill]`.
[5–10 itens]

## Checklist "pronta"
- [ ] [Item verificável sim/não]
- [ ] A `description` tem o quê + quando/gatilhos (+ trava, se sob demanda)?
- [ ] [Item verificável]

## Referências (Camada 3 — leia sob demanda)
- `references/workflow.md` — workflow detalhado com antes/depois.
- `references/templates.md` — templates de preenchimento. *(se houver)*
- `references/examples.md` — exemplo bom e ruim. *(se houver)*
- `scripts/[nome].[ext]` — [o que automatiza]. *(se houver)*
```

**Exemplos de `description`:**
- Proativa: `Refatora para Clean Code (SRP, guard clauses). Use ao escrever ou revisar código com funções longas, nomes ruins ou lógica aninhada.`
- Sob demanda: `Otimização de performance custo zero. Use APENAS quando o usuário pedir otimização explicitamente. NÃO acione proativamente.`

---

## Template: `references/workflow.md` *(Camada 3 — detalhamento)*

```markdown
# Workflow Detalhado: [Nome da Skill]

Versão expandida do workflow do `SKILL.md`. Leia quando precisar do detalhe de um passo.
Trate **um [item] por vez**.

## Passo 1: [Nome]
**Objetivo:** [o que alcança]
1. [Ação atômica com ferramenta declarada]
2. [O que fazer com o resultado]

**O que detectar:**
- [Sintoma 1]

**Como corrigir:**
1. [Ação concreta]

**Antes:**
\`\`\`[linguagem]
[código com o problema]
\`\`\`

**Depois:**
\`\`\`[linguagem]
[código corrigido]
\`\`\`

## Passo N: Registro (opcional)
Só se houver sistema de registro/GSD ativo. Caso não exista, omita.
```

---

## Template: `references/examples.md` *(Camada 3)*

```markdown
# Exemplos: [Nome da Skill]

## Exemplo bom

### Cenário
[Contexto: sistema, problema, arquivo em foco]

### Antes (com problema)
[código/estrutura/documento]
**Problemas:**
- ⚠️ [problema 1]

### Depois (após a skill)
[resultado corrigido]
**Correções aplicadas:**
- [categoria] [descrição]

---

## Exemplo ruim

### Estado incorreto
[código/estrutura/decisão errada]

**Por que é ruim:**
| Problema | Impacto |
|----------|---------|
| [violação] | [por que prejudica] |
```

---

## Template: `scripts/[nome].[ext]` *(condicional — automação determinística na linguagem do repositório)*

> **Nota:** Molde o script para a linguagem principal do repositório. O exemplo abaixo está em Python, mas converta para TypeScript, Go, etc. conforme a necessidade do projeto alvo.

```python
"""
[Nome do script] — [o que faz em uma frase].

Uso:
    python [nome].py [args]

Retorno:
    [o que imprime/gera — ex.: lista de ocorrências em JSON]

Regras (padrao-escrita): zero hardcoded, zero segredos, responsabilidade única.
Valores configuráveis vêm de argumentos ou de config.json — nunca embutidos.
"""
import argparse
import json
from pathlib import Path


def load_config(config_path: str) -> dict:
    """Lê parâmetros externos (padrões, limites, caminhos). Nada hardcoded."""
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def execute(target: Path, config: dict) -> list:
    """Faz UMA coisa. Retorna estrutura clara para o agente consumir."""
    results = []
    # ... lógica determinística ...
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="[descrição]")
    parser.add_argument("target", help="Caminho do arquivo/pasta a processar")
    parser.add_argument("--config", default="config.json", help="Caminho do config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    results = execute(Path(args.target), config)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```
