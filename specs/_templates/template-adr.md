---
tipo: "adr"
titulo: "Título Curto e Direto (Ex: Escolha do PostgreSQL)"
status: "Proposto" # Opções: Proposto, 🟢 Aceito, Rejeitado, 🔴 Substituído
tags: ["adr"]
relacionados: [] # SÓ specs fixas e outros ADRs. NUNCA uma plan — ela some na síntese.
substitui: ""      # Ex: [[001-escolha-mysql]]
substituido_por: ""
alternativas_consideradas: # OBRIGATÓRIO, no mínimo 2 — ver o portão abaixo
  - "<alternativa real que foi descartada> — descartada porque <o custo dela>"
  - "<outra> — descartada porque <o custo dela>"
---

> ## 🚧 Portão: isto é mesmo um ADR?
>
> **Responda às três perguntas antes de criar o arquivo. Se qualquer uma for "não", não é ADR** — a verdade
> vai para `arquitetura/` ou `specs/`, ou não vai para lugar nenhum.
>
> 1. **Havia pelo menos duas opções reais?** Não hipotéticas — opções que alguém defenderia.
> 2. **A escolhida tem um custo que as outras não tinham?** Se ela era melhor em tudo, não houve decisão:
>    houve constatação.
> 3. **Voltar atrás depois seria caro?** Se trocar amanhã custa uma tarde, não precisa de registro imutável.
>
> O preenchimento de `alternativas_consideradas` é a **prova mecânica** disso: se você não consegue nomear
> duas alternativas reais com o custo de cada uma, não houve trade-off — e sem trade-off não há ADR.
>
> **Não é ADR:** escolher a biblioteca óbvia do ecossistema · seguir uma convenção que o projeto já adota ·
> corrigir um bug · refatorar sem mudar comportamento · qualquer coisa que uma spec fixa já implica ·
> "documentar para não esquecer" (isso é `arquitetura/` ou `specs/`).
>
> **ADR é o destino mais raro do ciclo.** A maioria das plans tem destino `—` ou uma spec fixa. Se os ADRs
> estão nascendo com frequência, o portão não está sendo aplicado.

> **Onde vive cada ADR.** `specs/adr/` é o **único** diretório de decisões do projeto:
>
> | Arquivo | O quê | Editável? |
> |---|---|---|
> | `000-decisoes-do-template.md` | ADR-001..007 — por que o template de módulos é como é | **Não.** Vem do template; mudar de ideia é ADR novo aqui |
> | `NNN-<nome>.md` | decisões deste projeto (stack, schema, idioma das pastas, fornecedor) | você escreve, usando este molde |
>
> **Exceção ao gate de módulos** (`config/compliance.json`) exige o campo `decisao` apontando para um ADR
> daqui — **sem esse link, o gate rejeita a própria exceção**. Escreva a decisão *antes* de registrar a
> exceção, nunca depois.

# 1. Contexto e Problema
Qual era a situação que nos forçou a tomar essa decisão?

# 2. Alternativas consideradas

As mesmas do frontmatter, agora com uma linha cada. **Duas, no mínimo, e reais.**

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| ... | ... | ... |
| ... | ... | ... |

# 3. Decisão
O que decidimos fazer de fato.

# 4. Consequências
- **Positivas:** ...
- **Negativas (Trade-offs):** o custo que aceitamos ao descartar as alternativas da §2. Se esta linha está
  vazia, releia o portão do topo: decisão sem custo não é decisão.
