---
tipo: "plan"
familia: "03"
item: "R03.6"
titulo: "Responder em degraus no pipeline: serviço, canal geral, \"não tenho a informação\" e telefones de emergência"
dominio: "Automação"
status: "🔴 A executar"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[04.03-orquestracao-rpa]]", "[[04.02-interface]]", "[[03.02-resposta-final-e-llm]]", "[[02.02-confianca-e-revisao-humana]]"]
depende_de: "plan-03.05-localizador-de-servicos — precisa estar 🟢"
destino_sintese: "specs/arquitetura/04.03-orquestracao-rpa.md"
---

# 1. Objetivo
O pipeline passa a responder ao cidadão em três degraus — **(1)** serviço específico aprovado; **(2)** portal ou canal geral
aprovado do órgão certo, achado pelo localizador; **(3)** "não tenho essa informação", com encaminhamento humano — e, em
pedido urgente, mostra os telefones de emergência aprovados, sem nunca inventar link ou número.

# 2. Contexto
Fluxo atual (`pipeline/processor.py::_triage`): classifica; se a decisão não é `auto_answer`, o pedido vai à revisão e o
cidadão vê só "Encaminhamos seu pedido para atendimento humano." ([[04.02-interface]] §2.2). Pedidos como "alvará" ou
"buraco na rua" (`out_of_catalog`) e o pedido de saúde urgente não recebem nenhuma ajuda. O localizador (plan anterior)
acha a fonte aprovada por texto; o catálogo v2 traz links, telefones e a área `safety` com os canais de emergência.

Decisões do grupo: o sistema só **roteia**; critério é ser serviço público; **sem fonte efetiva, o cidadão é informado de que
o sistema não tem a informação**; o texto de interação pode ser melhorado por LLM (plan posterior), mas link e telefone
só saem do catálogo aprovado.

## 2.1 Regras do fluxo (decisão desta plan)
Ordem fixa em `_triage`, preservando todo o resto:
1. Modelo ausente → revisão `low_confidence`, mensagem genérica de hoje (não muda).
2. `triage_decision` decide. **`urgent`** → revisão com mensagem de emergência (§2.2). Sem localizador nem resolução.
3. `auto_answer` → como hoje (degrau 1: `resolve_service` e `build_response`); link fora do ar → revisão
   `link_unavailable`, como hoje.
4. `out_of_catalog` ou `low_confidence` → chama o localizador com o texto **anonimizado**:
   - achou → `resolve_entry` verifica os links; vivo → resposta `answered` (degrau 2, ou degrau 1 se `kind=service`);
     sem link vivo → revisão `link_unavailable`;
   - não achou → revisão com o **mesmo motivo** de antes e a mensagem "não tenho a informação" (degrau 3).
5. `ambiguous` → revisão, como hoje, mensagem genérica (duas categorias plausíveis exigem pessoa).

Persistência **sem mudança de esquema**: o registro grava a categoria e a confiança do classificador e `status`
`answered` ou `queued_for_review` como hoje; o degrau vira o campo `tier` do `ProcessingResult` (`catalog` ou `finder`;
`None` quando não respondeu) e entra no relatório.

## 2.2 Mensagens
Textos fixos em português, nunca gerados por LLM:
- **não tenho a informação:** diz que o sistema não encontrou fonte oficial para o pedido e que ele foi encaminhado a
  atendimento humano; não promete prazo.
- **emergência:** "Se há risco imediato à vida ou à segurança, ligue agora:" seguido de um telefone por canal `approved`
  de `area=safety` e `kind=channel` do catálogo (`rótulo: número`), mais a frase de que o pedido também foi encaminhado
  a atendimento humano. Sem nenhum canal aprovado: só a frase de encaminhamento prioritário, com log `WARNING`; nunca um
  número escrito no código.
- **degrau 2:** o template de `kind` `portal`/`channel` abre dizendo que **não foi achado um serviço específico** e que o
  canal oficial indicado é o do órgão; depois nome, órgão, abrangência, instruções, links e telefones. A fonte vem do
  localizador, que errou 3 de 18 pedidos sem fonte na amostra de teste: o texto deve soar como **sugestão** ("pode atender
  ao seu pedido; se não for o que procura, o pedido segue para atendimento humano"), nunca como resposta certa.

# 3. Escopo
## 3.1 Dentro
- `src/triage/pipeline/processor.py` — `_triage`, `Deps` (+ `finder`), `ProcessingResult` (+ `tier`), `build_deps`
- `src/triage/pipeline/report.py` — contagem por degrau no relatório JSON e Markdown
- `src/triage/automation/templates.py` — texto do degrau 2 conforme o `kind`
- `src/triage/automation/messages.py` (novo) — mensagens "não tenho a informação" e de emergência
- `src/triage/interface/service.py` — `_outcome_from` mostra a mensagem de `response_text` quando o pedido foi à revisão
- `tests/pipeline/`, `tests/interface/`, `tests/automation/` — testes novos e ajustes

## 3.2 Fora
- `src/triage/classification/`, `triage.privacy`, `triage.storage` (esquema), `triage.automation.finder`/`catalog` (só são usados).
- `src/triage/interface/views.py` (a tela já mostra a mensagem do `SubmitOutcome`; mexer só se um teste provar que não).
- Qualquer chamada a LLM nova; `data/` e `README.md`.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[04.03-orquestracao-rpa]] | pipeline, relatório e ordem de etapas |
| Spec fixa | [[04.02-interface]] | desfechos mostrados ao cidadão |
| Spec fixa | [[03.02-resposta-final-e-llm]] · [[03.01-catalogo-e-allowlist]] | template, guarda e catálogo v2 |
| Spec fixa | [[02.02-confianca-e-revisao-humana]] | motivos de revisão e ordem dos gatilhos |
| Spec fixa | [[03.03-localizador-de-servicos]] (após a síntese da plan anterior; antes, a própria plan-03.05) | contrato do localizador |
| ADR | [[003-seguranca-sem-autenticacao]] · [[005-llm-apenas-reformula-resposta]] | só texto anonimizado; link só do catálogo |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | limiares; função ≤ 40 linhas (a `_triage` hoje é curta: dividir) |
| Skill | `test-unitario` | testes com fakes |
| Código | `src/triage/pipeline/*.py`, `src/triage/interface/service.py`, `src/triage/automation/*.py`, `tests/pipeline/conftest.py`, `tests/interface/conftest.py` | o que será alterado |

