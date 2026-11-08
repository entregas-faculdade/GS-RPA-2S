---
tipo: "processo"
titulo: "Planejamento — Famílias e Horizonte"
dominio: "Governança de Specs (SDD)"
status: "🟢 Vigente"
tags: ["processo", "planejamento", "familias", "sdd"]
relacionados: ["[[00-contexto]]", "[[00-indice]]", "[[00-prompt-revisor]]"]
---

# 0. O que é este arquivo

O **catálogo de famílias** do projeto: a **fonte única** dos grupos de assunto que numeram as specs fixas
(`specs/`, `arquitetura/`) e as plans. Nenhum outro arquivo lista as famílias — todos apontam para cá. Na §2,
o **horizonte**: a evolução de longo prazo, em itens por família — a base do progresso do `00-resumo.md`.

**Quem escreve/atualiza:** o **agente revisor** ([[00-prompt-revisor]]), e cada família nova só depois da
**aprovação do usuário**.

---

# 1. Famílias

> **Como escrever:**
> - **Família** = número de dois dígitos `FF` + nome. Agrupa por **assunto** (ex.: `01` Conexão, `02` Base de
>   dados), não por pasta nem por tipo de arquivo.
> - **`00` é reservada à fundação.** Seus nomes chegam fixos e **não são renomeados** para `FF.NN`:
>   - os arquivos de processo `00-*.md` (este inclusive);
>   - em projeto modular, a lei do template em `arquitetura/`: `00-arquitetura.md`, `01-modulo.md`,
>     `02-contrato-e-dados.md`, `03-operacao.md`, `04-regras.md` e `00-base-<binding>.md` — cobrados pelo gate;
>   - `arquitetura/00-fundacao-tecnologica.md`, gerada pela skill `spec-fundacao` na abertura do repositório.
>
>   **Esta é a única lista desses nomes** — os outros arquivos apontam para cá.
> - **`specs/` e `arquitetura/`**: `FF.NN-<slug>.md`, zero à esquerda nos dois números, mais `familia: "FF"` no
>   frontmatter. O par `FF.NN` é **único na família somando as duas pastas**; o próximo `NN` livre sai da
>   varredura das duas.
> - **Plans**: `plan-FF.NN-<slug>.md` + `familia: "FF"`. Contador **por família**, monotônico e definitivo, no
>   mapa `proximo_numero_plan` do [[00-indice]]; família sem entrada começa em `01`. Namespace separado do das
>   specs: `plan-02.03` e `specs/02.03-*.md` não têm relação.
> - **ADR não tem família**: `adr/NNN-<slug>.md`, cronológico.
> - **Família nova**: o revisor propõe, o **usuário aprova**, e só então ela entra nesta tabela — e só então é
>   usada. Spec ou plan com família fora daqui é defeito.
> - Uma linha por família, escopo em **uma** linha. Família não se renumera nem se reaproveita.

| FF | Família | Escopo (uma linha) |
|---|---|---|
| 00 | Fundação | processo SDD, lei do template e fundação tecnológica — reservada |

---

# 2. Horizonte

> **Como escrever:** o **longo prazo**, em tópicos por família — o que ainda vai virar plan ou spec. A unidade
> de progresso é o **item**, não a plan: a plan some na síntese, o item fica.
>
> - **Um título por família**, com o número e o nome do catálogo: `## 02 · Base de dados`.
> - **Um item por linha**, neste formato fixo, que a skill `spec-panorama` lê:
>   `- ⬜ **R02.3** Índices de busca — uma frase opcional`. Concluído pode levar a data no fim: `(✅ AAAA-MM-DD)`.
> - **ID** `R<FF>.<n>`: `FF` é a família do catálogo; `n` é sequencial dentro da família, sem zero à esquerda,
>   e **nunca** reaproveitado.
> - **Estado:** `⬜` planejado · `🔷` em andamento (ao menos uma plan aberta com `item:` apontando para ele) ·
>   `✅` concluído (a última plan dele foi sintetizada).
> - **Ligação:** a plan aponta para o item pelo campo opcional `item: "R02.3"` do frontmatter. Plan sem item
>   (bug, conformidade) é normal e não entra na % de progresso.
> - **Quem mexe:** só o revisor. Primeira plan de um item → `🔷`; síntese da última plan do item → `✅`, **na
>   mesma ação** em que a plan é removida. O **usuário** decide o que entra no horizonte; o revisor escreve.
> - **Não é backlog:** o [[00-backlog]] guarda *achados* (problemas notados); este horizonte guarda *evolução
>   pretendida*. Um achado que o usuário promove a evolução de longo prazo pode virar item.

<!-- Exemplo (comentado: não conta como item real)
## 02 · Base de dados
- ✅ **R02.1** Schema inicial — tabelas do domínio de pedidos (✅ 2026-10-09)
- 🔷 **R02.2** Índices de busca — há uma plan aberta com item: "R02.2"
- ⬜ **R02.3** Particionamento por mês
-->
