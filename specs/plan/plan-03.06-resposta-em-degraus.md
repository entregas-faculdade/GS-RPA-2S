---
tipo: "plan"
familia: "03"
item: "R03.6"
titulo: "Responder em degraus no pipeline: serviço, canal geral, \"não tenho a informação\" e telefones de emergência"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[04.03-orquestracao-rpa]]", "[[04.02-interface]]", "[[03.02-resposta-final-e-llm]]", "[[02.02-confianca-e-revisao-humana]]"]
depende_de: "—"
destino_sintese: "specs/arquitetura/04.03-orquestracao-rpa.md"
---

# 1. Objetivo
O pipeline passa a responder ao cidadão em três degraus — **(1)** serviço específico aprovado; **(2)** portal ou canal geral
aprovado do órgão certo, achado pelo localizador; **(3)** "não tenho essa informação", com encaminhamento humano — e, em
pedido urgente, mostra os telefones de emergência aprovados, sem nunca inventar link ou número.

# 2. Contexto
Fluxo atual (`pipeline/processor.py::_triage`): classifica; se a decisão não é `auto_answer`, o pedido vai à revisão e o
cidadão vê só "Encaminhamos seu pedido para atendimento humano." ([[04.02-interface]] §2.2). Pedidos como "alvará" ou
"buraco na rua" (`out_of_catalog`) e o pedido de saúde urgente não recebem nenhuma ajuda. O localizador ([[03.03-localizador-de-servicos]])
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
  ao seu pedido; se não for o que você procura, descreva o pedido de outra forma ou procure o atendimento do próprio
  órgão"), nunca como resposta certa e **sem prometer encaminhamento humano**: o pedido respondido no degrau 2 não entra
  na fila de revisão, e o 👎 só grava a avaliação.

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
| Spec fixa | [[03.03-localizador-de-servicos]] | contrato do localizador |
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
canal geral que não resolve o pedido; o pedido respondido não vai à revisão e o 👎 só grava a avaliação, então o texto
orienta o cidadão a reformular ou procurar o órgão.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências (a verificação do revisor com rede e `run.py`, reservada a ele pela §7, e um erro de `ruff` preexistente fora do escopo; ver abaixo)

