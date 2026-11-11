---
tipo: "plan"
familia: "03"
item: "R03.12"
titulo: "Aceitar uma base enriquecida do catálogo (conteúdo por página, vários arquivos) e usá-la na recuperação e na resposta"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[03.02-resposta-final-e-llm]]", "[[03.03-localizador-de-servicos]]", "[[007-llm-redige-a-resposta-com-rag-do-catalogo]]"]
depende_de: "—"
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

# 1. Objetivo
O catálogo passa a aceitar uma **base enriquecida** trazida pelo usuário: muitas entradas por tarefa (link da página específica) em
arquivos extras, cada uma com um **trecho oficial da página** (`content`) que o LLM usa para redigir respostas mais completas, e que
a recuperação também usa para achar a entrada certa. Tudo continua anterior ao LLM: o robô carrega, verifica e recupera; o LLM só
redige sobre o que foi recuperado.

# 2. Contexto
Hoje o catálogo (`data/catalog.json`, 55 registros, 51 aprovados) é quase só de portais, com 1 ou 2 links e uma instrução curta
por entrada, e a resposta fica rasa ("busque no portal"). O usuário vai **montar e entregar a base enriquecida** (páginas oficiais por
tarefa, com o trecho que responde), então esta plan entrega a **capacidade**, o **formato** e o **guia**, não o conteúdo. Navegação do
agente pela internet fica fora: o conteúdo é curado e verificado antes, nunca buscado na hora da pergunta.

Estado atual relevante: `ServiceEntry` tem `id, category, kind, scope, coverage, area, display_name, agency, instructions, keywords,
links, phones, source_note, verified_on, status`; `load_catalog(path=CATALOG_PATH)` lê um arquivo, ignora registro inválido e `id`
repetido com log; `ServiceFinder` indexa `keywords + display_name + agency`; `rag.py` monta o bloco de cada fonte (nome, órgão,
abrangência, instruções, links, telefones); `validate_rag_output` aceita só URL de link das fontes e só telefone das fontes (sequência
de 3+ dígitos); `scripts/verify_catalog.py` audita o catálogo; a allowlist é `gov.br` (inclui `*.sp.gov.br`).

## 2.1 Contrato (decisão desta plan)
- **Campo novo, opcional:** `content` (texto, padrão vazio): trecho oficial da página que fundamenta a resposta, até
  `MAX_CONTENT_LENGTH` = 3000 caracteres (constante do esquema, como `MAX_RESPONSE_LENGTH`); acima disso o registro é inválido,
  com log. Registro sem `content` continua válido e se comporta como hoje.
- **Vários arquivos:** `load_catalog()` lê `data/catalog.json` e depois todos os `data/catalog.d/*.json`, em ordem de nome, mesmo
  esquema (lista de registros). Pasta ausente ou vazia não é erro. `id` repetido entre arquivos: vale o primeiro, com log. A pasta
  `data/catalog.d/` nasce na entrega, sem nenhum `.json` (o exemplo vive só no guia, §5.5).
- **Regra de entrada da base trazida pelo usuário:** o registro entregue pelo usuário em `data/catalog.d/` conta como aprovado por
  ele (não precisa constar em `docs/fontes-publicas-sp-para-aprovacao.md`), mas só **responde** se `status` é `approved` **e** o
  verificador confirma domínio na allowlist e link vivo; senão fica `candidate`, como hoje.
- **Recuperação:** o documento de busca de cada entrada passa a ser `keywords + display_name + agency + content`. Sem nenhum `content`
  no catálogo, a pontuação e as métricas do localizador (`finder_metrics`, 96 pedidos) ficam **idênticas** às atuais.
- **Resposta:** o bloco de cada fonte enviado ao LLM ganha `Conteúdo:` (o `content`, quando houver) depois das instruções. A guarda
  passa a aceitar, além dos telefones das fontes, as sequências de 3+ dígitos que aparecem em `instructions` ou `content` das fontes
  enviadas (números do próprio texto oficial), e continua rejeitando qualquer outra; links seguem só os `links` das fontes.
- **Verificador:** `scripts/verify_catalog.py` audita o conjunto carregado (catálogo + `catalog.d`), aponta o arquivo de origem de
  cada erro e confere `content` (tamanho e se não é vazio quando presente).

