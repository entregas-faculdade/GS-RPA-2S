---
name: meta-create-skill
description: Padrão oficial para criar e revisar skills do ecossistema Sarak — estrutura em 3 camadas, description (o gatilho), workflow, regras e checklist. Use APENAS quando pedirem para criar, padronizar ou revisar uma skill. NÃO acione proativamente.
---

# Skill: Criar Skills

Skill-base de **meta-criação**: define como toda skill Sarak é construída — estrutura, densidade,
a `description` que dispara a skill, regras e validação. É a fonte de verdade do padrão.

> Padrões globais de código (clean code, zero hardcoded, segredos no `.env`) vivem em `padrao-escrita`.
> Estrutura/nomenclatura/contratos de **módulo** vivem no catálogo `04-regras.md` do template (mapa de qual
> lei responde a quê em `padrao-escrita/references/PADRAO-ORGANIZACAO.md`). **Referencie, nunca duplique.**

## Quando usar
- Ao criar uma skill nova do zero.
- Ao padronizar/revisar uma skill existente que pareça incompleta ou ambígua.
- Ao decidir se uma skill está pronta para uso.
- Acionada **sob demanda** (o usuário pede). Não dispara sozinha.

## Modelo de 3 camadas (progressive disclosure)

Toda skill é organizada para o agente ler o mínimo necessário:

| Camada | Conteúdo | Carrega | Regra |
|---|---|---|---|
| 1 — Gatilho | `name` + `description` | sempre | enxuto |
| 2 — Operação | corpo do `SKILL.md` | quando dispara | **denso e auto-suficiente** (~40–80 linhas) |
| 3 — Profundidade | `references/`, `scripts/`, `assets/` | sob demanda, via ponteiro | só o verboso/raro |

**Regra de ouro:** o `SKILL.md` resolve ~90% das execuções sozinho. A Camada 3 é mergulho opcional.

## Estrutura-padrão de toda skill

```
<prefixo>-<nome>/          # kebab-case com prefixo de área (code-review, nunca skill-review)
├── SKILL.md               # Camada 2 — denso, auto-suficiente
├── references/            # Camada 3 — completos, lidos sob demanda (CONDICIONAL)
│   ├── workflow.md        # passos detalhados com antes/depois
│   ├── templates.md       # templates de preenchimento (só se produz output)
│   └── examples.md        # exemplo bom + exemplo ruim
├── scripts/               # automação determinística na linguagem do repositório (CONDICIONAL)
│   └── *.<ext>
└── assets/                # binários / boilerplate copiável (CONDICIONAL)
```

`references/`, `scripts/` e `assets/` são condicionais: crie **só** quando houver conteúdo. Sem pastas
vazias. Todo arquivo de Camada 3 precisa de um ponteiro correspondente no `SKILL.md`.

**Dependências Mútuas:** Se a skill construir sobre convenções de outra (ex: `code-adequacao` requer `padrao-escrita`), **declare no topo do corpo (`SKILL.md`)**: `> **Dependência:** Esta skill aplica as regras definidas em <nome-da-skill>. Consulte-a antes de iniciar.`

## Convenção de nomes (prefixo por área)

O `name` (= nome da pasta) é `<prefixo>-<resto>`, kebab-case, com um **prefixo de área** de um
vocabulário **fechado** — ele agrupa as skills no `ls` e revela o papel de cada uma. O vocabulário
completo, com exemplos, é `references/nomenclatura.md` (Camada 3) — fonte única; não duplique a
tabela aqui. **Proibido** o prefixo redundante `skill-` (não agrupa nada). O `scaffold_skill.py`
valida prefixo + kebab-case no momento da criação.

## Como escrever a `description` *(decide se a skill dispara)*

É o campo mais importante: sem ela boa, a skill nunca aciona. Fórmula:

```
<O QUE faz, 1 frase> + <QUANDO / gatilhos: "Use ao…"> + [<trava, se sob demanda>]
```

- **Proativa** → linguagem de detecção: `Use ao escrever/revisar código quando detectar <sintoma>.`
- **Sob demanda** → termine com: `Use APENAS quando o usuário solicitar explicitamente. NÃO acione proativamente.`

**Tamanho (a `description` é Camada 1 — SEMPRE carregada):** ≤ ~2 frases. Lidere com **o quê + quando**;
**não** despeje a lista de features/sub-domínios (isso é Camada 2, no corpo). No máximo **1 oração** de desambiguação.

**Trava ≠ desambiguação** (são coisas diferentes e coexistem):
- **Trava** = o gatilho de disparo. Sob demanda → `NÃO acione proativamente`; proativa → **sem** trava. É **obrigatória** (toda sob-demanda termina com a trava).
- **Desambiguação** = uma oração curta opcional separando de skill irmã (`≠ Z` / "histórico é da Y"). **Não** substitui a trava.

Detalhamento e exemplos antes/depois em `references/workflow.md` (Passo 2).

## Workflow

Trate **uma skill por vez**. Cada passo é acionável; o detalhe verboso está em `references/workflow.md`.

