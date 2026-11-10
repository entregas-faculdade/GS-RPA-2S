---
tipo: "plan"
familia: "03"
item: "R03.9"
titulo: "Identificar o verificador de links e aceitar links bloqueados ao robô, validados manualmente"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "plan-03.04-catalogo-sao-paulo — precisa estar 🟢; e o usuário ter marcado a seção 7 do documento de fontes"
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

# 1. Objetivo
O verificador de links passa a se **identificar** com um User-Agent descritivo do projeto, e um link que o site bloqueia ao
robô (HTTP 403), mas que o usuário **validou manualmente**, pode ser entregue ao cidadão; assim as páginas da prefeitura de
São Paulo (IPTU, alvará, UBS, portal) deixam de ficar reservadas.

# 2. Contexto
`www.prefeitura.sp.gov.br` responde HTTP 403 ao cliente automatizado do projeto, que hoje não se identifica
(`requests` com o User-Agent padrão), e o resolvedor descarta o link ([[03.01-catalogo-e-allowlist]] §2.3 e §2.4). Na
plan do catálogo de São Paulo, essas quatro páginas ficaram `candidate`. O usuário decidiu: (1) tentar o verificador
identificado; (2) como são poucas páginas, **validá-las à mão** e atestar no documento
`docs/fontes-publicas-sp-para-aprovacao.md`, seção 7.

Limites éticos e de segurança desta plan:
- A identificação é **honesta**: o nome do projeto, sem imitar navegador. Não se contorna nenhum bloqueio por disfarce.
- Link aceito "por validação manual" **só** quando o bloqueio é 403 (o site existe e recusa o robô). 404, 5xx, timeout, erro
  de conexão e de SSL continuam derrubando o link.
- O atestado manual **tem data e validade**: vence com o `--max-age-days` do verificador (padrão 180), e o verificador avisa.
- Ainda vale tudo o que já vale: allowlist, HTTPS, sem credencial embutida.

# 3. Escopo
## 3.1 Dentro
- `src/triage/automation/link_check.py` — User-Agent descritivo em HEAD e GET (passos 1 e 2)
- `src/triage/config.py` e `.env.example` — `LINK_CHECK_USER_AGENT` (padrão descritivo do projeto)
- `src/triage/automation/catalog.py` — campo opcional `manual_check_on` (data ISO) em cada link (passo 4)
- `src/triage/automation/resolver.py` — aceitar link com atestado manual válido quando a verificação automática dá 403
- `src/triage/automation/catalog_audit.py` e `scripts/verify_catalog.py` — o mesmo User-Agent; aviso para link atestado manualmente (passo 5)
- `data/catalog.json` — **só** a promoção dos registros e links que o usuário validou (passo 6)
- `tests/automation/` — testes novos e ajustes (inclui o teste de conteúdo do catálogo)
- `notebooks/evidence.ipynb` — **só** a célula do caso "link fora do ar" e o import dela, que chamam `check_link` com a assinatura antiga (rodada de correção)

## 3.2 Fora
- Qualquer técnica que imite navegador, rotacione identidade ou ignore `robots`/bloqueio de outra forma.
- Aceitar por atestado manual link que deu 404, 5xx, timeout, conexão ou SSL.
- `data/allowed_domains.json` (nada de domínio novo), `triage.pipeline`, `triage.interface`, `triage.classification`.
- O documento `docs/fontes-publicas-sp-para-aprovacao.md` (só leitura).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | formato v2 do catálogo, `check_link`, `resolve_entry`, verificador |
| ADR | [[003-seguranca-sem-autenticacao]] | só domínios oficiais; nada de contornar proteção |
| Dados | `docs/fontes-publicas-sp-para-aprovacao.md` (seção 7) | páginas que o usuário validou à mão |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | ≤ 4 parâmetros (agrupar em objeto de configuração), sem estado global mutável |
| Skill | `test-unitario` | testes sem rede |
| Código | `src/triage/automation/link_check.py`, `catalog.py`, `resolver.py`, `catalog_audit.py`, `scripts/verify_catalog.py`, `src/triage/config.py` | o que será alterado |