**O que foi feito**
- `src/triage/pipeline/processor.py` — `_triage` reescrita em funções pequenas (`_answer_or_review`, `_find_or_review`, `_urgent_review`, `_answered`, `_failed_resolution`) na ordem do §2.1: modelo ausente → `auto_answer` → urgente → `out_of_catalog`/`low_confidence` pelo localizador → `ambiguous`. `Deps.finder` opcional (`None` cai no degrau 3), `ProcessingResult.tier` (`catalog`/`finder`/`None`), `build_deps` monta `ServiceFinder(lookup.approved_entries(), settings)`.
- `src/triage/automation/messages.py` (novo) — mensagem "não tenho a informação" e a de emergência, montada só de entradas `approved`, `area=safety`, `kind=channel`; sem canal devolve só o encaminhamento prioritário e loga `WARNING`.
- `src/triage/automation/templates.py` — `kind != service` abre com "Não encontrei um serviço específico…" como sugestão; `kind=service` inalterado.
- `src/triage/interface/service.py` — `_outcome_from` mostra `response_text` quando o pedido foi à revisão (sem botões), senão a mensagem genérica.
- `src/triage/pipeline/report.py` — `tiers` no JSON e tabela "Respondidos por degrau" no Markdown.
- Testes novos; nenhum teste existente foi alterado.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/pipeline/processor.py` | alterado | fluxo em degraus, `Deps.finder`, `ProcessingResult.tier` |
| `src/triage/pipeline/report.py` | alterado | contagem e tabela por degrau |
| `src/triage/automation/templates.py` | alterado | abertura do degrau 2 por `kind` |
| `src/triage/automation/messages.py` | criado | mensagens de "sem informação" e de emergência |
| `src/triage/interface/service.py` | alterado | revisão com mensagem própria |
| `tests/automation/test_messages.py` | criado | mensagens e template do degrau 2 |
| `tests/pipeline/test_tiers.py` | criado | um teste por ramo do §2.1, anonimização, idempotência |
| `tests/pipeline/test_report_tiers.py` | criado | contagem por degrau no relatório |
| `tests/interface/test_service_tiers.py` | criado | desfecho de tela de cada degrau |

**Verificações executadas**
- `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation tests/classification -q` → 481 passed (o subconjunto automation/pipeline/interface tinha 285 passed antes das mudanças).
- `python -m ruff check src/triage/pipeline src/triage/automation src/triage/interface tests/pipeline tests/interface tests/automation` → 1 erro, **fora do escopo** (UP033 em `src/triage/automation/allowlist.py:18`, preexistente). Nos arquivos que toquei: sem erro (corrigi 3 `I001` de ordenação de import que eu mesmo gerei; reexecutado só neles: "All checks passed").
- `validate.py` do `padrao-python` em `src/triage/pipeline`, `src/triage/automation`, `src/triage/interface` e `tests/interface` → 0 achados; em `tests/pipeline` e `tests/automation` só `hardcoded` de baixa confiança (URL literal em teste, mesmo padrão dos testes existentes). Um `thresholds` real que ele apontou (função de teste com 6 parâmetros) foi corrigido e o validador reexecutado sem achado não-`hardcoded`.
- Sonda do passo 7 (catálogo real, modelo treinado em memória com `data/labeled/requests_labeled.csv` — nenhum arquivo de modelo gravado —, banco em pasta temporária removida; **havia rede**, nenhum link caiu em `link_unavailable`):
  - `Quero tirar o alvará de funcionamento` → `answered`, degrau 2: "Não encontrei um serviço específico para o seu pedido. O canal oficial indicado é o do órgão: Alvará de funcionamento e IPTU municipal (caminho geral)…", três links do SP156 e `Central 156: 156`.
  - `tem um buraco enorme na minha rua` → `answered`, degrau 2: SP156 (zeladoria), mesmos links e telefone.
  - `dores no peito e falta de ar` → `human_review` (`urgent`): "Se há risco imediato à vida ou à segurança, ligue agora:" + Polícia Militar 190, Corpo de Bombeiros 193, SAMU 192, Defesa Civil 199, Disque Direitos Humanos 100, Central de Atendimento à Mulher 180 + "O seu pedido também foi encaminhado a atendimento humano."
  - `como renovar a CNH` → `answered`, degrau 1: texto do serviço, link da CNH digital.
  - `preciso de um passaporte para viajar` → `human_review` (`out_of_catalog`): "Não encontrei uma fonte oficial para o seu pedido, por isso não tenho essa informação. O seu pedido foi encaminhado a atendimento humano."
  - Fila após a sonda: motivos `urgent` e `out_of_catalog`.
- Busca por `plan-0` em `src` e `tests` → nenhum resultado (nenhum comentário cita plan).
- **Não rodei** `python run.py` sobre `data/samples` nem a suíte inteira: a §7 reserva ao revisor.

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`, limpa).

**Ambiente após a verificação:** `snapshot` antes e `diff` depois (`code-limpeza-ambiente`). O `diff` lista dezenas de processos novos e encerrados (shells, `Code.exe`, `chrome.exe`…) que ele mesmo declara não atribuíveis: a máquina é compartilhada e não consegui separar o que é meu; não iniciei servidor, contêiner nem processo deixado de pé. O único artefato criado (pasta temporária da sonda, com o banco SQLite) foi removido e confirmei que não existe mais. O snapshot fica no scratchpad da sessão, fora do repositório.

**Critérios de aceite**
- [x] Os cinco ramos do §2.1 têm teste — evidência: `tests/pipeline/test_tiers.py` (urgente com e sem canal, `auto_answer` e link morto, `out_of_catalog`/`low_confidence` achado, achado com link morto e não achado, `ambiguous`, modelo ausente, sem localizador).
- [x] Emergência só com telefones `approved` de `safety`, nenhum número no código — evidência: `test_urgent_request_shows_only_approved_safety_phones_and_skips_the_finder` (exclui `candidate` e canal de outra área), `test_urgent_request_with_real_catalog_lists_only_catalog_numbers`, `tests/automation/test_messages.py`; `messages.py` não contém número de telefone.
- [x] Pedido não achado devolve "não tenho a informação" e abre revisão com o motivo original — `test_source_not_found_says_no_information_and_keeps_the_original_reason` (nos dois motivos).
- [x] Nenhum link ou telefone chega sem estar `approved` e (links) sem `resolve_entry` — o degrau 2 passa por `deps.lookup.resolve_entry`; `test_found_source_with_dead_link_goes_to_review_link_unavailable`.
- [x] Localizador recebe só texto anonimizado; esquema não mudou; reexecutar não duplica — `test_finder_receives_only_the_anonymized_text`, `test_same_request_again_is_skipped_for_every_tier`; `src/triage/storage/` não foi tocado.
- [x] Relatório conta os degraus; interface mostra a mensagem certa; 👍/👎 só em respondido — `test_report_tiers.py`, `test_service_tiers.py` (`request_hash` só em `answered`).
- [x] Sonda registrada; testes do escopo verdes; validador sem violação real nos arquivos tocados; nenhuma chave no diff.
- [ ] `ruff` sem erro em todos os caminhos da §7 — motivo: 1 erro preexistente fora do escopo (ver achados); nos arquivos que toquei não há erro.

