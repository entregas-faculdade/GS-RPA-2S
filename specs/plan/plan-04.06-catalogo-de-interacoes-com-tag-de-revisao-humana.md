---
tipo: "plan"
familia: "04"
item: "R04.6"
titulo: "Catalogar cada interação com categoria, tag de revisão humana e saída por execução"
dominio: "Operação e interface"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan", "pipeline", "persistencia", "catalogo", "revisao-humana"]
relacionados: ["[[04.01-persistencia]]", "[[04.03-orquestracao-rpa]]", "[[02.02-confianca-e-revisao-humana]]", "[[03.05-categoria-da-interacao]]"]
depende_de: ""
destino_sintese: "arquitetura/04.01-persistencia.md + arquitetura/04.03-orquestracao-rpa.md"
---

# 1. Objetivo

Toda interação processada (lote ou chat) fica **catalogada** no banco com texto anonimizado, **categoria** (escolhida pelo
LLM, ou pelas regras quando ele está desligado ou falha), **quem escolheu**, **tag `needs_human`** (interação humana
necessária) e a **resposta dada**; cada execução em lote ainda grava um **CSV de saída** com essas interações e o
relatório passa a contar por categoria e por tag.

# 2. Contexto

Pré-requisito pronto (sintetizado em `specs/03.05-categoria-da-interacao.md`): `choose_topic(...)` devolve
`TopicChoice(topic, source)` e nunca levanta por falha do LLM. Hoje o banco guarda em `requests` o texto anonimizado, a
categoria do **classificador**, o `status` e o motivo de revisão; a **resposta dada não é gravada** em lugar nenhum
(só aparece na tela do chat), e o lote só produz banco e relatório de totais. Isso deixa fraca a "saída" do robô em lote
e não permite contar interações por tema. Esta plan fecha as duas pontas.

Regras que valem e não mudam: só texto **anonimizado** chega ao banco, ao log e ao LLM; o relatório e o log não carregam
texto de pedido; uma falha em um pedido não derruba os demais; gravar com retry; idempotência por hash; o esquema
existente (`requests`, `review_queue`, `feedback`, `labels`, `runs`) **não muda**: a tabela nova é **adicionada**, e
`init_db` tem de continuar funcionando sobre um `.db` já existente.

# 3. Escopo

## 3.1 Dentro
- `src/triage/storage/schema.py` — tabela `interactions` (DDL com `CREATE TABLE IF NOT EXISTS`) e nada mais.
- `src/triage/storage/repository.py` — o registro da interação e os métodos de gravação e leitura.
- `src/triage/storage/__init__.py` — exportar o que for público.
- `src/triage/pipeline/processor.py` — `ProcessingResult` ganha categoria da interação, origem e tag; `process_request`,
  `process_rejection` e o caminho de rejeição chamam `choose_topic` e gravam a interação.
- `src/triage/pipeline/runner.py` — repassar o `run_id` ao processamento e gravar o CSV ao fechar a execução.
- `src/triage/pipeline/report.py` — contagem por categoria da interação, por origem e `needs_human` no relatório (`.json` e `.md`).
- `src/triage/pipeline/__init__.py` — só se for preciso exportar algo novo.
- Arquivo novo para a exportação do CSV dentro de `src/triage/pipeline/` (nome à escolha do executor).
- Testes novos ou ajustados em `tests/storage/`, `tests/pipeline/` e `tests/test_run.py`.

## 3.2 Fora (não tocar)
- `src/triage/interface/` e `app.py`: nenhuma tela nova nesta plan (a tag aparece na fila de revisão existente como já aparece; mostrar a categoria na interface é item de backlog).
- `src/triage/automation/topics.py`, `data/interaction_topics.json` e o agente: ficam como estão.
- `config/settings.json`, `.env`, o catálogo, o classificador, a decisão de revisão e a ingestão.
- As tabelas existentes e os métodos existentes do `Repository` (comportamento idêntico).
- `notebooks/` (plan 05.02) e `README.md`.

# 4. Referências obrigatórias

| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | `arquitetura/04.01-persistencia.md` | contrato do `Repository`, `init_db`, erros |
| Spec fixa | `arquitetura/04.03-orquestracao-rpa.md` | ordem de `process_request`, retry de gravação, relatório, idempotência |
| Spec fixa | `specs/03.05-categoria-da-interacao.md` | `choose_topic`, `TopicChoice`, valores de `topic_source` |
| Spec fixa | `specs/02.02-confianca-e-revisao-humana.md` | motivos de revisão |
| Spec fixa | `specs/03.02-resposta-final-e-llm.md` | `Response`, `used_llm`, `fallback_reason`, `tier` |
| Contexto | `specs/00-contexto.md` · `specs/00-knowledge.md` | sempre |
| Skill | `padrao-escrita` + `padrao-python` | limiares (função ≤ 40 linhas, ≤ 4 parâmetros), erros, logs sem PII |
| Skill | `test-unitario` | testes do repositório, do pipeline e do relatório |
| Código | `src/triage/storage/schema.py`, `repository.py` | padrão de tabela, `RequestRecord`, `StorageError` |
| Código | `src/triage/pipeline/processor.py`, `runner.py`, `report.py` | onde a gravação e o relatório vivem hoje |
| Código | `src/triage/interface/service.py` (`export_labeled`) | modelo de exportação em CSV: codificação, aviso de PII residual e proteção contra célula iniciada em `=`, `+`, `-` ou `@` |

# 5. Instruções de execução

1. [dirigido] **Tabela `interactions`** (uma linha por pedido, chave `request_hash` com FK para `requests`). Colunas
   obrigatórias: `request_hash`, `run_id` (nulo no chat), `topic` (nulo quando `topic_source=none`), `topic_source`
   (`llm`, `catalog`, `classifier`, `rule`, `none`, garantido por `CHECK`), `needs_human` (0/1, `CHECK`), `tier`
   (`catalog`, `finder` ou nulo), `used_llm` (0/1), `fallback_reason` (nulo se não houve), `response_text` (a resposta
   dada ao cidadão, nula se não houve), `created_at` (ISO-8601, UTC). `init_db` só **acrescenta** a tabela: um `.db`
   criado antes desta plan abre sem erro nem perda, e chamar de novo continua inofensivo.
2. [dirigido] **Repositório.** Um registro imutável `InteractionRecord` (agrupa os campos; limite de 4 parâmetros) e:
   `save_interaction(record)` (mesmo hash de novo é ignorado, nunca erro; `topic_source` ou `needs_human` inválidos
   levantam `ValueError`; exige que o hash exista em `requests`, senão `StorageError`), `interactions(run_id=None)`
   (por `created_at`, filtrável por execução) e `interaction_counts()` (contagem por categoria e por `needs_human`). SQL
   com parâmetros vinculados; falha de I/O vira `StorageError` com a causa preservada e log só com o nome do erro.
3. [dirigido] **Regra da tag `needs_human`**: é `True` exatamente quando o pedido entra na fila de revisão **ou** foi
   rejeitado na ingestão (todo `ReviewReason`, inclusive `urgent`, `link_unavailable` e `invalid_input`); `False` quando
   o robô respondeu sozinho. Sem outra fonte: derive do mesmo ponto onde a fila é alimentada, para as duas coisas nunca
   divergirem.
4. [dirigido] **Pipeline.** Depois que o degrau da resposta está decidido (e já se conhece a fonte resolvida, se houver),
   `process_request` chama `choose_topic` com o texto anonimizado, as mensagens anteriores anonimizadas do chat, a
   categoria do classificador, a fonte resolvida, a urgência e o cliente de LLM, e grava a interação **junto com** o
   pedido e a fila, no mesmo bloco que já usa `retry_with_backoff` com `StorageError` como transitório. Pedido
   rejeitado na ingestão: `topic=None`, `source=none`, `needs_human=True`, sem LLM. O caminho seguro existente
   (`route_to_safe_review`) também grava a interação (`needs_human=True`, `source` determinístico, nunca LLM).
   `ProcessingResult` ganha `topic`, `topic_source` e `needs_human`, sem carregar texto do cidadão. Duplicado
   (`skipped_duplicate`) não grava nada novo.
