---
tipo: "plan"
familia: "03"
item: "R03.13"
titulo: "Dar memória à conversa do chat (mensagens anteriores anonimizadas) e um botão de nova conversa"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[04.02-interface]]", "[[03.02-resposta-final-e-llm]]", "[[04.03-orquestracao-rpa]]", "[[007-llm-redige-a-resposta-com-rag-do-catalogo]]"]
depende_de: "—"
destino_sintese: "specs/04.02-interface.md"
---

# 1. Objetivo
Dentro de uma conversa do chat, o sistema considera as **mensagens anteriores do cidadão, já anonimizadas**, para recuperar a fonte e
redigir a resposta ("me passe o link correto para parcelamento" entende que o assunto é o IPTU da mensagem anterior); um botão
**Nova conversa** limpa a memória e começa outra.

# 2. Contexto
No teste do usuário, a pergunta "Preciso negociar o IPTU em atraso…" foi bem respondida e a seguinte, "ME passe o link correto para
parcelamento", caiu em "não tenho a informação": cada mensagem era um pedido independente e a segunda não dizia "IPTU". O usuário aprovou
a memória **da conversa toda**, com botão de nova conversa. Isso muda a decisão da 04.05 (histórico só de exibição, sem contexto).

Estado atual: a aba Cidadão guarda o histórico só em `st.session_state` (`ChatTurn`); `AppService.submit(text)` anonimiza e chama
`process_request(request, deps)`; o pipeline calcula `request_hash(texto anonimizado)` para a idempotência (pedido repetido vira
`skipped_duplicate` e a tela diz "Este pedido já foi registrado."); a recuperação usa `ServiceFinder.top_candidates(texto, limite)`; `rag.py`
monta a mensagem ao LLM com o pedido e as fontes. `Settings` vem de `config/settings.json`.

## 2.1 Contrato (decisão desta plan)
- **Conversa:** a interface mantém uma conversa com um identificador próprio (gerado ao abrir e a cada "Nova conversa") e a lista das mensagens
  anteriores do cidadão. `AppService.submit(text, conversation=None)` recebe essa conversa (identificador e mensagens anteriores **brutas**, que
  vivem só na sessão); o serviço **anonimiza cada mensagem anterior** com a mesma função da mensagem atual, e só o texto anonimizado segue adiante.
- **Quantas:** as últimas `chat.history_turns` mensagens anteriores (padrão 6), em `config/settings.json` (seção nova `chat`), lida por `load_settings`
  como os demais campos (ausente ou inválido volta ao padrão com `WARNING`).
- **Pipeline:** `process_request(request, deps, conversation=None)` com a conversa já anonimizada (identificador e mensagens). Sem conversa
  (`run.py`, lote), nada muda. Com conversa:
  - a **classificação** e a decisão de revisão seguem sobre a **mensagem atual** sozinha;
  - a **recuperação** (`top_candidates`, `find`) usa a mensagem atual **mais** as mensagens anteriores anonimizadas (a atual primeiro);
  - a mensagem ao LLM ganha um bloco `CONVERSA ANTERIOR` (as mensagens anteriores anonimizadas, em ordem, entre delimitadores tratados como dado,
    como o pedido) antes das fontes; as respostas anteriores do sistema **não** são reenviadas;
  - urgência, ambíguo e modelo ausente seguem como hoje (sem LLM), decididos pela mensagem atual.
- **Idempotência no chat:** o `request_hash` de um pedido de chat inclui o identificador da conversa e o número da mensagem dentro dela, de modo
  que **repetir a mesma pergunta** (na mesma conversa ou em outra) é processado e respondido, e não "já registrado". Pedido de lote continua pelo
  hash do texto anonimizado.
- **Armazenamento:** o banco continua guardando só o texto **anonimizado da mensagem atual** (a fila de revisão mostra a mensagem, sem o contexto);
  nenhuma mensagem anterior bruta é gravada, logada ou enviada.
- **Interface:** botão "Nova conversa" na aba Cidadão: limpa histórico, memória e avaliações da tela e gera um novo identificador. O histórico
  continua só na sessão do Streamlit e some ao recarregar.
- **Privacidade:** com o LLM ligado, as mensagens anteriores anonimizadas também saem rumo ao provedor a cada turno; o risco residual da anonimização
  ([[01.03-anonimizacao-de-pii]] §2.7) cresce com o tamanho da conversa e é declarado no README.