# 5. Instruções de execução
1. [dirigido] **User-Agent.** `LINK_CHECK_USER_AGENT` em `Settings` (padrão descritivo, por exemplo `GS-RPA-Triagem/1.0
   (projeto academico FIAP)`), documentado no `.env.example`. `check_link` e a leitura de páginas do verificador enviam esse
   cabeçalho. Como `check_link` já tem 4 parâmetros, agrupe a configuração em um objeto (ou use `functools.partial` em
   `build_default_lookup` e no script) sem passar de 4. Testes: o cabeçalho vai em HEAD e em GET (fake de HTTP).
2. [dirigido] **HEAD reiniciado.** Em `check_link`, quando o **HEAD** falha por erro de conexão (reinício da conexão pelo servidor), a tentativa
   passa a ser repetida como **GET**, e só o resultado do GET conta; o servidor do MEC reinicia o HEAD e responde 200 ao GET. Os
   demais comportamentos (4xx, 5xx, timeout, retry com espera) não mudam. Teste com fake: HEAD levanta `ConnectionError` e GET
   responde 200 → link vivo; os dois falham → falha.
3. [dirigido] **Medir o efeito.** Com rede, rodar `python scripts/verify_catalog.py` e registrar no resumo, para cada link de
   `www.prefeitura.sp.gov.br` e para `gov.br/mdh`, `gov.br/mec`, `gov.br/mec/pt-br/pe-de-meia` e
   `corpodebombeiros.sp.gov.br`, o resultado **antes** (HTTP 403 ou erro) e **depois** do User-Agent. Não tente nenhuma
   variação além do cabeçalho configurado.
4. [dirigido] **Atestado manual.** Cada `link` do catálogo aceita o campo opcional `manual_check_on` (data ISO, inválida =
   registro inválido). Em `resolve_entry`, quando a verificação automática do link falha **com HTTP 403** e o link tem
   `manual_check_on` que não excede a idade máxima do §2.3 (180 dias, o mesmo `--max-age-days` do verificador, vindo de
   configuração e não de literal), o link é mantido, com log `WARNING` dizendo que foi aceito por validação manual. Qualquer
   outra falha (404, 5xx, timeout, conexão, SSL) continua descartando o link. Allowlist continua valendo.
5. [dirigido] **Verificador.** Link bloqueado com atestado válido aparece como `aviso` (nunca erro), com a data do atestado;
   atestado mais velho que o limite aparece como `aviso` de vencido e o link deixa de ser aceito em runtime. Códigos de saída
   inalterados.
6. [dirigido] **Promoção dos registros.** Ler a seção 7 do documento de fontes. Para cada fonte marcada `[x]` (validada à
   mão): se o passo 2 mostrou que o link **responde** com o User-Agent, o registro vira `approved` sem atestado; se continua
   com 403, o link ganha `manual_check_on` com a data indicada na seção 7 e o registro vira `approved`. Fonte `[ ]` ou `[-]`
   permanece `candidate`. Os registros `mec` e `pe_de_meia` (aprovados na lista, hoje `candidate` por erro de conexão) voltam a
   `approved` se o link responder depois do passo 2. **Telefones continuam sob a regra de números oficiais** da plan do catálogo de São Paulo. Dizer no
   resumo quais fontes foram promovidas e por qual caminho.
7. [dirigido] **Testes** (sem rede): link 403 com atestado válido é mantido; com atestado vencido, descartado; 404 e 5xx
   com atestado, descartados; 403 sem atestado, descartado; atestado em data inválida invalida o registro; o verificador
   avisa nos três casos; o teste de conteúdo do catálogo cobre os registros promovidos (todo `approved` com link só tem link
   permitido, vivo ou atestado).
8. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] O cabeçalho de identificação é enviado em HEAD e GET e vem de configuração; nada imita navegador.
- [ ] Um HEAD com erro de conexão é repetido como GET, e o resultado do GET decide.
- [ ] O resumo traz o antes e o depois do User-Agent para cada link bloqueado ou com erro listado no passo 2.
- [ ] 403 + atestado válido mantém o link; qualquer outra falha, ou atestado vencido ou ausente, o descarta.
- [ ] O verificador avisa (nunca erra) em link atestado manualmente e em atestado vencido.
- [ ] Só as fontes marcadas `[x]` na seção 7 foram promovidas; as demais seguem `candidate`.
- [ ] O notebook de evidências continua executando sem erro com a nova assinatura de `check_link`.
- [ ] Nenhum teste usa rede; ambiente e worktree limpos; testes do escopo verdes; `ruff` e validador sem violação; nenhuma chave no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — muda check_link e resolve_entry, que o pipeline consome`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py -q` → verde.
- `python -m ruff check src/triage/automation src/triage/config.py scripts tests/automation` → sem erro.
- `validate.py` do `padrao-python` nos `.py` alterados → sem achado.
- `python scripts/verify_catalog.py` com rede, uma vez: o revisor confere o antes/depois do resumo e que as fontes
  promovidas correspondem à seção 7, linha a linha.
- Sondagem: `resolve_service` real sobre as categorias existentes continua devolvendo links vivos.
- **Gate:** `nenhum — coberto por testes e pelo verificador`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md`

Levar, **substituindo**: o User-Agent descritivo do verificador (§2.3); o campo `manual_check_on` do link e a regra de
aceitação (só 403, com validade, nunca para 404, 5xx, timeout, conexão ou SSL) em §2.1 e §2.4; o aviso do verificador em
§2.6; e o limite declarado: um atestado manual depende de a página continuar existindo, e o robô só detecta o 403, então a
página pode sair do ar sem que ele perceba até o atestado vencer.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências (passo 6: nenhuma fonte promovida, porque a seção 7 ainda não tem `[x]`).

**O que foi feito**
- `config.py:15,32,66` e `.env.example` — `LINK_CHECK_USER_AGENT` em `Settings.link_check_user_agent`, padrão `GS-RPA-Triagem/1.0 (projeto academico FIAP)`; valor vazio ou em branco volta ao padrão.
- `link_check.py` — `LinkCheckOptions(timeout, retries, backoff, user_agent)` agrupa a configuração (`check_link(url, options)` fica com 2 parâmetros); o cabeçalho `User-Agent` vai em HEAD e GET; `build_link_checker(user_agent)` devolve um `partial`. Passo 1.
- `link_check.py` (`_probe`) — HEAD com `ConnectionError` é repetido como GET e o GET decide; `Timeout` (inclusive `ConnectTimeout`) não vira GET; 4xx, 5xx, timeout e retry com espera seguem iguais. Passo 2.
- `catalog.py` — `Link.manual_check_on` opcional (data ISO; ausente = `None`; presente e inválida invalida o registro), `manual_check_valid(link, today, max_age_days)` e `DEFAULT_MAX_AGE_DAYS = 180` (movida de `catalog_audit.py`, que a importa). Passo 4.
- `resolver.py` — `ManualCheckPolicy(max_age_days, today)` injetada em `CatalogLookup`; `_accepted_manually` mantém o link só com HTTP 403 + atestado vigente, com log `WARNING` "aceito por validação manual"; atestado vencido ou ausente descarta com `WARNING`. `build_default_lookup` usa o User-Agent de `Settings`. Passo 4.
- `catalog_audit.py` — link 403 com atestado vigente vira `aviso` com a data; atestado vencido vira `aviso` de vencido; atestado vigente conta como link utilizável no resumo da entrada, mas não como link vivo para confirmar telefone; `fetch_page_text` envia o User-Agent. `verify_catalog.py` usa `Settings` para o User-Agent. Códigos de saída inalterados. Passo 5.
- Testes sem rede em `tests/automation/` e `tests/test_config.py`. Passo 7.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/config.py` | alterado | campo e constante do User-Agent |
| `.env.example` | alterado | `LINK_CHECK_USER_AGENT=` (sem valor) |
| `src/triage/automation/link_check.py` | alterado | opções, User-Agent, HEAD→GET em erro de conexão, `build_link_checker` |
| `src/triage/automation/catalog.py` | alterado | `manual_check_on`, `manual_check_valid`, `DEFAULT_MAX_AGE_DAYS` |
| `src/triage/automation/resolver.py` | alterado | `ManualCheckPolicy`, aceite por atestado só com 403 |
| `src/triage/automation/catalog_audit.py` | alterado | avisos de atestado, User-Agent na leitura de página |
| `scripts/verify_catalog.py` | alterado | User-Agent vindo de `Settings` |
| `tests/automation/test_link_check.py`, `test_resolver.py`, `test_catalog_audit.py`, `test_catalog.py`, `test_catalog_content.py`, `tests/test_config.py` | alterado | testes novos e ajuste à nova assinatura de `check_link` |
| `data/catalog.json` | **não alterado** | nenhuma fonte promovida (ver passo 6) |