5. [dirigido] **`run_id`.** O lote passa o id da execução ao processamento para gravar em `interactions.run_id`; o chat
   não tem execução e grava nulo. Mantenha o limite de 4 parâmetros (objeto de contexto se for preciso).
6. [dirigido] **Relatório.** `RunReport` e os arquivos `.json`/`.md` ganham: contagem por categoria da interação, por
   `topic_source` e o total com `needs_human` (e quantos desses `urgent`). Continua sem texto de pedido e sem PII.
7. [dirigido] **CSV de saída por execução.** Ao fechar a execução do lote (no mesmo `try/finally` do relatório), grava
   `<output>/exports/interactions-run-<id>.csv` com as interações **criadas naquela execução** (não as duplicadas).
   Colunas: `request_hash`, `created_at`, `topic`, `topic_label` (o rótulo em português do JSON, vazio sem categoria),
   `topic_source`, `needs_human`, `status`, `review_reason`, `tier`, `used_llm`, `fallback_reason`, `anonymized_text`,
   `response_text`. Mesma codificação e mesmo tratamento de célula iniciada em `=`, `+`, `-` ou `@` do `export_labeled`.
   Falha ao gravar o CSV é logada (só o tipo do erro) e **não** muda o código de saída nem impede o relatório. Execução sem
   interação nova não cria arquivo. O caminho é relativo ao `--output`, nunca ao diretório corrente.
8. [dirigido] Testes: tabela criada e `init_db` repetido sem perda, inclusive sobre um `.db` do esquema antigo; gravar e
   ler; hash repetido ignorado; `topic_source`/`needs_human` inválidos; hash inexistente vira `StorageError`; tag
   verdadeira para cada `ReviewReason` e falsa para respondido; urgência → `safety`/`rule` e **nenhuma** chamada ao
   LLM; rejeição → `none` e nenhuma chamada ao LLM; LLM falso devolvendo id válido → `llm`; LLM falhando → fallback
   determinístico e a resposta continua sendo entregue; duplicado não cria interação; relatório com as novas contagens e
   **sem** texto; CSV com colunas e linhas esperadas, sem duplicados, com célula perigosa neutralizada, sem arquivo
   quando nada foi criado, e falha de gravação do CSV não derruba a execução. Todos sem rede e sem `.env` (cliente falso).
9. Rodar a verificação escopada (§7) e garantir verde.

# 6. Critérios de aceite

- [ ] Rodar `python run.py --input data/samples --output <tmp> --no-llm` cria `interactions-run-<id>.csv` com uma linha por pedido processado (válidos e rejeitados), `needs_human` verdadeiro nos rejeitados e nas revisões, e nenhuma linha dos duplicados numa segunda execução.
- [ ] Toda interação gravada tem `topic_source` válido; urgente → `safety`/`rule`; rejeitado → `none`.
- [ ] `needs_human` é verdadeiro **se e somente se** o pedido entrou na fila ou foi rejeitado.
- [ ] A resposta dada ao cidadão fica em `interactions.response_text`; nada de texto bruto, só anonimizado.
- [ ] O relatório (`.json` e `.md`) traz contagem por categoria, por origem e `needs_human`, sem texto de pedido.
- [ ] Um `.db` criado antes da plan abre e funciona; as tabelas e métodos existentes têm o mesmo comportamento (testes antigos verdes).
- [ ] Falha do LLM, do CSV ou da tabela nova não interrompe a execução nem o chat; o pedido continua respondido ou em revisão.
- [ ] Nenhum log, relatório ou mensagem de erro carrega texto de pedido ou chave.
- [ ] Nenhum arquivo fora de §3.1 alterado.
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nova nos arquivos alterados.

# 7. Como verificar (uso do revisor)

