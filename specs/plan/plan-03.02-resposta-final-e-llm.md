---
tipo: "plan"
familia: "03"
item: "R03.2"
titulo: "Montar a resposta final ao cidadão, com LLM opcional e caminho seguro"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Média"
tags: ["plan"]
relacionados: ["[[005-llm-apenas-reformula-resposta]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "plan-03.01-catalogo-e-allowlist"
destino_sintese: "specs/03.02-resposta-final-e-llm.md"
---

# 1. Objetivo
`build_response(service)` devolve sempre uma resposta utilizável: o texto em template com o link oficial e, quando o
LLM está habilitado e responde de forma válida, a mesma resposta reformulada em linguagem natural; qualquer falha do
LLM cai no template, com log.

# 2. Contexto
Decisão em [[005-llm-apenas-reformula-resposta]]: o LLM **só reformula** o que já foi decidido, recebe apenas texto
anonimizado, não escolhe categoria nem URL, e o sistema funciona integralmente com ele desligado. O enunciado exige,
se houver LLM, tratar resposta vazia ou inválida e ter caminho seguro quando a chamada falhar. Provedor ainda em
aberto: para não travar, o cliente é **genérico, compatível com a API de chat no formato OpenAI** (URL base, modelo e
chave vêm de variáveis de ambiente), o que atende provedores gratuitos que expõem esse formato.

# 3. Escopo
## 3.1 Dentro
- `src/triage/automation/templates.py` — `render_template(service)` com o texto padrão em português (órgão, instruções, link)
- `src/triage/automation/llm_client.py` — `LlmClient` (protocolo) e `OpenAICompatibleClient` (`requests`, timeout, uso do `retry_with_backoff` da plan 03.01)
- `src/triage/automation/response.py` — `build_response(service, client=None) -> Response(text, used_llm, fallback_reason)`
- `src/triage/automation/response_guard.py` — `validate_llm_output(text, service)`
- `tests/automation/test_response.py`, `tests/automation/test_llm_client.py`, `tests/automation/test_response_guard.py` — com cliente simulado (sem rede)

## 3.2 Fora
- Escolha do provedor, criação de conta ou chave (do usuário; fora do repositório).
- Classificação e decisão de revisão (família 02); gravação (plan 04.01).
- Conversa multi-turno ou esclarecimento de pedido (explicitamente fora, ADR 005).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[005-llm-apenas-reformula-resposta]] | papel e limites do LLM |
| ADR | [[003-seguranca-sem-autenticacao]] | chave em `.env`, PII anonimizada |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `src/triage/automation/` (catálogo, allowlist, `retry_with_backoff` em `src/triage/common/retry.py`) | reutilizar o que a plan 03.01 entregou |
| Código | `src/triage/config.py` | `llm_enabled`, `llm_base_url`, `llm_model`, `llm_api_key` |

# 5. Instruções de execução
1. [dirigido] `render_template(service)`: texto curto, claro, em português, com nome do serviço, órgão, instruções e o link. Determinístico; é o **padrão** e o fallback.
2. [dirigido] `OpenAICompatibleClient.rewrite(prompt) -> str`: POST em `{base_url}/chat/completions` com `model`, `messages` e `temperature` baixa; `timeout` explícito; `retry_with_backoff` para falhas transitórias; chave só no header `Authorization`, **nunca** em log. Resposta sem `choices`, sem conteúdo, vazia ou só espaços → levantar `LlmInvalidResponse`. Erro de rede/HTTP persistente → `LlmUnavailable`.
3. [dirigido] Prompt de reformulação: contém **somente** a resposta-template já pronta (que traz o link) e a instrução de reescrever de forma amigável e curta, sem alterar link, órgão nem acrescentar fatos. Nenhum texto do cidadão entra no prompt (mesmo anonimizado) — **decisão desta plan**, mais restritiva que o ADR: o LLM não precisa dele para reformular.
4. [dirigido] `validate_llm_output(text, service)`: rejeita se (a) vazio; (b) acima de `MAX_RESPONSE_LENGTH` (constante); (c) contém **qualquer** URL diferente da URL do serviço (regex de URL; comparar por igualdade exata); (d) não contém a URL do serviço. Rejeição → `fallback_reason` e uso do template.
5. [dirigido] `build_response(service, client=None)`: sem cliente ou `llm_enabled=False` → template (`used_llm=False`, `fallback_reason=None`). Com cliente: tenta reformular; `LlmInvalidResponse`, `LlmUnavailable` ou saída reprovada por `validate_llm_output` → template com `fallback_reason` (`llm_unavailable`, `llm_invalid_response`, `llm_output_rejected`) e log; **nunca** propaga exceção.
6. [dirigido] Testes com cliente simulado: LLM desligado; sucesso; resposta vazia; JSON sem `choices`; timeout; resposta com URL inventada; resposta sem o link; resposta gigante; e que a chave de API não aparece em `caplog` nem no prompt enviado.
7. Rodar `python -m pytest tests/automation -q` e `ruff`.

