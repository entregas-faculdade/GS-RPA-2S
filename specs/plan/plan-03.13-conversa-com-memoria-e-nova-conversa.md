---
tipo: "plan"
familia: "03"
item: "R03.13"
titulo: "Dar memória à conversa do chat (mensagens anteriores anonimizadas) e um botão de nova conversa"
dominio: "Automação"
status: "🔴 A executar"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