# 3. Escopo
## 3.1 Dentro
- `config/settings.json` e `src/triage/config.py` — `chat.history_turns`
- `src/triage/interface/service.py` — `submit(text, conversation=None)`, anonimização das mensagens anteriores, conversa
- `src/triage/interface/views.py` — conversa na sessão, identificador, botão "Nova conversa"
- `src/triage/pipeline/processor.py` — `process_request(..., conversation=None)`, recuperação com as mensagens anteriores, hash do chat
- `src/triage/automation/rag.py` — bloco `CONVERSA ANTERIOR` na mensagem
- `README.md` — a conversa com memória, o botão e o que a mais vai ao provedor
- `tests/pipeline/`, `tests/automation/`, `tests/interface/`, `tests/test_config.py`

## 3.2 Fora
- `triage.classification`, `triage.privacy`, `triage.storage` (a idempotência muda só no cálculo do hash, feito no pipeline) e o catálogo.
- Reenviar respostas anteriores do sistema ao LLM; gravar a conversa; qualquer login.
- Resumo automático da conversa por LLM; limite de conversa além de `chat.history_turns`.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[04.02-interface]] · [[04.03-orquestracao-rpa]] | aba Cidadão, `submit`, ordem de `process_request` e hash |
| Spec fixa | [[03.02-resposta-final-e-llm]] · [[03.03-localizador-de-servicos]] | mensagem ao LLM e recuperação |
| Spec fixa | [[01.03-anonimizacao-de-pii]] | limites residuais |
| ADR | [[007-llm-redige-a-resposta-com-rag-do-catalogo]] · [[003-seguranca-sem-autenticacao]] | o LLM só vê texto anonimizado e fontes do catálogo |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` · `cyber-ia` | injeção de prompt por mensagens anteriores, zero hardcoded |
| Skill | `test-unitario` | testes com cliente falso e `AppTest` |
| Código | `src/triage/interface/{service,views}.py`, `src/triage/pipeline/processor.py`, `src/triage/automation/rag.py`, `src/triage/config.py`, `config/settings.json` | o que muda |
| Código | `tests/interface/`, `tests/pipeline/`, `tests/automation/test_rag.py`, `tests/test_config.py` | testes a ajustar |

# 5. Instruções de execução
1. [dirigido] **Configuração.** `chat.history_turns` (inteiro positivo, padrão 6) em `config/settings.json` e `Settings`, com o mesmo tratamento de campo inválido.
2. [dirigido] **Pipeline.** `process_request` aceita a conversa anonimizada opcional e aplica o §2.1: classificação só pela mensagem atual, recuperação com
   as mensagens anteriores, hash do chat com identificador e número da mensagem, lote inalterado. Sem conversa, o resultado é idêntico ao atual.
3. [dirigido] **RAG.** `build_rag_message` aceita as mensagens anteriores e monta o bloco `CONVERSA ANTERIOR` com os delimitadores neutralizados, como o pedido.
4. [dirigido] **Serviço e tela.** `AppService.submit(text, conversation=None)` anonimiza as mensagens anteriores e entrega ao pipeline; a tela mantém na sessão
   o identificador e as mensagens, passa só as últimas `chat.history_turns`, e tem o botão "Nova conversa" conforme o §2.1. Nada de texto do usuário em log.
5. [dirigido] **README.** Seção curta: a conversa tem memória, o botão de nova conversa, e que as mensagens anteriores anonimizadas também vão ao provedor com o LLM ligado.
6. [dirigido] **Testes** (sem rede): o caso do usuário (primeira "IPTU em atraso", segunda "o link para parcelamento": a recuperação da segunda traz a entrada do IPTU e a
   mensagem ao LLM contém `CONVERSA ANTERIOR` com o texto anonimizado); mensagem anterior com nome e CPF só chega anonimizada ao cliente e ao banco; classificação só
   pela mensagem atual; repetir a mesma pergunta é respondida (hash do chat), e o lote continua deduplicando; só as últimas `chat.history_turns` entram; "Nova conversa" limpa
   histórico e muda o identificador; sem conversa, resultado idêntico ao anterior; injeção numa mensagem anterior não altera o resultado fora do bloco de dado.
7. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Uma pergunta de seguimento sem o assunto usa as mensagens anteriores da conversa para recuperar a fonte e redigir a resposta (teste do IPTU prova).
- [ ] Só texto anonimizado das mensagens anteriores é enviado ao LLM ou gravado; o banco guarda só a mensagem atual anonimizada; nenhum log traz texto do usuário.
- [ ] Só as últimas `chat.history_turns` mensagens entram; o valor vem de `config/settings.json`.
- [ ] Repetir a mesma pergunta no chat é respondido; o lote (`run.py`) continua idempotente e idêntico ao atual.
- [ ] Classificação, urgência, ambíguo e modelo ausente seguem decididos pela mensagem atual e sem LLM.
- [ ] "Nova conversa" limpa histórico, memória e avaliações da tela e começa uma conversa nova.
- [ ] README descreve o que a mais vai ao provedor; ambiente e worktree limpos; testes do escopo, `ruff` e validador sem violação nova.
- [ ] O notebook de evidências continua executando sem erro.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — muda process_request e a mensagem ao LLM, consumidos por pipeline, interface, notebook e relatório`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/classification tests/test_config.py -q` → verde.
- `python -m ruff check src/triage/pipeline src/triage/interface src/triage/automation src/triage/config.py tests/pipeline tests/interface tests/automation tests/test_config.py` → sem erro novo.
- `validate.py` do `padrao-python` nos `.py` tocados → sem achado.
- Sondagem no app real (`AppTest.from_file("app.py")` em pasta temporária, cliente falso no serviço): duas mensagens ("IPTU em atraso", depois "o link para parcelamento"); a segunda
  traz o `CONVERSA ANTERIOR`; nome e CPF digitados na primeira nunca aparecem no cliente, no banco nem no log; repetir a pergunta responde; "Nova conversa" zera.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` sem erro.
