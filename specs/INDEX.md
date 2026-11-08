# 🧭 Mapa de Especificações: GS RPA 2S

> **Atenção IAs:** Este diretório é a fonte da verdade do projeto. **Comece por `00-contexto.md`** — nenhuma
> tarefa começa antes dele.

## Ordem de leitura

| # | Arquivo | O que é |
|---|---|---|
| 0 | `panorama/00-resumo.md` | **Para o humano:** o estado do projeto de relance (gerado). O agente começa pelo `00-contexto`. |
| 1 | **`00-contexto.md`** | O que este repositório é, regras inegociáveis e o mapa "que spec eu leio para esta tarefa?" |
| 2 | **`00-knowledge.md`** | Roteador de capacidades: situação → skill/command/agent/hook. Universal. |
| 3 | **`00-indice.md`** | Fila de execução das plans, com dependências e status. |
| 4 | **`00-prompt-revisor.md`** / **`00-prompt-executor.md`** | O prompt do seu papel. Leia o seu, conheça o outro. |
| 5 | `arquitetura/` → `specs/` → `adr/` | O detalhe: o COMO, o QUÊ e o POR QUÊ. |

## Estrutura do Vault

- 📄 **`00-*.md`**: as specs de processo — contexto, roteamento de capacidades, índice de execução, backlog de
  achados e os prompts dos dois papéis. São a entrada de qualquer agente.
- 📁 **`arquitetura/`**: design vivo e regras globais (O COMO).
- 📁 **`specs/`**: specs vivas de funcionalidades (O QUÊ).
- 📁 **`adr/`**: decisões imutáveis (O POR QUÊ). Decisão nova = ADR novo.
- 📁 **`plan/`**: as plans **abertas** (`plan-FF.NN-<slug>.md`). Não há subpasta: o `status` do frontmatter diz
  se a plan está na fila (🔴 🟡 🟠 🔵 ⛔) ou aprovada aguardando o commit do veredito e a síntese (🟢). **A plan é
  temporária** — no ato da síntese o revisor a remove junto com a linha do índice, e o rastro passa a viver
  no histórico do Git.
- 📁 **`panorama/`**: o planejamento e o panorama. `00-planejamento.md` traz o **catálogo de famílias** (§1),
  fonte única do `FF` que numera specs (`FF.NN-<slug>.md`) e plans (`plan-FF.NN-<slug>.md`), e o
  **horizonte** de itens (§2); `00-resumo.md` é o estado de relance, **gerado** pela skill `spec-panorama`.
- 📁 **`_templates/`**: moldes (`template-spec`, `template-arquitetura`, `template-operacao`, `template-adr`, `template-plan`).

## O ciclo em uma linha

**Com plan** (a demanda deixa verdade): `revisor escreve plan` → `executor executa (worktree, sem commit)` →
`revisor verifica e aprova` → `usuário commita o veredito` → `revisor sintetiza nas specs fixas **e remove a plan**` →
`usuário roda o comando completo`

**Via direta** (não deixa): `revisor emite o prompt` → `executor executa (worktree, sem commit)` →
`revisor verifica e aprova` → `usuário commita`. Nenhum arquivo nasce; sem síntese.

Detalhe em [`README.md`](README.md).
