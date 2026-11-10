---
tipo: "plan"
familia: "04"
item: "R04.3"
titulo: "Orquestrar o pipeline em lote com retry, idempotência, agendamento e relatório de execução"
dominio: "Operação e interface"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[00-fundacao-tecnologica]]", "[[002-persistencia-sqlite-e-arquivos]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "plan-03.02-resposta-final-e-llm"
destino_sintese: "arquitetura/04.03-orquestracao-rpa.md"
---

# 1. Objetivo
`python run.py --input <pasta> --output <pasta>` executa o robô do início ao fim — ingestão, anonimização,
classificação, decisão, resposta ou fila de revisão, persistência — e produz um relatório de execução; rodar duas
vezes sobre a mesma entrada não duplica trabalho.

# 2. Contexto
É o **robô de verdade** do enunciado e o núcleo do tema **Automação/RPA** (peso 25% de ponta a ponta e 20% de
resiliência no barema): ingestão em lote, retry, idempotência, agendamento e relatório. Esta plan **compõe** os
pacotes das plans anteriores (`ingestion`, `privacy`, `classification`, `automation`, `storage`) e não reimplementa
nada deles. Etapa que falha para **um** pedido não derruba os demais.

# 3. Escopo
## 3.1 Dentro
- `src/triage/pipeline/processor.py` — `process_request(request, deps) -> ProcessingResult`
- `src/triage/pipeline/runner.py` — `run_batch(input_dir, deps) -> RunReport`
- `src/triage/pipeline/report.py` — `build_report(...)` e gravação em `output/reports/` (JSON + Markdown)
- `src/triage/pipeline/scheduler.py` — `watch(input_dir, interval_seconds, deps, stop_event)` (reexecução periódica)
- `src/triage/pipeline/__init__.py`
- `run.py` — completar: flags `--input`, `--output`, `--db`, `--watch`, `--interval`, `--llm/--no-llm`
- `tests/pipeline/` — testes de integração com `deps` simuladas e um teste ponta a ponta sobre `data/samples/`

## 3.2 Fora
- Interface Streamlit (plan 04.02) e métricas de acerto (plan 05.01).
- Novas regras de classificação ou de revisão; alterar pacotes já entregues, exceto correção de bug declarada.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[00-fundacao-tecnologica]] | fluxo ponta a ponta |
| ADR | [[002-persistencia-sqlite-e-arquivos]] | idempotência e fila no SQLite |
| ADR | [[003-seguranca-sem-autenticacao]] | PII antes de log/gravação; revisão humana |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `src/triage/{ingestion,privacy,classification,automation,storage}` | blocos a compor |
| Código | `src/triage/common/retry.py` | retry com espera (plan 03.01) |

# 5. Instruções de execução
1. [dirigido] `process_request`: ordem fixa — anonimizar → `request_hash` → se `already_processed` então `skipped_duplicate` → classificar → `triage_decision` → se `auto_answer`: `resolve_service` + `build_response`; se `Resolution.reason == link_unavailable` → revisão com esse motivo → gravar (`save_request(..., anonymized=True)`) e, se for o caso, `enqueue_review`. Devolve `ProcessingResult(status, category, confidence, reason, response_text)`.
2. [dirigido] **Isolamento de falha:** exceção em um pedido (inclusive `StorageError`, `ModelNotAvailableError`) é capturada no `run_batch`, registrada em log **sem texto** e contada em `errors`; o pedido tenta a fila de revisão como caminho seguro; a execução continua. Modelo ausente → todos os pedidos vão à revisão (`low_confidence`) em vez de abortar.
3. [dirigido] `run_batch`: usa `read_folder`; cada `Rejection` da ingestão vira registro `rejected` + revisão `invalid_input`; abre `start_run()` e fecha com `finish_run(totals)` **mesmo em erro** (`try/finally`).
4. [dirigido] **Relatório de execução** (`RunReport`): `run_id`, início/fim, duração, totais por status (`answered`, `queued_for_review`, `rejected`, `skipped_duplicate`, `errors`), contagem por categoria e por motivo de revisão, links verificados/falhos, uso de LLM e fallbacks. Gravar `output/reports/run-<timestamp>.json` e `.md`. **Sem texto de pedido e sem PII**.
5. [dirigido] `scheduler.watch`: laço que chama `run_batch` a cada `interval_seconds` até `stop_event`/`KeyboardInterrupt`; erro numa rodada é logado e o laço segue. Idempotência garante que arquivos já processados não repetem. Documentar no docstring como agendar externamente (cron/Agendador de Tarefas do Windows chamando `python run.py`).
6. [dirigido] `run.py`: `--watch` liga o agendador; códigos de saída: `0` execução concluída (mesmo com revisões), `1` falha de infraestrutura que impediu a execução (ex.: banco inacessível), `2` argumento/pasta inválidos.
7. [dirigido] Testes: execução ponta a ponta sobre `data/samples/`; **duas execuções seguidas** (segunda: tudo `skipped_duplicate`); falha injetada em um pedido (demais continuam); modelo ausente; link indisponível; LLM falhando; relatório gerado e sem PII; `watch` com `stop_event` após uma iteração.
8. Rodar `python -m pytest tests/pipeline -q`, a suíte completa e `ruff`.

