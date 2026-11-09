---
tipo: "plan"
familia: "01"
item: "R01.2"
titulo: "Ingerir pedidos de txt/csv/json e sanitizar a entrada"
dominio: "Núcleo do robô"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[003-seguranca-sem-autenticacao]]", "[[00-fundacao-tecnologica]]"]
depende_de: ""
destino_sintese: "specs/01.02-ingestao-e-sanitizacao.md"
---

# 1. Objetivo
Dada uma pasta de entrada, o robô devolve uma lista de pedidos válidos e sanitizados (`Request`) mais uma lista de
rejeições com motivo, sem nunca interromper a execução por um arquivo ou registro ruim.

# 2. Contexto
Etapa 1 do fluxo ([[00-fundacao-tecnologica]]). Cobre os temas **Automação/RPA** (ingestão em lote tolerante a
falhas) e **Regras/regex** (sanitização). A anonimização de PII é a plan seguinte; aqui o texto ainda é bruto e
**não pode ser logado**. Formatos: `.txt` (um pedido por arquivo), `.csv` (colunas `id,text`), `.json` (lista de
objetos `{"id": "...", "text": "..."}` ou um objeto único).

# 3. Escopo
## 3.1 Dentro
- `src/triage/ingestion/models.py` — `dataclass(frozen=True)` `Request(id, text, source)` e `Rejection(source, reason)`
- `src/triage/ingestion/readers.py` — `read_txt`, `read_csv`, `read_json` e `read_folder(path)`
- `src/triage/ingestion/sanitizer.py` — `sanitize(text)` e `validate(request)`
- `src/triage/ingestion/__init__.py` — exporta `read_folder`, `sanitize`, `Request`, `Rejection`
- `data/samples/` — 6 a 10 arquivos sintéticos (txt/csv/json), incluindo casos ruins: arquivo vazio, JSON inválido, CSV sem coluna `text`, texto gigante, texto com HTML/`<script>`, caracteres de controle, encoding quebrado
- `tests/ingestion/` — testes dos leitores e do sanitizador

## 3.2 Fora
- Anonimização de CPF/telefone/e-mail (plan 01.03).
- Persistência e idempotência (plan 04.01) e classificação (família 02).
- Qualquer chamada de rede.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[003-seguranca-sem-autenticacao]] | controles de sanitização exigidos |
| Spec fixa | [[00-fundacao-tecnologica]] | posição da etapa 1 no fluxo |
| Spec fixa | [[01.01-estrutura-do-projeto]] | layout `src/triage/`, configuração, log e comandos de verificação |
| Enunciado | `GS2026_2_Enunciado_Final_RPA_IA(2).pdf` §4 | falhas previsíveis (arquivo ausente, dado inválido) com log e caminho seguro |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |

# 5. Instruções de execução
1. [dirigido] Modelos imutáveis `Request` e `Rejection` em `models.py`.
2. [dirigido] Leitores: cada um lê um arquivo e devolve `(requests, rejections)`; erro de leitura de **um** arquivo ou **uma** linha vira `Rejection` com motivo curto (`empty_file`, `invalid_json`, `missing_text_column`, `unreadable_encoding`, `too_large`), nunca exceção propagada. Ler com `encoding="utf-8"` estrito; falha de decodificação vira `unreadable_encoding`.
3. [dirigido] `read_folder`: varre a pasta (não recursivo), registra em log `WARNING` as extensões não suportadas e agrega resultados. Pasta inexistente → levantar `FileNotFoundError`, tratado pelo chamador (`run.py`), não engolido aqui.
4. [dirigido] `sanitize(text)`: normalizar Unicode (NFKC); remover caracteres de controle exceto quebra de linha e tab; remover tags HTML (`<script>...</script>` inclusive o conteúdo; demais tags, só o marcador); neutralizar sequências típicas de injeção SQL (`;--`, `' OR '1'='1`) trocando-as por espaço (o pipeline nunca monta SQL por concatenação); colapsar espaços; rejeitar com `too_large` quando exceder `MAX_TEXT_LENGTH` (constante nomeada, padrão 2000).
5. [dirigido] `validate(request)`: id não vazio; texto, **após** sanitização, com ao menos `MIN_TEXT_LENGTH` (constante, padrão 3) caracteres; devolve `Rejection` ou `None`.
6. [dirigido] Gerar `data/samples/` com dados **sintéticos**, nomes e números claramente fictícios; incluir ao menos um arquivo bom de cada formato e os casos ruins de §3.1.
7. [dirigido] Testes cobrindo: arquivo bom de cada formato; cada motivo de rejeição; pasta mista (bons + ruins = resultado parcial, execução continua); HTML/script removido; controle removido; truncamento/limite; e que **nenhum log contém o texto do pedido** (`caplog`).
8. Rodar `python -m pytest tests/ingestion -q` e `ruff`.