- **Nível:** ampla — muda o esquema do banco e a assinatura de `process_request`/`ProcessingResult`, que o chat (`interface`) consome; rodar também os testes da interface para provar que não quebrou.
- `git diff --stat` e `git status --short` → só os arquivos de §3.1.
- `python -m pytest tests/storage tests/pipeline tests/interface tests/test_run.py -q` → verde.
- `python -m ruff check src/triage/storage src/triage/pipeline tests/storage tests/pipeline tests/test_run.py` → sem erro novo.
- Validador de `padrao-python` (`scripts/validate.py`) sobre `src/triage/storage` e `src/triage/pipeline` → sem violação nova.
- Probe do revisor (sem LLM, saída em pasta temporária e banco temporário, `--no-llm`): `python run.py --input data/samples --output <tmp> --db <tmp>/t.db --no-llm` duas vezes; conferir o CSV (colunas, linhas, `needs_human`), o relatório e que a segunda execução não gera arquivo novo. Revisor apaga a pasta temporária ao fim e refaz `git status`.
- Leitura de `processor.py`: `choose_topic` chamado depois da decisão do degrau; a interação gravada no mesmo bloco com retry; caminho seguro grava a interação sem LLM.
- Leitura do SQL novo: só parâmetros vinculados; DDL literal; nenhuma coluna de texto de pedido além de `response_text`.
- **Gate:** `nenhum` — sem gate de módulo neste repositório; as invariantes são comportamento observável do módulo e ficam em teste.

# 8. Destino da síntese

**Destino:** `arquitetura/04.01-persistencia.md` e `arquitetura/04.03-orquestracao-rpa.md`.

Texto pronto para transporte:

- **04.01:** nova linha na tabela de tabelas, `interactions` (colunas e `CHECK`s da §5.1), os métodos
  `save_interaction`, `interactions`, `interaction_counts` e o registro `InteractionRecord` na árvore e no contrato; nota de
  que `init_db` só acrescenta tabelas e abre bancos antigos.
- **04.03:** no passo de `process_request`, depois do degrau, a escolha da categoria (`choose_topic`) e a gravação da
  interação; a regra da tag `needs_human` (fila ou rejeição); `ProcessingResult` com `topic`, `topic_source`,
  `needs_human`; no relatório, as contagens novas; novo parágrafo **"Saída por execução"** com o CSV
  `<output>/exports/interactions-run-<id>.csv` (colunas, só interações novas, falha não derruba, mesma proteção de célula
  do export de rotulados, aviso de PII residual por ser anonimização por regras); no diagrama, o nó "catalogar interação"
  antes de "gravar".

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-12

**Resultado:** Concluído com pendências (critérios atendidos, exceto o de "nenhum arquivo fora de §3.1", por um ajuste de teste declarado em Decisões)