# 6. Critérios de aceite
- [ ] `python run.py --input data/samples` termina com código 0 e gera `output/reports/run-*.json|md`.
- [ ] Segunda execução sobre a mesma entrada processa 0 novos pedidos (todos `skipped_duplicate`).
- [ ] Falha em um pedido não impede os demais; contagem em `errors`; execução fecha com `finish_run`.
- [ ] Modelo ausente, link fora do ar e LLM falhando são tratados com log e caminho seguro (revisão ou template).
- [ ] O relatório não contém texto de pedido nem PII.
- [ ] `--watch` reexecuta e para limpo ao receber o sinal de parada.
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — esta plan integra todos os pacotes anteriores`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest -q` (suíte inteira) → verde.
- `python -m ruff check .` → sem erro.
- `python run.py --input data/samples --output <pasta temporária>` duas vezes → relatório da 1ª com respostas e revisões; da 2ª com `skipped_duplicate`.
- Leitura do relatório gerado → sem texto de pedido nem PII.
- Se a verificação cria `output/` ou `.db`: apenas em pasta temporária; o revisor refaz o `git status` e confirma limpo.
- **Gate:** `nenhum — comportamento coberto por teste de integração`.

# 8. Destino da síntese
**Destino:** `arquitetura/04.03-orquestracao-rpa.md`

Levar: ordem das etapas em `process_request`; política de isolamento de falha por pedido e de caminhos seguros; campos
do relatório de execução; semântica de idempotência; modo `--watch` e como agendar externamente; códigos de saída do
`run.py`. Atualizar a §3 do `00-contexto` com os comandos verificados.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências

**O que foi feito**
- `src/triage/pipeline/processor.py` — `process_request` na ordem anonimizar → `request_hash` → `already_processed` (`skipped_duplicate`) → classificar → `triage_decision` → `resolve_service` + `build_response` (ou revisão com a causa, inclusive `link_unavailable`) → `save_request(..., anonymized=True)` + `enqueue_review`. Também `Deps`, `ProcessingResult`, `build_deps`, `process_rejection` e `route_to_safe_review`.
- `src/triage/pipeline/runner.py` — `run_batch`: `start_run` → `read_folder` → cada pedido isolado (`_isolated`) → `finish_run` e relatório no `finally`; cada `Rejection` vira `rejected` + revisão `invalid_input`.
- `src/triage/pipeline/report.py` — `RunReport`, `build_report`, `render_markdown`, `write_report` (`output/reports/run-<data>-<id>.json|md`).
- `src/triage/pipeline/scheduler.py` — `watch` com `stop_event`, `KeyboardInterrupt` e erro de rodada logado; docstring explica cron e Agendador de Tarefas.
- `run.py` — flags `--db`, `--watch`, `--interval`, `--llm/--no-llm`; saída 0 / 1 (`StorageError`, `OSError`) / 2.
- `tests/pipeline/` — 27 testes (processor, runner, scheduler, CLI).

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `run.py` | alterado | chama o pipeline; novas flags e códigos de saída |
| `src/triage/pipeline/__init__.py` | alterado | exporta a API pública |
| `src/triage/pipeline/processor.py` | criado | processamento de um pedido, dependências e caminhos seguros |
| `src/triage/pipeline/runner.py` | criado | lote com isolamento de falha |
| `src/triage/pipeline/report.py` | criado | relatório JSON e Markdown |
| `src/triage/pipeline/scheduler.py` | criado | `watch` |
| `tests/pipeline/conftest.py`, `test_processor.py`, `test_runner.py`, `test_scheduler.py`, `test_run_cli.py` | criados | testes de integração com `deps` simuladas e ponta a ponta sobre `data/samples/` |

