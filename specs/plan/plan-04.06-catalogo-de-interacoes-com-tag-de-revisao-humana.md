---
tipo: "plan"
familia: "04"
item: "R04.6"
titulo: "Catalogar cada interação com categoria, tag de revisão humana e saída por execução"
dominio: "Operação e interface"
status: "🔴 A executar"
prioridade: "Alta"
tags: ["plan", "pipeline", "persistencia", "catalogo", "revisao-humana"]
relacionados: ["[[04.01-persistencia]]", "[[04.03-orquestracao-rpa]]", "[[02.02-confianca-e-revisao-humana]]", "[[03.05-categoria-da-interacao]]"]
depende_de: "plan-03.15-categoria-da-interacao-escolhida-pelo-llm — precisa estar 🟢 e sintetizada antes"
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
- `src/triage/automation/topics.py`, `data/interaction_topics.json` e o agente: ficam como a plan 03.15 os deixou.
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
