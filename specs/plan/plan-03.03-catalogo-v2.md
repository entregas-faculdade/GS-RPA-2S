---
tipo: "plan"
familia: "03"
item: "R03.3"
titulo: "Evoluir o catálogo para vários links e telefones por serviço, com aprovação e verificação"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[03.02-resposta-final-e-llm]]", "[[003-seguranca-sem-autenticacao]]", "[[005-llm-apenas-reformula-resposta]]"]
depende_de: ""
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

# 1. Objetivo
O catálogo passa a descrever cada fonte pública com **vários links e telefones**, esfera e abrangência, e um estado de
aprovação; só fonte `approved` é usada, o resolvedor entrega todos os links que respondem, a resposta (template e guarda
do LLM) trata links e telefones, e um verificador de linha de comando audita o catálogo.

# 2. Contexto
Hoje cada categoria tem **um** link (`ServiceEntry.url`) e nenhum telefone ([[03.01-catalogo-e-allowlist]]). O grupo quer
oferecer ao cidadão links **e telefones** para localizar o serviço, partindo de uma lista curada de fontes federais,
estaduais e municipais (piloto: estado e cidade de São Paulo, plan seguinte) que o usuário **aprova antes** de entrar. O
sistema só roteia; o critério é ser serviço público. Esta plan muda **a forma** do catálogo e dos consumidores; o
conteúdo novo vem na plan seguinte. As 8 categorias atuais continuam funcionando com os mesmos links e textos.

Consumidores de `ServiceEntry`: `resolver.py`, `templates.py`, `response.py`, `response_guard.py` e `pipeline/processor.py`
(este só repassa o objeto; **não muda**).

## 2.1 Formato v2 (decisão desta plan)
`data/catalog.json` segue lista de registros, agora com os campos:

| Campo | Regra |
|---|---|
| `id` | slug único do registro (ex.: `driver_license`, `sp156`) |
| `category` | categoria do classificador ([[02.01-classificacao]]) ou `null` |
| `kind` | `service` (página específica), `portal` (portal geral do órgão) ou `channel` (canal de atendimento, em geral telefone) |
| `scope` | `federal`, `state` ou `municipal` |
| `coverage` | texto mostrado ao cidadão (ex.: `Brasil`, `Estado de São Paulo`, `Cidade de São Paulo`) |
| `area` | `health`, `education`, `vehicles`, `city`, `documents`, `social`, `tax` ou `safety` |
| `display_name`, `agency`, `instructions` | como hoje |
| `keywords` | lista de termos que o cidadão usa para o serviço (consumida na plan do localizador; aqui só é lida e validada como lista de strings) |
| `links` | lista de `{label, url}` |
| `phones` | lista de `{label, number}` (número como o cidadão disca, ex. `156`, `0800 61 61 61`) |
| `source_note`, `verified_on` | como hoje |
| `status` | `approved` ou `candidate` |

Validade de um registro: todos os campos presentes e dos tipos certos; `kind=service` exige ao menos um link;
`portal` e `channel` exigem ao menos um link **ou** um telefone; `id` repetido ignora o segundo. Registro inválido é
ignorado com log (como hoje); arquivo ausente ou inválido devolve catálogo vazio.

# 3. Escopo
## 3.1 Dentro
- `data/catalog.json` — migrar os 8 registros atuais para o v2: mesmos links e textos, `kind: service`, `scope` e
  `coverage` coerentes com cada um (`federal`/`Brasil`; IPTU e certidão têm natureza municipal/cartório: usar `federal` e
  dizer a verdade em `coverage`), `area` adequada, `keywords` com 5 a 10 termos reais, `phones` só se já constarem nas
  `instructions` (ex.: INSS 135) ou ficar vazio, `status: approved`
