---
tipo: "plan"
familia: "02"
item: "R02.1"
titulo: "Criar o conjunto rotulado sintético e o classificador regex + TF-IDF"
dominio: "Classificação"
status: "🟡 Em execução"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