# 6. Critérios de aceite
- [ ] `read_folder("data/samples")` devolve pedidos válidos **e** rejeições, sem exceção.
- [ ] Cada motivo de rejeição de §5.2 tem ao menos um teste.
- [ ] `<script>alert(1)</script>` some inteiro após `sanitize`.
- [ ] Nenhuma mensagem de log contém o conteúdo bruto de um pedido (teste com `caplog`).
- [ ] Limites em constantes nomeadas, sem número solto no código.
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/ingestion -q` → verde.
- `python -m ruff check src/triage/ingestion tests/ingestion` → sem erro.
- Com `PYTHONPATH=src`: `python -c "from triage.ingestion import read_folder; r, x = read_folder('data/samples'); print(len(r), len(x))"` → ambos maiores que 0.
- Leitura de `data/samples/` → nenhum CPF, telefone ou e-mail realista; só valores fictícios óbvios.
- **Gate:** `nenhum — comportamento coberto por teste`.

# 8. Destino da síntese
**Destino:** `specs/01.02-ingestao-e-sanitizacao.md`

Levar: formatos aceitos e o esquema de cada um; motivos de rejeição e quando ocorrem; regras de sanitização e
constantes de limite; garantia de que arquivo/linha ruim vira rejeição sem derrubar a execução; proibição de logar
texto bruto.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-09

**Resultado:** Concluído

**O que foi feito**
- `models.py` — `Request` e `Rejection` (`dataclass(frozen=True)`) e constantes `REASON_*` dos motivos de rejeição.
- `sanitizer.py` — `sanitize` (limite → NFKC → controles → comentário/`<script>`/`<style>` com conteúdo → demais tags → SQL → espaços), `validate`, `MAX_TEXT_LENGTH=2000`, `MIN_TEXT_LENGTH=3`, `TextTooLargeError`.
- `readers.py` — `read_txt`, `read_csv`, `read_json`, `read_folder`; erro de arquivo ou registro vira `Rejection`; pasta inexistente levanta `FileNotFoundError`; log só com nome de arquivo e motivo.
- `__init__.py` — exporta `read_folder`, `sanitize`, `Request`, `Rejection`.
- `data/samples/` — 10 arquivos sintéticos (3 bons, 1 misto com HTML/SQL, 6 ruins).
- `tests/ingestion/` — 44 testes.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/ingestion/__init__.py` | alterado | exporta a API pública |
| `src/triage/ingestion/models.py` | criado | modelos e motivos |
| `src/triage/ingestion/sanitizer.py` | criado | sanitização e validação |
| `src/triage/ingestion/readers.py` | criado | leitores e `read_folder` |
| `data/samples/*` (10 arquivos) | criado | amostras sintéticas |
| `tests/ingestion/test_sanitizer.py`, `test_readers.py` | criado | testes |
| `specs/plan/plan-01.02-ingestao-e-sanitizacao.md` | alterado | este resumo e `status` |