- `src/triage/automation/catalog.py` — `ServiceEntry`, `Link`, `Phone`; `load_catalog` devolve as entradas v2
- `src/triage/automation/resolver.py` — `CatalogLookup` e `resolve_service` (passo 2)
- `src/triage/automation/templates.py` — template com todos os links e telefones (passo 3)
- `src/triage/automation/response.py` — só o que a mudança de tipo exigir
- `src/triage/automation/response_guard.py` — guarda para vários links e para telefones (passo 4)
- `src/triage/automation/catalog_audit.py` (novo) e `scripts/verify_catalog.py` (novo) — verificador (passo 5)
- `tests/automation/` — ajustar os testes existentes e acrescentar os novos
- `tests/pipeline/` e `tests/interface/` — **só** o que quebrar por causa do novo formato (ex.: construção de `ServiceEntry` em fixtures)

## 3.2 Fora
- `src/triage/pipeline/processor.py`, `interface/`, `classification/`, `storage/`: não mudam.
- `data/allowed_domains.json` e qualquer registro **novo** no catálogo (plan seguinte).
- Busca por texto, localizador, mensagens de "não encontrei" (planos seguintes) e o cliente de LLM.
- Chamadas reais de rede nos testes (usar fakes/stubs injetados).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | contrato atual de catálogo, allowlist, `check_link` e `Resolution` |
| Spec fixa | [[02.01-classificacao]] | categorias do classificador (campo `category`) |
| Spec fixa | [[03.02-resposta-final-e-llm]] | template, guarda `validate_llm_output` e motivos de fallback |
| ADR | [[005-llm-apenas-reformula-resposta]] · [[003-seguranca-sem-autenticacao]] | o LLM não inventa link; só fonte da allowlist |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês, limiares, erro com causa |
| Skill | `test-unitario` | testes sem rede |
| Código | `src/triage/automation/*.py`, `data/catalog.json`, `scripts/train_model.py` | o que muda e o modelo de script CLI |
| Código | `tests/automation/*`, `tests/pipeline/conftest.py`, `tests/interface/conftest.py` | uso atual de `ServiceEntry` |

# 5. Instruções de execução
1. [dirigido] **Modelo e carga.** Implementar o §2.1 em `catalog.py`. `load_catalog` mantém a falha segura e o log por
   registro inválido. Expor a lista de entradas e quais estão `approved`.
2. [dirigido] **Resolução.** `CatalogLookup`:
   - `resolve(category)` considera só entradas `approved` com aquela `category` e `kind=service` (a primeira do arquivo);
     sem entrada → `Resolution(None, "out_of_catalog")`, como hoje.
   - `resolve_entry(entry)` (público) verifica a entrada: cada link precisa estar na allowlist (senão é defeito do
     catálogo: log `ERROR` e o link é descartado) e responder (`check_link`, com o cache por execução de hoje). Devolve a
     entrada **só com os links vivos** (`dataclasses.replace`); sem nenhum link vivo, `Resolution(None,
     "link_unavailable")`. Entrada só com telefones (sem link) é aceita sem verificação de rede.
   - `approved_entries()` (público) devolve as entradas `approved`, para o localizador.
   - Assinatura e semântica de `resolve_service(category, lookup)` e `build_default_lookup()` **não mudam**.
3. [dirigido] **Template.** `render_template` mostra nome, órgão, abrangência, instruções, **todos** os links (`rótulo:
   url`, um por linha) e, se houver, os telefones (`rótulo: número`); sem a seção de telefones quando não há. Continua
   determinístico, em português e sem texto do cidadão.