**Verificações executadas**
- `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py -q` → 268 passed.
- `python -m ruff check src/triage/automation src/triage/config.py scripts tests/automation` → 1 erro, anterior à tarefa, em `allowlist.py:18` (UP033); nenhum nos arquivos tocados. `ruff check tests/test_config.py` → limpo.
- `validate.py` (`padrao-python`) nos 12 `.py` alterados → nenhum achado em `src/` e `scripts/`; nos testes, só `hardcoded` de baixa confiança em constantes de URL (mesmo padrão dos testes existentes).
- `python scripts/verify_catalog.py --max-age-days 100000` com rede, antes e depois (passo 3), abaixo. Saída do depois: código 0.
- `git diff --stat` (fora de `specs/`) → só arquivos da §3.1; a busca por chave/segredo no diff só achou o nome `LINK_CHECK_USER_AGENT` em `ENV_KEYS`.

**Medição do passo 3 (antes = código anterior, User-Agent padrão do `requests`; depois = User-Agent descritivo + HEAD→GET)**
| Link | Antes | Depois |
|---|---|---|
| `https://www.prefeitura.sp.gov.br` | HTTP 403 | responde |
| `.../cidade/secretarias/fazenda` | HTTP 403 | responde |
| `.../cidade/secretarias/saude` | HTTP 403 | responde |
| `.../cidade/secretarias/educacao` | HTTP 403 | responde |
| `https://www.gov.br/mec/pt-br` | ConnectionError | responde |
| `https://www.gov.br/mec/pt-br/pe-de-meia` | ConnectionError | responde |
| `https://www.gov.br/mdh/pt-br` (sem link no catálogo; sondado à parte, só com o cabeçalho configurado) | HEAD 403 / GET 403 | 200 |
| `https://www.corpodebombeiros.sp.gov.br` (idem) | SSLError (`CERTIFICATE_VERIFY_FAILED`) | SSLError (continua falhando; não é 403, não se contorna) |

Os avisos de telefone `156` não confirmado de `sp_finance_secretariat`, `sp_city_health` e `sp_city_education_page` também sumiram no depois, pois as páginas passaram a abrir.

**Estado inicial do worktree:**
```
 M specs/00-indice.md
 M specs/panorama/00-resumo.md
 M specs/plan/plan-03.09-verificacao-de-links-prefeitura.md
```
Branch `develop`. Esses três arquivos vinham modificados antes de eu começar; da plan, só acrescentei este resumo e o `status`.

**Ambiente após a verificação:** nada criado. A verificação só rodou processos Python que terminaram (pytest, ruff, verify_catalog, uma sondagem avulsa); nenhum servidor, contêiner ou navegador. O script de sondagem e as saídas antes/depois ficaram no scratchpad da sessão, fora do repositório. O `snapshot` de `code-limpeza-ambiente` não foi tirado, porque nada de longa duração foi iniciado; confirmei à mão.

