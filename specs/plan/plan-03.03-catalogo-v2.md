---
tipo: "plan"
familia: "03"
item: "R03.3"
titulo: "Evoluir o catálogo para vários links e telefones por serviço, com aprovação e verificação"
dominio: "Automação"
status: "🟡 Em execução"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->