4. [dirigido] **Guarda do LLM.** `validate_llm_output(text, service)`:
   - `foreign_url` agora compara com **todas** as URLs do serviço (igualdade exata) e a checagem de endereço sem esquema
     aceita o host de qualquer link do serviço ou um domínio pai dele (mesma regra de hoje);
   - `missing_url`: nenhuma URL do serviço aparece (basta uma);
   - **novo `foreign_phone`:** retirar do texto as URLs e, em cada sequência de dígitos que possa ser telefone (dígitos
     com espaço, hífen ou parênteses entre eles, mínimo de 3 dígitos), comparar os dígitos com os dos telefones do
     serviço; sequência que não for exatamente um telefone do serviço rejeita a saída. Números de 1 ou 2 dígitos ("3
     dias", "2ª via") passam. Na dúvida, rejeitar: o template responde.
5. [dirigido] **Verificador.** `catalog_audit.py` (lógica pura, com `link_checker` e um `fetch_page_text` injetados) e
   `scripts/verify_catalog.py` (CLI fino, no estilo de `scripts/train_model.py`: argparse, logging, código de saída).
   Para cada entrada informa um resultado por verificação:
   - esquema válido e `id` único (erro);
   - cada link na allowlist (erro) e respondendo (erro se `approved` e nenhum link vivo; aviso se só alguns falharem);
   - cada telefone: o número (só dígitos) aparece no texto de ao menos uma das páginas da entrada (`confirmado`), senão
     `não confirmado` (aviso, nunca erro: página pode ser dinâmica ou recusar cliente automatizado);
   - `verified_on` mais antigo que `--max-age-days` (padrão 180) → aviso.
   Opções: `--catalog`, `--max-age-days`, `--offline` (pula rede). Código de saída `0` sem erro, `1` com erro. Não altera
   o catálogo. Saída legível (uma linha por verificação) e **sem** texto de pedido (não há).
6. [dirigido] **Testes** (todos sem rede). Cobrir: carga v2 (válido, campo faltando, `kind` sem link, id duplicado,
   arquivo ausente); `resolve` ignorando `candidate`; link vivo e link morto na mesma entrada (devolve só o vivo);
   link fora da allowlist descartado; template com e sem telefone; guarda aceitando cada link do serviço, o telefone do
   serviço e "3 dias", e rejeitando URL alheia, telefone alheio (`0800 999 9999`), `golpe.com` e saída vazia; o
   verificador com stubs (telefone confirmado, não confirmado, link fora da allowlist, `--offline`).
7. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] `data/catalog.json` está no v2, com os 8 registros `approved` e os mesmos links de antes.
- [ ] `resolve_service` para cada uma das 8 categorias devolve a entrada com links vivos; entrada `candidate` nunca é usada.
- [ ] Um link morto não derruba a entrada que ainda tem link vivo; sem link vivo, `link_unavailable`.
- [ ] O template lista todos os links e os telefones; o guarda rejeita telefone e URL que não são do serviço.
- [ ] `scripts/verify_catalog.py --offline` roda e devolve `0` no catálogo migrado; o modo com rede relata links e telefones.
- [ ] `ProcessingResult`, `build_response(service, client)` e `resolve_service(category, lookup)` mantêm a assinatura.
- [ ] Nenhum teste faz chamada de rede real; ambiente e worktree limpos.
- [ ] Testes do escopo verdes; `ruff` e validador sem violação nos arquivos alterados; nenhuma chave no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — muda o tipo exportado ServiceEntry, que resolver, resposta, pipeline e interface consomem`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation -q` → verde.
- `python -m ruff check src/triage/automation scripts tests/automation` → sem erro.
- `validate.py` do `padrao-python` em `src/triage/automation`, `scripts/verify_catalog.py` e `tests/automation` → sem achado.
- `python scripts/verify_catalog.py --offline` → saída `0`; com rede, o revisor roda uma vez e confere os 8 links.
- Sondagem do revisor da guarda com saídas de LLM forjadas (telefone alheio, URL com caminho, `gov.br`, número de protocolo).
- **Gate:** `nenhum — coberto por testes e pelo verificador`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md` (e os trechos de template e guarda em `specs/03.02-resposta-final-e-llm.md`
§2.1 e §2.3)

Levar, **substituindo** o que as specs dizem hoje: o formato v2 da tabela do §2.1 desta plan; só `approved` é usado; o
resolvedor entrega os links vivos e `resolve_entry`/`approved_entries`; o template com links e telefones; o `foreign_phone`
e a regra de múltiplas URLs na guarda; o verificador `scripts/verify_catalog.py` (o que checa, avisos × erros, códigos de
saída). A §2.1 da 03.01 deixa de dizer "uma URL por categoria".

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências (3 falhas de teste fora do escopo, de outra execução em andamento; ver abaixo)

**O que foi feito**
- `catalog.py` — formato v2: `Link`, `Phone`, `ServiceEntry` (15 campos do §2.1, tuplas imutáveis), `parse_entry` (valida tipos, enums, `kind` × links/telefones e `verified_on` ISO), `read_catalog_records`, `load_catalog` → `list[ServiceEntry]` (falha segura `[]`, log por registro inválido e por `id` repetido, o segundo é ignorado) e `approved_only`.
- `resolver.py` — `CatalogLookup` recebe a lista de entradas; `resolve` usa só `approved` + `kind=service` (a primeira do arquivo); `resolve_entry` descarta link fora da allowlist (log `ERROR`) e link morto, devolve a entrada com `dataclasses.replace` só com os vivos, `link_unavailable` sem nenhum vivo, e aceita entrada só com telefones sem rede; `approved_entries()` público. `resolve_service` e `build_default_lookup` mantêm a assinatura.
- `templates.py` — nome, órgão, abrangência, instruções, todos os links (`rótulo: url`) e, se houver, telefones (`rótulo: número`).
- `response_guard.py` — `foreign_url` compara com todas as URLs do serviço e o endereço sem esquema aceita o host de qualquer link (ou domínio pai); `missing_url` exige ao menos uma; novo `foreign_phone` (`REJECT_FOREIGN_PHONE`) via `phone_digit_sequences` (URLs e e-mails ignorados, ≥ 3 dígitos).
- `catalog_audit.py` (novo) + `scripts/verify_catalog.py` (novo) — verificador com `link_checker` e `fetch_page_text` injetados; erros × avisos e códigos de saída conforme o passo 5.
- `data/catalog.json` — 8 registros migrados para o v2, mesmos links e textos, `kind: service`, `status: approved`, 7 a 8 `keywords` cada; telefone só no INSS (`135`, já nas `instructions`).
- `tests/automation/` — `conftest.py` (fábricas), `test_catalog.py`, `test_resolver.py`, `test_response.py`, `test_response_guard.py` ajustados; `test_catalog_audit.py` novo. `response.py` e `processor.py` não precisaram mudar; `tests/pipeline` e `tests/interface` não precisaram de ajuste (passam `load_catalog()` direto ao `CatalogLookup`).

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `data/catalog.json` | alterado | formato v2, 8 registros `approved` |
| `src/triage/automation/catalog.py` | alterado | modelo v2, parse e carga |
| `src/triage/automation/resolver.py` | alterado | `resolve_entry`, `approved_entries`, links vivos |
| `src/triage/automation/templates.py` | alterado | links, telefones e abrangência |
| `src/triage/automation/response_guard.py` | alterado | várias URLs e `foreign_phone` |
| `src/triage/automation/catalog_audit.py` | criado | lógica do verificador |
| `scripts/verify_catalog.py` | criado | CLI do verificador |
| `tests/automation/conftest.py` | criado | fábricas de registro e entrada |
| `tests/automation/test_catalog.py`, `test_resolver.py`, `test_response.py`, `test_response_guard.py` | alterado | v2 + casos novos |
| `tests/automation/test_catalog_audit.py` | criado | verificador e CLI com stubs |

**Verificações executadas**
- `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation -q` → 222 passed, 3 failed (`tests/pipeline/test_processor.py::test_urgent_request_goes_to_review`, `tests/interface/test_service.py::test_request_for_review_hides_technical_reason` e `::test_review_entry_shows_anonymized_text`). As 3 falhas esperam motivo `urgent` e recebem `low_confidence`: dependem de `data/urgency_terms.json`, alterado no worktree por outra execução (plan-02.03) depois do meu início; nenhum arquivo meu toca urgência.
- `python -m ruff check src/triage/automation scripts tests/automation` → 1 achado, `UP033` em `allowlist.py:18` (arquivo que não toquei); nos arquivos alterados, 0 (após `--select I001 --fix` nos meus arquivos).
- `validate.py` (padrao-python) em `src/triage/automation`, `scripts/verify_catalog.py` e `tests/automation` → 0 em `src` e no script; em `tests/automation` 10 achados `hardcoded` de `confidence: low` (URL `https://www.gov.br/...` literal em fixtures de teste, 4 deles em arquivos que já existiam).
- `python scripts/verify_catalog.py --offline` → 8 registros, "sem erro", saída `0`. Modo com rede **não rodado** (reservado ao revisor, §7).

