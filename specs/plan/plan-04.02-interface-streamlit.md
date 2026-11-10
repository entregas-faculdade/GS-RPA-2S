---
tipo: "plan"
familia: "04"
item: "R04.2"
titulo: "Criar a interface Streamlit de atendimento, fila de revisão e feedback"
dominio: "Operação e interface"
status: "🟢 Aprovada"
prioridade: "Média"
tags: ["plan"]
relacionados: ["[[001-stack-principal]]", "[[003-seguranca-sem-autenticacao]]", "[[004-infra-execucao-local]]"]
depende_de: "plan-04.03-orquestracao-rpa"
destino_sintese: "specs/04.02-interface.md"
---

# 1. Objetivo
`streamlit run app.py` abre uma tela onde o cidadão digita um pedido, recebe a resposta (ou o aviso de encaminhamento
humano) e avalia com 👍/👎, e onde há uma aba de revisão com a fila pendente.

# 2. Contexto
Decisão de interface local ([[001-stack-principal]], [[004-infra-execucao-local]]): Streamlit roda **localmente**; o
Colab não o suporta sem túnel, então a avaliação remota usa `run.py` e o notebook (plan 05.01). A interface é **fina**:
chama `triage.pipeline.process_request` e `triage.storage`; **não** contém regra de negócio. Sem autenticação
([[003-seguranca-sem-autenticacao]]); a aba de revisão fica sem login (limite declarado).

# 3. Escopo
## 3.1 Dentro
- `app.py` — ponto de entrada Streamlit (apenas montagem e chamada das telas)
- `src/triage/interface/service.py` — `AppService`: monta as dependências (`Repository`, modelo, catálogo, cliente LLM opcional) e expõe `submit(text)`, `pending_reviews()`, `resolve(id, note)`, `send_feedback(hash, rating)`
- `src/triage/interface/views.py` — funções de renderização (`render_citizen_tab`, `render_review_tab`)
- `src/triage/interface/__init__.py`
- `tests/interface/` — testes do `AppService` (a UI em si é conferida manualmente)
- `src/triage/storage/repository.py` — **só** o acréscimo de `Repository.get_request(request_hash) -> RequestRecord | None` (leitura simples de `requests`, mesmas regras do módulo: `?` vinculado, erro vira `StorageError`); a aba Revisão precisa de categoria, confiança e texto anonimizado, que `pending_reviews()` não traz. Nenhuma outra alteração no storage
- `tests/storage/test_repository.py` — testes do `get_request` (existente, inexistente)

## 3.2 Fora
- Autenticação, perfis e deploy (ADRs 003 e 004).
- Qualquer regra de classificação, revisão ou resposta (já nos pacotes do núcleo); alterar `triage.pipeline` ou qualquer outro pacote além do `get_request` acima.
- Reprocessar um pedido repetido só para exibir a resposta: `skipped_duplicate` não traz texto de resposta, e a interface mostra uma **mensagem neutra** ("este pedido já foi registrado"), sem resposta e sem botões de feedback. Melhorar isso exige mudar o pipeline e fica para depois da plan.
- Edição do catálogo pela interface.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[001-stack-principal]] | Streamlit como interface |
| ADR | [[004-infra-execucao-local]] | execução local, sem deploy |
| ADR | [[003-seguranca-sem-autenticacao]] | limites de acesso e proteção de PII |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `src/triage/pipeline/processor.py`, `src/triage/storage/` | o que a interface chama |

