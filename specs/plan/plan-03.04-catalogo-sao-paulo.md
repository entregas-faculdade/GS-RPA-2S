---
tipo: "plan"
familia: "03"
item: "R03.4"
titulo: "Carregar no catálogo a lista aprovada de fontes públicas (saúde, educação, veículos e prefeitura de São Paulo)"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: ""
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

> A lista foi **aprovada pelo usuário em 2026-11-10** (documento do §5.A). Pendente só a decisão sobre as linhas `[?]` da
> prefeitura, que entram como `candidate`.

# 1. Objetivo
O catálogo cobre, para o piloto **estado e cidade de São Paulo**, as áreas de saúde, educação, veículos e serviços da
prefeitura, com links e telefones oficiais **aprovados pelo usuário** e verificados por máquina, e continua dando a
resposta certa às 8 categorias que já existem.

# 2. Contexto
O formato v2 (vários links e telefones, esfera, abrangência, aprovação) vem da plan-03.03
([[03.01-catalogo-e-allowlist]]). Esta plan é **só conteúdo**: dados e testes de dados. A curadoria é do usuário: ele
decide a lista (documento do §5.A), o executor a carrega.

Regras de honestidade do conteúdo (valem acima de qualquer conveniência):
- **Nenhum link nem telefone é inventado.** Valem só os que estão no documento do §5.A ou que o executor encontrou na
  página **oficial** do órgão e registrou no `source_note` (de onde veio).
- Link que não responde ou telefone `não confirmado` pelo verificador **não** vira `approved`: fica `candidate`, com o
  motivo no `source_note`, e vai listado no resumo.
- O critério do catálogo é ser **serviço público** de órgão oficial; sem esfera ou órgão claros, não entra.
- O catálogo atual tem três fragilidades já conhecidas (certidão de nascimento aponta uma notícia; título de eleitor e
  IPTU apontam o catálogo geral do gov.br; `tse.jus.br` fora da allowlist). Onde a lista aprovada trouxer uma fonte
  melhor, **acrescente** o registro novo (id diferente) e mantenha o antigo como está.

# 3. Escopo
## 3.1 Dentro
- `data/catalog.json` — registros novos conforme o §5.A (`status: approved` ou `candidate`)
- `data/allowed_domains.json` — **só** os sufixos que o §5.A marcar como aprovados, cada um com `reason`
- `tests/automation/test_catalog_content.py` (novo) — testes de conteúdo, sem rede

## 3.2 Fora
- Qualquer código em `src/` e `scripts/` (o formato e o verificador são da plan anterior).
- Domínio fora da allowlist e que o §5.A não aprovou; links de redes sociais e de aplicativos.
- Busca por texto e mensagens (planos seguintes).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | catálogo, allowlist, verificação de links (o formato v2 está descrito na plan-03.03 e, após a síntese, na spec) |
| ADR | [[003-seguranca-sem-autenticacao]] | só domínios oficiais |
| Dados | `docs/fontes-publicas-sp-para-aprovacao.md` | a lista aprovada pelo usuário (§5.A) |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | testes |
| Skill | `test-unitario` | testes de dados |
| Código | `data/catalog.json`, `data/allowed_domains.json`, `src/triage/automation/catalog.py`, `src/triage/automation/catalog_audit.py`, `scripts/verify_catalog.py` | formato e verificador |

# 5. Instruções de execução

## 5.A Lista aprovada (entrada desta plan)
A lista aprovada pelo usuário em 2026-11-10 é o arquivo **`docs/fontes-publicas-sp-para-aprovacao.md`** (fonte única; não
a copie para esta plan nem a edite). Leia-o inteiro, inclusive as seções 5 e 6. Regras de leitura:

1. **Decisão.** `[x]` = aprovada pelo usuário: vira `approved` **se** passar na verificação do passo 4; se falhar, vira
   `candidate`, com o motivo no `source_note`. `[-]` = cortada: não entra. `[?]` = pendente de decisão do usuário (M04 a
   M07, prefeitura com HTTP 403): entra como `candidate`, **nunca** `approved`.
