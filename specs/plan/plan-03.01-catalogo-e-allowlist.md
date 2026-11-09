---
tipo: "plan"
familia: "03"
item: "R03.1"
titulo: "Criar o catálogo de serviços com allowlist de domínios e verificação de links"
dominio: "Automação"
status: "🔴 A executar"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[003-seguranca-sem-autenticacao]]", "[[00-fundacao-tecnologica]]"]
depende_de: "plan-02.01-dataset-e-classificador"
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

# 1. Objetivo
`resolve_service(category)` devolve o serviço do catálogo (órgão, URL oficial, instruções curtas) **apenas** se a URL
pertencer a um domínio permitido e responder; links fora do ar ou fora da allowlist nunca chegam ao cidadão.

# 2. Contexto
Etapa 3; temas **Automação/RPA** (verificação com timeout e retry com espera) e **Regras**. O catálogo é estático e
curado ([[00-contexto]] §7: sem scraping ao vivo). Uma URL por categoria do recorte A (ids definidos na plan 02.01).
Cobre o requisito do enunciado de tratar "site fora do ar" com log e caminho seguro.

# 3. Escopo
## 3.1 Dentro
- `data/catalog.json` — um registro por categoria de 02.01 (exceto `other`): `category`, `display_name`, `agency`, `url`, `instructions` (1–2 frases), `source_note`, `verified_on` (AAAA-MM-DD)
- `data/allowed_domains.json` — lista de sufixos permitidos (`gov.br` e subdomínios; adicionar apenas órgãos oficiais comprovados, cada um com comentário no campo `reason`)
- `src/triage/automation/catalog.py` — `load_catalog()` e `ServiceEntry`
- `src/triage/automation/allowlist.py` — `is_allowed(url)` (compara o domínio **registrável** do host, não substring)
- `src/triage/automation/link_check.py` — `check_link(url, timeout, retries, backoff)` com `requests`
- `src/triage/common/retry.py` — decorador/função `retry_with_backoff` reutilizável (RPA)
- `src/triage/automation/resolver.py` — `resolve_service(category) -> Resolution(service | None, reason)`
- `tests/automation/` — testes com `requests` simulado (nenhuma chamada de rede real nos testes)

## 3.2 Fora
- Montagem do texto de resposta e LLM (plan 03.02); gravação na fila (plan 04.03).
- Scraping, captura de conteúdo das páginas ou qualquer coleta além de HTTP HEAD/GET de verificação.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[003-seguranca-sem-autenticacao]] | allowlist de domínios |
| Spec fixa | [[00-fundacao-tecnologica]] | etapa 3 e verificação de links |
| Spec fixa | [[00-contexto]] | fronteira: catálogo estático, sem scraping |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `data/labeled/requests_labeled.csv` | ids das categorias (coluna `label`) |

# 5. Instruções de execução
1. [dirigido] **Pesquisar cada URL oficial** (sites `.gov.br`/órgãos) e preenchê-las no catálogo com `verified_on` da data da pesquisa. **Não inventar URL**: se não houver certeza de uma página específica, usar a página do serviço no portal gov.br (`https://www.gov.br/...`). Todas as URLs precisam passar em `is_allowed`.
2. [dirigido] `is_allowed(url)`: só `https`; extrai o host; compara com a allowlist pelo **sufixo de domínio completo** (`.gov.br` casa `servicos.gov.br` mas **não** `gov.br.evil.com` nem `evilgov.br`); URL malformada ou com credenciais embutidas (`user@host`) → `False`.
3. [dirigido] `retry_with_backoff`: parâmetros `attempts`, `base_delay`, espera exponencial limitada; só repete para exceções declaradas como transitórias (timeout, erro de conexão, HTTP 5xx); registra cada tentativa em log. Reutilizável pelo LLM (plan 03.02).
4. [dirigido] `check_link`: HEAD com `timeout` (padrão 5 s), fallback GET se HEAD não for aceito; sucesso = status 200–399; usa `retry_with_backoff` (padrão 3 tentativas). Retorna `LinkStatus(ok, status_code, error)`; **nunca levanta** exceção de rede.
5. [dirigido] `resolve_service(category)`: categoria desconhecida ou `other` → `Resolution(None, "out_of_catalog")`; URL fora da allowlist → `Resolution(None, "link_unavailable")` com log `ERROR` (defeito do catálogo); link não responde → `Resolution(None, "link_unavailable")`; caso contrário `Resolution(service, None)`. Cache em memória do resultado do `check_link` por execução (um link não é verificado duas vezes na mesma execução).
6. [dirigido] Testes: allowlist (válidos, `gov.br.evil.com`, `http://`, credencial embutida, malformada); `retry_with_backoff` (sucesso na 2ª tentativa, esgota e falha, não repete erro não transitório); `check_link` com `requests` simulado (200, 404, timeout, 503→200); `resolve_service` (cada caso de §5.5); catálogo íntegro (toda categoria de 02.01 exceto `other` presente e todas as URLs passam em `is_allowed`).
7. Rodar `python -m pytest tests/automation -q` e `ruff`.

# 6. Critérios de aceite
- [ ] Catálogo cobre as 8 categorias e todas as URLs passam em `is_allowed`.
- [ ] `https://gov.br.evil.com` e `http://...gov.br` são rejeitadas por `is_allowed`.
- [ ] `check_link` nunca propaga exceção de rede; tem timeout e retry com espera (testado).
- [ ] Link indisponível resulta em `Resolution(None, "link_unavailable")`, com log, sem interromper nada.
- [ ] Nenhum teste faz chamada de rede real.
- [ ] Nenhuma URL inventada: cada uma tem `source_note` e `verified_on`.
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation -q` → verde.
- `python -m ruff check src/triage/automation src/triage/common tests/automation` → sem erro.
- Verificação manual **fora dos testes**: abrir 2–3 URLs do catálogo no navegador e confirmar que correspondem ao serviço descrito.
- Leitura de `data/catalog.json` → 8 registros, `verified_on` preenchido, todas `https` e em `gov.br`/allowlist.
- **Gate:** `nenhum — coberto por teste`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md`

Levar: esquema do `catalog.json` e da allowlist; regra de comparação por sufixo de domínio; política de verificação de
links (timeout, retries, backoff, HTTP aceito); causas e valores de `Resolution.reason`; política de que o catálogo é
curado manualmente com data de verificação e deve ser revisado periodicamente; `retry_with_backoff` como utilitário
comum.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