**Verificações executadas**
- `python -m pytest tests/pipeline -q` → 27 passed.
- `python -m pytest -q` (suíte inteira, exigida pela §7 da plan) → 343 passed (316 antes).
- `python -m ruff check run.py src/triage/pipeline tests/pipeline` → All checks passed. (`ruff check run.py src tests` inteiro tem 17 erros em arquivos de outras plans, não tocados.)
- `padrao-python/scripts/validate.py` em `run.py`, `src/triage/pipeline`, `tests/pipeline` → 0 achados (os 6 de anotação de tipo nos testes foram corrigidos).
- `python run.py --input data/samples --output <pasta temporária>` duas vezes → ambas saíram com 0. 1ª: 8 `queued_for_review` e 7 `rejected`, 0 `answered`; 2ª: `skipped_duplicate` = 15, demais 0. `--input nao-existe` → saída 2. Relatórios `.json` e `.md` gerados nas duas; a rede real foi usada (verificação de links), mas não houve resposta a verificar (ver pendências).
- Leitura dos relatórios: só contagens, sem texto de pedido nem PII; teste `test_report_has_no_request_text_or_pii` cobre também o log.

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** pasta temporária do scratchpad com banco, log e relatórios criada → removida (`rm -rf`); nenhum processo, servidor ou contêiner subido; `output/` não existe no repositório. `snapshot` de `code-limpeza-ambiente` não rodado (indisponível: só processos Python curtos que terminaram sozinhos); confirmado à mão.

**Critérios de aceite**
- [x] `python run.py --input data/samples` sai com 0 e gera `output/reports/run-*.json|md` — evidência: execução acima; `tests/pipeline/test_run_cli.py::test_run_over_samples_exits_0_and_writes_reports`.
- [x] Segunda execução sem novos pedidos — evidência: 2ª execução real com `skipped_duplicate: 15`; `test_runner.py::test_second_run_processes_nothing_new`.
- [x] Falha em um pedido não impede os demais; `finish_run` sempre — evidência: `test_one_failing_request_does_not_stop_the_others`, `test_run_is_closed_even_when_reading_the_folder_fails`.
- [x] Modelo ausente, link fora do ar e LLM falhando tratados — evidência: `test_missing_model_queues_every_request`, `test_unavailable_link_goes_to_review_with_that_reason`, `test_failing_llm_falls_back_to_template`.
- [x] Relatório sem texto de pedido nem PII — evidência: `test_report_has_no_request_text_or_pii`.
- [x] `--watch` reexecuta e para limpo — evidência: `tests/pipeline/test_scheduler.py` (parada por evento, erro de rodada, `KeyboardInterrupt`) e `test_watch_flag_hands_control_to_the_scheduler`.
- [x] Ambiente e worktree limpos — evidência: `git status --short` só com os arquivos de §3.1.
- [x] Testes verdes; `ruff` e validador sem violação nos arquivos alterados.
- [x] Nenhum dado pessoal real, chave ou `.env` no diff.

**Decisões e suposições**
- Total de erros se chama `error` (constante `STATUS_ERROR`), não `errors` como no texto da plan.
- `ProcessingResult` ganhou `link_status`, `used_llm` e `fallback_reason` além dos cinco campos da plan, para alimentar o relatório sem reabrir o resultado.
- Pedido que falha de forma inesperada vai à fila com `low_confidence`, porque `ReviewReason` é um conjunto fechado e não tem motivo de erro.
- Retry com `retry_with_backoff` (3 tentativas, `StorageError` como transitório) só em torno da gravação, não do pedido inteiro: repetir o pedido todo perderia o item da fila se a falha viesse depois de `save_request`.
- Rejeição da ingestão: o hash vem de `origem|motivo` e o texto gravado é `[pedido rejeitado na ingestão: <motivo>]`; assim a segunda execução também as marca `skipped_duplicate`. A contagem por motivo de revisão inclui `rejected` (`invalid_input`).
- `links` do relatório conta por pedido, não por URL única.
- Três `except Exception` (isolamento por pedido, caminho seguro e rodada do `watch`) levam `# noqa: BLE001` com justificativa, no padrão de `allowlist.py:43`. O `ruff` do repositório os barra porque o handler engole a exceção; a plan manda capturar qualquer exceção por pedido. Revisor: se preferir outra forma, aponte.
- O modelo é lido de `DEFAULT_MODEL_PATH` (`output/models/classifier.joblib`, relativo à pasta atual), não de `<--output>/models`.
- Não atualizei a §3 do `00-contexto` (comandos verificados): é do revisor na síntese.