- **Gate:** `nenhum — coberto por testes e sondagem`.

# 8. Destino da síntese
**Destino:** `specs/04.02-interface.md`, **substituindo** a regra de que cada mensagem é independente e o histórico é só de exibição.

Escrever: a conversa tem memória das últimas `chat.history_turns` mensagens anonimizadas; recuperação e mensagem ao LLM as usam, a classificação não; hash do chat com
identificador e número da mensagem (repetir pergunta responde); botão "Nova conversa"; privacidade (mensagens anteriores anonimizadas também vão ao provedor).
Levar também: `specs/03.02` §2.2 (bloco `CONVERSA ANTERIOR`), `specs/arquitetura/04.03-orquestracao-rpa.md` (`process_request(..., conversation)`, recuperação e hash do chat) e
`specs/05.01-validacao-e-entrega.md` §2.5 se ela ainda disser "sem conversa multi-turno".

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-11

**Resultado:** Concluído com pendências

**O que foi feito**
- `chat.history_turns` (inteiro positivo, padrão 6) em `config/settings.json:11` e em `Settings.chat_history_turns` (`src/triage/config.py:25`, `:50`, `:152`), com o mesmo tratamento de campo ausente/inválido (`_is_positive_int`, `_positive_int`: `config.py:97`, `:118`). Bool, texto, decimal, zero e negativo voltam ao padrão com `WARNING`.
- `Conversation(id, turn, messages)` e `message_hash(text, conversation)` em `src/triage/pipeline/processor.py:85` e `:288`; `process_request(request, deps, conversation=None)` (`:298`). Classificação e decisão usam só a mensagem atual (`_triage`, `:263`); a recuperação (`top_candidates` e `find`) usa `_Turn.search_text` = atual + anteriores (`:105`); `answer_with_sources` recebe o histórico. O banco grava só a mensagem atual anonimizada. Sem conversa, o `digest` continua `request_hash(texto)` e o fluxo é o mesmo de antes.
- Bloco `CONVERSA ANTERIOR` em `src/triage/automation/rag.py:20` (delimitadores), `:66` (`_history_block`), `:72` (`build_rag_message(text, sources, history=())`), `:82` (`answer_with_sources(..., history=())`). Os quatro delimitadores são neutralizados no pedido, nas mensagens anteriores e no `content` das fontes. O bloco só existe com histórico não vazio e fica antes das fontes.
- `AppService.submit(text, conversation=None)` (`src/triage/interface/service.py:87`): sanitiza e anonimiza cada mensagem anterior (`_anonymize_message`, `:199`; `_anonymize_conversation`, `:207`) antes de entregar ao pipeline; a anterior vazia ou acima do limite de tamanho é descartada. `AppService.history_turns` (`:83`). O hash do feedback agora vem de `message_hash` (`_outcome_from`, `:215`), o mesmo que o pipeline gravou.
- Tela (`src/triage/interface/views.py`): identificador da conversa na sessão, `_current_conversation` (`:91`, últimas `history_turns` perguntas e número da mensagem), botão "Nova conversa" (`:99`, `:101`) e `_reset_conversation` (`:84`: limpa histórico, avaliações e troca o identificador).
- README: seção "Conversa com memória" (`README.md:45`) com a memória, o botão e o que a mais vai ao provedor.
- Testes novos e ajustados (sem rede), listados na tabela abaixo.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `config/settings.json` | alterado | seção `chat.history_turns` |
| `src/triage/config.py` | alterado | `CHAT_HISTORY_TURNS`, `Settings.chat_history_turns`, validação de inteiro positivo |
| `src/triage/pipeline/processor.py` | alterado | `Conversation`, `_Turn`, `message_hash`, `process_request(..., conversation)`, recuperação com histórico |
| `src/triage/automation/rag.py` | alterado | bloco `CONVERSA ANTERIOR` e neutralização dos quatro delimitadores |
| `src/triage/interface/service.py` | alterado | `submit(text, conversation)`, anonimização das anteriores, `history_turns`, hash do feedback |
| `src/triage/interface/views.py` | alterado | conversa na sessão, identificador, botão "Nova conversa" |
| `README.md` | alterado | seção "Conversa com memória" |
| `tests/pipeline/test_conversation.py` | criado | 14 testes do pipeline com conversa |
| `tests/interface/test_service_conversation.py` | criado | 9 testes do serviço com conversa |
| `tests/automation/test_rag.py` | alterado | 6 testes do bloco `CONVERSA ANTERIOR` |
| `tests/interface/test_chat.py` | alterado | dublê com `history_turns` e `conversation`; 4 testes novos (últimas N, identificador e número, "Nova conversa" duas vezes), 1 teste renomeado e 2 asserções ajustadas pelo botão |
| `tests/test_config.py` | alterado | `chat.history_turns` nos campos, tipos errados, seções e leitura completa |