**Decisões e suposições**
- O `tier` de uma fonte achada pelo localizador é sempre `finder`, mesmo com `kind=service` (o §2.1 diz "degrau 1 se `kind=service`", mas o campo só admite `catalog`/`finder`). Nesse caso o texto ao cidadão é o do serviço, sem a abertura de sugestão.
- A ordem implementada põe `auto_answer` antes da checagem de urgência; é equivalente ao §2.1, pois `triage_decision` já dá prioridade à urgência e então `auto_answer` nunca coexiste com `urgent`.
- Mensagem de emergência: lista todos os telefones de cada canal elegível e **não repete** o mesmo par `rótulo: número` (o catálogo tem `fire_brigade_193` e `gap_fire_brigade` com o mesmo 193).
- A redação dos textos fixos do §2.2 é minha, seguindo as frases que a plan exige; "não promete prazo" é verificado por teste.
- Modelo ausente com pedido urgente continua `low_confidence` genérico (regra 1 do §2.1 vem antes).
- Falha de resolução da fonte achada devolve a revisão com o motivo da resolução (`link_unavailable`) e **sem** mensagem própria, como o §2.1 descreve; a tela mostra a genérica.
- Os testes de ramo fixam a decisão do classificador (`monkeypatch` de `triage_decision`) para não depender do modelo treinado; os casos urgente e `auto_answer` usam o modelo real.
- `KIND_CHANNEL` ficou como constante local em `messages.py` para não tocar `catalog.py` (fora do escopo, §3.2).

**Achados fora do escopo (não corrigidos)**
- `src/triage/automation/allowlist.py:18` — ruff UP033 (`lru_cache(maxsize=None)` → `functools.cache`); faz o comando de ruff da §7 sair com erro.
- Na sonda, `dores no peito e falta de ar` lista também Polícia, Defesa Civil, Direitos Humanos e Mulher: é o que a plan manda (todo canal `approved` de `safety`), mas pode ser ruído num caso de saúde; decisão de produto do revisor.
- O pedido respondido pelo degrau 2 grava a `category` do classificador (`other`), pois o esquema não muda; `by_category` do relatório passa a contar `other` entre respondidos.

**Pendências / riscos**
- O revisor repete a sonda e roda `python run.py` sobre `data/samples` (§7). Não rodei a suíte inteira.
- O degrau 2 pode indicar canal geral que não resolve (o localizador errou 3 de 18 pedidos sem fonte no `test`, [[03.03-localizador-de-servicos]] §2.3). O texto é de sugestão. A plan (§8) afirma que o 👎 abre a revisão humana; não verifiquei nem alterei o comportamento do feedback.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->

## Veredito — 2026-11-10 — 🔴 Reprovado

Verifiquei, sem confiar no resumo: o escopo bate com o §3.1 (5 arquivos alterados e 5 novos, nenhum fora da lista; `storage`, `classification`, `finder` e `catalog` intactos); `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation tests/classification -q` → 481 passed; `ruff` só com o `UP033` de `allowlist.py` (anterior, backlog item 14); `validate.py` nos três pacotes e nos testes → nenhum achado fora `hardcoded` de baixa confiança; nenhuma plan citada em código. Código lido inteiro: a ordem do §2.1 está implementada, o localizador recebe o texto anonimizado, `resolve_entry` verifica o link do degrau 2, a emergência sai só de entradas `approved` de `safety` e `channel`, e o esquema do banco não mudou. Repeti a sonda com o catálogo real e rede (alvará e buraco → degrau 2 pelo SP156; `dores no peito e falta de ar` e `meu pai está desmaiado` → emergência; CNH → degrau 1; passaporte e capital da França → "não tenho a informação"; CPF no texto e IPTU → degrau 1) e rodei `python run.py --input data/samples --output <pasta temporária>`: código 0, 5 respondidos (`tiers`: 4 `catalog`, 1 `finder`), 3 em revisão, 7 rejeitados por entrada inválida, relatório JSON e Markdown com a tabela por degrau. Um achado bloqueia:

