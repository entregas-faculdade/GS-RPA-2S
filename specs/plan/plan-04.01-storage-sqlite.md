---
tipo: "plan"
familia: "04"
item: "R04.1"
titulo: "Persistir pedidos, fila de revisão, feedback e execuções em SQLite"
dominio: "Operação e interface"
status: "🔴 A executar"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[002-persistencia-sqlite-e-arquivos]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "plan-01.01-setup-projeto"
destino_sintese: "arquitetura/04.01-persistencia.md"
---

# 1. Objetivo
O pacote `triage.storage` oferece, sobre um arquivo SQLite local, idempotência por hash de pedido, fila de revisão
humana, feedback 👍/👎 e registro de execuções; é o **único** código do projeto que toca o banco.

# 2. Contexto
Decisão em [[002-persistencia-sqlite-e-arquivos]]: SQLite local, sem cache, arquivo `.db` fora do Git. Tema
**Automação/RPA** (idempotência e relatório de execução). Só texto **anonimizado** pode ser gravado
([[003-seguranca-sem-autenticacao]]); esta plan não anonimiza, apenas **recusa** gravar sem a marca de que o texto
passou pela anonimização (ver §5.3).

# 3. Escopo
## 3.1 Dentro
- `src/triage/storage/schema.py` — DDL das tabelas e `init_db(path)` idempotente
- `src/triage/storage/repository.py` — classe `Repository` com a API de §5
- `src/triage/storage/hashing.py` — `request_hash(anonymized_text)` (SHA-256 do texto normalizado)
- `src/triage/storage/__init__.py` — exporta `Repository`, `init_db`, `request_hash`
- `tests/storage/` — testes com banco em arquivo temporário (`tmp_path`)

## 3.2 Fora
- Anonimização (plan 01.03), classificação e regras de revisão (família 02), uso no pipeline (plan 04.03) e na interface (plan 04.02).
- Qualquer outra camada acessar o SQLite diretamente.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[002-persistencia-sqlite-e-arquivos]] | escolha e limites do SQLite |
| ADR | [[003-seguranca-sem-autenticacao]] | só texto anonimizado é gravado |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |

# 5. Instruções de execução
1. [dirigido] Esquema (nomes em inglês): `requests(hash PK, anonymized_text, category, confidence, status, review_reason, created_at)`; `review_queue(id PK, request_hash FK, reason, created_at, resolved INTEGER DEFAULT 0, resolution_note)`; `feedback(id PK, request_hash FK, rating CHECK IN ('up','down'), created_at)`; `runs(id PK, started_at, finished_at, totals_json)`. `status` ∈ `answered`, `queued_for_review`, `rejected`.
2. [dirigido] `init_db(path)`: cria diretório e tabelas se faltarem, **idempotente**, `PRAGMA foreign_keys=ON`, modo WAL desnecessário. Usar sempre **parâmetros vinculados** (`?`), nunca concatenar SQL.
3. [dirigido] `Repository` com os métodos: `already_processed(hash) -> bool`; `save_request(hash, anonymized_text, category, confidence, status, review_reason)` (gravar o mesmo hash duas vezes é no-op, nunca erro); `enqueue_review(hash, reason)`; `pending_reviews()`; `resolve_review(id, note)`; `add_feedback(hash, rating)` (rating inválido → `ValueError`); `start_run()` → id; `finish_run(id, totals: dict)`. O texto recebido deve ser aceito apenas se o chamador passar `anonymized=True` (parâmetro nomeado obrigatório em `save_request`); caso contrário, levantar `ValueError` — barreira contra gravar texto bruto.
4. [dirigido] Erros de I/O do SQLite são logados (sem o texto) e relançados como `StorageError` (exceção própria), para o pipeline decidir o caminho seguro.
5. [dirigido] Testes: `init_db` duas vezes; idempotência (`already_processed` antes/depois; segundo `save_request` não duplica); fila (enfileirar, listar pendentes, resolver); feedback válido e inválido; `save_request` sem `anonymized=True` falha; injeção (`'; DROP TABLE requests;--` como texto) não altera o esquema; `finish_run` grava totais.
6. Rodar `python -m pytest tests/storage -q` e `ruff`.

# 6. Critérios de aceite
- [ ] `init_db` pode ser chamado repetidamente sem erro nem perda de dados.
- [ ] Reprocessar o mesmo hash não cria segundo registro.
- [ ] Gravar sem `anonymized=True` é recusado.
- [ ] Rating diferente de `up`/`down` é recusado.
- [ ] Nenhum SQL é montado por concatenação (leitura do código).
- [ ] Nenhum outro pacote importa `sqlite3`.
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/storage -q` → verde.
- `python -m ruff check src/triage/storage tests/storage` → sem erro.
- `grep -rn "sqlite3" src` → só em `src/triage/storage/`.
- Se a verificação cria banco: apenas em `tmp_path`; confirmar que nenhum `.db` ficou no worktree.
- **Gate:** `nenhum — coberto por teste e leitura`.

# 8. Destino da síntese
**Destino:** `arquitetura/04.01-persistencia.md`

Levar: esquema das quatro tabelas e o significado de `status`; contrato do `Repository`; regra "só texto anonimizado
é gravado" (barreira `anonymized=True`); idempotência por SHA-256 do texto normalizado; `StorageError`; fronteira
"só `triage.storage` toca o banco". Atualizar o limite do ADR 002 (sem acesso multiusuário) se algo mudar.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
