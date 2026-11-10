---
tipo: "plan"
familia: "03"
item: "R03.9"
titulo: "Identificar o verificador de links e aceitar links bloqueados ao robô, validados manualmente"
dominio: "Automação"
status: "🔴 A executar"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->