2. **Uma linha do documento = um registro** (`id` curto e único, em inglês). `kind` conforme a coluna *O que é* e
   `scope` pela seção (Federal, Estadual, Municipal); `area` pelo assunto (`safety` para a seção 4).
3. **Telefones: só números oficiais.** Entram como `approved` (a) o número **confirmado** pelo verificador numa página
   oficial da própria fonte e (b) os códigos oficiais de emergência e atendimento 190, 192, 193, 199, 100, 180, 136 e 156.
   Qualquer outro número (ANVISA e MEC/INEP, 0800) só entra se o executor o achar e confirmar na página de contato do
   próprio órgão, alcançada pelos links do site oficial; se não achar, **fica de fora** e o resumo diz qual. Nenhum número
   de outra origem.
4. **Lacunas (seção 5 do documento).** Para cada assunto, criar um registro `kind: portal` ou `channel` **com os links e
   telefones das fontes que a coluna *Fontes usadas* indica** (sem URL nova), `keywords` do assunto (como o cidadão o
   escreve) e `instructions` que dizem que é o **caminho geral e não o serviço específico** e o que buscar ali (ex.:
   "ligue para o 156 ou procure no SP156"). Heredam o `status` das fontes de que dependem.
5. **Fonte sem link vivo** (MEC, Pé-de-Meia, Corpo de Bombeiros, `gov.br/mdh`, 403 da prefeitura): sem link vivo e sem
   telefone oficial permitido, o registro é `candidate`; com telefone oficial permitido (ex.: 193, 100), o canal pode ser
   `approved` só com o telefone, **sem o link que não responde**.

## 5.B Passos
1. [dirigido] **Registros.** Para cada linha `[x]` ou `[?]` do documento do §5.A, e para cada lacuna da seção 5, um registro v2 em `data/catalog.json`: `id` curto e único (sem
   reutilizar um id existente), `category` só quando o serviço corresponde **exatamente** a uma das 8 categorias do
   classificador (senão `null`), `kind`, `scope`, `coverage` verdadeiro (ex.: `Cidade de São Paulo`), `area`,
   `display_name`, `agency`, `instructions` (1 a 2 frases em português claro, sem prometer nada que a página não diga),
   `keywords` (6 a 12 termos **como o cidadão escreve**, sem acento, com variações: `buraco na rua`, `tapa buraco`,
   `lampada queimada`), `links`, `phones`, `source_note`, `verified_on` (a data da verificação) e `status`.
2. [dirigido] **Links.** Quando o §5.A traz só o domínio, abrir o site **oficial** e escolher a página mais específica
   que existir para o serviço; registrar no `source_note` como foi achada. Se não for possível abrir ou achar, o
   registro fica `candidate`. **Proibido** adivinhar caminho de URL.
3. [dirigido] **Allowlist.** Os sufixos de `*.sp.gov.br` e `*.prefeitura.sp.gov.br` já cabem em `gov.br`. Qualquer outro
   domínio entra em `data/allowed_domains.json` **somente** se o §5.A o aprovou, com `reason`.
4. [dirigido] **Verificação.** Rodar `python scripts/verify_catalog.py` **com rede**. Todo erro (link fora da allowlist, sem
   link vivo) corrige o dado ou rebaixa o registro a `candidate`. Colar no resumo a saída resumida e a lista de
   registros rebaixados e de telefones `não confirmados`. Telefone `não confirmado` segue a regra 3 do §5.A: só fica se for um
   dos códigos oficiais listados ali; os demais saem do catálogo e o resumo diz quais.
5. [dirigido] **Testes de conteúdo** (sem rede, em `test_catalog_content.py`): todo registro carrega no v2; `id` único;
   todo link dos `approved` está na allowlist; todo `approved` tem `keywords` com ao menos 5 termos; as 8 categorias
   originais ainda resolvem para a mesma URL de antes; para cada área (`health`, `education`, `vehicles`, `city`,
   `safety`) existe ao menos um `approved`; há ao menos um `approved` com `phones` em `safety`; nenhum `keywords` repete
   um termo de outro registro de **área diferente** sem estar em uma lista de exceções documentada no teste.
6. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Cada linha `[x]` do documento virou registro `approved` ou, com motivo registrado, `candidate`; nenhuma linha `[?]` ou `[-]` virou `approved`.
- [ ] Cada lacuna da seção 5 tem um registro de caminho geral, sem URL nova e com instrução que não promete o serviço específico.
- [ ] Todo telefone `approved` é confirmado numa página oficial da fonte ou é um dos códigos oficiais do §5.A, regra 3.
- [ ] Nenhum link ou telefone foi inventado: todo item vem do §5.A ou de página oficial citada no `source_note`.
- [ ] `scripts/verify_catalog.py` (com rede) roda sem erro; avisos listados no resumo.
- [ ] As 8 categorias originais resolvem como antes; os canais `safety` aprovados têm telefone.
- [ ] Testes de conteúdo verdes e sem rede; `ruff` sem erro no arquivo de teste; nenhuma chave no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só `data/catalog.json`, `data/allowed_domains.json` e o teste de conteúdo (o documento de `docs/` não muda).
- `python -m pytest tests/automation -q` → verde.
- `python -m ruff check tests/automation` e `validate.py` do `padrao-python` no teste novo → sem achado.
- `python scripts/verify_catalog.py` (com rede, uma vez) → sem erro; o revisor abre uma amostra de links e confere
  cada telefone `approved` contra a página citada no `source_note`.
