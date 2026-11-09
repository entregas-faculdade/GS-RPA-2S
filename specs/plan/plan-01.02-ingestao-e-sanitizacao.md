---
tipo: "plan"
familia: "01"
item: "R01.2"
titulo: "Ingerir pedidos de txt/csv/json e sanitizar a entrada"
dominio: "Núcleo do robô"
status: "🟡 Em execução"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