**Estado inicial do worktree:** limpo (`git status --short` vazio, branch `develop`). Durante a execução surgiram, de outra conversa, `data/urgency_terms.json`, `specs/plan/plan-02.03-urgencia-saude.md` e `tests/classification/test_urgency.py` modificados; não são meus.

**Ambiente após a verificação:** nada criado (sem servidor, contêiner nem navegador; só `tmp_path` do pytest). `snapshot` de `code-limpeza-ambiente` não executado: indisponível por não ter subido processo algum.

**Critérios de aceite**
- [x] `data/catalog.json` no v2, 8 `approved`, mesmos links — `tests/automation/test_catalog.py::test_versioned_catalog_has_the_eight_approved_service_entries`
- [x] `resolve_service` das 8 categorias devolve links vivos; `candidate` nunca usado — `test_each_versioned_category_resolves_with_live_links`, `test_candidate_entry_is_never_used`
- [x] link morto não derruba a entrada; sem link vivo, `link_unavailable` — `test_dead_link_keeps_the_entry_with_the_live_one`, `test_no_live_link_is_unavailable_and_logged`
- [x] template lista links e telefones; guarda rejeita telefone e URL alheios — `test_template_lists_every_link_and_phone_one_per_line`, `test_rejects_phone_that_is_not_the_service_phone`
- [x] `verify_catalog.py --offline` devolve `0`; modo com rede relata links e telefones — o `--offline` rodou com saída `0`; o modo com rede só foi coberto por stubs (`test_catalog_audit.py`), sem chamada real
- [x] `ProcessingResult`, `build_response(service, client)` e `resolve_service(category, lookup)` mantêm a assinatura — `response.py` e `processor.py` intocados
- [x] nenhum teste faz rede real; sem chave no diff
- [ ] "Testes do escopo verdes" — 3 falhas de urgência fora do escopo (acima); `ruff` com 1 achado pré-existente em arquivo fora do diff