**Verificações executadas**
- `python -m pytest tests/ingestion -q` → 44 passed.
- `python -m ruff check src/triage/ingestion tests/ingestion` → All checks passed.
- `padrao-python/scripts/validate.py` em `src/triage/ingestion` e `tests/ingestion` → 0 achados em ambos.
- `PYTHONPATH=src python -c "...read_folder('data/samples')..."` → 8 pedidos, 7 rejeições (ambos > 0).
- `python -m pytest -q` (suíte inteira, rodada uma vez só para confirmar que `run.py`/config não regrediram) → 55 passed. Fora da verificação escopada; declarado aqui.

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** nada criado (sem processo, servidor ou banco). Script gerador das amostras ficou fora do repositório, no scratchpad da sessão.

**Critérios de aceite**
- [x] `read_folder("data/samples")` devolve pedidos e rejeições sem exceção — 8 / 7.
- [x] Cada motivo de §5.2 tem teste — `tests/ingestion/test_readers.py` (`test_empty_file`, `test_invalid_json`, `test_csv_without_text_column`, `test_unreadable_encoding`, `test_too_large_text_is_rejected_per_record`), mais os motivos acrescentados.
- [x] `<script>alert(1)</script>` some inteiro — `test_script_block_is_removed_with_its_content`; amostra `html_script.txt` sai como "Quero abrir uma reclamação. Urgente obrigado.".
- [x] Nenhum log contém texto bruto — `test_logs_never_contain_the_raw_request_text` (`caplog` em DEBUG, com marcador em id, texto grande, curto e JSON ruim).
- [x] Limites em constantes nomeadas — `MAX_TEXT_LENGTH`, `MIN_TEXT_LENGTH`, `FILE_ENCODING`, `ID_FIELD`, `TEXT_FIELD`.
- [x] Ambiente e worktree limpos — `git status` só mostra o escopo §3.1 e esta plan.
- [x] Testes, `ruff` e validador sem violação — ver Verificações.
- [x] Nenhum dado pessoal real, chave ou `.env` — amostras só com texto fictício, sem CPF/telefone/e-mail.

**Decisões e suposições**
- Motivos de rejeição além dos cinco da plan, necessários para não propagar exceção: `invalid_csv` (`csv.Error`, ex.: campo acima do limite do parser), `unreadable_file` (`OSError`), `missing_text` (item JSON sem `text` string, ou item que não é objeto → `invalid_json`), `empty_id` e `text_too_short` (de `validate`).
- Decodificação com `utf-8-sig` (UTF-8 estrito que também tolera BOM de CSV do Excel), em vez de `utf-8` puro.
- `sanitize` sinaliza `too_large` levantando `TextTooLargeError`, capturada pelos leitores; o limite vale para o texto bruto, antes de qualquer regex.
- Id: `.txt` usa o nome do arquivo sem extensão; CSV sem coluna `id` não tem regra própria (todas as linhas caem em `empty_id`). Id numérico do JSON vira `str`.
- Quebras de linha são preservadas (linhas aparadas, 3+ quebras viram 2); tabs viram espaço ao colapsar. `<style>` é tratado como `<script>`; comentários HTML são removidos. NFKC converte "ª" em "a" (visível em `pedidos_bons.csv#2`).
- Tag HTML exige letra, `/` ou `!` após `<`, para não apagar "2 < 3".
- Padrões SQL: `;\s*--` e `' OR '1'='1` (sem diferenciar maiúsculas, aspa final opcional).
- Mensagem de log de rejeição cita `source` (nome do arquivo e posição), nunca id nem texto.
- `data/samples` tem 10 arquivos (limite da plan é 6–10): HTML/SQL ficou em `html_script.txt` e caracteres de controle dentro de `pedidos_bons.json`.

**Achados fora do escopo (não corrigidos)**
- `run.py:34` — ainda não chama `read_folder` (previsto para a plan 04.03); com a pasta padrão `data/samples` agora populada, nada muda no comportamento atual.

**Pendências / riscos**
- Arquivo muito grande é lido inteiro na memória (sem limite de bytes por arquivo); aceitável no protótipo com dados sintéticos.
- O hook do harness avisou "ruff not installed" durante as edições, mas `python -m ruff` (0.14.2) existe e foi rodado com sucesso.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-09 — 🟢 Aprovado