1. `src/triage/automation/templates.py:13` — o texto do degrau 2 diz "se não for o que você procura, o pedido segue para atendimento humano", e isso **não é verdade**: o pedido respondido tem `status` `answered`, não entra na fila de revisão (`pending_reviews`), e `AppService.send_feedback` (`service.py:102-111`) só grava a avaliação. O cidadão recebe uma promessa que o sistema não cumpre. O defeito nasceu do meu texto do §2.2 e do §8 da plan, que afirmavam o encaminhamento pelo 👎; ambos foram corrigidos agora. Critério violado: nenhuma informação falsa ao cidadão (§2.2 e ADR 005, o robô só roteia e não promete o que não faz). **Correção exata** (arquivo `src/triage/automation/templates.py`, uma linha):
   - antes: `"Ele pode atender ao seu pedido; se não for o que você procura, o pedido segue para atendimento humano.
"`
   - depois: `"Ele pode atender ao seu pedido; se não for o que você procura, descreva o pedido de outra forma ou procure o atendimento do próprio órgão.
"`
   - mais um teste em `tests/automation/test_messages.py` que prove que o texto do degrau 2 (`kind` `portal` e `channel`) **não contém** a palavra "humano" e contém "descreva o pedido de outra forma"; o teste de mensagem do `kind=service` continua como está.
   - verificação: `python -m pytest tests/automation tests/pipeline tests/interface -q` verde.


---

## Resumo da execução (correção 1) — 2026-11-10

**Resultado:** Concluído

**Achado 1 — o texto do degrau 2 prometia encaminhamento humano que o sistema não cumpre**
- `src/triage/automation/templates.py:13` — apliquei o antes→depois do veredito: "…se não for o que você procura, o pedido segue para atendimento humano." virou "…se não for o que você procura, descreva o pedido de outra forma ou procure o atendimento do próprio órgão."
- `tests/automation/test_messages.py` — novo `test_general_channel_template_does_not_promise_human_review`, parametrizado em `kind` `portal` e `channel`: o texto **não contém** "humano" e contém "descreva o pedido de outra forma". O teste do `kind=service` (`test_service_template_keeps_its_original_opening`) ficou como estava.
- Consequência direta da correção: removi do teste `test_general_channel_template_opens_as_suggestion_and_keeps_the_sections` a asserção `"atendimento humano" in text`, que passou a contradizer o achado. As demais asserções dele permanecem.

**Verificação:** `python -m pytest tests/automation tests/pipeline tests/interface -q` → 319 passed (eram 317 antes da correção, com 2 casos novos parametrizados). `python -m ruff check src/triage/automation/templates.py tests/automation/test_messages.py` → sem erro.

**Estado inicial do worktree:** os arquivos do `src` e `tests` desta plan modificados ou novos (da execução anterior), mais `specs/00-backlog.md`, `specs/00-indice.md` e `specs/panorama/00-resumo.md` alterados pelo revisor; não toquei nesses três.

**Ambiente:** nada criado (só `pytest` e `ruff`, sem processo, servidor ou arquivo temporário remanescente).

**Decisões e suposições**
- Nenhuma além da asserção removida acima. Nada além do achado foi alterado.

**Achados fora do escopo (não corrigidos):** nenhum novo.

**Pendências / riscos:** nenhuma nova. Permanece o que o revisor já tratou (`UP033` em `allowlist.py`, backlog item 14).

## Veredito — 2026-11-10 — 🟢 Aprovado (correção 1)

Verifiquei o achado 1 sem confiar no resumo: o diff de `templates.py` troca exatamente a frase pedida ("…descreva o pedido de outra forma ou procure o atendimento do próprio órgão."); renderizei o template de um portal real do catálogo e a abertura sai com o texto novo. `tests/automation/test_messages.py` tem o teste novo parametrizado em `portal` e `channel` (sem "humano", com "descreva o pedido de outra forma"); a asserção `"atendimento humano"` que sobra na linha 30 é a da mensagem "não tenho a informação", que é verdadeira porque aquele pedido vai à fila de revisão. Regressão: `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation tests/classification -q` → 483 passed; `ruff` só com o `UP033` anterior de `allowlist.py` (backlog item 14); `validate.py` em `test_messages.py` sem achado. A sonda real, o `run.py` sobre `data/samples` e o restante da verificação do veredito anterior continuam válidos, pois a correção só mudou uma frase e seu teste.
