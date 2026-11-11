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
| 01 | Núcleo do robô | estrutura do projeto, ingestão, sanitização e anonimização de PII (etapa 1) |
| 02 | Classificação | regex + TF-IDF, confiança e gatilhos de revisão humana (etapa 2) |
| 03 | Automação | catálogo, allowlist, verificação de links e resposta final com LLM opcional (etapa 3) |
| 04 | Operação e interface | persistência SQLite, orquestração RPA, relatório de execução e interface Streamlit |
| 05 | Validação e entrega | conjunto rotulado, métricas, evidências, README e quadro de temas |

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

## 01 · Núcleo do robô
- ✅ **R01.1** Estrutura do projeto — dependências, configuração, log e `run.py` mínimo (✅ 2026-11-09)
- ✅ **R01.2** Ingestão e sanitização — txt/csv/json tolerante a falhas (✅ 2026-11-09)
- ✅ **R01.3** Anonimização de PII — CPF, telefone e e-mail (✅ 2026-11-09)
- ✅ **R01.4** Anonimização ampliada — nome, endereço, CEP, RG, data e documentos (✅ 2026-11-10)

## 02 · Classificação
- ✅ **R02.1** Classificador — conjunto rotulado sintético, regex e TF-IDF (✅ 2026-11-09)
- ✅ **R02.2** Confiança e revisão humana — limiares e gatilhos (✅ 2026-11-09)
- ✅ **R02.3** Urgência de saúde — termos de emergência e "urgente" de cortesia (✅ 2026-11-10)
- ✅ **R02.4** Dataset ampliado e calibração — treino ≥ 40 por categoria e limiares por validação cruzada (✅ 2026-11-10)

## 03 · Automação
- ✅ **R03.1** Catálogo e allowlist — links oficiais verificados (✅ 2026-11-09)
- ✅ **R03.2** Resposta final — template com LLM opcional e fallback (✅ 2026-11-09)
- ✅ **R03.3** Catálogo v2 — vários links e telefones, esfera, aprovação e verificador (✅ 2026-11-10)
- ✅ **R03.4** Catálogo de São Paulo — fontes aprovadas de saúde, educação, veículos e prefeitura (✅ 2026-11-10)
- ✅ **R03.5** Localizador de serviços — busca determinística nas fontes aprovadas, com medição (✅ 2026-11-10)
- ✅ **R03.6** Resposta em degraus — serviço, canal geral, "não tenho a informação" e emergência (✅ 2026-11-10)
- ✅ **R03.8** Agente LLM — persona, regras, fluxo e parâmetros em arquivos versionados, com validador (✅ 2026-11-10)
- ✅ **R03.9** Verificação de links — identificação do robô e links bloqueados validados à mão (✅ 2026-11-10)
- ✅ **R03.7** LLM assistente de localização — escolha entre fontes aprovadas, opcional (✅ 2026-11-10)
- ✅ **R03.10** Configuração em JSON — só a chave do LLM fica no `.env` (✅ 2026-11-11)
- ✅ **R03.11** Resposta redigida pelo LLM com RAG do catálogo — fluxo único, guarda na saída (✅ 2026-11-11)
- 🔷 **R03.12** Base enriquecida do catálogo — conteúdo por página e vários arquivos
- 🔷 **R03.13** Conversa com memória e botão de nova conversa

## 04 · Operação e interface
- ✅ **R04.1** Persistência SQLite — idempotência, fila, feedback e execuções (✅ 2026-11-09)
- ✅ **R04.2** Interface Streamlit — atendimento, revisão e feedback (✅ 2026-11-10)
- ✅ **R04.3** Orquestração RPA — lote, retry, agendamento e relatório de execução (✅ 2026-11-10)
- ✅ **R04.4** Revisão com categoria e exportação — catalogar pedidos anonimizados (✅ 2026-11-11)
- ✅ **R04.5** Interface em formato de chat — conversa na tela e avaliação por resposta (✅ 2026-11-11)

## 05 · Validação e entrega
- ✅ **R05.1** Validação e entrega — métricas, notebook de evidências e README (✅ 2026-11-10)

<!-- Exemplo (comentado: não conta como item real)
## 02 · Base de dados
- ✅ **R02.1** Schema inicial — tabelas do domínio de pedidos (✅ 2026-10-09)
- 🔷 **R02.2** Índices de busca — há uma plan aberta com item: "R02.2"
- ⬜ **R02.3** Particionamento por mês
-->
