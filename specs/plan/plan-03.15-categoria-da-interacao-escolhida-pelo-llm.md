---
tipo: "plan"
familia: "03"
item: "R03.15"
titulo: "Escolher a categoria da interação com o LLM, com saída segura sem ele"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan", "llm", "categoria", "interacao"]
relacionados: ["[[03.02-resposta-final-e-llm]]", "[[03.04-agente-llm]]", "[[03.01-catalogo-e-allowlist]]", "[[02.01-classificacao]]", "[[02.02-confianca-e-revisao-humana]]"]
depende_de: ""
destino_sintese: "specs/03.05-categoria-da-interacao.md (nova) + specs/03.04-agente-llm.md"
---

# 1. Objetivo

Existe uma função `choose_topic(...)` que devolve a **categoria da interação** (uma de 9, de um vocabulário fechado e
versionado) escolhida pelo LLM quando ele está ligado, e por regras determinísticas quando não está ou quando ele falha,
sempre dizendo **quem escolheu** (`topic_source`). Nada é gravado ainda: a gravação é a plan seguinte.

# 2. Contexto

Hoje o pedido só tem a categoria do classificador (`driver_license`, `property_tax`… `other`), que é o assunto *do
serviço* para decidir se o robô responde. Falta uma **categoria de catalogação**, de granularidade de tema, para guardar e
contar as interações (saúde, impostos, trânsito…). O usuário pediu que **o LLM escolha** essa categoria e que a automação
a guarde junto com uma tag de interação humana (plan 04.06). O catálogo já tem o campo `area` com 8 valores (`health`,
`education`, `vehicles`, `city`, `documents`, `social`, `tax`, `safety`); a decisão é **reusar esse vocabulário mais
`other`** (9 categorias), para a categoria de catalogação e a área das fontes serem a mesma coisa.

Regras que já valem e não mudam: o LLM só recebe texto **anonimizado**; emergência **nunca** passa pelo LLM; o sistema
funciona integralmente sem LLM; saída do LLM só vale se passar numa guarda; a chave só existe no `.env`.

# 3. Escopo

## 3.1 Dentro
- `data/interaction_topics.json` — **novo**. O vocabulário fechado: lista de `{ "id", "label" (pt-BR), "description" (uma frase, só para o prompt) }` com os 9 ids acima (`other` obrigatório e último), e o mapa `classifier_category → topic id` das 9 categorias do classificador (`driver_license→vehicles`, `property_tax→tax`, `id_card→documents`, `cpf_registration→documents`, `voter_id→documents`, `social_benefits→social`, `social_security→social`, `birth_certificate→documents`, `other→other`).
- `src/triage/automation/topics.py` — **novo**: carga e validação do JSON, `choose_topic`, a guarda da saída do LLM.
- `src/triage/automation/__init__.py` — exportar o que for público.
- `data/agents/triage-assistant/workflow.md` — nova seção `## Tarefa: categorize`.
- `src/triage/agent/` — apenas o necessário para a tarefa `categorize` ser **obrigatória** no agente (como `answer`) e o linter a exigir; sem mudar o contrato do restante.
- `tests/automation/test_topics.py` e, se o agente mudar, o teste correspondente em `tests/agent/`.

## 3.2 Fora (não tocar)
- `src/triage/pipeline/`, `src/triage/storage/`, `src/triage/interface/`, `run.py`, `app.py`: a ligação ao pipeline e a gravação são da plan 04.06.
- `config/settings.json`, `.env`, `data/catalog*.json`, `data/catalog.d/`, o classificador e a decisão de revisão.
- O prompt da tarefa `answer`, `rules.md`, `identity.md`, `global_rules.md` e `config.json` do agente (item de backlog separado).
- Qualquer mudança no cliente HTTP (`llm_client.py`): usar o contrato existente (`complete(task, user_message)`, `LlmUnavailable`, `LlmInvalidResponse`).

# 4. Referências obrigatórias

| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | `specs/03.02-resposta-final-e-llm.md` | cliente, `fallback_reason`, delimitadores `<<<PEDIDO`, guarda de saída |
| Spec fixa | `specs/03.04-agente-llm.md` | arquivos do agente, tarefas, linter |
| Spec fixa | `specs/03.01-catalogo-e-allowlist.md` | campo `area` das fontes |
| Spec fixa | `specs/02.01-classificacao.md` | as 9 categorias do classificador |
| Spec fixa | `specs/02.02-confianca-e-revisao-humana.md` | `is_urgent`, motivos de revisão |
| Contexto | `specs/00-contexto.md` · `specs/00-knowledge.md` | sempre |
| Skill | `padrao-escrita` + `padrao-python` | limiares e idioma (código em inglês, texto de usuário em português) |
| Skill | `test-unitario` | testes com cliente de LLM falso, sem rede |
| Código | `src/triage/automation/rag.py` | como a mensagem ao LLM, os delimitadores e a conversa anterior são montados hoje |
| Código | `src/triage/automation/llm_client.py`, `src/triage/automation/messages.py` | contrato do cliente e tratamento de falha |
| Código | `src/triage/agent/` | carga do agente e linter |
| Código | `src/triage/automation/catalog.py` | `ServiceEntry.area` |

# 5. Instruções de execução

1. [dirigido] Criar `data/interaction_topics.json` com o conteúdo da §3.1. A carga valida: ids únicos, `other` presente e
   último, cada id do mapa do classificador existente na lista, as 9 categorias do classificador todas mapeadas. Arquivo
   ausente ou inválido levanta erro com mensagem acionável e causa preservada (o chamador, na plan 04.06, decide o caminho seguro).
2. [dirigido] Criar `triage.automation.topics` com, no mínimo: tipo imutável `TopicChoice(topic, source)` e
   `choose_topic(...)`. `source` é um de: `llm` (o LLM escolheu e a guarda aprovou), `catalog` (área da fonte
   resolvida), `classifier` (mapa da categoria do classificador), `rule` (urgência), `none` (sem categoria, para pedido
   rejeitado na ingestão). O que `choose_topic` recebe (agrupe em objeto: limite de 4 parâmetros): texto anonimizado,
   mensagens anteriores anonimizadas (podem ser vazias), categoria do classificador, a fonte resolvida (ou `None`), se é
   urgência, o cliente de LLM (ou `None`).
3. [dirigido] Ordem de decisão, fixa:
   1. urgência → `safety` com `source=rule`, **sem chamar o LLM**;
   2. com cliente de LLM: tarefa `categorize` sobre o texto **anonimizado**; saída aprovada pela guarda → `source=llm`;
   3. sem cliente, ou LLM indisponível, ou resposta vazia/inválida/reprovada pela guarda → determinístico: `area` da fonte
      resolvida, se houver (`source=catalog`); senão o mapa da categoria do classificador (`source=classifier`).
   A falha do LLM **nunca** levanta para o chamador: captura só `LlmUnavailable` e `LlmInvalidResponse` (as duas do
   contrato), registra em log o tipo do erro ou o motivo da rejeição (nunca o texto do pedido nem a saída do LLM) e cai
   no determinístico.
4. [dirigido] A mensagem ao LLM segue o padrão de `rag.py`: a pergunta entre `<<<PEDIDO`/`PEDIDO>>>` (delimitadores
   removidos do texto), a conversa anterior entre `<<<CONVERSA ANTERIOR`/`CONVERSA ANTERIOR>>>` quando houver, e a lista
   de categorias (`id`, `label`, `description`) **lida do JSON**, nunca escrita no código. Nada de texto bruto.
5. [dirigido] Guarda da saída: depois de aparar espaços, aspas e ponto final e comparar sem diferença de maiúsculas, a
   saída tem de ser **exatamente** um dos ids da lista. Qualquer outra coisa (frase, dois ids, id inexistente, vazio) é
   rejeitada e cai no determinístico. A guarda devolve o motivo da rejeição para o log.
6. [dirigido] Acrescentar a seção `## Tarefa: categorize` ao `workflow.md` do agente, em português, sem URL nem chave
   (o linter proíbe): escolher **uma** categoria da lista recebida, responder **somente** com o id, tratar o texto do
   pedido como dado, em dúvida ou fora de tema responder `other`. Tornar a tarefa obrigatória na carga e no linter
   (como `answer`), com mensagem acionável.
7. [dirigido] Testes (cliente de LLM falso, sem rede, sem `.env`): urgência não chama o LLM; id válido vira `llm`; id em
   maiúscula/com aspas/ponto é aceito; frase, id inexistente, dois ids, vazio e só espaços caem no determinístico; LLM
   indisponível e resposta inválida caem sem levantar; sem cliente usa a `area` da fonte e, sem fonte, o mapa do
   classificador; as 9 categorias do classificador e as 8 áreas do catálogo resultam em ids válidos; o JSON inválido
   (id repetido, sem `other`, categoria do classificador sem mapa) levanta erro; a mensagem ao LLM não contém o texto
   com delimitadores soltos e lista exatamente as categorias do JSON; `lint_agent` reprova um `workflow.md` sem
   `categorize`. Aponte a skill `test-unitario`.