**Critérios de aceite**
- [x] Cabeçalho de identificação em HEAD e GET, vindo de configuração, sem imitar navegador — `test_user_agent_is_sent_on_head_and_get`, `test_default_user_agent_names_the_project_and_does_not_mimic_a_browser`, `tests/test_config.py`.
- [x] HEAD com erro de conexão repetido como GET, GET decide — `test_head_connection_reset_*` (GET 200 → vivo; GET falha → falha; GET 404 → decide sem retry) e `test_head_timeout_is_not_repeated_as_get`.
- [x] Antes e depois do User-Agent para cada link — tabela acima.
- [x] 403 + atestado válido mantém; demais falhas, atestado vencido ou ausente descartam — `test_resolver.py` (403 vigente, no limite de 180 dias, vencido, ausente, data futura, 404/503/timeout/conexão/SSL, allowlist).
- [x] Verificador avisa, nunca erra, em link atestado e em atestado vencido — `test_blocked_link_with_valid_manual_check_*`, `test_blocked_link_with_expired_*`; ver decisão 4 sobre o `links` de entrada `approved` só com atestado vencido.
- [ ] Só as fontes `[x]` da seção 7 foram promovidas — **nenhuma linha está `[x]`**; nada foi promovido (ver pendências).
- [x] Nenhum teste usa rede; testes do escopo verdes (268); `ruff` e validador sem violação nos arquivos tocados; nenhuma chave no diff. Ambiente e worktree conferidos.

**Decisões e suposições**
1. **Passo 6 — leitura da seção 7:** feita só ao chegar no passo, como o usuário pediu. As oito linhas (M04–M07, S05, F09, F12, S02) estavam `[ ]` e sem data. Nenhum registro foi alterado: `sp_city_portal`, `sp_finance_secretariat`, `sp_city_health`, `sp_city_education_page`, `mec` e `pe_de_meia` seguem `candidate`; `S05` (`gov.br/mdh`) e `S02` (bombeiros) também.
2. **`mec` e `pe_de_meia`:** o passo 6 da plan os devolve a `approved` se o link responder, e hoje respondem. Segui a instrução circunstancial ("apenas as marcadas `[x]`"), que é mais restritiva e mais recente; F09 e F12 estão `[ ]` na seção 7. Se o revisor entender que a aprovação da lista (§§1–5) já basta, é uma edição de dois registros.
3. **Sem 403 persistente, nenhum registro precisaria de `manual_check_on`:** as quatro páginas da prefeitura e `gov.br/mdh` respondem com o User-Agent. Quando o usuário marcar `[x]`, o caminho será **promoção sem atestado**; o campo `manual_check_on` fica implementado e testado, mas sem uso no catálogo.
4. **Atestado vencido em entrada `approved`:** o link vira `aviso` de vencido e, como deixa de ser aceito, o resumo `links` da entrada `approved` sem outro link vivo continua sendo `erro` ("nenhum link vivo"), como já era para link morto. O aviso de vencido em si nunca é erro.
5. **Data futura em `manual_check_on`** não vale como atestado (`0 <= idade <= 180`), porque a plan não diz e é dado suspeito. O registro continua válido; o link apenas não é aceito por atestado.
6. **API:** `check_link(url, options)` troca os argumentos soltos `timeout`/`retries`/`backoff` por `LinkCheckOptions`, para não passar de 4 parâmetros. Os chamadores de produção usavam só `url` (default), e os testes foram ajustados. `CatalogLookup` ganhou `manual_policy` (4º parâmetro) com default.
7. **Idade máxima:** `DEFAULT_MAX_AGE_DAYS` (180) passou a morar em `catalog.py` e é a mesma constante usada pelo resolvedor e por `--max-age-days`; `verify_catalog.py` a importa de lá.
8. `.env.example` foi editado mantendo o fim de linha CRLF do arquivo.

**Achados fora do escopo (não corrigidos)**
- `src/triage/automation/allowlist.py:18` — `@lru_cache(maxsize=None)` aciona UP033 do ruff (usar `@functools.cache`); já falhava antes desta plan e faz o comando de `ruff` da §7 devolver 1 erro.
- `tests/classification/test_decision.py`, `test_model.py`, `tests/ingestion/test_sanitizer.py`, `tests/storage/test_repository.py` — I001 e SIM117 do ruff; só aparecem se o `ruff` rodar em `tests` inteiro.
- `src/triage/automation/link_check.py` agora importa `triage.config` (folha, sem ciclo); só uma observação de dependência entre pacotes.
- O catálogo não tem registro com link em `corpodebombeiros.sp.gov.br`; o domínio segue com `SSLError` e, se o usuário marcar S02, o link ainda não poderá entrar.