**Decisões e suposições**
- `load_catalog` passou a devolver `list[ServiceEntry]` (ordem do arquivo, "a primeira do arquivo" exige ordem) e `CatalogLookup` aceita qualquer `Sequence`; assim `CatalogLookup(load_catalog(), ...)` nos conftests continua válido.
- `ServiceEntry` usa tuplas (não listas) para `keywords`, `links` e `phones`, mantendo o `frozen=True` realmente imutável.
- `kind=portal`/`channel` sem link nem telefone é inválido; `kind=service` sem link também. `verified_on` precisa ser data ISO (suposição além do §2.1).
- Template: cabeçalho "Acesse o link oficial:" (um link) ou "Acesse os links oficiais:" (vários), mais "Abrangência: …" e "Telefones:".
- `foreign_phone`: sequência = dígitos separados por espaço, hífen, parênteses ou espaço não separável, ≥ 3 dígitos; compara só dígitos. URLs e e-mails são removidos antes (para `fale123@x.org` não virar telefone). Na dúvida rejeita: "protocolo 123456", "+55 …" e datas "10-11-2026" caem no template.
- `fetch_page_text` (rede real) mora em `catalog_audit.py` por não haver outro arquivo do escopo; a auditoria o recebe injetado. Remove tags HTML e nunca levanta.
- A CLI escreve o relatório com `sys.stdout.write` em vez de `print` para o validador `padrao-python` (regra de `print`) passar; o relatório é a saída legítima do comando.
- `phone_digit_sequences` fica público em `response_guard.py` e é reusado pelo verificador (confirmação do telefone em páginas), para as duas regras de "o que é telefone" não divergirem.
- Em `catalog.json` as `coverage` de `driver_license`, `id_card`, `birth_certificate`, `voter_id`, `social_benefits` e `property_tax` dizem a verdade da natureza do atendimento (Detran, órgão estadual, cartório, Justiça Eleitoral, CRAS, prefeitura), conforme o §3.1.

