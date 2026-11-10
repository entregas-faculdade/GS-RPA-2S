---
tipo: "plan"
familia: "03"
item: "R03.2"
titulo: "Montar a resposta final ao cidadão, com LLM opcional e caminho seguro"
dominio: "Automação"
status: "🟡 Em execução"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