- Conferência linha a linha entre o documento do §5.A e o catálogo (`[x]` × `approved`; `[?]` e `[-]`).
- **Gate:** `nenhum — coberto pelo verificador e pelos testes de conteúdo`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md`

Levar, **substituindo** a descrição do conteúdo ("oito serviços, uma URL por categoria"): o piloto SP (estado e cidade),
as áreas cobertas, que a lista é **aprovada pelo usuário** antes de entrar e que o conteúdo exige verificação por máquina;
os domínios de allowlist acrescentados, se houver; o limite declarado (apenas SP; outras cidades e estados ficam sem fonte).

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências

**O que foi feito**
- `data/catalog.json`: 47 registros v2 acrescentados aos 8 originais (55 no total; 49 `approved`, 6 `candidate`). São 39 linhas do documento (F01–F19, E01–E08, M01–M07, S01–S06) e 7 lacunas da seção 5 (ids `gap_*`). Todos com `category: null`, `verified_on: 2026-11-10`; os 8 originais ficaram intactos e continuam primeiro no arquivo.
- Telefones `approved`: 136, 156, 190, 192, 193, 199, 100 e 180 (códigos oficiais da regra 3) e três confirmados pelo verificador em página oficial: ANVISA `0800 642 9782` (link `gov.br/anvisa/pt-br/canais_atendimento`, achado nos links do site da ANVISA), INEP `0800 61 61 61` (link `gov.br/inep/pt-br/canais-de-atendimento/fale-conosco`, achado nos links do site do INEP) e INSS `135` (já confirmado em `gov.br/inss/pt-br/servicos/aposentadorias`, link do registro `social_security`, repetido em `meu_inss`).
- `data/allowed_domains.json`: não alterado. Todos os hosts novos terminam em `gov.br` (inclusive `*.sp.gov.br` e `*.prefeitura.sp.gov.br`) e nenhum domínio novo foi aprovado no documento.
- `tests/automation/test_catalog_content.py` (novo): 7 testes de conteúdo, sem rede (carregamento v2, `id` único, allowlist dos `approved`, mínimo de 5 `keywords`, 8 categorias originais com a mesma URL, 5 áreas com `approved`, `safety` com telefone, `keywords` sem repetir entre áreas).
- `tests/automation/test_catalog.py:30-43` e `tests/automation/test_resolver.py:143`: três testes que assumiam "o catálogo tem 8 registros" passaram a olhar só os registros com `category` (ver Decisões).

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `data/catalog.json` | alterado | +47 registros v2 |
| `tests/automation/test_catalog_content.py` | criado | testes de conteúdo |
| `tests/automation/test_catalog.py` | alterado | os 2 testes dos "oito" filtram por `category` |
| `tests/automation/test_resolver.py` | alterado | loop do teste de categorias filtra por `category` |

**Verificações executadas**
- `python scripts/verify_catalog.py` (com rede, duas rodadas): na 1ª, `mec` e `pe_de_meia` ficaram `approved` e deram `ERRO nenhum link vivo` (`ConnectionError`; o HEAD é reiniciado pelo servidor, embora um GET meu tenha dado 200); rebaixei os dois e na 2ª rodada → `55 registro(s) verificado(s); sem erro.` Avisos: ver abaixo.
- `python -m pytest tests/automation -q` → 187 passed.
- `python -m ruff check tests/automation` → All checks passed. `validate.py` (padrao-python) em `test_catalog_content.py` → 0 achados.
- Gate: `nenhum` na §7, não se aplica.

**Avisos do verificador e rebaixados**
- Rebaixados por link sem resposta (`candidate`, motivo no `source_note`): `mec`, `pe_de_meia` (ConnectionError).
- `candidate` por decisão `[?]` pendente, HTTP 403: `sp_city_portal` (M04), `sp_finance_secretariat` (M05), `sp_city_health` (M06), `sp_city_education_page` (M07).
- Telefone `não confirmado` mantido por ser código oficial: 193 (`fire_brigade_193`, `gap_fire_brigade`), 199, 100, 156 (M05–M07, candidatos).
- Telefones `não confirmados` e removidos: nenhum. Telefone da lista que ficou de fora: o `0800 61 61 61` do MEC (F09), que só aparece na página do INEP, não do MEC.
- Registros só com telefone, sem link (regra 5): `fire_brigade_193`, `human_rights_100`, `gap_fire_brigade`.

**Estado inicial do worktree:** `M specs/00-indice.md`, `M specs/panorama/00-resumo.md`, `M specs/plan/plan-03.04-catalogo-sao-paulo.md`, `?? docs/fontes-publicas-sp-para-aprovacao.md`. Ao final apareceram também `specs/panorama/00-planejamento.md`, `plan-03.07`, `plan-03.08` (novo), alterações que não são minhas (provavelmente do revisor em paralelo).

**Ambiente após a verificação:** nada criado no repositório; rascunhos (gerador e saídas) ficaram só no scratchpad da sessão, fora do repo. Nenhum processo, servidor ou contêiner subido (`snapshot` da `code-limpeza-ambiente` não rodado: a tarefa só fez requisições HTTP).

**Critérios de aceite**
- [x] Cada `[x]` virou `approved` ou `candidate` com motivo; nenhuma `[?]`/`[-]` virou `approved` — `mec` e `pe_de_meia` rebaixados com motivo; M04–M07 `candidate`; não há linha `[-]`.
- [x] Cada lacuna da seção 5 tem registro `gap_*` de caminho geral, só com URLs de fontes já listadas e instrução que diz "caminho geral, não o serviço específico".
- [x] Todo telefone `approved` é código oficial da regra 3 ou confirmado em página oficial (ANVISA, INEP, INSS).
- [x] Nenhum link ou telefone inventado: tudo vem do documento ou de página oficial citada no `source_note`.
- [x] `verify_catalog.py` roda sem erro; avisos listados acima.
- [x] As 8 categorias resolvem como antes (testes parametrizados); canais `safety` aprovados têm telefone.
- [x] Testes de conteúdo verdes e sem rede; `ruff` sem erro; nenhuma chave no diff.

**Decisões e suposições**
- Os 3 testes antigos assumiam exatamente 8 registros e quebrariam com o conteúdo novo; ajustei-os com a menor mudança possível (filtrar por `category`), embora o §3.1 só liste o teste novo. Se o revisor preferir outra solução, é só pedir.
- `category: null` em todos os registros novos, para não competir com os 8 originais (que ficam primeiros no arquivo).
- `meu_inss` leva um segundo link (`gov.br/inss/.../aposentadorias`, já no catálogo) só para o verificador conseguir confirmar o 135.
- `mec` e `pe_de_meia` rebaixados porque o verificador do projeto (HEAD+GET) não os alcançou, mesmo com um GET simples meu dando 200; a regra da plan é seguir o verificador.
- `SHARED_KEYWORDS_ACROSS_AREAS` ficou vazia: não havia repetição entre áreas.
- Áreas atribuídas por assunto (ex.: Receita Federal, JUCESP, SEFAZ em `tax`; Trabalho e Emprego em `social`).

**Achados fora do escopo (não corrigidos)**
- `data/catalog.json`: `birth_certificate` ainda aponta uma notícia, `voter_id` e `property_tax` o catálogo geral do gov.br (fragilidades já conhecidas na plan); os registros `gap_*` novos coexistem com eles.
- `verify_catalog.py`: a saída vai em console cp1252 (acentos ilegíveis no Windows) e o HEAD reiniciado pelo servidor do MEC derruba um link que o GET alcança.

**Pendências / riscos**
- Decisão do usuário sobre M04–M07 (prefeitura, 403): `candidate` até lá; sem a Fazenda municipal ativa, "alvará" e "IPTU municipal" caem no `gap_city_permit_property_tax`.
- `mec` e `pe_de_meia` voltam a `approved` quando o link responder.
- Verificação só escopada: não rodei a suíte inteira do repositório.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->

## Veredito — 2026-11-10 — 🟢 Aprovado

Verifiquei, sem confiar no resumo:
- **Escopo:** `git status` mostra `data/catalog.json`, o teste novo `tests/automation/test_catalog_content.py` e, fora da lista do §3.1, `test_catalog.py` e `test_resolver.py` (três testes que assumiam "o catálogo tem 8 registros" e quebrariam com o conteúdo novo). A mudança é mínima (filtrar por `category`), necessária e justificada no resumo; aceito. `data/allowed_domains.json`, `src/` e `scripts/` intactos.
- **Catálogo:** 55 registros (49 `approved`, 6 `candidate`). Os 8 originais permanecem idênticos aos do `HEAD` e continuam primeiros. As 39 linhas do documento (F01–F19, E01–E08, M01–M07, S01–S06) e as 7 lacunas têm registro; `[?]` (M04–M07) ficaram `candidate`; `mec` e `pe_de_meia` ficaram `candidate` por não terem link vivo. Nenhuma linha `[x]` ficou sem registro, nenhuma `[?]` virou `approved`.
- **Links:** todo link novo vem do documento; as exceções são `anvisa` e `inep`, cujas páginas de contato o executor achou pelos links do site oficial e que o verificador abre; `meu_inss` repete o link do INSS para confirmar o 135. Nenhum link deduzido.
- **Telefones `approved`:** só 136, 156, 190, 192, 193, 199, 100, 180, 135 (códigos oficiais da regra 3) e os 0800 da ANVISA e do INEP, confirmados pelo verificador em página oficial. O 0800 do MEC (F09) ficou de fora, como a regra manda.
- **Lacunas:** os 7 registros `gap_*` usam só links e telefones das fontes que a seção 5 indica e dizem na instrução que são "caminho geral, não o serviço específico".
- **Verificador:** `python scripts/verify_catalog.py` com rede → `55 registro(s) verificado(s); sem erro.`, só avisos: `mec` e `pe_de_meia` (erro de conexão), os 4 da prefeitura (HTTP 403) e telefones `não confirmados` dos códigos oficiais (193, 199, 100, 156).
- **Testes e lint:** `python -m pytest tests/automation tests/pipeline tests/interface tests/classification tests/evaluation -q` → 351 passed; `ruff` limpo; `validate.py` em `test_catalog_content.py` → 0 achados.
- **Sinais de atalho:** nenhum TODO, nenhuma plan citada em dado ou teste, nenhuma chave.
Registrado: o HEAD que o servidor do MEC reinicia derruba um link que o GET alcança; a correção entra na plan do verificador de links.
