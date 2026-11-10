---
tipo: "plan"
familia: "02"
item: "R02.1"
titulo: "Criar o conjunto rotulado sintético e o classificador regex + TF-IDF"
dominio: "Classificação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[00-fundacao-tecnologica]]", "[[005-llm-apenas-reformula-resposta]]"]
depende_de: "plan-01.03-anonimizacao-de-pii"
destino_sintese: "specs/02.01-classificacao.md"
---

# 1. Objetivo
`classify(text)` devolve a categoria mais provável (e as probabilidades por categoria) usando atalhos determinísticos
por regex e, na ausência deles, um modelo TF-IDF + regressão logística treinado sobre um conjunto rotulado sintético
versionado.

# 2. Contexto
Etapa 2 do fluxo; temas **NLP** (limpeza, TF-IDF) e **Regras/regex**. O núcleo é determinístico e **não usa LLM**
([[005-llm-apenas-reformula-resposta]]). Recorte A: 8 categorias de serviço + `other` (fora do catálogo):

| id | serviço |
|---|---|
| `driver_license` | CNH (primeira habilitação, renovação, 2ª via) |
| `property_tax` | IPTU |
| `id_card` | RG / carteira de identidade |
| `cpf_registration` | CPF (inscrição, regularização) |
| `voter_id` | título de eleitor |
| `social_benefits` | CadÚnico / Bolsa Família |
| `social_security` | INSS (aposentadoria, benefícios) |
| `birth_certificate` | certidões (nascimento, casamento, óbito) |
| `other` | qualquer assunto fora das categorias acima |

A confiança e os gatilhos de revisão são a plan 02.02; esta entrega a classificação e as probabilidades.

# 3. Escopo
## 3.1 Dentro
- `data/labeled/requests_labeled.csv` — **≥ 160 linhas** sintéticas, colunas `id,text,label,split,urgent`; `split` ∈ `train`/`test` (70/30 estratificado, fixo, definido no arquivo); ≥ 15 exemplos por categoria, ≥ 20 de `other`, ≥ 10 com `urgent=1` (emergência/risco, texto livre)
- `src/triage/classification/preprocessing.py` — `normalize(text)` (minúsculas, remoção de acentos, pontuação, stopwords PT-BR curtas definidas em constante)
- `src/triage/classification/rules.py` — regex por categoria (atalhos determinísticos, ex.: `\bcnh\b`, `\biptu\b`)
- `src/triage/classification/model.py` — `train(csv_path)`, `save`, `load`, `predict_proba(text)` (Pipeline `TfidfVectorizer` + `LogisticRegression`, `random_state` fixo)
- `src/triage/classification/classifier.py` — `classify(text) -> Classification(label, probabilities, source)` com `source` ∈ `rule` | `model`
- `src/triage/classification/__init__.py` — exporta `classify`, `Classification`
- `scripts/train_model.py` — treina com `split=train` e grava em `output/models/classifier.joblib`
- `tests/classification/` — testes

## 3.2 Fora
- Score de confiança final, limiares e motivos de revisão (plan 02.02).
- Catálogo e links (família 03); métricas e notebook de evidências (plan 05.01).
- Uso de LLM em qualquer ponto.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[00-fundacao-tecnologica]] | posição da etapa 2 e temas |
| ADR | [[005-llm-apenas-reformula-resposta]] | classificação sem LLM |
| ADR | [[003-seguranca-sem-autenticacao]] | dados sintéticos, sem PII real |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `src/triage/privacy/` | o classificador recebe só texto anonimizado |