# 6. Critérios de aceite
- [ ] Com `LLM_ENABLED=false` (padrão) nenhuma chamada de rede é feita e a resposta sai do template.
- [ ] Toda falha do cliente (vazia, inválida, timeout, rede) resulta em template + `fallback_reason` + log, sem exceção.
- [ ] Resposta do LLM com URL diferente da do serviço é descartada.
- [ ] A chave de API não aparece em log, prompt nem exceção.
- [ ] O texto do cidadão nunca é enviado ao provedor.
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation -q` → verde.
- `python -m ruff check src/triage/automation tests/automation` → sem erro.
- Leitura de `llm_client.py` → timeout presente; chave só no header; nenhum `logging` com `api_key`.
- `grep -rn "api_key" src` → nenhuma ocorrência em chamada de log.
- **Gate:** `nenhum — coberto por teste`.

# 8. Destino da síntese
**Destino:** `specs/03.02-resposta-final-e-llm.md`

Levar: contrato de `build_response` e de `Response`; valores de `fallback_reason`; regras de `validate_llm_output`;
variáveis de ambiente do LLM e o fato de o padrão ser desligado; decisão de que **nenhum texto do cidadão** vai ao
provedor (prompt só com a resposta-template); formato de API compatível com OpenAI. Atualizar o ADR 005 apenas se o
provedor escolhido pelo usuário mudar a decisão.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-09

**Resultado:** Concluído

**O que foi feito**
- `templates.py:12` — `render_template` determinístico com nome, órgão, instruções e link.
- `llm_client.py` — `LlmClient` (Protocol), `LlmUnavailable`/`LlmInvalidResponse`, `OpenAICompatibleClient` (POST `{base_url}/chat/completions`, timeout de 15 s, `retry_with_backoff` com 2 tentativas, chave só no header) e `build_llm_client(settings)`.
- `response_guard.py` — `validate_llm_output` devolve o motivo da rejeição (`empty`, `too_long`, `foreign_url`, `missing_url`) ou `None`; `MAX_RESPONSE_LENGTH = 1200`.
- `response.py` — `Response` e `build_response(service, client=None)`; prompt = instrução + template, sem texto do cidadão.
- Testes sem rede nos três arquivos de `tests/automation/`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/automation/templates.py` | criado | template padrão |
| `src/triage/automation/llm_client.py` | criado | cliente OpenAI-compatível e fábrica |
| `src/triage/automation/response_guard.py` | criado | validação da saída do LLM |
| `src/triage/automation/response.py` | criado | `Response` e `build_response` |
| `tests/automation/test_response.py` | criado | template, sucesso e fallbacks |
| `tests/automation/test_llm_client.py` | criado | requisição, falhas, chave fora de log, fábrica |
| `tests/automation/test_response_guard.py` | criado | limites e falsos positivos da regra de URL |

**Verificações executadas**
- `python -m pytest tests/automation -q` → 108 passed (0,39 s).
- `python -m ruff check src/triage/automation tests/automation` → All checks passed (ruff local 0.14.2; o pin do projeto é 0.17.4).
- `scripts/validate.py` do `padrao-python` nos 4 arquivos de `src` → sem achados.
- `grep -rn "api_key" src` → única ocorrência perto de log é `logging_setup.py:52` (filtro que mascara a chave), não é chamada de log.

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** nada criado (só pytest/ruff, sem processo, servidor ou banco).

**Critérios de aceite**
- [x] LLM desligado → sem rede e template — `build_llm_client` devolve `None` (`test_factory_returns_none_when_llm_is_disabled`); `build_response` sem cliente (`test_without_client_...`).
- [x] Falha do cliente → template + `fallback_reason` + log, sem exceção — `test_every_failure_falls_back_to_template_with_reason_and_log`; vazia/inválida/timeout/5xx em `test_llm_client.py`.
- [x] URL diferente descartada — casos `foreign_url` em `test_response_guard.py` e `test_response.py`.
- [x] Chave fora de log, prompt e exceção — `test_api_key_never_reaches_logs_or_exceptions`; `test_posts_chat_completion_...` (corpo sem chave).
- [x] Texto do cidadão nunca enviado — `build_response` não recebe esse texto; `test_prompt_carries_only_the_template_text`.
- [x] Ambiente/worktree limpos — só os 7 arquivos do escopo (`git status`).
- [x] Testes, ruff e validador sem violação.
- [x] Sem dado pessoal, chave ou `.env` — a chave nos testes é fictícia.