# 5. Instruções de execução
1. [dirigido] `Repository.get_request(request_hash)` em `storage/repository.py` (ver §3.1), com testes. Depois, `AppService.submit(text)`: sanitiza (via ingestão), cria `Request` com id gerado, chama `process_request` e devolve `ProcessingResult` + o `hash` do pedido (para o feedback). Entrada vazia/inválida → mensagem amigável, sem exceção para a UI. Resultado `skipped_duplicate` → mensagem neutra "este pedido já foi registrado", sem resposta e sem feedback.
2. [dirigido] Aba **Cidadão**: caixa de texto, botão enviar, exibição da resposta **ou** do aviso "encaminhamos seu pedido para atendimento humano" (sem expor o motivo técnico), botões 👍/👎 que chamam `send_feedback` uma única vez por resposta.
3. [dirigido] Aba **Revisão**: lista de `pending_reviews()` completada por `get_request` com categoria sugerida, confiança, motivo e texto **anonimizado**; botão para marcar como resolvido com nota. Aviso visível: "dados de demonstração; não envie dados pessoais reais".
4. [dirigido] Banner na tela inicial: protótipo acadêmico, dados sintéticos, sem dado pessoal real.
5. [dirigido] Dependências e modelo montados uma vez (`st.cache_resource`); falha ao montar (modelo ausente, banco inacessível) → mensagem clara na tela e log, sem traceback.
6. [dirigido] Testes do `AppService` com dependências simuladas: pedido respondido; pedido para revisão; entrada vazia; feedback duplicado ignorado; resolução de revisão.
7. Rodar `python -m pytest tests/interface -q`, `ruff` e **abrir a interface manualmente** (`streamlit run app.py`), percorrendo os fluxos de §6.

# 6. Critérios de aceite
- [ ] `streamlit run app.py` sobe sem erro e a aba Cidadão responde a "onde tiro minha CNH?" com o link do catálogo.
- [ ] Pedido com termo de urgência mostra o aviso de encaminhamento humano e aparece na aba Revisão.
- [ ] 👍/👎 grava um feedback por resposta (verificar no SQLite de teste).
- [ ] Texto exibido na aba Revisão é o anonimizado; nenhum PII aparece em tela ou log.
- [ ] `app.py` não contém regra de negócio (só montagem e renderização).
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1 (inclui `storage/repository.py` e `tests/storage/test_repository.py`, só pelo `get_request`).
- `python -m pytest tests/interface tests/storage -q` → verde.
- `python -m ruff check app.py src/triage/interface tests/interface` → sem erro.
- Verificação **visual no navegador**: `streamlit run app.py`; enviar (1) pedido de CNH, (2) pedido urgente, (3) texto vazio, (4) texto com um CPF fictício; conferir resposta, aviso, aba Revisão e que o CPF aparece como `[CPF]`.
- Encerrar o processo do Streamlit ao final; o revisor confirma que nada ficou rodando e que não há `.db` no worktree.
- **Gate:** `nenhum — a UI é conferida visualmente; a lógica está nos pacotes testados`.

# 8. Destino da síntese
**Destino:** `specs/04.02-interface.md`

Levar também: a linha de `get_request` na tabela do contrato do `Repository` em `arquitetura/04.01-persistencia.md` (substituir, não acrescentar texto). Levar: telas (Cidadão e Revisão) e o comportamento de cada uma; regra "interface fina, sem regra de negócio";
mensagens ao cidadão para resposta e encaminhamento; limite declarado de que a revisão não tem autenticação; como
iniciar (`streamlit run app.py`) e por que não roda no Colab.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências (verificação visual feita por `AppTest` + subida real do servidor, sem navegador)