**Pendências / riscos**
- **Passo 6 aguarda o usuário:** marcar `[x]` (com data) na seção 7 do documento de fontes e então promover os registros correspondentes, por promoção sem atestado. Nenhum registro aguarda um `manual_check_on`; mdh (S05) deve só virar `approved` se o registro também tiver telefone oficial (100), conforme as regras do catálogo.
- O robô só detecta 403: uma página atestada que saia do ar só será percebida quando o atestado vencer (limite a declarar na síntese, §8).
- Verificação feita no nível escopado; a §7 pede nível `ampla` para o revisor, e o `pipeline`/`interface` já rodaram (verdes), mas a suíte inteira e a sondagem `resolve_service` real ficam com ele.

## Resumo da execução (correção 1) — 2026-11-10

**Resultado:** Concluído (os três achados atendidos; sobre o achado 3, a seção 7 continua aberta, sem `[x]`).

**Achado 1 — `notebooks/evidence.ipynb` quebrava com a nova assinatura de `check_link`**
- Aplicadas as duas substituições exatas do veredito: `evidence.ipynb:58` (`import LinkCheckOptions, check_link`) e `evidence.ipynb:1725` (`check_link("http://127.0.0.1:9/", LinkCheckOptions(timeout=0.5, retries=2, backoff=0.1))`). O `Edit` recusa `.ipynb`; fiz a troca por substituição de texto, conferindo que cada trecho ocorria uma vez, para não reserializar o notebook.
- Evidência: `git diff -- notebooks` mostra só essas duas linhas; o JSON continua válido; `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` terminou e gravou a cópia (71 132 bytes), sem erro. O notebook do repositório não foi reescrito (as saídas salvas ficam como estavam). `output/notebook-evidence/` não existe depois da execução; `output/` segue com `logs`, `models` e `reports`, que já estavam lá (a pasta é ignorada pelo Git).

**Achado 2 — `mec` e `pe_de_meia` de volta a `approved`**
- `data/catalog.json` (registro `mec`, ~l.421-423; registro `pe_de_meia`, ~l.495-497): `"status": "candidate"` → `"approved"`; no `source_note`, removida a frase final "Rebaixado a candidate: … volta a approved quando responder." e acrescentada "Link verificado em 2026-11-10 com o User-Agent identificado do projeto." Nenhum telefone novo (o 0800 do MEC continua de fora, como a nota já dizia); nenhum outro campo mexido.
- Evidência: `python -m pytest tests/automation -q` → 220 passed (inclui o teste de conteúdo do catálogo); `python scripts/verify_catalog.py` com rede → `55 registro(s) verificado(s); sem erro.`, código 0, com `OK mec [link] https://www.gov.br/mec/pt-br: responde` e `OK pe_de_meia [link] https://www.gov.br/mec/pt-br/pe-de-meia: responde`, sem nenhuma linha `ERRO`.

**Achado 3 — seção 7 (passo 6), relida nesta rodada**
- `docs/fontes-publicas-sp-para-aprovacao.md`, seção 7, estado lido agora: M04, M05, M06, M07, S05, F09, F12 e S02 continuam todos `[ ]` e sem data. Portanto **nada da seção 7 foi promovido**: `sp_city_portal` (M04), `sp_finance_secretariat` (M05), `sp_city_health` (M06), `sp_city_education_page` (M07) e o registro de `gov.br/mdh` (S05) seguem `candidate`; S02 (bombeiros) segue sem link no catálogo e o domínio continua com erro de SSL.
- Promovidos nesta rodada, só pelo achado 2: `mec` (F09) e `pe_de_meia` (F12), por **promoção sem atestado**, porque o link responde ao User-Agent identificado. Nenhum `manual_check_on` foi usado no catálogo.