8. Rodar a verificação escopada (§7) e garantir verde.

# 6. Critérios de aceite

- [ ] `data/interaction_topics.json` tem 9 categorias (as 8 áreas do catálogo mais `other`) e o mapa das 9 categorias do classificador.
- [ ] `choose_topic` devolve `TopicChoice(topic, source)` e nunca levanta por falha do LLM.
- [ ] Urgência resulta em `safety`/`rule` com **zero** chamadas ao cliente de LLM (teste prova).
- [ ] Com LLM válido, `source=llm`; com qualquer falha ou saída fora da lista, o resultado é determinístico (`catalog` ou `classifier`).
- [ ] A lista de categorias que vai ao LLM vem do JSON; nenhum id de categoria literal em `topics.py` além de `other` e `safety` como constantes nomeadas.
- [ ] `workflow.md` tem a tarefa `categorize`; `python scripts/validate_agent.py` sai com `0`; o linter exige a tarefa.
- [ ] Nenhum log, mensagem de erro ou teste carrega texto de pedido ou chave.
- [ ] Nenhum arquivo fora de §3.1 alterado.
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nova nos arquivos alterados.

# 7. Como verificar (uso do revisor)

- **Nível:** `escopada`.
- `git diff --stat` e `git status --short` → só os arquivos de §3.1.
- `python -m pytest tests/automation/test_topics.py tests/agent -q` → verde.
- `python scripts/validate_agent.py` → `OK`, saída `0`.
- `python -m ruff check src/triage/automation src/triage/agent tests/automation tests/agent` → sem erro novo.
- Validador de `padrao-python` (`scripts/validate.py`) sobre `src/triage/automation/topics.py` e os arquivos de `src/triage/agent/` tocados → sem violação nova.
- Leitura de `topics.py`: ordem urgência → LLM → determinístico; nenhuma lista de ids no código; `except` só das duas exceções do contrato.
- Revisor roda a ordem de decisão em um probe isolado (sem rede) com cliente falso para confirmar os 5 `source`.
- Não sobe processo nem arquivo temporário fora do `tmp_path` dos testes.
- **Gate:** `nenhum` — o repositório não tem gate de módulo; o invariante vale só para este módulo e é coberto por teste.

# 8. Destino da síntese

**Destino:** `specs/03.05-categoria-da-interacao.md` (spec nova, família 03, `NN` livre depois de 03.04) e `specs/03.04-agente-llm.md`.

Texto pronto para transporte:

- **03.05 (nova):** a categoria de catalogação da interação: 9 ids fechados em `data/interaction_topics.json` (as 8 áreas do
  catálogo mais `other`), o mapa do classificador, a ordem de decisão (urgência `rule` sem LLM → LLM `llm` com guarda de
  id exato → `catalog` → `classifier`; `none` para pedido rejeitado na ingestão), o contrato de `choose_topic` e
  `TopicChoice`, a mensagem ao LLM (pedido e conversa como dado, categorias lidas do JSON), a guarda e as falhas
  (nunca levanta; log só com o tipo do erro). Diferença para `category` do classificador: esta é de catalogação, aquela
  decide se o robô responde.
- **03.04:** a tabela do `workflow.md` passa a ter duas tarefas obrigatórias, `answer` e `categorize`; o linter exige as duas.
  Aproveitar para trocar a frase "O LLM vem desligado (`enabled: false`)" por "a configuração entregue liga o LLM; sem
  `LLM_API_KEY` o robô funciona sem ele", que já é o comportamento do repositório.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-12

**Resultado:** Concluído com pendências