# 5. Instruções de execução
1. [dirigido] Escrever o CSV rotulado **sintético**, em português, com variações reais de linguagem (formal, informal, erros leves de digitação, frases curtas e longas); **nenhum** dado pessoal real. Incluir exemplos com marcadores `[CPF]`/`[TELEFONE]`/`[EMAIL]` para refletir o texto já anonimizado. Registrar no cabeçalho do README de dados (`data/labeled/README.md`) que o conjunto é sintético e como foi construído.
2. [dirigido] `normalize`: determinístico e puro. Constantes de stopwords nomeadas.
3. [dirigido] `rules.py`: um conjunto pequeno de regex **de alta precisão** por categoria; devolve o conjunto de categorias que casaram. Regex nunca decide sozinho quando casam duas ou mais categorias (nesse caso `classify` segue para o modelo e a plan 02.02 trata como ambiguidade).
4. [dirigido] `model.py`: `train` lê o CSV, usa só `split=train`, treina o Pipeline, devolve o modelo; `save`/`load` com `joblib`; falha ao carregar (arquivo ausente/corrompido) levanta `ModelNotAvailableError`, tratada pelo pipeline (caminho seguro: fila de revisão).
5. [dirigido] `classify`: se exatamente uma categoria casar por regra → `source="rule"`; senão → `source="model"` com `predict_proba`. Sempre devolve as probabilidades das 9 classes (para a plan 02.02). Para `source="rule"`, as probabilidades são as do modelo (a regra só fixa o rótulo).
6. [dirigido] Testes: `normalize`; cada regra com positivo e negativo; `train`+`predict` em amostra pequena temporária; `classify` com regra única, com modelo, com duas regras (cai no modelo); `load` de arquivo inexistente → `ModelNotAvailableError`; reprodutibilidade (mesmo CSV → mesmas probabilidades).
7. Rodar `python scripts/train_model.py`, `python -m pytest tests/classification -q` e `ruff`.