# 5. Instruções de execução
1. [dirigido] **Fluxo.** Implementar o §2.1 em `processor.py`, dividindo a lógica em funções pequenas (limite do Nível 0).
   `Deps.finder` é opcional (`None` = sem localizador: o degrau 2 fica de fora e o fluxo cai no degrau 3);
   `build_deps` o monta com `lookup.approved_entries()` e os limiares de `Settings`. `ProcessingResult.tier` novo.
2. [dirigido] **Mensagens.** `messages.py` com as duas mensagens do §2.2 e função que monta a de emergência a partir das
   entradas aprovadas de `safety`. O `ProcessingResult` de revisão com mensagem leva o texto em `response_text`.
3. [dirigido] **Template.** `render_template` muda a abertura quando `service.kind != "service"` (§2.2). O texto do
   `kind=service` permanece exatamente como estava depois da plan do catálogo v2.
4. [dirigido] **Interface.** `AppService._outcome_from`: pedido `queued_for_review` com `response_text` mostra esse texto
   (tipo `human_review`, sem botões de avaliação); sem texto, a mensagem genérica de hoje. Respondido pelo degrau 2 mostra
   a resposta e os botões 👍/👎, como qualquer respondido.
5. [dirigido] **Relatório.** `report.py` conta respondidos por degrau (`catalog`, `finder`) e inclui no JSON e no MD, sem
   texto de pedido.
6. [dirigido] **Testes** (sem rede, com fakes de catálogo, localizador e `link_checker`): para cada linha do §2.1 um teste
   de pipeline (urgente com e sem canal de emergência; `auto_answer`; `out_of_catalog` achado, achado com link morto e não
   achado; `low_confidence` achado e não achado; `ambiguous`; modelo ausente); a mensagem de emergência traz **só** os
   telefones das entradas `approved` e `safety` (e nenhum de `candidate`); o texto do degrau 2; a interface para cada
   desfecho; o relatório com o degrau; **idempotência** (o mesmo pedido de novo continua `skipped_duplicate`); e que o texto
   enviado ao localizador é o anonimizado.
7. [dirigido] **Sonda manual (registrar no resumo).** Com o catálogo e o modelo reais (treinar o modelo em pasta
   temporária e removê-la), submeter via `AppService` estes pedidos e colar o desfecho de cada um: `Quero tirar o alvará
   de funcionamento`, `tem um buraco enorme na minha rua`, `dores no peito e falta de ar`, `como renovar a CNH`, `preciso de
   um passaporte para viajar`. Sem rede, relatar quais caíram em `link_unavailable`.
8. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Os cinco ramos do §2.1 têm teste e se comportam como descrito.
- [ ] A resposta de emergência lista só telefones de canais `approved` de `safety`; nenhum número escrito no código.
- [ ] Pedido não achado devolve a mensagem "não tenho a informação" e abre revisão com o motivo original.
- [ ] Nenhum link ou telefone chega ao cidadão sem estar no catálogo `approved` e (links) passar por `resolve_entry`.
- [ ] O localizador recebe só texto anonimizado; o esquema do banco não mudou; reexecutar não duplica.
- [ ] O relatório conta os degraus; a interface mostra a mensagem certa em cada desfecho; 👍/👎 só em respondido.
- [ ] Sonda do passo 7 registrada; ambiente e worktree limpos; testes do escopo verdes; `ruff` e validador sem violação; nenhuma chave no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — muda ProcessingResult e Deps, que runner, scheduler, relatório e interface consomem`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation tests/classification -q` → verde.
- `python -m ruff check src/triage/pipeline src/triage/automation src/triage/interface tests/pipeline tests/interface tests/automation` → sem erro.
- `validate.py` do `padrao-python` em `src/triage/pipeline`, `src/triage/automation`, `src/triage/interface` e nos testes → sem achado.
- O revisor repete a sonda do passo 7 com o catálogo real e rede, confere cada telefone da mensagem de emergência contra o
  catálogo e roda `python run.py` sobre `data/samples` (pasta temporária de saída) conferindo o relatório.
- **Gate:** `nenhum — coberto por testes de ramo e pela sonda`.

# 8. Destino da síntese
**Destino:** `specs/arquitetura/04.03-orquestracao-rpa.md` (e as regras de mensagem em `specs/04.02-interface.md` §2.2 e do
template em `specs/03.02-resposta-final-e-llm.md` §2.1)

Levar, **substituindo**: a ordem do §2.1 (com o degrau de cada ramo), as três mensagens do §2.2, o campo `tier` e a
contagem no relatório, e o desfecho da interface para revisão com mensagem. O risco declarado: o degrau 2 pode apontar um
canal geral que não resolve o pedido; a revisão humana continua disponível pelo feedback 👎.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->