**O que foi feito**
- `data/interaction_topics.json` criado: 9 categorias (as 8 áreas do catálogo + `other` por último) e `classifier_map` das 9 categorias do classificador — vocabulário fechado fora do código.
- `src/triage/automation/topics.py` criado: `load_topics` (valida ids únicos, `other` último, mapa apontando para id existente, categorias do classificador todas mapeadas; erro `TopicsError` com causa preservada), `TopicChoice`, `TopicRequest` (agrupa os parâmetros, limite de 4), `choose_topic`, `build_topic_message`, `guard_topic_output`, `NO_TOPIC` (`source=none`).
- Ordem fixa em `choose_topic`: urgência → `safety`/`rule` sem LLM; cliente → tarefa `categorize` + guarda → `llm`; senão `area` da fonte (`catalog`) ou mapa do classificador (`classifier`). `except` só de `LlmUnavailable` e `LlmInvalidResponse`; log só com o tipo do erro ou o motivo da rejeição.
- `src/triage/automation/__init__.py`: exporta a API pública de `topics`.
- `data/agents/triage-assistant/workflow.md`: nova seção `## Tarefa: categorize`.
- `src/triage/agent/definition.py:19` — `REQUIRED_TASKS = ("answer", "categorize")`; carga e linter (que usa a mesma constante) passam a exigi-la.
- Testes: `tests/automation/test_topics.py` (novo) e ajustes em `tests/agent/test_definition.py` e `tests/agent/test_lint.py`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `data/interaction_topics.json` | criado | vocabulário de 9 categorias e mapa do classificador |
| `src/triage/automation/topics.py` | criado | carga/validação, `choose_topic`, mensagem ao LLM, guarda |
| `src/triage/automation/__init__.py` | alterado | exporta a API de `topics` |
| `data/agents/triage-assistant/workflow.md` | alterado | seção `categorize` |
| `src/triage/agent/definition.py` | alterado | `categorize` obrigatória |
| `tests/automation/test_topics.py` | criado | testes do módulo |
| `tests/agent/test_definition.py` | alterado | testes que assumiam só `answer` agora esperam `answer` + `categorize`; novo teste de `categorize` ausente |
| `tests/agent/test_lint.py` | alterado | novo teste de `categorize` ausente; `test_all_problems_come_back_together` passa de 2 para 3 problemas |

**Verificações executadas**
- `python -m pytest tests/automation/test_topics.py tests/agent -q` → 135 passed.
- `python scripts/validate_agent.py` → `OK`, saída 0.
- `python -m ruff check` nos arquivos tocados (`topics.py`, `__init__.py`, `test_topics.py`, `tests/agent`, `src/triage/agent`) → All checks passed. No escopo da plan inteira (`src/triage/automation`) há 1 erro **preexistente** em `allowlist.py` (`@lru_cache(maxsize=None)`, UP033), fora do diff.
- Validador `padrao-python` (`validate.py`) em `topics.py`, `definition.py`, `__init__.py`, `test_topics.py`, `test_definition.py`, `test_lint.py` → `findings: []` em todos.
- Gate declarado `nenhum`: sem mais evidência exigida. Os 5 `source` (`rule`, `llm`, `catalog`, `classifier`; `none` via `NO_TOPIC`) e as entradas exatas da guarda estão em `test_topics.py`.

**Estado inicial do worktree:** `git status --short` vazio (limpo), branch `develop`.

**Ambiente após a verificação:** nada criado (testes usam `tmp_path`; sem processo, servidor nem arquivo temporário).

**Critérios de aceite**
- [x] JSON com 9 categorias e mapa das 9 do classificador — `data/interaction_topics.json`; `test_the_real_vocabulary_has_nine_topics_with_other_last`.
- [x] `choose_topic` devolve `TopicChoice` e não levanta por falha do LLM — `test_llm_failures_fall_back_without_raising`.
- [x] Urgência → `safety`/`rule` com zero chamadas — `test_urgency_is_safety_by_rule_and_never_calls_the_llm`.
- [x] LLM válido → `llm`; falha ou saída fora da lista → `catalog`/`classifier` — testes parametrizados.
- [x] Lista de categorias vem do JSON; só `other` e `safety` como constantes — `topics.py` (`OTHER_TOPIC`, `SAFETY_TOPIC`); `test_the_message_lists_exactly_the_json_topics_and_the_request_as_data`.
- [x] `workflow.md` tem `categorize`; `validate_agent.py` sai 0; linter exige — `test_missing_categorize_section_is_reported`.
- [x] Nenhum log/erro/teste carrega texto de pedido ou chave — `test_logs_carry_neither_the_request_nor_the_llm_output`.
- [x] Nenhum arquivo fora de §3.1 alterado — ver ressalva em Decisões.
- [x] Testes verdes; `ruff` e validador sem violação nos arquivos alterados.

