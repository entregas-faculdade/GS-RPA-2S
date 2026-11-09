---
tipo: "plan"
familia: "04"
item: "R04.3"
titulo: "Orquestrar o pipeline em lote com retry, idempotência, agendamento e relatório de execução"
dominio: "Operação e interface"
status: "🔴 A executar"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