**Verificações executadas**
- `python -m pytest tests/automation -q` → 220 passed.
- `python scripts/verify_catalog.py` (com rede, uma vez) → sem erro, código 0.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` → concluído sem erro.
- `python -c "json.load(...)"` em `data/catalog.json` e `notebooks/evidence.ipynb` → ambos válidos.
- `git status --short` → além dos arquivos da rodada anterior, só `data/catalog.json` e `notebooks/evidence.ipynb` entraram no diff.

**Estado inicial do worktree (desta rodada):** os arquivos da rodada anterior (`.env.example`, `scripts/verify_catalog.py`, `src/triage/automation/{catalog,catalog_audit,link_check,resolver}.py`, `src/triage/config.py`, `tests/automation/test_{catalog,catalog_audit,catalog_content,link_check,resolver}.py`, `tests/test_config.py`) mais `specs/00-indice.md`, `specs/panorama/00-resumo.md` e a plan, todos modificados; `data/catalog.json` e `notebooks/evidence.ipynb` ainda limpos.

**Ambiente após a verificação:** nada criado no repositório. O `nbconvert` subiu um kernel Jupyter que terminou junto com o comando; a cópia executada e as saídas de verificação ficaram no scratchpad da sessão, fora do repositório. Confirmei `output/` à mão (sem `notebook-evidence/`).

**Critérios de aceite**
- [x] Achado 1 — notebook executa sem `TypeError`: `nbconvert --execute` terminou sem erro.
- [x] Achado 2 — `mec` e `pe_de_meia` `approved`, `source_note` ajustado: `pytest tests/automation` verde e `verify_catalog.py` sem erro.
- [x] Achado 3 — seção 7 relida; nada marcado `[x]`, nada promovido por ela, dito linha a linha acima.

**Decisões e suposições**
- O notebook foi editado por substituição de texto em vez de pelo `Edit`/`NotebookEdit`, porque o revisor pediu duas edições nas linhas de `source` do JSON e a reserialização de um notebook com saídas salvas geraria diff grande e alheio ao achado.
- Considerei que o veredito prevalece sobre a leitura restritiva da instrução circunstancial para `mec` e `pe_de_meia` (decisão 2 do resumo anterior), como o próprio veredito esclarece.

**Achados fora do escopo (não corrigidos)**
- Nada novo. Continuam os da rodada anterior: `allowlist.py:18` (UP033, já no backlog) e os avisos de `ruff` em testes de outros pacotes.

**Pendências / riscos**
- A promoção dos registros da seção 7 (M04–M07 e, se houver link e telefone 100 oficial, S05) continua pendente até o usuário marcar `[x]` com data; o caminho previsto é a promoção sem atestado, pois todos respondem hoje.
- Suíte inteira e sondagem `resolve_service` real seguem com o revisor (nível `ampla`).

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->

## Veredito — 2026-11-10 — 🔴 Reprovado

Verifiquei, sem confiar no resumo: o escopo bate com o §3.1; `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py -q` → 268 passed; `ruff` nos arquivos tocados limpo (o único erro do comando do §7 é `UP033` em `allowlist.py:18`, anterior e já no backlog, item 14); `validate.py` nos 12 `.py` → só `hardcoded` de baixa confiança em URLs de teste; `python scripts/verify_catalog.py` com rede → `55 registro(s) verificado(s); sem erro`, com as quatro páginas da prefeitura e o MEC respondendo ao User-Agent identificado (sem aviso 403 nem erro de conexão). O código de `link_check.py`, `catalog.py`, `resolver.py` e `catalog_audit.py` lido inteiro: User-Agent em HEAD e GET, HEAD com erro de conexão repetido como GET (timeout não), atestado só com 403 e vigente. Dois achados bloqueiam e um terceiro depende da seção 7:

1. `notebooks/evidence.ipynb:1725` — a célula do caso "link fora do ar" chama `check_link("http://127.0.0.1:9/", timeout=0.5, retries=2, backoff=0.1)`, e a assinatura nova é `check_link(url, options)`: reproduzi `TypeError: check_link() got an unexpected keyword argument 'timeout'`. O notebook de evidências, entregável do projeto, deixa de executar. Critério violado: regressão em consumidor de `check_link` (nível `ampla`, §7); o notebook não constava do §3.1 por defeito da plan, que agora o inclui só nesta célula. **Correção exata** (arquivo `notebooks/evidence.ipynb`, duas edições nas linhas de `source` do JSON):
   - antes: `"from triage.automation.link_check import check_link\n",` → depois: `"from triage.automation.link_check import LinkCheckOptions, check_link\n",`
   - antes: `"    return check_link(\"http://127.0.0.1:9/\", timeout=0.5, retries=2, backoff=0.1)\n",` → depois: `"    return check_link(\"http://127.0.0.1:9/\", LinkCheckOptions(timeout=0.5, retries=2, backoff=0.1))\n",`
   - verificação: `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <pasta do scratchpad>` termina sem erro (não reescreva o notebook do repositório; as saídas salvas continuam válidas). Confira que `output/notebook-evidence/` não sobra.
2. `data/catalog.json` registros `mec` (linha ~404) e `pe_de_meia` (linha ~478) — o passo 6 manda devolvê-los a `approved` se o link responder; respondem (medição do passo 3 e `verify_catalog.py`), e F09 e F12 estão `[x]` na lista aprovada (§§1–5 do documento de fontes), então a seção 7 não é pré-condição. A instrução circunstancial do despacho ("apenas as marcadas na seção 7") foi ambígua e o executor a leu de forma restritiva; o passo 6 da plan prevalece. Correção: nesses dois registros, `"status": "candidate"` → `"status": "approved"` e, no `source_note`, remover a frase final "Rebaixado a candidate: … volta a approved quando responder." e acrescentar "Link verificado em 2026-11-10 com o User-Agent identificado do projeto." Sem telefone novo (o 0800 do MEC segue de fora). Verificação: `python -m pytest tests/automation -q` verde (o teste de conteúdo do catálogo cobre os `approved`) e `python scripts/verify_catalog.py` sem erro com os dois em `approved`.
3. Seção 7 (passo 6): reler `docs/fontes-publicas-sp-para-aprovacao.md` na rodada de correção. Fonte marcada `[x]` com data cujo registro hoje é `candidate` (`sp_city_portal`, `sp_finance_secretariat`, `sp_city_health`, `sp_city_education_page`, M04–M07; S05/`gov.br/mdh` só se o registro tiver link e o telefone 100 oficial) é promovida a `approved` **sem atestado**, se o link responder (todos respondem hoje). Fonte `[ ]` ou `[-]` permanece `candidate`. Dizer no resumo, linha a linha, o que foi promovido. Se nada estiver marcado, registre que a seção 7 continua aberta e que só os dois do achado 2 foram promovidos.

## Veredito — 2026-11-10 — 🟢 Aprovado (correção 1)

Verifiquei os três achados do veredito anterior, sem confiar no resumo:
1. **Notebook:** `git diff` mostra só as duas linhas pedidas (`import LinkCheckOptions, check_link` e a chamada com `LinkCheckOptions(timeout=0.5, retries=2, backoff=0.1)`). Reproduzi a chamada: `LinkStatus(ok=False, status_code=None, error='ConnectTimeout')`, sem `TypeError`; o JSON é válido e `output/notebook-evidence/` não existe.
2. **`mec` e `pe_de_meia`:** o diff de `data/catalog.json` é exatamente `candidate` → `approved` e o ajuste do `source_note` nos dois registros, nada mais. `resolve_entry` real, com rede, devolve o link dos dois sem motivo de falha; `resolve_service` real das 8 categorias continua devolvendo link vivo.
3. **Seção 7:** relida pelo executor; continua sem nenhum `[x]`, e nada foi promovido por ela. O critério "só as marcadas foram promovidas" está atendido; a promoção de M04–M07 e S05 fica para depois da marcação do usuário, sem atestado (todas respondem).

Regressão: `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py tests/classification tests/evaluation -q` → 409 passed; `ruff` nos arquivos tocados com o único erro anterior (`UP033` em `allowlist.py`, backlog item 14); `python scripts/verify_catalog.py` com rede → `55 registro(s) verificado(s); sem erro`, só avisos de telefone dos códigos oficiais (193, 199, 100). Nenhum TODO, teste em skip, chave ou citação a plan; `manual_check_on` implementado e testado, sem uso no catálogo.