**Verificações executadas**
- `git diff --stat` → 10 arquivos alterados mais 2 criados (`tests/pipeline/test_conversation.py`, `tests/interface/test_service_conversation.py`), todos dentro do §3.1.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/classification tests/test_config.py -q` → **685 passed, 1 failed**. A falha é `tests/test_config.py::test_shipped_config_equals_the_code_defaults` (`llm_enabled is False`) e **existe em HEAD** (ver Achados fora do escopo).
- `python -m ruff check <paths do §7>` → 1 erro, `src/triage/automation/allowlist.py:18` `UP033`, arquivo que não toquei; nenhum erro novo (corrigi 2 `I001` de import meus).
- `validate.py` do `padrao-python` nos `.py` tocados → 0 achados em `config.py`, `rag.py`, `processor.py`, `service.py`, `views.py`, `test_service_conversation.py`, `test_chat.py`, `test_config.py`; **2 achados de baixa confiança** em `tests/pipeline/test_conversation.py:26-27` (URLs `https://www.gov.br/...` de dado de teste) e os 2 de `tests/automation/test_rag.py:18-19`, que já existem em HEAD com o mesmo motivo.
- Mutação (testes quebram quando a regra quebra): busca sem o histórico → 3 falhas; hash sem a conversa → 3; classificação com o histórico → 1; histórico sem neutralizar delimitadores → 2. Arquivos restaurados e a suíte voltou a 51/51 nos três módulos novos.
- Sondagem no app real (`AppTest.from_file("app.py")`, pasta temporária com cópia de `data/`, cliente falso, catálogo real): 1ª mensagem "Meu nome é Maria Souza, meu CPF é 123.456.789-09 e preciso negociar o IPTU em atraso" → sem bloco; 2ª "me passe o link correto para parcelamento" → mensagem ao LLM com `<<<CONVERSA ANTERIOR` + `- Meu nome é [NOME], meu CPF é [CPF] e preciso negociar o IPTU em atraso` e a fonte `IPTU (imposto predial e territorial urbano)`; "Maria", "Souza" e "123.456.789-09" ausentes do cliente, do dump do banco e do log; a 2ª pergunta repetida foi processada (não "já registrado"); depois de "Nova conversa": 0 mensagens na tela, histórico `[]` e a 1ª mensagem seguinte sem bloco.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` → sem erro (2 execuções; saída descartada).

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** `snapshot` e `diff` da `code-limpeza-ambiente`: nenhum diretório temporário, contêiner, imagem, volume, rede nem branch novos; o diff de processos mostra só ruído do sistema (Chrome, svchost, indexador de busca e os `head`/`grep` do próprio comando). Pasta temporária da sondagem, snapshot e cópias de HEAD removidos; saída do notebook fora do repositório. O `diff` não aceitou `--tmp-prefix`; o snapshot sim.

**Critérios de aceite**
- [x] Pergunta de seguimento sem o assunto usa as mensagens anteriores — evidência: `tests/pipeline/test_conversation.py::test_follow_up_recovers_the_source_from_the_previous_message`, `tests/interface/test_service_conversation.py::test_follow_up_sends_the_anonymized_previous_message_and_recovers_the_iptu_source` (catálogo real: sozinha não recupera nada, com a anterior traz `property_tax`) e a sondagem.
- [x] Só texto anonimizado das anteriores vai ao LLM ou ao banco; nenhum log traz texto do usuário — evidência: `test_raw_previous_message_never_reaches_the_client_the_database_or_the_log`, `test_only_the_current_message_is_stored`, `test_no_log_has_the_previous_messages`, `test_log_never_has_the_previous_messages` e a sondagem.
- [x] Só as últimas `chat.history_turns` entram; o valor vem de `config/settings.json` — evidência: `tests/interface/test_chat.py::test_only_the_last_history_turns_questions_are_sent`, `test_history_turns_comes_from_the_settings`, `tests/test_config.py` (padrão, leitura, tipos errados, seção ausente).
- [x] Repetir a mesma pergunta no chat é respondido; o lote continua idempotente — evidência: `test_the_same_question_is_answered_in_each_message_and_each_conversation`, `test_resending_the_same_message_of_the_same_conversation_is_a_duplicate`, `test_batch_without_a_conversation_keeps_hashing_the_text_and_deduplicating`, `test_a_request_without_a_conversation_still_deduplicates`; suíte do pipeline existente verde.
- [x] Classificação, urgência, ambíguo e modelo ausente seguem pela mensagem atual e sem LLM — evidência: `test_classification_and_decision_see_only_the_current_message`, `test_urgent_and_ambiguous_with_a_conversation_never_call_the_client`, `test_missing_model_with_a_conversation_never_calls_the_client`.
- [x] "Nova conversa" limpa histórico, memória e avaliações e começa outra conversa — evidência: `test_new_conversation_clears_the_screen_the_memory_and_the_ratings_and_changes_the_id`, `test_new_conversation_does_not_carry_the_old_ratings_to_the_new_answers` e a sondagem.
- [ ] README descreve o que a mais vai ao provedor; ambiente e worktree limpos; testes do escopo, `ruff` e validador sem violação nova — README (`README.md:45`) e ambiente limpos; `ruff` sem erro novo; **parcial**: 1 teste do escopo falha (anterior à mudança) e o validador tem 2 achados de baixa confiança novos em arquivo de teste (URLs de dado de teste).
- [x] O notebook de evidências continua executando sem erro — evidência: `nbconvert --execute` sem erro.

**Decisões e suposições**
- `Conversation` leva um campo `turn` além do identificador e das mensagens: o número da mensagem não pode vir do tamanho de `messages`, que é um recorte das últimas N; sem `turn`, da (N+1)-ª mensagem em diante a mesma pergunta repetida geraria o mesmo hash. Quem mantém a conversa (a tela) conta todas as mensagens.
- O hash do chat é `request_hash("<id>|<turn>|<texto anonimizado>")`. `message_hash` é público porque o hash do feedback (`SubmitOutcome.request_hash`) tem de ser o que o pipeline gravou.
- `Conversation` e `message_hash` são importados de `triage.pipeline.processor`, como o serviço já faz com os `STATUS_*`: **não editei `src/triage/pipeline/__init__.py`**, que não está no §3.1.
- A tela corta as últimas `history_turns` perguntas pelo `AppService.history_turns` (propriedade nova); o serviço sanitiza e anonimiza cada uma, e descarta as vazias ou acima de `MAX_TEXT_LENGTH`. Perguntas com desfecho inválido ou erro também contam como anteriores; o serviço as filtra por tamanho/vazio, não por desfecho.
- Texto de recuperação = atual, depois as anteriores em ordem cronológica, separados por quebra de linha. Os delimitadores são `<<<CONVERSA ANTERIOR` e `CONVERSA ANTERIOR>>>`, e cada mensagem entra como `- <texto>`.
- Sem o LLM, a recuperação determinística (`find`) também usa o histórico, como o §2.1 manda para `top_candidates` e `find`.
- O botão "Nova conversa" fica sempre visível no topo da aba, mesmo com a conversa vazia.
- Terminações de linha CRLF da árvore de trabalho preservadas nos arquivos editados e criados.

**Achados fora do escopo (não corrigidos)**
- `tests/test_config.py:91` — `test_shipped_config_equals_the_code_defaults` falha em HEAD: o commit `9cc58c7` pôs `"enabled": true` em `config/settings.json:4` e o teste ainda afirma `llm_enabled is False`. Ou o teste ou o padrão entregue precisa mudar; é decisão do revisor.
- `data/agents/triage-assistant/workflow.md:5-7` — descreve só `<<<PEDIDO`…`PEDIDO>>>` e manda ignorar instrução "dentro dele"; não menciona o bloco `CONVERSA ANTERIOR`. Fora do §3.1. Hoje a proteção é a neutralização dos delimitadores e a guarda de saída (`validate_rag_output`), que independem do prompt.
- `src/triage/automation/allowlist.py:18` — `ruff UP033` (`lru_cache(maxsize=None)`), anterior e fora do escopo.

**Pendências / riscos**
- A anonimização reduz o risco, mas não o elimina: com o LLM ligado, as mensagens anteriores anonimizadas também saem rumo ao provedor a cada turno (declarado no README).
- Um histórico longo dilui o cosseno do localizador (`find` com `finder.min_score` e `finder.margin`). Não há conjunto rotulado de conversas, então o efeito nos limiares não foi medido.
- Os dois achados de baixa confiança do validador em `tests/pipeline/test_conversation.py:26-27` são URLs de dado de teste, do mesmo tipo dos que já existem em `tests/automation/test_rag.py:18-19`; mantive os literais porque a guarda de saída compara URL exata.
- Não rodei a suíte inteira (`pytest -q`) nem `ruff` em `run.py src tests`: o §7 pede os caminhos que rodei.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-11 — 🟢 Aprovado

**Verificado pelo revisor (sem confiar no resumo):**
- `git status`/`diff`: só arquivos do §3.1 (config, processor, rag, service, views, README e testes). `src/triage/pipeline/__init__.py` aparece em `status` mas não tem diferença de conteúdo (só aviso de fim de linha). `config/settings.json` ganhou só a seção `chat`.
- Diff lido por inteiro: `Conversation(id, turn, messages)` e `message_hash` (lote inalterado; chat com identificador e número); classificação e decisão só pela mensagem atual (`_triage`); recuperação e `find` com atual + anteriores; bloco `CONVERSA ANTERIOR` antes das fontes com os quatro delimitadores neutralizados (também no `content`); `submit` anonimiza cada mensagem anterior antes do pipeline; tela com identificador, últimas `history_turns` e botão "Nova conversa"; `chat.history_turns` validado como inteiro positivo.
- `pytest tests/automation tests/pipeline tests/interface tests/classification tests/test_config.py tests/evaluation -q` → 738 passed, 1 failed (`test_shipped_config_equals_the_code_defaults`, `llm.enabled: true` do commit anterior `9cc58c7`; existe em `HEAD`, fora do escopo).
- `ruff` nos caminhos do §7 → 1 erro, `UP033` em `allowlist.py:18`, pré-existente. `validate.py`: 0 achados nos 5 `.py` de produção; 2 `hardcoded` de baixa confiança em URL de dado de teste (`test_conversation.py`).
- Sondagem própria (serviço real, catálogo + base importada, cliente falso): mensagem de seguimento com anterior "Maria Souza, CPF …, IPTU em atraso" → a mensagem ao LLM traz `CONVERSA ANTERIOR` com `[NOME]` e `[CPF]` e nenhum dado bruto; banco e log sem "Maria", "Souza" ou o CPF; o mesmo número de mensagem na mesma conversa repetido → `duplicate`; mesma pergunta em outra conversa → processada.
- `nbconvert --execute notebooks/evidence.ipynb` → sem erro. Ambiente limpo.

**Fora do escopo, para o backlog:** `workflow.md` do agente não cita o bloco `CONVERSA ANTERIOR` (somado ao item 30); o efeito de uma conversa longa nos limiares do `find` não foi medido (risco declarado no README).