**Achados fora do escopo (não corrigidos)**
- `python -m ruff check run.py src tests` falha com 17 erros (ordenação de imports e SIM117, por exemplo em `tests/storage/test_repository.py:143`) em arquivos de plans anteriores.
- Não existe modelo treinado versionado nem etapa que o gere antes do `run.py`; `scripts/train_model.py` existe, mas sem o modelo o robô encaminha tudo à revisão.

**Pendências / riscos**
- Com a pasta `output/` vazia, o `run.py` real não responde nenhum pedido (todos `low_confidence`); o caminho de resposta foi provado só nos testes, com modelo treinado em `data/labeled/` e link simulado. Rodar `scripts/train_model.py` antes dá a execução com respostas; não fiz isso para não deixar `output/` no worktree.
- Gate: a plan declara `nenhum`, então não há tabela de limites.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-10 — 🟢 Aprovado

**Verificado (nível ampla, como a §7 declara), com saída real:** `git status`/`git diff` (só `run.py`, `src/triage/pipeline/` e `tests/pipeline/`; nada fora do escopo, nada faltando) · leitura integral de `processor.py`, `runner.py`, `report.py`, `scheduler.py`, `__init__.py` e `run.py` · `python -m pytest -q` (suíte inteira) → 343 passed · `python -m ruff check --no-cache run.py src/triage/pipeline tests/pipeline` → All checks passed (ruff 0.17.4, o do pin) · `padrao-python/scripts/validate.py` em `run.py`, `src/triage/pipeline` e `tests/pipeline` → 0 achados · **execução real**, em pasta temporária fora do repositório: sem modelo treinado, `python run.py --input data/samples --output <tmp>` → código 0, 8 `queued_for_review` (`low_confidence`) e 7 `rejected`; segunda execução → código 0, `skipped_duplicate: 15` e o resto zero; `--input nao-existe` → código 2; depois de `python scripts/train_model.py`, nova pasta → código 0, 4 `answered` (links verificados na rede real, 4 `ok`), 4 `queued_for_review` (`urgent`, `out_of_catalog` ×2, `low_confidence`), 7 `rejected`, e a segunda execução com 15 `skipped_duplicate` · relatórios `.json` e `.md` das duas rodadas: só contagens, sem texto de pedido nem PII; busca por texto de pedido, e-mail e CPF no `run.log` → vazia (o log traz só tipo de erro e origem do arquivo) · banco: 4 `answered`, 4 `queued_for_review` e 7 `rejected` em `requests`, 11 itens em `review_queue` (os não respondidos) e `totals_json` fechado nas duas execuções · `finish_run` e o relatório saem no `finally` · sem `TODO`/`FIXME`/skip/`print` nem citação a plan · removi `output/`, a pasta temporária, os caches e os `__pycache__`.

**Decisões do executor aceitas:** `STATUS_ERROR = "error"` (a plan escreve `errors`); `ProcessingResult` com `link_status`, `used_llm` e `fallback_reason` a mais; falha inesperada vai à fila com `low_confidence` (`ReviewReason` é conjunto fechado); retry só em torno da gravação; rejeição da ingestão com hash de `origem|motivo` e texto-marcador, o que a torna idempotente; os três `except Exception` com `# noqa: BLE001` e justificativa, que a plan manda para isolar o pedido (log só com o tipo do erro, nunca o texto); o modelo vem de `DEFAULT_MODEL_PATH`. A síntese registra tudo isso como é.

**Achados:** nenhum que reprove. Três itens foram para o `00-backlog`.
