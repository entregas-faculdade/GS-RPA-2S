---
tipo: "plan"
familia: "03"
item: "R03.15"
titulo: "Escolher a categoria da interação com o LLM, com saída segura sem ele"
dominio: "Automação"
status: "🟡 Em execução"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