**O que foi feito**
- Parte desta plan já estava no worktree (conversa anterior). Li, conferi contra a §5 e completei; não reescrevi do zero.
- `schema.py` — tabela `interactions` (`CREATE TABLE IF NOT EXISTS`, `CHECK` de `topic_source`, `needs_human`, `tier`, `used_llm`; FK para `requests`); tabelas antigas intactas.
- `repository.py` — `InteractionRecord`, `StoredInteraction`, `InteractionCounts`, `save_interaction` (`INSERT OR IGNORE`, validação antes de gravar, hash sem pedido → `StorageError` pela FK), `interactions(run_id)`, `interaction_counts()`; SQL só com parâmetros vinculados.
- `processor.py` — `_with_topic` chama `choose_topic` depois do degrau decidido; `needs_human` vem de `_requires_human(status)`, a mesma regra que `_store` usa para alimentar a fila; `process_request`, `process_rejection` e `route_to_safe_review` gravam a interação (`run_id` opcional); rejeição: `none`, sem LLM; caminho seguro: `llm_client=None`. `ProcessingResult` ganhou `topic`, `topic_source`, `needs_human` (e `service`, descartado no resultado final; nenhum texto do cidadão).
- `runner.py` — repassa `run_id` e chama `write_interactions_csv` no mesmo `finally` do relatório.
- `export.py` (novo) — `<output>/exports/interactions-run-<id>.csv`, 13 colunas da §5.7, só as interações da execução, sem arquivo quando não há interação, falha (`StorageError`/`OSError`) só logada pelo tipo.
- `report.py` — `by_topic`, `by_topic_source`, `needs_human {total, urgent}` no `.json` e no `.md`.
- Fechamento desta rodada: corrigi I001 em `runner.py` e nos dois testes novos; TRY004 em `repository.py` (ver Decisões); renomeei `tests/storage/test_interactions.py` para `tests/storage/test_interactions_repository.py` (o mesmo basename de `tests/pipeline/test_interactions.py` quebrava a coleta, pois não há `__init__.py`); corrigi o teste de falha de gravação do CSV, que substituía `Path.open` globalmente e derrubava catálogo e relatório; agora simula a falha só em `export._write`; acrescentei o teste de `needs_human` não booleano.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/storage/schema.py` | alterado | tabela `interactions`, `VALID_TOPIC_SOURCES`, `VALID_TIERS` |
| `src/triage/storage/repository.py` | alterado | registros da interação e 3 métodos |
| `src/triage/storage/__init__.py` | alterado | exporta os registros novos |
| `src/triage/pipeline/processor.py` | alterado | categoria, tag e gravação da interação |
| `src/triage/pipeline/runner.py` | alterado | `run_id` e CSV no `finally` |
| `src/triage/pipeline/report.py` | alterado | contagens novas |
| `src/triage/pipeline/export.py` | criado | CSV por execução |
| `tests/storage/test_interactions_repository.py` | criado | tabela, banco antigo, gravar/ler, duplicado, inválidos, contagens |
| `tests/pipeline/test_interactions.py` | criado | tag, urgência, rejeição, LLM válido/falho, duplicado, caminho seguro, sem texto |
| `tests/pipeline/test_interactions_export.py` | criado | CSV, relatório, célula perigosa, falhas |
| `tests/pipeline/test_conversation.py`, `tests/pipeline/test_rag_flow.py`, `tests/interface/test_service_conversation.py` | alterado | os clientes LLM falsos ignoram a chamada `CATEGORIZE_TASK` nova |

**Verificações executadas**
- `python -m pytest tests/storage tests/pipeline tests/interface tests/test_run.py -q` → 219 passed (antes dos ajustes de fechamento: erro de coleta, depois 1 failed e 218 passed).
- `python -m ruff check src/triage/storage src/triage/pipeline tests/storage tests/pipeline tests/test_run.py` → restam só 3 preexistentes e fora do escopo (UP017 `repository.py:111`; I001 e SIM117 em `tests/storage/test_repository.py`); nenhum novo.
- `validate.py` do `padrao-python` em `src/triage/storage` e em `src/triage/pipeline` → `findings: []` nos dois.
- Probe (`python run.py --input data/samples --output <tmp> --db <tmp>/t.db --no-llm`, duas vezes): 1ª → `answered 5, queued_for_review 3, rejected 7`; CSV com 15 linhas, 10 com `needs_human=1` (3 revisões + 7 rejeitados), origens `{none, catalog, classifier}`; 2ª → nenhum `interactions-run-2.csv` (só o `run-1`). Pasta temporária removida.
- Nível "ampla" da §7: a suíte inclui `tests/interface` (chat, consumidor de `process_request`), verde.

**Estado inicial do worktree:** já continha o trabalho parcial, na branch `develop`: `M` em `pipeline/{processor,report,runner}.py`, `storage/{__init__,repository,schema}.py`, `tests/interface/test_service_conversation.py`, `tests/pipeline/{test_conversation,test_rag_flow}.py`; `??` em `pipeline/export.py`, `tests/pipeline/{test_interactions,test_interactions_export}.py`, `tests/storage/test_interactions.py`.

**Ambiente após a verificação:** o probe criou só uma pasta temporária e um `.db` fora do repositório, removidos; nenhum processo, contêiner ou servidor subido.

**Critérios de aceite**
- [x] CSV por execução com uma linha por pedido (válidos e rejeitados), `needs_human` nos rejeitados e revisões, nada dos duplicados — probe acima; `test_a_batch_writes_one_row_per_processed_request_valid_and_rejected`, `test_the_second_run_creates_no_file_and_no_duplicate_rows`.
- [x] `topic_source` válido; urgente → `safety`/`rule`; rejeitado → `none` — `CHECK` em `schema.py`; `test_urgency_is_safety_by_rule_and_never_calls_the_llm`, `test_a_rejection_has_no_topic_needs_human_and_never_calls_the_llm`.
- [x] `needs_human` se e somente se fila ou rejeição — `_requires_human` em `processor.py`; `test_the_tag_is_true_for_every_review_reason`, `test_the_tag_is_false_when_the_robot_answered`, `test_the_tag_matches_the_review_queue_exactly`.
- [x] Resposta em `interactions.response_text`, só anonimizado — `test_save_and_read_back_every_field`, `test_only_anonymized_text_reaches_the_interaction`.
- [x] Relatório `.json`/`.md` com contagens por categoria, origem e `needs_human`, sem texto — `test_the_written_reports_carry_the_counts_and_no_request_text`.
- [x] `.db` antigo abre; testes antigos verdes — `test_an_old_database_opens_without_loss_and_gains_the_table`; 219 passed.
- [x] Falha do LLM, do CSV ou da tabela nova não interrompe — `test_an_llm_failure_falls_back_and_the_answer_is_still_delivered`, `test_a_csv_write_failure_is_logged_and_does_not_break_the_run`, `test_a_failing_interaction_table_does_not_undo_the_request_or_the_queue`.
- [x] Nenhum log, relatório ou erro com texto de pedido ou chave — logs só com `type(error).__name__`; asserts nos testes de CSV e de relatório.
- [ ] Nenhum arquivo fora de §3.1 — `tests/interface/test_service_conversation.py` foi ajustado (falso de LLM que agora recebe também a chamada de categoria); está fora da lista literal da §3.1, mas a §7 manda rodar `tests/interface` e sem o ajuste o teste antigo quebra.
- [x] Testes verdes; `ruff` e `validate.py` sem violação nova nos arquivos alterados — acima.

**Decisões e suposições**
- `needs_human` não booleano levanta **`TypeError`**, não `ValueError` (resolve o TRY004 sem `noqa`, por ser tipo errado e não valor errado); `topic_source` e `tier` inválidos continuam `ValueError`. É um desvio da letra da §5.2: se o revisor preferir `ValueError`, será preciso outra forma de checagem ou `noqa` justificado.
- Falha persistente ao gravar a interação (`StorageError` depois do retry) é logada e não desfaz pedido e fila: a §5.4 pede a gravação "no mesmo bloco" do retry; mantive o mesmo `retry_with_backoff`, mas em chamada própria, para a falha da tabela nova nunca derrubar o pedido (critério de aceite).
- Vocabulário de categorias inválido (`TopicsError`) vira `none`, logado.
- O CSV neutraliza `=`, `+`, `-`, `@` com um apóstrofo na frente. A plan diz "mesmo tratamento do `export_labeled`", mas esse método não tem tratamento algum (ver achados).

**Achados fora do escopo (não corrigidos)**
- `src/triage/interface/service.py:154-162` — `export_labeled` não neutraliza célula iniciada em `=`, `+`, `-`, `@`, ao contrário do que a §4 e a §5.7 afirmam; o export de rotulados fica exposto a injeção de fórmula.
- `src/triage/storage/repository.py:111` — UP017 preexistente; `tests/storage/test_repository.py:1,158` — I001 e SIM117 preexistentes.
- `tests/` não tem `__init__.py`: dois testes com o mesmo basename em pastas diferentes quebram a coleta.

**Pendências / riscos**
- O validador de `padrao-python` rodou a partir da cópia do plugin (`~/.claude/plugins/cache/.../padrao-python/scripts/validate.py`), não de uma pasta do repositório.
- Só as interações novas são catalogadas; execuções anteriores à plan não ganham linha.
- Nada commitado; branch `develop`.


---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-12 — 🟢 Aprovado

**Nível:** ampla, como a plan declarou: muda o esquema do banco e a assinatura de `process_request`/`ProcessingResult`, que o chat consome. A suíte inteira não foi repetida (é do commit e da CI).

**Escopo.** `git status` e `git diff --stat`: `schema.py`, `repository.py`, `storage/__init__.py`, `processor.py`, `runner.py`, `report.py`, `export.py` (novo) e os testes novos de storage e pipeline. Três testes antigos foram ajustados só para que o cliente de LLM falso ignore a chamada `categorize`: dois em `tests/pipeline/` (dentro do escopo) e `tests/interface/test_service_conversation.py` (4 linhas, **fora da lista literal de §3.1**). A exceção é aceita: a própria §7 manda rodar `tests/interface`, e sem o ajuste o teste antigo não passa. O defeito é da plan (escopo que não permitia o que o critério exigia), não do executor. Nada mais fora do escopo; nada faltando. O resumo bate com o diff.

**Evidências por critério**
- CSV por execução: o probe `python run.py --input data/samples --output <tmp> --db <tmp>/t.db --no-llm` gerou `exports/interactions-run-1.csv` com 15 linhas e as 13 colunas da §5.7: 7 rejeitadas (`none`, `needs_human=1`), 5 respondidas (`catalog`, `needs_human=0`) e 3 em revisão (`classifier`, `needs_human=1`). A segunda execução saiu com código `0` e **não** criou `run-2.csv`. Banco com 15 pedidos e 15 interações.
- Tag = fila ou rejeição: `processor.py` usa `_requires_human(status)` na gravação do pedido e na tag (mesma regra); testes `test_the_tag_is_true_for_every_review_reason`, `test_the_tag_is_false_when_the_robot_answered`, `test_the_tag_matches_the_review_queue_exactly`.
- Urgência → `safety`/`rule` sem chamar o LLM; rejeição → `none` sem LLM; caminho seguro com `llm_client=None`: testes dedicados e probe com o LLM real (chat): IPTU → `tax`/`llm`, parcelamento → `tax`/`llm`, emergência → `safety`/`rule` com `needs_human`, futebol → `other`/`llm` com `needs_human`. A resposta ficou gravada em `response_text`.
- Falha do LLM não derruba nada: no probe um texto do LLM foi barrado pela guarda (`foreign_phone`) e o pedido saiu pelo template; testes `test_an_llm_failure_falls_back_and_the_answer_is_still_delivered`, `test_a_failing_interaction_table_does_not_undo_the_request_or_the_queue`, `test_a_csv_write_failure_is_logged_and_does_not_break_the_run`.
- Banco antigo abre e ganha a tabela: `test_an_old_database_opens_without_loss_and_gains_the_table`; `init_db` só acrescenta (`CREATE TABLE IF NOT EXISTS`).
- Relatório com `by_topic`, `by_topic_source`, `needs_human {total, urgent}` no `.json` e no `.md`, sem texto de pedido: conferido no relatório do probe.
- CSV: célula iniciada em `=`, `+`, `-` ou `@` ganha apóstrofo (`export.py`); sem arquivo quando nada foi criado; caminho relativo ao `--output`.
- Logs só com o tipo do erro; sem `TODO`, `skip`, `print` nem citação de plan; os dois `noqa` de `runner.py` já existiam.

**Comandos rodados**
- `python -m pytest tests/storage tests/pipeline tests/interface tests/test_run.py -q` → 219 passed.
- `python -m ruff check src/triage/storage src/triage/pipeline tests/storage tests/pipeline tests/test_run.py` → só 3 violações preexistentes (UP017 em `repository.py:111`; I001 e SIM117 em `tests/storage/test_repository.py`), nenhuma nova.
- Validador de `padrao-python` em `src/triage/storage` e `src/triage/pipeline` → 0 achados.

**Decisão do executor aceita.** `needs_human` não booleano levanta `TypeError` (e não `ValueError`, como a letra da §5.2): resolve o TRY004 sem `noqa`, tem teste e foi declarado no resumo. `topic_source` e `tier` inválidos seguem `ValueError`. A síntese descreve exatamente isso.

**Correção ao texto da plan.** A §4 e a §5.7 diziam que o `export_labeled` neutraliza célula de fórmula; ele não neutraliza. O executor implementou a proteção no CSV novo mesmo assim. O achado do `export_labeled` foi para o backlog.

**Ambiente.** Pastas temporárias do probe removidas; nenhum processo ou arquivo largado.