**O que foi feito**
- `Repository.get_request(request_hash) -> RequestRecord | None` em `src/triage/storage/repository.py:53` — leitura de `requests` com `?` vinculado; erro vira `StorageError` pelo `session`.
- `AppService` em `src/triage/interface/service.py` — `submit` (sanitiza, valida, id `uuid4`, `process_request`; vazio/curto/longo → mensagem amigável; `skipped_duplicate` → "Este pedido já foi registrado." sem hash; falha inesperada → mensagem de erro, log só com o tipo), `pending_reviews` (completa com `get_request`), `resolve`, `send_feedback` (uma vez por hash, em memória do serviço).
- `src/triage/interface/views.py` — banner, aba Cidadão (resposta/aviso + 👍/👎 só quando há resposta) e aba Revisão (categoria, confiança, motivo, texto anonimizado, nota + resolver, aviso de demonstração/sem login).
- `app.py` — só `st.cache_resource` da montagem (falha → `st.error`, log, sem traceback), abas e chamada das views.
- Testes: `tests/interface/` (11 casos + conftest) e 3 casos de `get_request` em `tests/storage/test_repository.py`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `app.py` | criado | entrada Streamlit, só montagem |
| `src/triage/interface/service.py` | criado | `AppService`, `SubmitOutcome`, `ReviewEntry`, `build_service` |
| `src/triage/interface/views.py` | criado | telas Cidadão e Revisão |
| `src/triage/storage/repository.py` | alterado | só `get_request` |
| `tests/interface/conftest.py`, `tests/interface/test_service.py` | criado | testes do `AppService` |
| `tests/storage/test_repository.py` | alterado | testes do `get_request` (existente, inexistente, SQL como dado) |

**Verificações executadas**
- `python -m pytest tests/interface tests/storage -q` → 38 passed.
- `python -m ruff check app.py src/triage/interface tests/interface` → All checks passed (3 I001 de ordenação de imports corrigidos com `--fix` nesses arquivos).
- `validate.py` do `padrao-python` em `app.py`, `src/triage/interface`, `storage/repository.py`, `tests/interface` → `findings: []` em cada um.
- Fluxos via `streamlit.testing.AppTest` sobre `app.py` real (modelo treinado por `scripts/train_model.py`): "onde tiro minha CNH?" → resposta com link `https://www.gov.br/...cnh-e`; 👍 → "Obrigado pela avaliação!" e botões somem; pedido urgente → "Encaminhamos seu pedido para atendimento humano." e item na aba Revisão (motivo `urgent`); texto vazio → aviso amigável; texto com CPF `123.456.789-09` → aba Revisão exibe `[CPF]`; repetir a CNH → "Este pedido já foi registrado.".
- `python -m streamlit run app.py --server.headless true --server.port 8599` → `/_stcore/health` 200 e `/` 200; encerrado (depois, 000).

**Estado inicial do worktree:** `git status --short` vazio na leitura inicial (branch `develop`). Ao retomar, já constavam `specs/00-backlog.md` e a própria plan modificados pelo revisor (não são meus).

**Ambiente após a verificação:** criei `output/` (modelo, log, `triage.db`) e um servidor Streamlit na porta 8599 → servidor encerrado, `output/` removido, scripts temporários removidos; `find *.db` fora do `.git` sem resultado.

**Critérios de aceite**
- [x] `streamlit run app.py` sobe sem erro e responde à CNH com o link do catálogo — evidência: health 200 e saída do `AppTest` acima (sem navegador).
- [x] Urgência mostra aviso humano e aparece na aba Revisão — evidência: `AppTest`; `test_request_for_review_hides_technical_reason`.
- [x] 👍/👎 grava um feedback por resposta — evidência: `test_feedback_is_recorded_once_per_request` (conta 1 linha em `feedback`).
- [x] Aba Revisão exibe o anonimizado — evidência: `test_review_entry_shows_anonymized_text` e `AppTest` (`[CPF]`). Logs: nenhum texto de pedido é logado pelo código novo (só `type(error).__name__`).
- [x] `app.py` sem regra de negócio — evidência: `app.py` inteiro (montagem + `st.tabs`).
- [x] Ambiente e worktree limpos — evidência: acima.
- [x] Testes, `ruff` e validador sem violação nos arquivos alterados — evidência: acima.
- [x] Sem dado pessoal real, chave ou `.env` no diff — o CPF usado é fictício, só em teste.