**Verificado (nível escopada), com saída real:**
- `git status` / `git diff --stat` → só `src/triage/ingestion/` (`__init__.py` alterado; `models.py`, `readers.py`, `sanitizer.py` criados), `data/samples/` (10 arquivos), `tests/ingestion/` (2 arquivos) e esta plan. Nada fora do escopo de §3.1, nada faltando. O resumo confere com o diff: 10 amostras, 44 testes, 8 pedidos e 7 rejeições nas amostras.
- `python -m pytest tests/ingestion -q` → 44 passed.
- `python -m ruff check src/triage/ingestion tests/ingestion` → All checks passed.
- `padrao-python/scripts/validate.py` em `src/triage/ingestion` e `tests/ingestion` → 0 achados.
- `read_folder('data/samples')` → 8 pedidos e 7 rejeições, sem exceção; motivos: `unreadable_encoding`, `too_large`, `invalid_json`, `text_too_short`, `missing_text`, `missing_text_column`, `empty_file`.
- Sondagem da sanitização com entradas adversariais: `<scr<script>x</script>ipt>alert(1)</script>` → `alert(1)` (sem marcador); `<SCRIPT >a</SCRIPT >ok` → `ok`; script sem fechamento descarta o resto; tag com NUL no meio e `<script>` em largura plena (NFKC) caem; `<img onerror=...>` → vazio; `1 < 2 e 3 > 2` preservado; `;--` e `' OR '1'='1` neutralizados.
- Leitura integral de `models.py`, `sanitizer.py`, `readers.py`, dos dois arquivos de teste e de todas as amostras: sem `TODO`, `print`, `noqa`, skip nem comentário citando plan; funções ≤ 40 linhas, ≤ 4 parâmetros, aninhamento ≤ 3; limites em constantes (`MAX_TEXT_LENGTH`, `MIN_TEXT_LENGTH`, `FILE_ENCODING`, `ID_FIELD`, `TEXT_FIELD`); amostras só com texto fictício, sem CPF, telefone nem e-mail.
- Ambiente: restavam `.pytest_cache`, `.ruff_cache` e `__pycache__` (todos ignorados pelo Git; o resumo diz "nada criado"). Removi-os; `git status --ignored` voltou a limpo. Não reprovo por isso: é cache de ferramenta, sem processo nem arquivo da tarefa. O gate de segredos (`verify_commit.py`) sem nada em stage não tem o que varrer; rodará no commit.

**Critérios de aceite (§6)**
- [x] `read_folder("data/samples")` devolve pedidos e rejeições sem exceção — 8 / 7.
- [x] Cada motivo de §5.2 tem teste — `tests/ingestion/test_readers.py` (`test_empty_file`, `test_invalid_json`, `test_csv_without_text_column`, `test_unreadable_encoding`, `test_too_large_text_is_rejected_per_record`).
- [x] `<script>alert(1)</script>` some inteiro — `test_request_text_comes_sanitized` e a amostra `html_script.txt` ("Quero abrir uma reclamação. Urgente obrigado.").
- [x] Nenhum log com texto bruto — `test_logs_never_contain_the_raw_request_text` (`caplog` em DEBUG, marcador em texto, id e JSON); `readers.py:126-137` só loga nome de arquivo e motivo.
- [x] Limites em constantes nomeadas.
- [x] Ambiente e worktree limpos — ver acima.
- [x] Testes, `ruff` e validador sem violação.
- [x] Nenhum dado pessoal real, chave ou `.env` no diff.

**Decisões do executor aceitas:** motivos extras (`invalid_csv`, `unreadable_file`, `missing_text`, `empty_id`, `text_too_short`) que evitam exceção propagada; `utf-8-sig`; `too_large` sobre o texto bruto.

**Achados:** nenhum que reprove. Ao backlog: limite checado antes da NFKC (item 3). O achado do executor sobre `run.py` não chamar `read_folder` é escopo já previsto da orquestração, e foi descartado, sem item.