**Decisões e suposições**
- A assinatura fixa `build_response(service, client=None)` não recebe `Settings`; a flag `llm_enabled` é aplicada em `build_llm_client(settings)` (devolve `None` se desligado ou com URL/modelo/chave vazios). Quem monta o pipeline passa esse cliente.
- `validate_llm_output` devolve `str | None` (motivo ou aprovado) em vez de `bool`, para o log dizer a causa.
- A regex de URL também pega `www.` sem esquema e remove pontuação final de frase antes de comparar; `http://` ou `/extra` contam como URL diferente.
- HTTP 5xx é transitório (repete, reaproveitando `TransientHttpError` de `link_check`); 4xx → `LlmUnavailable` sem nova tentativa.
- `build_response` captura só `LlmUnavailable` e `LlmInvalidResponse` (contrato do cliente); exceção inesperada de um cliente alheio propagaria, em vez de ser engolida.
- `MAX_RESPONSE_LENGTH = 1200`, timeout 15 s e 2 tentativas são constantes escolhidas por mim; a plan não fixou os valores.

**Achados fora do escopo (não corrigidos)**
- `.env.example` não documenta que `LLM_ENABLED=false` é o padrão nem o formato esperado de `LLM_BASE_URL` (ex.: termina em `/v1`).

**Pendências / riscos**
- Nenhuma chamada real ao provedor foi feita (provedor ainda em aberto); o formato foi validado só contra cliente simulado.
- ruff local (0.14.2) difere do pin do projeto (0.17.4).

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-09 — 🔴 Reprovado

**Verificado (nível escopada), com saída real:** `git status`/`git diff --stat` (só os sete arquivos de §3.1; nada fora do escopo, nada faltando) · leitura integral de `templates.py`, `llm_client.py`, `response_guard.py` e `response.py` · `python -m pytest tests/automation -q` → 108 passed · `python -m ruff check --no-cache src/triage/automation tests/automation` → All checks passed · `padrao-python/scripts/validate.py src/triage/automation` → 0 achados · `grep -rn api_key src` → nenhuma chamada de log com a chave (`logging_setup.py:52` é o filtro de máscara) · timeout explícito de 15 s, chave só no header `Authorization`, mensagens de erro e de log sem a chave · prompt = instrução fixa + template, sem texto do cidadão · sondagem do guard: `http://evil.com` junto do link, link em markdown com URL estranha e `www.` sem esquema → rejeitados; pontuação final colada ao link → aceita · cliente real contra um servidor local que responde `{}` → `fallback_reason="llm_invalid_response"` com o template · caches removidos.

**Decisões do executor aceitas:** `build_llm_client(settings)` aplica `llm_enabled` e devolve `None` com configuração incompleta; `validate_llm_output` devolve o motivo (`str | None`); 5xx transitório e 4xx definitivo; os valores de timeout, tentativas e `MAX_RESPONSE_LENGTH` como constantes nomeadas.

**Achados**
1. `src/triage/automation/response_guard.py:7` (`URL_PATTERN`) — só reconhece URL com `http(s)://` ou `www.`. Domínio sem esquema passa: `validate_llm_output("Acesse detran-sp.com.br/pagar ou <url do serviço>", service)` e o mesmo com `golpe.com` devolvem `None` (aprovado), e o texto com o link inventado chega ao cidadão. Critério violado: §6 "Resposta do LLM com URL diferente da do serviço é descartada" e o ADR 005 (o LLM não escolhe URL). Exigido: a regra rejeita (`foreign_url`) também endereço sem esquema que não seja o do serviço, sem rejeitar a menção legítima ao próprio domínio do serviço ou a um domínio pai dele (por exemplo "gov.br" quando o serviço é `www.gov.br/...`); testes com `detran-sp.com.br/pagar` e `golpe.com` (rejeitados) e com "no portal gov.br" (aceito).
2. `tests/automation/test_llm_client.py:21` — o validador de `padrao-python` acusa `secrets`, severidade alta, na constante `API_KEY` (o valor é uma chave fictícia de teste, mas casa a heurística). Critério violado: §6 "o validador de `padrao-python` sem violação nos arquivos alterados"; o resumo declarou o validador só sobre `src`. Exigido: renomear a constante (e seus nove usos) para um nome que não case a heurística, sem mudar o que os testes verificam; `validate.py` sem achado de `secrets` em `tests/automation`, e o bloco da correção registra a saída real do validador sobre `src/triage/automation` **e** `tests/automation` (os dois `hardcoded` de baixa confiança de URL de fixture em `test_response.py:18` e `test_response_guard.py:15` seguem aceitos).