**Decisões e suposições**
- Feedback "uma única vez por resposta": controle em memória no `AppService` (`_rated`) mais `st.session_state`; reiniciar o app permite avaliar de novo o mesmo hash, mas o mesmo texto volta como duplicado e não exibe botões.
- O `hash` do feedback é recalculado no serviço (`anonymize` + `request_hash`), pois `ProcessingResult` não o traz e o pipeline não podia mudar (§3.2).
- Confiança exibida em porcentagem; categoria/confiança ausentes aparecem como "—".
- `AppService` reexporta `RATING_UP`/`RATING_DOWN` em `__all__` por conveniência das views (que importam do schema).
- Execução sem navegador real: no ambiente não há ferramenta de navegador; usei `AppTest` (executa `app.py` de verdade) mais a subida do servidor.

**Achados fora do escopo (não corrigidos)**
- `ruff` já reportava em `src/triage/storage/repository.py:38` (UP017, `timezone.utc`) e em `tests/storage/test_repository.py` (I001 na linha 8 e SIM117 na ~158), código anterior à tarefa.
- A primeira chamada `ruff check` sobre `src` inteiro acusa esses itens; o comando da plan (§7) não os cobre.

**Pendências / riscos**
- Conferência visual em navegador real (CSS, rótulos de botão) fica para o revisor.
- Em `AppTest`, o aviso "Encaminhamos…" é `st.info`, não destaque forte; estético, não funcional.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-10 — 🟢 Aprovado

**Verificado (nível escopada), com saída real:** `git status`/`git diff` (só `app.py`, `src/triage/interface/`, `tests/interface/` e, no storage, apenas `get_request` e seus três testes, como a §3.1 ampliada pelo revisor autoriza; nenhum outro pacote tocado) · leitura integral de `app.py`, `service.py`, `views.py` e do diff do storage · `python -m pytest tests/interface tests/storage -q` → 38 passed · `python -m ruff check --no-cache` nos arquivos do escopo → limpo, exceto 3 erros antigos de `repository.py:38` (UP017) e `test_repository.py` (I001 e SIM117), anteriores a esta tarefa e já no `00-backlog` · `padrao-python/scripts/validate.py` em `app.py`, `src/triage/interface`, `storage/repository.py`, `tests/interface` e `tests/storage/test_repository.py` → `findings: []` em todos · **execução real do `app.py` por `streamlit.testing.AppTest`** (modelo treinado por `scripts/train_model.py`, banco e log em `output/`, removido depois): "onde tiro minha CNH?" → resposta com o link oficial da CNH e botões 👍/👎; pedido urgente → "Encaminhamos seu pedido para atendimento humano." e item na aba Revisão com motivo `urgent`, categoria sugerida e confiança; texto vazio → aviso amigável, sem exceção; texto com CPF → respondido, e o banco guarda `[CPF]` (nenhum dígito do CPF no `requests` nem no `run.log`); repetir a CNH → "Este pedido já foi registrado.", sem resposta e sem botões de feedback (a decisão do revisor sobre duplicados) · `app.py` só monta e renderiza · `get_request` com `?` vinculado, testado com texto SQL como dado · sem `TODO`/`FIXME`/`print` nem citação a plan · nenhum processo do Streamlit rodando, nenhum `.db` no worktree, `output/` e caches removidos.

**Limite da verificação:** a conferência visual em navegador real (a §7 pede) não foi feita por mim nem pelo executor; o `AppTest` executa o `app.py` de verdade e prova fluxo e conteúdo, não CSS nem rótulos na tela. Fica a cargo do usuário um olhar rápido ao abrir `streamlit run app.py`.

**Decisões do executor aceitas:** feedback uma vez por resposta por controle em memória do `AppService` e `st.session_state`; hash do feedback recalculado no serviço (o `ProcessingResult` não o traz e o pipeline não podia mudar); confiança em porcentagem; falha inesperada no envio vira mensagem amigável, com log só do tipo do erro.

**Achados:** nenhum que reprove. O controle de feedback em memória foi para o `00-backlog`.