# 6. Critérios de aceite
- [ ] CSV com ≥ 160 linhas, ≥ 15 por categoria, ≥ 20 `other`, ≥ 10 `urgent=1`, `split` 70/30 preenchido.
- [ ] `scripts/train_model.py` gera o modelo sem erro, de forma reprodutível.
- [ ] `classify("onde tiro minha CNH?")` devolve `driver_license` com `source="rule"`.
- [ ] Texto sem regra casando passa pelo modelo e devolve probabilidades para as 9 classes.
- [ ] Modelo ausente é tratado por exceção própria, não por traceback.
- [ ] Nenhum dado pessoal real no CSV; modelo treinado **não** versionado (`output/` ignorado).
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/classification -q` → verde.
- `python -m ruff check src/triage/classification tests/classification scripts` → sem erro.
- `python scripts/train_model.py` → termina com código 0.
- Contagem: `python -c "import pandas as pd; d=pd.read_csv('data/labeled/requests_labeled.csv'); print(len(d)); print(d.label.value_counts()); print(d.split.value_counts()); print(d.urgent.sum())"` → atende §6.
- Leitura amostral do CSV → nenhum dado pessoal realista.
- **Gate:** `nenhum — coberto por teste e contagem do conjunto`.

# 8. Destino da síntese
**Destino:** `specs/02.01-classificacao.md`

Levar: lista das 9 classes e seus ids; esquema do CSV rotulado e a regra de `split`; fluxo regra → modelo e o campo
`source`; hiperparâmetros fixos e `random_state`; erro `ModelNotAvailableError`; o fato de o modelo não ser
versionado e como regenerá-lo. As métricas medidas entram na spec de validação (plan 05.01), não aqui.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-09

**Resultado:** Concluído

**O que foi feito**
- Conjunto rotulado sintético de 180 linhas (20 por categoria e 20 `other`), com `split` 70/30 por categoria (14 train + 6 test) e 11 linhas `urgent=1` — `data/labeled/requests_labeled.csv`; construção e esquema documentados em `data/labeled/README.md`.
- `normalize` (puro, stopwords em constante `PT_BR_STOPWORDS`) e `fold` (minúsculas, sem acento, sem marcadores) — `src/triage/classification/preprocessing.py`.
- Regex de alta precisão para as 8 categorias; `match_categories` devolve o conjunto que casou — `rules.py`.
- `train`/`save`/`load`/`predict_proba` com Pipeline `TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)` + `LogisticRegression(C=10.0, max_iter=1000, random_state=42)`; falha de carga vira `ModelNotAvailableError` — `model.py`.
- `classify(text, model=None) -> Classification(label, probabilities, source)`: uma regra → `rule`; zero ou duas ou mais → `model`; probabilidades sempre as do modelo — `classifier.py`; exporta `classify`, `Classification` e `ModelNotAvailableError` em `__init__.py`.
- `scripts/train_model.py` treina com `split=train` e grava em `output/models/classifier.joblib`.
- 68 testes em `tests/classification/`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `data/labeled/requests_labeled.csv` | criado | 180 pedidos sintéticos rotulados |
| `data/labeled/README.md` | criado | declara o conjunto sintético, colunas e regra do split |
| `src/triage/classification/preprocessing.py` | criado | `fold`, `normalize`, stopwords |
| `src/triage/classification/rules.py` | criado | regex por categoria e `match_categories` |
| `src/triage/classification/model.py` | criado | treino, persistência, `predict_proba`, `ModelNotAvailableError` |
| `src/triage/classification/classifier.py` | criado | `classify` e `Classification` |
| `src/triage/classification/__init__.py` | alterado | exporta `classify`, `Classification`, `ModelNotAvailableError` |
| `scripts/train_model.py` | criado | CLI de treino |
| `tests/classification/` (`conftest.py`, `test_preprocessing.py`, `test_rules.py`, `test_model.py`, `test_classifier.py`, `test_dataset.py`) | criado | testes do escopo |

**Verificações executadas**
- `python -m pytest tests/classification -q` → 68 passed.
- `python -m ruff check src/triage/classification tests/classification scripts` → All checks passed.
- `validate.py` do `padrao-python` em `src/triage/classification`, `scripts` e `tests/classification` → 0 achados.
- `python scripts/train_model.py` → código 0, modelo gravado.
- Contagem do CSV (`test_dataset.py` e leitura direta): 180 linhas; 20 por categoria incluindo `other`; split 126 train / 54 test; `urgent` somado = 11. Nenhum dado pessoal: `anonymize` não substitui nada em nenhuma linha.
- Com o modelo real: `classify("onde tiro minha CNH?")` → `driver_license`, `source="rule"`, 9 probabilidades; texto sem regra → `source="model"`, 9 probabilidades. Dois treinos do mesmo CSV → probabilidades idênticas.
- Checagem das regras contra o CSV (script provisório fora do repositório): nenhuma regra casa uma categoria diferente do rótulo; só 3 linhas casam duas regras (CPF + CNH/RG), de propósito.

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** nenhum processo, servidor ou contêiner subido. O `train_model.py` criou `output/` (ignorado pelo Git), removido ao final. Script provisório de geração do CSV ficou só no scratchpad, fora do repositório. `snapshot` da skill `code-limpeza-ambiente`: não executado (nada além de processos curtos), conferido à mão.

**Critérios de aceite**
- [x] CSV ≥ 160 linhas, ≥ 15 por categoria, ≥ 20 `other`, ≥ 10 `urgent=1`, split 70/30 — evidência: `tests/classification/test_dataset.py`, 5 passed.
- [x] `train_model.py` gera o modelo sem erro, reprodutível — saída 0; teste `test_train_is_reproducible`.
- [x] `classify("onde tiro minha CNH?")` → `driver_license`, `rule` — `test_single_rule_decides_the_label` e execução real.
- [x] Sem regra, passa pelo modelo e devolve 9 probabilidades — `test_without_rule_the_model_decides`.
- [x] Modelo ausente tratado por exceção própria — `test_load_missing_file_raises_model_not_available`, `test_missing_model_raises_model_not_available`.
- [x] Sem dado pessoal real; modelo não versionado — `test_no_real_personal_data`; `output/` está no `.gitignore`.
- [x] Ambiente e worktree limpos — ver acima.
- [x] Testes verdes; `ruff` e `validate.py` sem violação.
- [x] Sem dado pessoal, chave ou `.env` no diff.

**Decisões e suposições**
- `predict_proba(model, text)` recebe o modelo: a plan escreve `predict_proba(text)`, mas um modelo global seria estado mutável (`padrao-escrita`). Pelo mesmo motivo `classify(text, model=None)`: sem `model`, carrega o arquivo padrão a cada chamada; o pipeline deve carregar uma vez e repassar.
- `ModelNotAvailableError` também sai de `triage.classification`, para o pipeline poder tratá-la.
- Os marcadores `[CPF]`, `[TELEFONE]`, `[EMAIL]` são removidos em `normalize`/`fold`: sem isso, `[CPF]` viraria o token `cpf` e acionaria a regra de CPF em qualquer pedido com CPF anonimizado. Os marcadores vêm de `triage.privacy.patterns`.
- As regras rodam sobre `fold(text)` (sem acento, sem remoção de stopwords), não sobre `normalize`.
- 20 linhas por categoria (180 no total) para o split 70/30 ficar exato (14/6).
- `data/labeled/README.md` não está na lista §3.1, mas é pedido no passo 1 da §5.
- O ambiente tem `scikit-learn 1.8.0`, enquanto `requirements.txt` fixa `1.9.1`; testei com o instalado.

**Achados fora do escopo (não corrigidos)**
- `ruff format --check` já reprova arquivos anteriores (`src/triage/storage/repository.py`, `tests/privacy/test_anonymizer.py`, entre outros); o repositório não impõe `ruff format`, e o código novo segue o estilo vizinho (linhas de até 120).
- Os arquivos novos saíram com finais de linha mistos (CRLF e LF) por causa do ambiente Windows; não há `.gitattributes` para normalizar.

**Pendências / riscos**
- Acurácia indicativa no `split=test` (~80%, medida à parte, fora do repositório) é só sanidade; as métricas oficiais são da plan 05.01.
- O conjunto é pequeno e sintético: pedidos reais podem se comportar diferente. `other` cai por vezes em categorias de serviço (ex.: "passaporte" → `property_tax`); a plan 02.02 trata a baixa confiança.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-09 — 🟢 Aprovado

**Verificado (nível escopada), com saída real:** `git status`/`git diff --stat` (só arquivos de §3.1 mais o `data/labeled/README.md` que o passo 1 pede; nada fora do escopo, nada faltando) · leitura integral de `preprocessing.py`, `rules.py`, `model.py`, `classifier.py`, `__init__.py` e `scripts/train_model.py` · `python -m pytest tests/classification -q` → 68 passed · `python -m ruff check --no-cache src/triage/classification tests/classification scripts` → All checks passed · `padrao-python/scripts/validate.py` em `src/triage/classification`, `scripts` e `tests/classification` → `findings: []` nos três · `python scripts/train_model.py` → código 0, modelo gravado (removi `output/` depois) · contagem do CSV: 180 linhas, 20 por categoria incluindo `other`, split 14 train + 6 test em cada, `urgent` somado 11, ids únicos, nenhum texto duplicado · busca por telefone, e-mail e sequência numérica no CSV → vazia, e a amostra de 15 linhas é sintética · sondagem com o modelo real: `onde tiro minha CNH?` → `driver_license`/`rule`; `preciso renovar meu RG e meu CPF` (duas regras) → `model`; `[CPF] quero ajuda` → `model` (o marcador não aciona a regra de CPF); `ÍPTU atrasado` → `rule`; texto vazio → `model`; sempre 9 probabilidades somando 1 · sem `TODO`/`FIXME`/skip/`print` e nenhuma citação a plan nos comentários · `load` converte arquivo ausente ou inválido em `ModelNotAvailableError` com a causa preservada · nenhum modelo versionado, `output/` ignorado · caches e `__pycache__` removidos; nada mais largado.

**Decisões do executor aceitas:** `predict_proba(model, text)` e `classify(text, model=None)` recebem o modelo, em vez do global da §3.1, para evitar estado mutável (`padrao-escrita`); a síntese registra a assinatura real. `ModelNotAvailableError` exportada em `triage.classification`. Marcadores de anonimização removidos na normalização.

**Achados:** nenhum que reprove. Dois itens baixos foram para o `00-backlog`.