# 3. Escopo
## 3.1 Dentro
- `src/triage/automation/catalog.py` — campo `content`, validação do tamanho, leitura de `data/catalog.json` + `data/catalog.d/*.json`
- `src/triage/automation/finder.py` — `content` no documento de busca
- `src/triage/automation/rag.py` — `Conteúdo:` no bloco da fonte
- `src/triage/automation/response_guard.py` — dígitos do texto das fontes aceitos
- `src/triage/automation/catalog_audit.py` e `scripts/verify_catalog.py` — auditar o conjunto e o `content`
- `data/catalog.d/` (nova pasta, só com um `README.md`) e `docs/guia-da-base-enriquecida.md` (novo)
- `README.md` — um parágrafo curto sobre a base enriquecida e o guia
- `tests/automation/` — testes de catálogo, finder, rag, guarda e auditoria

## 3.2 Fora
- O **conteúdo** da base (é do usuário) e qualquer entrada real nova em `data/catalog.json`.
- Navegação do LLM, busca na internet em tempo de pergunta, scraping automático, rastreador (crawler).
- `triage.pipeline`, `triage.interface`, `triage.classification`, o agente (`data/agents/`) e as ADRs.
- Mudar `FINDER_MIN_SCORE`, `FINDER_MARGIN` ou o conjunto rotulado do localizador.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | esquema do catálogo, regras de entrada, verificador |
| Spec fixa | [[03.02-resposta-final-e-llm]] · [[03.03-localizador-de-servicos]] | mensagem ao LLM, guarda e documento de busca |
| ADR | [[007-llm-redige-a-resposta-com-rag-do-catalogo]] · [[003-seguranca-sem-autenticacao]] | o catálogo é o RAG; só link aprovado e verificado |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` · `cyber-ia` | zero hardcoded, saída não confiável |
| Skill | `test-unitario` | testes sem rede |
| Código | `src/triage/automation/{catalog,finder,rag,response_guard,catalog_audit,resolver}.py`, `scripts/verify_catalog.py`, `data/catalog.json` | o que muda e o formato dos registros |
| Código | `tests/automation/`, `docs/fontes-publicas-sp-para-aprovacao.md` | testes a ajustar e o formato de fonte já usado |

# 5. Instruções de execução
1. [dirigido] **Esquema e leitura.** `content` opcional em `ServiceEntry` e na validação (§2.1); `load_catalog()` lê `data/catalog.json` e
   `data/catalog.d/*.json`. Funções pequenas; arquivo ilegível ou JSON inválido em `catalog.d` é registrado e ignorado, sem derrubar os
   demais (como o catálogo único já faz). O caminho da pasta é parâmetro com padrão, para os testes usarem uma pasta temporária.
2. [dirigido] **Recuperação.** `ServiceFinder` indexa o `content`; sem `content` em nenhuma entrada, as pontuações e o resultado da medição de
   `finder_metrics` não mudam (teste prova, com o conjunto de 96 pedidos).
3. [dirigido] **RAG e guarda.** `Conteúdo:` no bloco da fonte; a guarda aceita os dígitos de `instructions` e `content` das fontes enviadas,
   mantendo `foreign_phone` para o resto, e a rejeição de URL e endereço alheios sem alteração.
4. [dirigido] **Verificador.** `scripts/verify_catalog.py` audita catálogo + `catalog.d`, informa o arquivo de cada achado, confere o `content` e
   segue com código de saída `0` sem erro e `1` com erro; o catálogo atual continua passando exatamente como hoje.
5. [dirigido] **Guia.** `docs/guia-da-base-enriquecida.md`, em português, para o usuário preencher a base: onde colocar os arquivos
   (`data/catalog.d/<nome>.json`), cada campo do registro (obrigatório ou opcional, o que escrever), como escrever `keywords` (o que o
   cidadão diz) e `content` (trecho oficial copiado da página, curto, sem dado pessoal), uma entrada de exemplo completa **marcada como
   exemplo** (use uma das entradas reais já existentes no catálogo como modelo, sem inventar URL), a regra de aprovação do §2.1, o
   comando de verificação (`python scripts/verify_catalog.py`) e como ler o resultado.
6. [dirigido] **Pasta e exemplo.** Criar `data/catalog.d/` com um `README.md` de uma linha apontando o guia; **nenhum** arquivo `.json` de
   exemplo fica na pasta (para não virar fonte real); o exemplo vive só no guia.
7. [dirigido] **Testes** (sem rede): `content` válido, vazio e acima do limite; carga de `catalog.json` + `catalog.d` (ordem, `id` repetido entre
   arquivos, JSON inválido num arquivo sem derrubar os outros, pasta ausente); recuperação acha a entrada pelo texto do `content`; recuperação
   idêntica sem `content`; bloco do RAG com `Conteúdo:`; guarda aceita dígito do `content` e rejeita dígito fora das fontes; verificador aponta o
   arquivo e o limite do `content`.
8. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Registro com `content` válido carrega; acima de `MAX_CONTENT_LENGTH` é rejeitado com log; sem `content` nada muda.
- [ ] `data/catalog.d/*.json` é lido além de `data/catalog.json`, com `id` repetido resolvido pelo primeiro e falha de um arquivo isolada.
- [ ] A recuperação usa `content`; sem `content`, as pontuações e as métricas do localizador são idênticas às atuais.
- [ ] O bloco de cada fonte no RAG traz `Conteúdo:`; a guarda aceita só dígitos do texto das fontes ou telefones delas e continua rejeitando URL e telefone alheios.
- [ ] `verify_catalog.py` audita o conjunto, indica o arquivo de origem e continua verde para o catálogo atual.
- [ ] O guia existe, está em português, é suficiente para o usuário montar a base, e não contém URL inventada.
- [ ] Nenhum teste faz chamada real; ambiente e worktree limpos; `ruff` e validador sem violação nova.
- [ ] O notebook de evidências continua executando sem erro (ele usa o catálogo e o localizador).

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — muda o esquema do catálogo, consumido por resolver, localizador, RAG, guarda, verificador e notebook`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py -q` → verde.
- `python -m ruff check src/triage/automation scripts tests/automation` → sem erro novo.
- `validate.py` do `padrao-python` nos `.py` tocados → sem achado.
- `python scripts/verify_catalog.py --offline` → sem erro; o revisor cria, no scratchpad, uma pasta com um registro com `content` (e outro acima do limite)
  e confere o resultado e o arquivo apontado.
- Sondagem: cliente falso, fonte com `content` contendo "30 dias" e "156": saída com esses números passa; saída com um número que não está nas fontes é rejeitada.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` sem erro.
- **Gate:** `nenhum — coberto por testes e sondagem`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md` (esquema, leitura de vários arquivos, regra de entrada da base do usuário, verificador) e, no que for
regra de resposta, `specs/03.02-resposta-final-e-llm.md` (`Conteúdo:` no bloco e dígitos aceitos pela guarda) e `specs/03.03-localizador-de-servicos.md` (documento de busca com `content`).

Escrever, **substituindo** o que hoje diz que cada fonte consta no documento de aprovação: a base entregue pelo usuário em `data/catalog.d/` vale como aprovada por ele, e só
responde com `status` aprovado, domínio na allowlist e link vivo.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-11

**Resultado:** Concluído com pendências (as pendências são riscos e achados fora do escopo; todos os critérios de aceite foram atendidos)

**O que foi feito**
- `catalog.py:95` `_content` e campo `ServiceEntry.content = ""`: opcional; ausente vale vazio; presente exige texto não vazio de até `MAX_CONTENT_LENGTH = 3000`, senão `CatalogRecordError` (o registro é ignorado com log) — §2.1.
- `catalog.py:234` `load_catalog(path, extra_dir=CATALOG_DIR_PATH)`: lê `path` e depois os `*.json` de `extra_dir` em ordem de nome (`catalog_extra_files`); `id` repetido vale o primeiro, também entre arquivos (`_parse_records`); arquivo ilegível ou fora de lista é registrado e ignorado sem derrubar os demais; `extra_dir=None` lê só `path`.
- `finder.py:31` `_search_document`: acrescenta `content` ao documento só quando existe (sem `content` o texto indexado é o de antes).
- `rag.py:27,48`: linha `Conteúdo:` depois das instruções, só quando a fonte tem `content`; `<<<PEDIDO` e `PEDIDO>>>` são removidos do trecho, como já eram do pedido.
- `response_guard.py:64,87` `_source_text_numbers`: a guarda aceita, além dos telefones, as sequências de 3+ dígitos de `instructions` e `content` das fontes enviadas; URL, endereço e demais números seguem rejeitados.
- `catalog_audit.py`: `Check.source` (arquivo de origem, padrão vazio); `CatalogAuditor` guarda os `id`s entre arquivos; `audit_catalog_files` audita o conjunto. O `content` é conferido pelo esquema (`parse_entry`): tamanho e vazio saem como erro `schema` com o arquivo.
- `scripts/verify_catalog.py`: opção `--catalog-dir` (padrão `data/catalog.d`); audita catálogo + pasta; linhas `AVISO`/`ERRO` terminam com `(arquivo: ...)`; arquivo ilegível da pasta vira erro `[file]` sem derrubar os demais; catálogo principal ilegível segue como antes (log e saída 1).
- `docs/guia-da-base-enriquecida.md` (novo), `data/catalog.d/README.md` (novo, uma linha, nenhum `.json`) e parágrafo "Base enriquecida" em `README.md`.
- Testes em `tests/automation/`: `content` e vários arquivos (`test_catalog.py`), busca por `content` e pontuação idêntica sem ele (`test_finder.py`), `Conteúdo:` (`test_rag.py`), dígitos da fonte (`test_response_guard.py`), conjunto e verificador (`test_catalog_audit.py`). `test_catalog.py` e `test_catalog_content.py` passaram a ler o catálogo versionado com `extra_dir=None`, para a base do usuário não alterar o que eles afirmam sobre o piloto.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/automation/catalog.py` | alterado | `content`, `MAX_CONTENT_LENGTH`, `CATALOG_DIR_PATH`, leitura de vários arquivos |
| `src/triage/automation/finder.py` | alterado | `content` no documento de busca |
| `src/triage/automation/rag.py` | alterado | `Conteúdo:` no bloco da fonte |
| `src/triage/automation/response_guard.py` | alterado | dígitos do texto das fontes aceitos |
| `src/triage/automation/catalog_audit.py` | alterado | `Check.source`, `id`s entre arquivos, `audit_catalog_files` |
| `scripts/verify_catalog.py` | alterado | `--catalog-dir`, arquivo de origem, arquivo ilegível |
| `docs/guia-da-base-enriquecida.md` | criado | guia para montar a base |
| `data/catalog.d/README.md` | criado | aponta o guia |
| `README.md` | alterado | parágrafo da base enriquecida |
| `tests/automation/test_catalog.py` | alterado | testes de `content` e de vários arquivos; leitura isolada do catálogo versionado |
| `tests/automation/test_catalog_content.py` | alterado | `load_catalog(extra_dir=None)` |
| `tests/automation/test_finder.py` | alterado | busca por `content`; pontuações idênticas sem `content` nos 96 pedidos |
| `tests/automation/test_rag.py` | alterado | `Conteúdo:`, delimitadores, número do `content` na guarda |
| `tests/automation/test_response_guard.py` | alterado | dígitos aceitos e rejeitados |
| `tests/automation/test_catalog_audit.py` | alterado | auditoria do conjunto, `content`, arquivo de origem e script |

**Verificações executadas**
- `python -m pytest tests/automation tests/evaluation -q`, antes de editar → 338 passed.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py -q` → 511 passed, 1 failed: `tests/test_config.py::test_shipped_config_equals_the_code_defaults`, porque `config/settings.json` já estava modificado no worktree (`llm.enabled: true`) antes de eu começar; não toquei nesse arquivo (ver Achados fora do escopo).
- `python -m pytest tests/automation -q`, depois do último ajuste → 326 passed.
- `python -m pytest tests/evaluation -q`, depois das edições (métricas do localizador) → 53 passed.
- `python -m ruff check scripts tests/automation` e os 5 `.py` de `src/triage/automation` que alterei → All checks passed. `python -m ruff check src/triage/automation` (diretório inteiro) → 1 erro, `UP033` em `allowlist.py:18`, arquivo que não toquei.
- `validate.py` do `padrao-python` em cada um dos 12 `.py` tocados → sem achado em 9. `test_rag.py` (2), `test_response_guard.py` (2) e `test_catalog_audit.py` (3) acusam só "URLs/hosts embutidos" em linhas que já existiam: rodei o validador sobre `git show HEAD:<arquivo>` e deu os mesmos achados e a mesma contagem. Um rascunho meu de `test_catalog_audit.py` somava uma URL nova e foi trocado.
- `python scripts/verify_catalog.py --offline --max-age-days 100000` → `55 registro(s) verificado(s); sem erro.`, saída 0.
- Sondagem do verificador (pasta temporária no scratchpad: `a.json` com `content` válido, `b.json` com `content` de 3001 caracteres) → `ERRO  probe_big [schema] campo content com 3001 caracteres (limite 3000) (arquivo: ...\probe\b.json)`, `57 registro(s) verificado(s); com erro.`, saída 1.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` → gravou o notebook executado, sem erro.
- Sondagem da guarda ("30 dias" e "156"): `test_rag.py::test_a_number_from_the_content_passes_the_guard_and_another_one_does_not` e `test_response_guard.py::test_accepts_numbers_that_appear_in_the_source_text` / `test_rejects_numbers_that_are_in_no_source_text_nor_phone`. Com `content` contendo "30 dias" e "156", a saída com esses números passa; "45", "120", "999" e "157" são rejeitados com `foreign_phone`.
- Não rodei a suíte inteira nem `ruff` em `run.py src tests` (verificação ampla é do revisor, §3.7 do prompt).

**Estado inicial do worktree:** ` M config/settings.json` (modificação do usuário, anterior à execução); branch `develop`.

**Ambiente após a verificação:** pytest e nbconvert subiram processos temporários (subprocessos do pytest, kernel do Jupyter), todos encerrados sozinhos. `environment.py snapshot` (antes do notebook, `--tmp-prefix gs-rpa`) e `diff` (depois): 0 diretórios temporários, 0 contêineres, imagens, volumes, redes, branches ou worktrees novos; o diff de processos lista só shells e utilitários desta sessão e processos do sistema, nenhum servidor ou kernel meu. Sondagem e notebook executado ficaram no scratchpad da sessão, fora do repositório.

**Critérios de aceite**
- [x] `content` válido carrega; acima de `MAX_CONTENT_LENGTH` é rejeitado com log; sem `content` nada muda — `test_catalog.py::test_content_defaults_to_empty_and_is_loaded_when_present`, `test_content_at_the_limit_is_valid_and_above_it_is_rejected_with_log`, `test_present_content_must_be_non_blank_text`.
- [x] `data/catalog.d/*.json` lido além de `data/catalog.json`, `id` repetido resolvido pelo primeiro, falha de um arquivo isolada — `test_extra_files_are_read_after_the_catalog_in_name_order`, `test_duplicate_id_across_files_keeps_the_first`, `test_a_broken_extra_file_is_logged_and_does_not_drop_the_others`, `test_missing_or_empty_extra_dir_is_not_an_error`.
- [x] A recuperação usa `content`; sem `content` as pontuações são idênticas — `test_finder.py::test_the_content_of_an_entry_is_searchable` e `test_without_content_scores_are_identical_to_the_previous_finder_on_the_labeled_requests` (96 pedidos contra uma montagem independente do índice antigo: entrada, pontuação e folga).
- [x] `Conteúdo:` no bloco; a guarda aceita só dígitos do texto das fontes ou telefones delas e rejeita URL e telefone alheios — `test_rag.py`, `test_response_guard.py` (os testes antigos de URL seguem verdes sem alteração).
- [x] `verify_catalog.py` audita o conjunto, indica o arquivo e segue verde no catálogo atual — sondagem acima e `test_catalog_audit.py::test_script_*`; catálogo atual: 55 registros, sem erro, saída 0.
- [x] Guia existe, em português, sem URL inventada — `docs/guia-da-base-enriquecida.md` (única URL: a da entrada real `popular_pharmacy`; o `content` do exemplo é um marcador).
- [x] Nenhum teste faz chamada real; ambiente e worktree limpos; `ruff` e validador sem violação nova — verificações acima.
- [x] Notebook de evidências executa sem erro — nbconvert acima.

**Decisões e suposições**
- `content` presente mas vazio, só espaços, `null` ou não texto é **registro inválido** (não vira "sem `content`"): leio assim a linha do §2.1 do verificador, "se não é vazio quando presente". Ausente continua válido.
- `content` é medido em caracteres brutos (sem `strip`) e guardado como veio.
- `load_catalog(path, extra_dir=None)` lê só `path`: criei esse modo para os testes do catálogo versionado não dependerem da pasta real, que vai passar a ter a base do usuário. O padrão de `extra_dir` é `data/catalog.d`; catálogo principal ausente não impede a leitura da pasta.
- No verificador as linhas `OK` não mudaram; só `AVISO` e `ERRO` ganharam `(arquivo: ...)`. A linha-resumo mantém o formato anterior, com o total de registros de todos os arquivos.
- O `content` do exemplo do guia é um marcador explícito: copiar texto oficial de uma página exigiria consultar a rede (fora do escopo). O exemplo vem com `status: "candidate"`.
- A guarda extrai os números do texto das fontes com o mesmo padrão dos telefones (`phone_digit_sequences`): número dentro de URL ou e-mail do `content` não vale.
- Um aviso da ferramenta de edição disse que o `ruff` não estava instalado; é falso: `python -m ruff` (0.17.4, o de `requirements-dev.txt`) roda e foi o usado.

**Achados fora do escopo (não corrigidos)**
- `config/settings.json` está modificado no worktree (`llm.enabled: true`, anterior a esta execução) e faz `tests/test_config.py::test_shipped_config_equals_the_code_defaults` falhar.
- `src/triage/automation/allowlist.py:18` — `ruff` UP033 (`@lru_cache(maxsize=None)` → `@functools.cache`), já existente.
- `ruff format --check` acusa 26 arquivos de `src/triage/automation`, `scripts` e `tests/automation`: o projeto não usa `ruff format` como gate.
- `tests/evaluation/test_finder_metrics.py`, `tests/pipeline/conftest.py`, `tests/interface/conftest.py`, `tests/interface/test_service_tiers.py` e `tests/automation/test_resolver.py` chamam `load_catalog()` sem `extra_dir=None`. Quando o usuário puser arquivos em `data/catalog.d/`, os que fixam contagens ou áreas do catálogo piloto (sobretudo o de métricas do localizador) podem passar a falhar por dado, não por defeito. Ficam fora do §3.1 (só `tests/automation/`), então não mexi.
- `data/agents/` (persona e regras do LLM) não nomeia o campo `Conteúdo:`; o LLM o recebe na mensagem, mas a regra "use só as fontes" não o cita. O agente está fora do escopo (§3.2).

**Pendências / riscos**
- Nenhuma entrada real foi criada: o conteúdo da base é do usuário (§3.2).
- Verificação ampla (suíte inteira, `ruff` em `run.py src tests`) não rodada por conta própria; a única falha conhecida é a de `test_config.py`, explicada acima.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-11 — 🟢 Aprovado

**Verificado pelo revisor (sem confiar no resumo):**
- `git status`/`diff --stat`: só arquivos do §3.1 (catalog, catalog_audit, finder, rag, response_guard, verify_catalog, README, guia, `data/catalog.d/README.md` sem `.json`, testes de `tests/automation/`). `config/settings.json` modificado é do usuário (anterior à execução).
- Diff lido por inteiro: `content` opcional validado (vazio, não texto e acima de 3000 são inválidos); `load_catalog(path, extra_dir)` lê catálogo + `*.json` em ordem de nome, `id` repetido vale o primeiro entre arquivos, arquivo ilegível isolado; `finder` só acrescenta `content` quando existe; `rag` ganha `Conteúdo:` com delimitadores neutralizados; guarda aceita dígitos de `instructions`/`content` das fontes; auditoria do conjunto com arquivo de origem.
- `pytest tests/automation tests/pipeline tests/interface tests/test_config.py tests/evaluation -q` → 564 passed, 1 failed: `test_shipped_config_equals_the_code_defaults`, causado só pelo `llm.enabled: true` local do usuário (`assert True is False`), não pela execução.
- `ruff check src/triage/automation scripts tests/automation` → 1 erro (UP033 em `allowlist.py:18`, arquivo não tocado, já no backlog 14). `validate.py`: 0 achados nos 6 `.py` de produção; nos testes, os achados `hardcoded` (3/2/2) são os mesmos de `HEAD`.
- `verify_catalog.py --offline` → 55 registros, sem erro, saída 0.
- Sondagem real (pasta temporária): registro com `content` achado por palavra só do `content` (`probe_iptu` primeiro); `id` repetido entre arquivos manteve o primeiro; JSON quebrado e `content` de 3001 isolados com log; guarda: "30 dias" e "156" passam, "120" é rejeitado (`foreign_phone`).
- `nbconvert --execute notebooks/evidence.ipynb` → sem erro. Ambiente limpo (nada criado fora do escopo; arquivos de sondagem no scratchpad).

**Fora do escopo, para o backlog:** log de registro inválido imprime o registro inteiro (com `content` de até 3000+ caracteres); persona/regras do agente não nomeiam `Conteúdo:`; testes que chamam `load_catalog()` sem `extra_dir=None` podem falhar por dado quando `data/catalog.d/` receber a base (tratado na 03.14).