**Itens para o `00-backlog` (não reprovam):** `.env.example` não documenta `LLM_ENABLED` padrão desligado nem o formato de `LLM_BASE_URL`.

---

## Resumo da execução (correção 1) — 2026-11-09

**Resultado:** Concluído

**Achado 1 — endereço sem esquema passava no guard**
- `response_guard.py` — novo `BARE_ADDRESS_PATTERN` e `_foreign_bare_address`: depois de retirar as URLs `http(s)://`, todo endereço sem esquema é `foreign_url`, exceto o host do serviço ou um domínio pai dele (`gov.br`), citado sem caminho. Endereço com `/...` é sempre rejeitado.
- `URL_PATTERN` deixou de tratar `www.` como URL: `www.*` agora cai no endereço sem esquema, para que a menção a `www.gov.br` (host do serviço) não seja confundida com um link diferente. `www.exemplo.com.br` continua rejeitado.
- Testes em `test_response_guard.py`: rejeitados `detran-sp.com.br/pagar`, `golpe.com`, `gov.br/outro`, `gov.br.evil.com`, `evilgov.br`; aceitos "portal gov.br", "portal www.gov.br." e e-mail `inss@example.org`.
- Evidência real: `validate_llm_output("Acesse detran-sp.com.br/pagar ou <url>")` → `foreign_url`; `"Acesse golpe.com ou <url>"` → `foreign_url`; `"no portal gov.br <url>"` → `None`.

**Achado 2 — `secrets` no validador em `tests/`**
- `test_llm_client.py` — `API_KEY` renomeada para `PROVIDER_CREDENTIAL` (9 ocorrências, mesmo valor e mesmas asserções).

**Verificações executadas**
- `python -m pytest tests/automation -q -p no:cacheprovider` → 116 passed.
- `python -m ruff check --no-cache src/triage/automation tests/automation` → All checks passed.
- `padrao-python/scripts/validate.py src/triage/automation` → 0 achados.
- `padrao-python/scripts/validate.py tests/automation` → 4 achados, todos `hardcoded` de baixa confiança (URL de fixture: `test_link_check.py:11`, `test_resolver.py:13`, `test_response.py:18`, `test_response_guard.py:15`); nenhum `secrets`. Os dois do veredito seguem aceitos; `test_link_check.py` e `test_resolver.py` são de entregas anteriores, não tocados.

**Arquivos alterados:** `src/triage/automation/response_guard.py`, `tests/automation/test_response_guard.py`, `tests/automation/test_llm_client.py` (todos ainda não commitados).

**Ambiente:** nada criado (pytest sem cache; ruff com `--no-cache`).

**Decisões e suposições**
- Efeito colateral aceito: texto com nome de arquivo ou abreviação no formato `x.yy` (ex.: `arquivo.pdf`) é lido como endereço e cai no template — falha segura, sem enviar link inventado.

**Achados fora do escopo:** nenhum novo.

## Veredito — 2026-11-09 — 🟢 Aprovado (correção 1)

**Verificado (nível escopada), com saída real:** `git status` (só os sete arquivos de §3.1 e os arquivos de spec do revisor) · leitura integral de `response_guard.py` · `python -m pytest tests/automation -q` → 116 passed · `python -m ruff check --no-cache src/triage/automation tests/automation` → All checks passed · `padrao-python/scripts/validate.py`: `src/triage/automation` → 0 achados; `tests/automation` → só os quatro `hardcoded` de baixa confiança (URLs de fixture), nenhum `secrets` · **achado 1:** sondagem do guard — `detran-sp.com.br/pagar`, `golpe.com`, `GOLPE.COM`, `golpe.com.br`, `gov.br/outro`, `https://evil.com` e `hxxp://golpe.com` junto do link do serviço → `foreign_url`; "no portal gov.br" e "no portal www.gov.br." e um e-mail → aceitos; texto sem link → `missing_url`; o template de **cada uma das 8 categorias do catálogo** passa no guard · **achado 2:** `API_KEY` virou `PROVIDER_CREDENTIAL`, mesmas asserções, sem achado de `secrets` · o bloco da correção registra a saída do validador nos dois diretórios, e confere com o que rodei · sem `TODO`/`FIXME`/skip/`print`, caches removidos.

**Decisão do executor aceita:** nome de arquivo ou abreviação no formato `x.yy` (por exemplo `arquivo.pdf`) é lido como endereço e cai no template; é falha segura, sem enviar link inventado.

**Achados:** nenhum que reprove. O item de `.env.example` já está no `00-backlog`.