**Decisões e suposições**
- `choose_topic(request, client, vocabulary=None)`: `TopicRequest` agrupa texto, histórico, categoria, urgência e fonte; o vocabulário é opcional (injeção em teste) e, ausente, vem de `data/interaction_topics.json` (cache) validado contra `CATEGORY_RULES` + `other` do classificador.
- Importei `CATEGORY_RULES` e `OTHER_LABEL` de `triage.classification` só para validar o mapa; não alterei esse pacote.
- Delimitadores e `DELIMITERS` reutilizados de `rag.py`; a neutralização foi reescrita em `topics.py` porque `_neutralize_delimiters` é privada e `rag.py` está fora do escopo.
- `source=none`: `NO_TOPIC = TopicChoice(None, "none")`; `topic` é `str | None`.
- Ajustei testes preexistentes de `tests/agent` que afirmavam "só `answer`" — consequência direta de tornar `categorize` obrigatória (§3.1 autoriza o teste correspondente do agente).
- A vaga/branch é `develop` (não `main`); não criei branch.

**Achados fora do escopo (não corrigidos)**
- `src/triage/automation/allowlist.py:18` — `@lru_cache(maxsize=None)` reprovado pelo `ruff` (UP033).

**Pendências / riscos**
- Texto das `description` das 9 categorias é minha redação (não havia texto pronto); o revisor pode querer ajustá-las.
- Nenhuma chamada real a LLM foi feita (sem rede); o prompt `categorize` só foi verificado por composição e testes com cliente falso.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-12 — 🟢 Aprovado

**Nível:** escopada, elevada para a suíte inteira por um motivo: o diff toca `src/triage/automation/__init__.py`, o pacote que todos os consumidores importam, e `REQUIRED_TASKS` do agente.

**Escopo.** `git status` e `git diff --stat` mostram exatamente os arquivos de §3.1: `data/interaction_topics.json`, `topics.py`, `automation/__init__.py`, `workflow.md`, `agent/definition.py` (uma linha), `tests/automation/test_topics.py`, `tests/agent/test_definition.py` e `tests/agent/test_lint.py`. Nada fora do escopo e nada faltando. O resumo bate com o diff.

**Evidências por critério**
- 9 categorias, `other` por último, mapa das 9 do classificador: `data/interaction_topics.json`; as 8 áreas do catálogo (`data/catalog.json` e `catalog.d/`) estão todas no vocabulário (varredura: nenhuma fora).
- `choose_topic` não levanta por falha do LLM: `topics.py:165-175` captura só `LlmUnavailable` e `LlmInvalidResponse`; `test_an_unexpected_exception_from_a_foreign_client_is_not_swallowed` prova que o resto sobe.
- Urgência sem LLM: `topics.py:193-194` retorna antes de carregar o vocabulário e antes de usar o cliente; teste dedicado e probe (`safety`/`rule`).
- Ordem urgência → LLM → catálogo → classificador: `topics.py:186-200`.
- Categorias lidas do JSON: só `OTHER_TOPIC` e `SAFETY_TOPIC` como constantes; mensagem montada a partir do vocabulário (`topics.py:143-151`); caminho do JSON relativo ao arquivo, não ao diretório corrente.
- Guarda: `topics.py:154-162` aceita só id exato (caixa, aspas e ponto final tolerados); frases e ids inexistentes caem no determinístico.
- Tarefa `categorize` obrigatória: `definition.py:20`; `python scripts/validate_agent.py` → `OK`.
- Logs sem texto de pedido nem saída do LLM: `topics.py:170,174` registram só o tipo do erro ou o motivo; `test_logs_carry_neither_the_request_nor_the_llm_output`.
- Sinais de atalho: nenhum `TODO`, `skip`, `print` nem citação de plan em código ou testes.

**Comandos rodados**
- `python -m pytest tests/automation/test_topics.py tests/agent -q` → 135 passed.
- `python -m pytest -q` (suíte inteira, pelo motivo acima) → 1124 passed.
- `python -m ruff check` nos arquivos tocados → All checks passed.
- Validador de `padrao-python` em `topics.py`, `definition.py`, `automation/__init__.py` e `test_topics.py` → 0 achados.
- Probe com o LLM **real** (perguntas sintéticas, sem dado pessoal): IPTU → `tax`, bilhete único → `city`, buraco → `city`, seguro-desemprego → `social`, futebol → `other`, CNH → `vehicles` (todas `source=llm`); tentativa de injeção com delimitadores soltos → `other` (sem obedecer); urgência → `safety`/`rule`; sem cliente → `classifier`. Isso cobre a pendência declarada pelo executor (prompt `categorize` sem chamada real).

**Ambiente.** Nenhum processo, servidor nem arquivo temporário restou; `git status` só mostra os arquivos da plan.

**Fora do escopo (já no backlog).** `allowlist.py:18` (`@lru_cache(maxsize=None)`, UP033) é o item 14, preexistente.
