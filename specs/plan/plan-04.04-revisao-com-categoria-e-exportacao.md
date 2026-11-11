---
tipo: "plan"
familia: "04"
item: "R04.4"
titulo: "Registrar a categoria correta na revisão e exportar pedidos anonimizados rotulados"
dominio: "Operação e interface"
status: "🟢 Aprovada"
prioridade: "Média"
tags: ["plan"]
relacionados: ["[[04.01-persistencia]]", "[[04.02-interface]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "—"
destino_sintese: "specs/arquitetura/04.01-persistencia.md"
---

# 1. Objetivo
Quem revisa um pedido na aba Revisão informa a **categoria correta**, o sistema grava esse rótulo e uma ação exporta os
pedidos rotulados, só com texto anonimizado, em um CSV pronto para virar dado de treino depois de nova conferência humana.

# 2. Contexto
A necessidade nasceu do uso real: "devemos catalogar solicitações". Hoje a aba Revisão ([[04.02-interface]] §2.3) mostra o
pedido anonimizado, a categoria sugerida e a confiança, e o revisor só escreve uma nota e marca como resolvido; nada alimenta
o conjunto rotulado. Persistência: `Repository` e SQLite ([[04.01-persistencia]]), tabelas criadas por `CREATE TABLE IF NOT
EXISTS` em `init_db`; **banco existente não pode quebrar**, por isso o rótulo vive numa **tabela nova**, sem alterar as
existentes.

Decisões desta plan:
- Tabela nova `labels(request_hash PK, category, created_at)` com chave estrangeira para `requests(hash)`. Um rótulo por
  pedido; rotular de novo substitui.
- As categorias válidas são as 9 do classificador (as 8 do catálogo mais `other`), vindas de `triage.classification` (as
  mesmas de `CATEGORY_RULES` mais `other`); a **interface** valida, o `storage` só exige texto não vazio e não importa
  `classification`.
- O CSV exportado segue o formato do conjunto rotulado (`id,text,label,split,urgent`) com `split=train` e `urgent` por
  `is_urgent`; vai para `output/exports/` (fora do Git). **Não** é gravado em `data/labeled/` por esta plan.
- O texto exportado é o **anonimizado** que já está no banco, nunca o bruto. Um aviso na tela diz que ele pode conter dado
  pessoal residual ([[01.03-anonimizacao-de-pii]] §2.7) e precisa ser revisado antes de entrar em `data/labeled/`.

# 3. Escopo
## 3.1 Dentro
- `src/triage/storage/schema.py` — a tabela `labels` no DDL
- `src/triage/storage/repository.py` — `set_label`, `labeled_requests` e o registro de retorno
- `src/triage/interface/service.py` — categorias disponíveis, `resolve` com categoria opcional, exportação
- `src/triage/interface/views.py` — seletor de categoria correta e botão/ação de exportar, com o aviso
- `tests/storage/`, `tests/interface/` — testes
- `.gitignore` — **só** se `output/exports/` ainda não estiver ignorado

## 3.2 Fora
- `triage.pipeline`, `triage.classification`, `triage.privacy`, `triage.automation`.
- Treinar o modelo ou alterar `data/labeled/`; qualquer envio a serviço externo.
- Autenticação (continua sem login, [[003-seguranca-sem-autenticacao]]).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Arquitetura | [[04.01-persistencia]] | tabelas, contrato do `Repository`, `StorageError` |
| Spec fixa | [[04.02-interface]] | aba Revisão e `AppService` |
| Spec fixa | [[01.03-anonimizacao-de-pii]] | limites residuais que o aviso declara |
| Spec fixa | [[02.01-classificacao]] | categorias e formato do CSV rotulado |
| ADR | [[003-seguranca-sem-autenticacao]] | só texto anonimizado é gravado; sem login |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` · `db-migrations` | SQL parametrizado, tabela nova sem quebrar banco existente |
| Skill | `test-unitario` | testes de repositório e de serviço |
| Código | `src/triage/storage/*.py`, `src/triage/interface/*.py`, `tests/storage/*`, `tests/interface/*` | o que será alterado |

# 5. Instruções de execução
1. [dirigido] **Tabela e repositório.** Criar `labels` em `init_db` (idempotente, sem tocar nas tabelas existentes).
   `Repository.set_label(request_hash, category)`: `category` vazia levanta `ValueError`; hash inexistente vira
   `StorageError` (chave estrangeira); regravar o mesmo hash substitui. `Repository.labeled_requests()` devolve, ordenado por
   data, os registros com `request_hash`, `anonymized_text` e `category`. Erros de banco seguem o contrato de
   `StorageError` (causa preservada, log sem texto do pedido).
2. [dirigido] **Serviço.** `AppService.label_options()` devolve as 9 categorias; `resolve(review_id, note, category=None)`
   mantém o comportamento atual e, quando `category` vem, valida contra as opções e grava o rótulo (do pedido do item)
   **antes** de resolver; categoria inválida devolve `False` sem resolver; falha de banco devolve `False`. `export_labeled
   (directory)` grava o CSV (`id,text,label,split,urgent`) em `directory/labeled_<AAAAMMDDTHHMMSS>.csv` (UTC), cria a pasta
   se faltar e devolve o caminho; sem rótulos devolve `None`. `id` do CSV: algo estável derivado do hash (nunca o texto).
3. [dirigido] **Tela.** Em cada item da fila, um seletor "Categoria correta" com a sugestão atual pré-selecionada (ou
   "não informar") e as 9 opções; "Marcar como resolvido" passa a categoria. Um botão "Exportar pedidos rotulados" chama
   `export_labeled` para `output/exports` e mostra o caminho ou a mensagem de que não há rótulos. O aviso da §2 aparece junto.
4. [dirigido] **Testes.** Repositório: criar/atualizar rótulo, hash inexistente, categoria vazia, banco antigo sem a tabela
   `labels` (criar um banco só com as tabelas antigas e abrir pelo `Repository`: a tabela nasce, nada se perde), lista
   ordenada. Serviço: resolver com categoria válida (rótulo gravado), inválida (não resolve), sem categoria (como antes),
   exportar com e sem rótulos, o CSV não contém texto bruto nem hash completo mais que o necessário, formato das colunas
   idêntico ao do conjunto rotulado.
5. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Rotular e resolver grava a categoria; categoria inválida não resolve; sem categoria o fluxo antigo continua igual.
- [ ] Um banco criado antes desta plan abre sem erro e ganha a tabela nova; nenhum dado se perde.
- [ ] O CSV exportado tem as colunas `id,text,label,split,urgent`, só texto anonimizado e `split=train`.
- [ ] A tela mostra o aviso de dado residual e o caminho exportado; `output/exports/` está fora do Git.
- [ ] SQL todo parametrizado; `storage` não importa `classification`; ambiente e worktree limpos.
- [ ] Testes do escopo verdes; `ruff` e validador sem violação; nenhuma chave e nenhum dado pessoal no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/storage tests/interface tests/pipeline -q` → verde.
- `python -m ruff check src/triage/storage src/triage/interface tests/storage tests/interface` → sem erro.
- `validate.py` do `padrao-python` em `src/triage/storage`, `src/triage/interface` e testes → sem achado.
- O revisor sonda `export_labeled` sobre um banco temporário com um pedido que continha dado pessoal bruto e confere que o
  CSV só tem o texto anonimizado; abre um banco antigo (só tabelas anteriores) e confere a migração por criação.
- **Gate:** `nenhum — coberto por testes de repositório e serviço`.

# 8. Destino da síntese
**Destino:** `specs/arquitetura/04.01-persistencia.md` (e as regras da aba Revisão e da exportação em `specs/04.02-interface.md` §2.3)

Levar, **substituindo**: a tabela `labels` e os dois métodos do `Repository` no contrato; a categoria correta na revisão e a
exportação (formato, destino `output/exports`, só texto anonimizado, aviso de risco residual, revisão humana antes de virar
dado de treino).

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-11

**Resultado:** Concluído

**O que foi feito**
- `schema.py`: tabela `labels(request_hash PK -> requests, category, created_at)` por `CREATE TABLE IF NOT EXISTS`; tabelas antigas intactas.
- `repository.py`: `LabeledRequest`, `Repository.set_label` (vazia -> `ValueError`; hash inexistente -> `StorageError`; `INSERT OR REPLACE`) e `labeled_requests` (JOIN com `requests`, por data e rowid); exportado em `storage/__init__.py`.
- `service.py`: `label_options()` (as 8 de `CATEGORY_RULES` + `other`), `resolve(review_id, note, category=None)` (rotula antes de resolver; inválida/inexistente/falha de banco -> `False`), `export_labeled(directory)` (CSV `id,text,label,split,urgent`, `split=train`, `urgent` por `is_urgent`, `labeled_<UTC>.csv`, `None` sem rótulos; `id` = `R` + 12 primeiros caracteres do hash).
- `views.py`: seletor "Categoria correta" (sugestão pré-selecionada ou "(não informar)"), botão "Exportar pedidos rotulados" para `output/exports` com aviso de dado residual e caminho exportado.
- Testes novos em `tests/storage/test_repository.py` e `tests/interface/test_service.py`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/storage/schema.py` | alterado | tabela `labels` no DDL |
| `src/triage/storage/repository.py` | alterado | `LabeledRequest`, `set_label`, `labeled_requests` |
| `src/triage/storage/__init__.py` | alterado | exporta `LabeledRequest` |
| `src/triage/interface/service.py` | alterado | `label_options`, `resolve` com categoria, `export_labeled` |
| `src/triage/interface/views.py` | alterado | seletor, botão de exportar e aviso |
| `tests/storage/test_repository.py` | alterado | 6 testes novos (inclui banco antigo sem `labels`); `TABLES` inclui `labels` |
| `tests/interface/test_service.py` | alterado | 8 testes novos (rótulo, inválida, sem categoria, exportação com e sem rótulos, formato) |

**Verificações executadas**
- `python -m pytest tests/storage tests/interface tests/pipeline -q` -> 139 passed (antes do ajuste final de imports); `python -m pytest tests/storage tests/interface -q` após o ajuste -> 64 passed.
- `python -m ruff check src/triage/storage src/triage/interface tests/storage tests/interface` -> 3 erros, **todos preexistentes** (conferido com `git stash`: UP017 em `repository.py` `_now`, I001 e SIM117 em `tests/storage/test_repository.py`); nenhum em linha minha.
- `validate.py` do `padrao-python` em `src/triage/storage`, `src/triage/interface`, `tests/storage`, `tests/interface` -> 0 achados em cada.
- `git diff --stat` -> só arquivos de §3.1 (mais as 3 specs que já estavam modificadas pelo revisor antes da execução).

**Estado inicial do worktree:** ` M specs/00-indice.md`, ` M specs/panorama/00-resumo.md`, ` M specs/plan/plan-04.04-revisao-com-categoria-e-exportacao.md`.

**Ambiente após a verificação:** nada criado (só `pytest` e `ruff`, encerrados; `output/` já é ignorado pelo Git; `snapshot` de ambiente não rodado por não haver processo, servidor ou contêiner iniciado).

**Critérios de aceite**
- [x] Rotular e resolver grava a categoria; inválida não resolve; sem categoria fluxo igual — `test_resolve_with_valid_category_records_label`, `..._invalid_category_does_not_resolve`, `..._without_category_keeps_old_flow`.
- [x] Banco antigo abre e ganha a tabela sem perda — `test_database_without_labels_table_is_upgraded_without_data_loss`.
- [x] CSV com `id,text,label,split,urgent`, texto anonimizado, `split=train` — `test_export_writes_only_anonymized_text_in_labeled_format` (CPF bruto e hash completo ausentes) e `test_export_header_matches_labeled_dataset`.
- [x] Tela com aviso e caminho; `output/exports/` fora do Git — `views.py` (`EXPORT_WARNING`, `st.success`); `git check-ignore` confirma `.gitignore:6:output/`. A renderização Streamlit **não foi conferida visualmente** (sem teste de tela no escopo).
- [x] SQL parametrizado; `storage` não importa `classification` — `repository.py`/`schema.py`; só `interface/service.py` importa.
- [x] Testes verdes; validador sem achado; `ruff` sem violação nova (3 preexistentes, ver acima); sem chave nem dado pessoal no diff (só CPF sintético de teste já usado na suíte).

**Decisões e suposições**
- `.gitignore` não foi tocado: `output/` já cobre `output/exports/`.
- `export_labeled` captura `StorageError`/`OSError`, loga só o tipo e devolve `None`; por isso a mensagem da tela para `None` cobre "sem rótulos" e "falha".
- `resolve` passou a devolver `False` também em `StorageError` ao resolver (a plan só pedia isso para o caminho com categoria; vale para os dois por simplicidade).
- O item da fila é localizado por `pending_reviews()` para obter o hash (item já resolvido ou inexistente -> `False`, sem rótulo).
- `label_options()` é `staticmethod`; importa `CATEGORY_RULES` e `OTHER_LABEL` de `triage.classification` no serviço, como a plan manda.
- `is_urgent` lê `data/urgency_terms.json` relativo ao diretório de execução (comportamento existente); fora da raiz do repositório falha segura e marca `urgent=1`.

**Achados fora do escopo (não corrigidos)**
- `src/triage/storage/repository.py:47` — `datetime.timezone.utc` (UP017 do ruff), preexistente.
- `tests/storage/test_repository.py:1,158` — I001 e SIM117 do ruff, preexistentes.

**Pendências / riscos**
- Tela Streamlit não foi aberta no navegador; só testada a camada de serviço.
- A spec `04.02-interface` §2.3 e `04.01-persistencia` seguem sem a mudança até a síntese (do revisor).


---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->

## Veredito — 2026-11-11 — 🟢 Aprovado

Verifiquei, sem confiar no resumo: o diff bate com o resumo e fica dentro do §3.1 (`schema.py`, `repository.py`, `storage/__init__.py`, `service.py`, `views.py` e os dois arquivos de teste); `.gitignore` não precisou de mudança (`output/` já está ignorado). `python -m pytest tests/storage tests/interface tests/pipeline tests/classification -q` → 250 passed; `ruff` em `src/triage/storage`, `src/triage/interface`, `tests/storage` e `tests/interface` → 3 erros, todos anteriores e fora das linhas novas (`UP017` em `repository.py:47`, `I001` e `SIM117` em `test_repository.py`; backlog 14); `validate.py` nos quatro alvos → 0 achados. Código lido inteiro: SQL parametrizado, `labels` criada por `CREATE TABLE IF NOT EXISTS` com chave estrangeira (a conexão liga `PRAGMA foreign_keys=ON`), `storage` não importa `classification`, `export_labeled` só captura `StorageError` e `OSError` e loga o tipo. Sondagem no app real (`AppTest.from_file("app.py")` em pasta temporária, banco com um pedido anonimizado na fila): a aba Revisão mostra o seletor "Categoria correta" com a sugestão pré-selecionada; escolher `driver_license` e clicar em "Marcar como resolvido" tira o item da fila; "Exportar pedidos rotulados" grava `output/exports/labeled_<UTC>.csv` com cabeçalho `id,text,label,split,urgent`, `split=train`, `id` derivado do hash e só o texto anonimizado; o aviso de dado residual aparece. Banco antigo sem `labels` ganha a tabela sem perda (teste do executor, conferido). `output/` só com `logs`, `models` e `reports` na raiz; nenhum processo restante. Fora do escopo, ao backlog 28: `is_urgent` lê `data/urgency_terms.json` relativo ao diretório corrente e, fora da raiz, marca `urgent=1` em silêncio (na pasta temporária da sondagem o CSV saiu com `urgent=1`; na raiz, `is_urgent` dá `False` para "renovar a CNH" e `True` para pedido de emergência), e a pasta de exportação é fixa em `output/exports` em vez de seguir a pasta de saída da configuração.