1. **Definir escopo** — responda por escrito: que problema resolve (1 frase, sem "e"); já existe similar (≥70% → expanda a existente); qual o gatilho; como é acionada (proativa / sob demanda / command).
2. **Escrever a `description`** — aplique a fórmula acima. _(detalhe em `references/workflow.md`)_
3. **Criar a estrutura** — pasta = `name` em kebab-case com **prefixo de área** (`padrao-`/`code-`/`deploy-`/`meta-`; ver "Convenção de nomes"). Use `scripts/scaffold_skill.py <nome>` para gerar o esqueleto (ele valida o prefixo). Crie `references/`/`scripts/`/`assets/` só se houver conteúdo.
4. **Escrever o `SKILL.md` denso** — seções: o que é, quando usar, workflow acionável, regras, checklist, ponteiros. Cada passo declara **ferramenta + ação + output/critério** ("analise o código" é proibido). ~40–80 linhas.
5. **Passo HITL** — se a skill modifica algo, inclua no workflow dela um passo de confirmação (Plano de Execução: o quê / por quê / como / expectativa → "⚠️ Confirma?") antes da 1ª ação mutativa.
6. **Preencher Camada 3** *(condicional)* — `references/workflow.md` (antes/depois), `templates.md` (se produz output), `examples.md`. Cada um com ponteiro no `SKILL.md`.
7. **Criar script** *(condicional)* — **criados obrigatoriamente na linguagem principal do repositório atual**. Só para tarefa determinística (mesma entrada→mesma saída). Tarefa que exige julgamento fica nas instruções. _(critérios e template em `references/workflow.md` e `templates.md`)_
8. **Validar** — passe o checklist abaixo na skill nova antes de considerá-la pronta.

## Regras e limites

- **NÃO** crie skill sem checar similares — sobreposição ≥70% fragmenta o sistema; expanda a existente.
- **NÃO** crie skill que faz mais de uma coisa — se a definição precisa de "e", divida.
- **NÃO** escreva passos vagos ("analise", "melhore onde necessário") — declare ferramenta, ação e critério.
- **NUNCA** escreva `description` sem gatilho — "Especialista em X" é título, não dispara. Sempre o quê + quando (+ trava se sob demanda).
- **NÃO** use o prefixo redundante `skill-` nem outro case no nome — kebab-case com **prefixo de área** (`padrao-`/`code-`/`deploy-`/`meta-`), igual à pasta.
- **NÃO** deixe o `SKILL.md` virar roteador vazio nem inchar — denso e auto-suficiente; verboso vai para Camada 3.
- **NÃO** crie arquivo de Camada 3 sem ponteiro no `SKILL.md`, nem `templates.md` vazio quando não há output.
- **NÃO** assuma que o modelo conhece o padrão base de outra skill (ex: padrao-escrita); declare dependências explicitamente no topo do corpo da skill com `> **Dependência:**`.
- **NÃO** invoque comandos genéricos locais de sistema (`pytest`, `eslint`, `bandit`, `flake8`) que exijam instalação no repositório-alvo do cliente. Oriente a IA a buscar os caminhos absolutos das ferramentas na Tabela de Roteamento (ex: `<SARAK_PYTHON_VENV> -m pytest` e `<SARAK_NODE_BIN>/eslint`).
- **NÃO** faça hardcoded/segredos em scripts, nem script para tarefa que exige julgamento (`padrao-escrita`).
- **NÃO** referencie skills inexistentes (ex.: sistema de registro/GSD) — o passo de Registro é opcional.

## Checklist "pronta"

- [ ] Responsabilidade única (definível em 1 frase sem "e") e sem sobreposição ≥70% com skill existente?
- [ ] `name` em kebab-case com prefixo de área válido (`padrao-`/`code-`/`deploy-`/`meta-`), igual ao nome da pasta?
- [ ] A `description` tem **o quê + quando/gatilhos** + a **trava** correta (sob-demanda termina com `NÃO acione proativamente`)?
- [ ] A `description` é **enxuta** (≤ ~2 frases, sem despejar lista de features) e a desambiguação (se houver) é **separada** da trava?
- [ ] O `SKILL.md` é auto-suficiente para o caminho comum (não força abrir Camada 3 para o básico)?
- [ ] Cada passo do workflow é acionável (ferramenta + ação + output/critério)?
- [ ] Há passo HITL antes de qualquer ação mutativa (se a skill modifica algo)?
- [ ] As regras começam com NÃO/NUNCA, têm justificativa e incluem ao menos 1 item de escopo?
- [ ] As dependências cruzadas (ex: uso do padrao-escrita) estão declaradas explicitamente no topo do SKILL.md?
- [ ] Cada arquivo de `references/`/`scripts/` tem ponteiro no `SKILL.md` e nenhum ponteiro é órfão?
- [ ] Scripts (se houver) foram escritos na **linguagem do repositório**, sem hardcoded/segredos, com responsabilidade única e saída clara?

## Referências (Camada 3 — leia sob demanda)

- `references/nomenclatura.md` — o vocabulário fechado de prefixos de área, com exemplos. Fonte
  única (o `README.md` da raiz da base aponta para cá também).
- `references/workflow.md` — workflow detalhado: cada passo com sintomas, ação e exemplos antes/depois.
- `references/templates.md` — templates copiáveis de `SKILL.md`, `workflow.md`, `examples.md` e script.
- `references/examples.md` — exemplo de skill boa vs. skill vaga, com análise de impacto.
- `scripts/scaffold_skill.py` — gera o esqueleto de uma skill nova a partir do nome.