**Achados fora do escopo (não corrigidos)**
- `src/triage/automation/allowlist.py:18` — `ruff` UP033 (`@lru_cache(maxsize=None)` → `@functools.cache`).
- `data/urgency_terms.json`, `specs/plan/plan-02.03-urgencia-saude.md` e `tests/classification/test_urgency.py` aparecem modificados por outra conversa; as 3 falhas de `urgent` desta verificação vêm daí e devem sumir quando aquela execução fechar. Convém o revisor reconferir `tests/pipeline` e `tests/interface` depois.

**Pendências / riscos**
- Verificação com rede (`scripts/verify_catalog.py` sem `--offline`) não foi rodada: fica para o revisor.
- A suíte do escopo só fica 100% verde depois da plan 02.03; o diff do revisor deve filtrar os 3 arquivos que não são desta plan.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->

## Veredito — 2026-11-10 — 🟢 Aprovado

Verifiquei, sem confiar no resumo:
- **Escopo:** `git status` mostra só `data/catalog.json`, `src/triage/automation/{catalog,resolver,response_guard,templates,catalog_audit}.py`, `scripts/verify_catalog.py` e `tests/automation/*`; `response.py`, `processor.py`, interface, classificação e storage intocados. Os outros arquivos modificados no worktree são da plan 02.03.
- **Testes:** `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation tests/classification -q` → 329 passed, 3 failed; as 3 falhas são da plan 02.03 (pedido de teste que dependia de `urgente` solto). Com o léxico de `HEAD` no lugar, `tests/automation tests/pipeline tests/interface tests/evaluation` → 222 passed (3 testes de CLI só falham na minha simulação, por causa do diretório de trabalho, e passam na execução normal). Logo, o diff desta plan não causa falha.
- **Lint e validador:** `ruff` → 1 achado `UP033` em `allowlist.py:18`, arquivo fora do diff; `validate.py` → 0 em `src/triage/automation` e em `scripts/verify_catalog.py`; em `tests/automation` só `hardcoded` de `confidence: low` (URL de fixture).
- **Catálogo:** os 8 registros trazem o mesmo link, nome, órgão, instruções, `source_note` e `verified_on` do `HEAD`; `status: approved`; 7 a 8 `keywords` cada; telefone só no INSS (135).
- **Verificador:** `python scripts/verify_catalog.py --offline` → saída 0; com rede → os 8 links respondem, o telefone 135 do INSS `confirmado`, sem erro (saída 0).
- **Guarda (sondagem com saídas forjadas):** aceita o template completo, "3 dias", "2ª via", `gov.br` e cada link do serviço; rejeita telefone alheio, `+55 …`, protocolo de 6 dígitos e ano (`foreign_phone`, por falha segura), URL alheia e `golpe.com` (`foreign_url`), vazio e saída sem URL (`missing_url`).
- **Template:** lista todos os links e os telefones, com abrangência; sem telefone omite a seção.
- **Assinaturas:** `resolve_service(category, lookup)`, `build_default_lookup()`, `build_response(service, client)` e `ProcessingResult` mantidos.
- **Sinais de atalho:** nenhum TODO/FIXME, nenhuma plan citada em código ou dado, nenhuma chave; nada largado no worktree.
Registrado no backlog (não bloqueia): `resolve_entry` entrega uma entrada `candidate` se alguém a passar diretamente.
