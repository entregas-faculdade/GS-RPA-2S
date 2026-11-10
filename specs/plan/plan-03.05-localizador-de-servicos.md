---
tipo: "plan"
familia: "03"
item: "R03.5"
titulo: "Criar o localizador determinístico de fontes aprovadas por texto do pedido, com medição"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[02.01-classificacao]]", "[[005-llm-apenas-reformula-resposta]]"]
depende_de: "—"
destino_sintese: "specs/03.03-localizador-de-servicos.md"
---

# 1. Objetivo
Dado o texto anonimizado de um pedido, um localizador **sem LLM** devolve a fonte aprovada do catálogo que melhor o
atende (ou nada, quando não há fonte), com pontuação e folga, e a qualidade dele é **medida** em um conjunto rotulado.

# 2. Contexto
O classificador só conhece 8 categorias mais `other` ([[02.01-classificacao]]). Pedidos como "alvará" ou "buraco na rua"
caem em `other` e hoje vão à revisão sem ajuda ao cidadão. Com o catálogo v2 e o conteúdo de São Paulo (planos
anteriores), cada fonte aprovada traz `keywords`, `display_name`, `area` e `kind`. Esta plan cria **só o módulo de busca**
sobre esses dados; ligá-lo ao pipeline e às mensagens é a plan seguinte.

Princípio de segurança: o localizador só devolve registros `approved` do catálogo; **nunca** produz link nem telefone. Sem
LLM, é medível e reprodutível ([[005-llm-apenas-reformula-resposta]]).

Padrões existentes a reusar: `fold` (`triage.classification.preprocessing`) normaliza texto; `scikit-learn` já é
dependência; `Settings` (`triage/config.py`) lê limiares do ambiente; `CatalogLookup.approved_entries()` ([[03.01-catalogo-e-allowlist]])
entrega as entradas.

# 3. Escopo
## 3.1 Dentro
- `src/triage/automation/finder.py` (novo) — `ServiceFinder`, `FinderMatch`
- `src/triage/config.py` e `.env.example` — limiares do localizador (passo 2)
- `data/labeled/finder_requests.csv` (novo) — pedidos sintéticos rotulados (passo 3)
- `src/triage/evaluation/finder_metrics.py` (novo) — métricas do localizador (passo 4)
- `notebooks/evidence.ipynb` — uma seção nova com a medição do localizador, saídas salvas, sem PII nem chave
- `README.md` — uma linha na seção de resultados com os números do localizador e o limite
- `tests/automation/test_finder.py`, `tests/evaluation/test_finder_metrics.py`, `tests/test_config.py` — testes

## 3.2 Fora
- `triage.pipeline`, `triage.interface`, `triage.classification`, `triage.storage`: o localizador ainda **não** é chamado por eles.
- Mensagens ao cidadão, template de "não encontrei" e telefones de emergência (plan seguinte).
- LLM de qualquer tipo; verificação de link (o pipeline fará via `resolve_entry`).
- `data/catalog.json` (a não ser para corrigir `keywords` que o passo 3 provar ruins, registrando cada mudança no resumo).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | formato v2, `approved_entries`, `resolve_entry` |
| Spec fixa | [[02.01-classificacao]] | `fold`, TF-IDF e o cuidado de não medir no que se ajusta |
| Spec fixa | [[05.01-validacao-e-entrega]] | método de validação e honestidade da amostra |
| ADR | [[005-llm-apenas-reformula-resposta]] | o núcleo é determinístico |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | limiares, injeção de dependência, sem estado global mutável |
| Skill | `test-unitario` | testes de tabela |
| Código | `src/triage/automation/catalog.py`, `resolver.py`, `src/triage/classification/preprocessing.py`, `src/triage/config.py`, `src/triage/evaluation/metrics.py` | o que será usado |
| Código | `notebooks/evidence.ipynb`, `data/labeled/requests_labeled.csv` | formato do notebook e do CSV rotulado |

# 5. Instruções de execução
1. [dirigido] **Localizador.** `ServiceFinder` é construído **uma vez** com as entradas aprovadas (injetadas, não lidas
   dentro) e uma instância de configuração; `find(text) -> FinderMatch | None` recebe texto **anonimizado**. Por
   entrada, o documento de busca junta `keywords`, `display_name` e `agency`, normalizados com `fold`. A pontuação é a
   similaridade TF-IDF (cosseno) entre o pedido e cada documento (a técnica exata é sua, desde que determinística e sem
   rede). `FinderMatch` traz `entry`, `score` e `margin` (diferença para a segunda melhor de **outra** entrada). Devolve
   `None` quando a melhor pontuação fica abaixo do limiar mínimo ou a folga abaixo do limiar de folga. Texto vazio ou sem
   nenhum termo conhecido → `None`. Nunca levanta exceção por texto; catálogo sem entradas aprovadas → `None` sempre.
2. [dirigido] **Limiares.** `FINDER_MIN_SCORE` e `FINDER_MARGIN` em `Settings`, lidos do ambiente como os outros
   limiares (mesma validação em [0, 1], mesmo aviso e retorno ao padrão), documentados no `.env.example`. Os padrões
   saem da medição do passo 4 e são justificados no resumo.
3. [dirigido] **Conjunto rotulado.** `data/labeled/finder_requests.csv` com colunas `id,text,expected_id,split`.
   `expected_id` é o `id` de uma entrada `approved` ou `none` (pedido que **nenhuma** fonte aprovada atende).
   Mínimo de 60 linhas **escritas por você, sintéticas, sem dado pessoal**, em português informal e variado (erros de
   digitação, frases curtas e longas): ao menos 36 com `expected_id` real, cobrindo ao menos 12 entradas diferentes e as
   áreas `health`, `education`, `vehicles` e `city`; ao menos 16 `none` (assuntos fora do catálogo, ex.: dúvida de
   empresa privada, pedido sem sentido); ao menos 8 que **citam um serviço do catálogo de outra esfera** (ex.: pedir
   IPVA em uma frase que também fala de IPTU) para testar folga. `split`: `train` (cerca de metade, para ajustar
   limiares) e `test` (a outra metade, **só** para reportar). Nenhuma frase pode repetir uma das 180 do CSV de
   classificação nem uma `keyword` literal sozinha.
4. [dirigido] **Medição.** Em `triage.evaluation.finder_metrics` (funções puras, como `metrics.py`): cobertura (fração
   com `find` diferente de `None`), acerto entre os que devolveram fonte, e falso positivo (devolveu fonte para `none`).
   Ajustar os dois limiares **só no `train`**; reportar no `test`. Escolher o padrão para **falso positivo baixo** (é
   melhor dizer "não sei" do que apontar a fonte errada) e dizer o que isso custa em cobertura. Colar os números do
   `train` e do `test`, com o tamanho da amostra e a frase "descreve esta amostra sintética, não pedidos reais", no
   resumo, no README (uma linha) e no notebook (seção nova, executada).
5. [dirigido] **Testes.** `test_finder.py`: com entradas fake em memória (sem arquivo), pedido que casa uma entrada, pedido
   sem relação (`None`), empate entre duas entradas de áreas diferentes (`None` por folga), catálogo vazio, texto vazio,
   ordem das entradas sem efeito no resultado, determinismo (duas chamadas iguais). `test_finder_metrics.py`: casos de
   cada métrica, inclusive amostra vazia e tamanhos diferentes levantando `ValueError` como em `metrics.py`.
   `test_config.py`: os dois limiares (padrão, valor válido, inválido).
6. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] `find` devolve a entrada certa para os casos obrigatórios do conjunto de teste e `None` para os `none` abaixo do limiar.
- [ ] O localizador só considera entradas `approved` e nunca devolve texto de link ou telefone (só a entrada).
- [ ] O CSV tem os mínimos do passo 3 e nenhuma linha com dado pessoal ou repetida do CSV de classificação.
- [ ] Limiares ajustados só no `train`; os números do `test` constam no resumo, no README e no notebook, com a amostra e o limite.
- [ ] Os padrões escolhidos privilegiam falso positivo baixo, e o custo em cobertura está dito.
- [ ] Pipeline, interface e classificação não foram tocados; nenhum teste usa rede; ambiente e worktree limpos.
- [ ] Testes do escopo verdes; `ruff` e validador sem violação; nenhuma chave no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation tests/evaluation tests/test_config.py -q` → verde.
- `python -m ruff check src/triage/automation src/triage/evaluation src/triage/config.py tests/automation tests/evaluation` → sem erro.
- `validate.py` do `padrao-python` em `finder.py`, `finder_metrics.py` e seus testes → sem achado.
- O revisor recalcula as métricas do `test` com o catálogo real e confere os números do README e do notebook; sonda
  pedidos novos (incluindo "buraco na rua", "alvará", pedidos sem relação e pedidos ambíguos entre áreas).
- Confere que os limiares não foram ajustados olhando o `test` (histórico do resumo e do CSV).
- **Gate:** `nenhum — coberto por testes e pela medição`.

# 8. Destino da síntese
**Destino:** `specs/03.03-localizador-de-servicos.md` (spec nova)

Escrever: o contrato de `ServiceFinder.find`; só entradas `approved`; pontuação, folga e limiares com os padrões e a
justificativa; o conjunto rotulado do localizador e os números medidos (com tamanho e limite); que ele não produz link nem
telefone e funciona sem LLM.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências (o falso positivo no `test` não ficou baixo; ver *Pendências / riscos*)

**O que foi feito**
- `ServiceFinder` e `FinderMatch` em `src/triage/automation/finder.py`: documento de busca por entrada (`keywords` + `display_name` + `agency`), TF-IDF (`normalize`, n-gramas (1, 2), `sublinear_tf`) e cosseno; entradas injetadas, filtradas por `approved` e ordenadas por `id` na construção; `find` devolve `None` abaixo de `finder_min_score` ou `finder_margin`, sem termo conhecido, texto vazio ou sem entrada aprovada. Só devolve a entrada.
- `src/triage/config.py:17-18,35-36,71-72` e `.env.example`: `FINDER_MIN_SCORE` e `FINDER_MARGIN` em `Settings`, lidos por `_parse_threshold` (faixa [0, 1], aviso e retorno ao padrão). Padrões `0.25` e `0.15`.
- `data/labeled/finder_requests.csv`: 96 pedidos sintéticos (60 com fonte, 32 entradas diferentes, áreas `health`, `education`, `vehicles` e `city` cobertas, 10 que citam serviço de outra esfera; 36 `none`). `train` 48 e `test` 48, 30 com fonte e 18 `none` em cada.
- `src/triage/evaluation/finder_metrics.py`: `coverage`, `answered_accuracy`, `false_positive_rate`, `score_finder`, `predictions_at` e `threshold_table`, puras; amostra vazia e tamanhos diferentes levantam `ValueError`.
- `notebooks/evidence.ipynb`: seção 5 nova (5 células, 2 de código executadas, saídas salvas); a antiga seção 5 de limites virou 6. `README.md`: um parágrafo com os números e o limite, após o de resultados.
- Testes: `tests/automation/test_finder.py` (24 casos coletados), `tests/evaluation/test_finder_metrics.py` (23, inclusive a integridade do CSV) e 12 novos em `tests/test_config.py` (19 no arquivo, contra 7 antes).

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/automation/finder.py` | criado | localizador determinístico |
| `src/triage/evaluation/finder_metrics.py` | criado | métricas e varredura de limiares |
| `data/labeled/finder_requests.csv` | criado | 96 pedidos rotulados, sintéticos |
| `tests/automation/test_finder.py` | criado | testes do localizador |
| `tests/evaluation/test_finder_metrics.py` | criado | testes das métricas e do CSV |
| `src/triage/config.py` | alterado | dois limiares em `Settings` |
| `.env.example` | alterado | os dois limiares, sem valor |
| `tests/test_config.py` | alterado | padrão, valor válido, inválido e limites dos dois limiares |
| `notebooks/evidence.ipynb` | alterado | seção 5 nova; antiga 5 renumerada para 6 |
| `README.md` | alterado | um parágrafo com os números do localizador |
| `specs/plan/plan-03.05-localizador-de-servicos.md` | alterado | este resumo e o `status` |

**Verificações executadas**
- `python -m pytest tests/automation tests/evaluation tests/test_config.py -q` → 316 passed (antes de editar: 257; +59 novos).
- `python -m ruff check src/triage/automation src/triage/evaluation src/triage/config.py tests/automation tests/evaluation` → 1 erro, **preexistente e fora do escopo**: `UP033` em `src/triage/automation/allowlist.py:18`. Nos arquivos que toquei (incluindo `tests/test_config.py`): `All checks passed`.
- `validate.py` do `padrao-python` em `finder.py`, `finder_metrics.py`, `test_finder.py`, `test_finder_metrics.py`, `config.py` e `test_config.py` → 0 achados em cada.
- Células novas do notebook executadas com `nbconvert` numa cópia temporária (célula de preparação + as novas, na raiz do repositório); o `nbformat.validate` passou. As células antigas não foram reexecutadas (usam a rede).
- Varredura de segredo por `grep` nos arquivos tocados: só ocorrências benignas (`LLM_API_KEY=` já existente, parâmetro vazio de teste, "secretariat" em um id).
- `git diff --stat`: 5 arquivos alterados (+547 −4) mais os 5 novos, só o que a §3.1 lista (mais este resumo).

**Medição (descreve esta amostra sintética, não pedidos reais)**

Padrões `FINDER_MIN_SCORE=0.25` e `FINDER_MARGIN=0.15`:

| Divisão | Pedidos | Cobertura | Acerto entre os que devolveram fonte | Falso positivo |
|---|---|---|---|---|
| `train` | 48 | 45,8% (22) | 90,9% (20 de 22) | 5,6% (1 de 18 `none`) |
| `test` | 48 | 47,9% (23) | 87,0% (20 de 23) | 16,7% (3 de 18 `none`) |

- **Como os padrões foram escolhidos (só no `train`):** entre os pares com no máximo 1 falso positivo em 18 e acerto ≥ 90%, o de maior cobertura cujo vizinho (±0,05 na pontuação) também cumpre. `(0.20, 0.15)` tem cobertura maior (47,9%), mas seu vizinho `(0.15, 0.15)` tem 11,1% de falso positivo; ficou `(0.25, 0.15)`. Zerar o falso positivo no `train` exigiria pontuação ≥ 0,35 (cobertura 33,3%) só para barrar uma linha, a de Curitiba; não adotei.
- **Custo em cobertura:** pouco mais da metade dos pedidos fica sem fonte; no `test`, 10 dos 30 pedidos com fonte esperada ficam sem resposta. Nenhum pedido com fonte esperada recebeu fonte errada no `test`; no `train`, 1 (pedido com vacina e creche, `F055`, devolveu `sme_sp`).
- **Fonte errada no `test` (3 pedidos `none`):** `F080` mensalidade de faculdade particular → `higher_education_access` (0,35/0,35); `F090` saúde mental no trabalho → `labor_ministry` (0,34/0,15); `F096` IPVA do Rio de Janeiro → `sefaz_sp_ipva` (0,38/0,38). O último é o limite declarado do piloto (só São Paulo).

**Estado inicial do worktree:** `git status --short` vazio (limpo), branch `develop`.

**Ambiente após a verificação:** fotografei com `snapshot` antes de editar. A verificação criou `output/notebook-evidence` (setup do notebook), removida por mim. Não subi processo, servidor nem contêiner. O `diff` final: 0 diretórios temporários, 0 contêineres/imagens/volumes/redes/branches/worktrees novos; os processos "appeared" são churn da máquina (o kernel do `nbconvert` encerrou sozinho, confirmado), e 3 `.tmp` informativos em `system_temp`. A fotografia ficou na pasta temporária da sessão (o comando avisou), fora do repositório.

**Critérios de aceite**
- [x] `find` devolve a entrada certa e `None` para os `none` abaixo do limiar — evidência: `tests/automation/test_finder.py` (casos de tabela) e medição do `test`: 20 de 23 respondidos certos; 15 dos 18 `none` ficam sem fonte. Os 3 restantes estão acima do limiar (ver acima).
- [x] Só entradas `approved`; nunca devolve link nem telefone — `ServiceFinder.__init__` filtra com `approved_only`; `test_candidate_entries_are_never_found`, `test_returns_the_entry_itself_and_nothing_else` (campos de `FinderMatch` = `entry`, `score`, `margin`).
- [x] CSV com os mínimos e sem dado pessoal nem linha repetida — `tests/evaluation/test_finder_metrics.py` (`test_labeled_set_meets_the_minimums`, `test_no_text_repeats_the_classification_set_or_is_a_bare_keyword`, que compara os 418 textos do CSV de classificação, não só os 180). Os 10 pedidos de outra esfera são conferência de leitura (não há como detectar por máquina).
- [x] Limiares ajustados só no `train`; números do `test` no resumo, README e notebook, com amostra e limite — seção 5 do notebook e README.
- [x] A escolha privilegia falso positivo baixo e o custo em cobertura está dito — **a escolha sim; o resultado no `test` não** (16,7%), ver pendências.
- [x] Pipeline, interface, classificação e storage não tocados (`git status`); nenhum teste usa rede; ambiente e worktree limpos.
- [x] Testes do escopo verdes; `ruff` e validador sem violação **nos arquivos tocados** (o erro `UP033` de `allowlist.py` é preexistente e fora do escopo); nenhuma chave no diff.

**Decisões e suposições**
- **Tokenização:** usei `normalize` (que começa por `fold`, tira stopwords e pontuação) como pré-processador do `TfidfVectorizer`, em vez de só `fold`, porque o TF-IDF precisa de tokens. É a mesma normalização do classificador.
- **Folga:** diferença para a melhor das **outras entradas**, de qualquer área (leitura literal da plan); com uma entrada só, é a própria pontuação. Duas entradas quase idênticas do catálogo derrubam a folga e viram `None` (custo em cobertura, por desenho).
- **Método extra `best(text)`:** devolve a melhor entrada com pontuação e folga **sem** limiar; `find` é `best` mais os limiares. Não está no contrato da plan; existe para a varredura de limiares não refazer a busca, e `predictions_at` repete a regra do `find` (um teste cobre os dois).
- **Sem `numpy`/`scipy` direto:** só chegam via scikit-learn e não estão no `requirements.txt`; a parte numérica é em Python puro.
- **Conjunto rotulado:** escrevi os 96 pedidos à mão, com rótulos fixados antes de rodar o localizador, e **não mudei nenhum rótulo depois**. O primeiro rascunho tinha 24 `none`, a maioria sem nenhum termo do catálogo, e a primeira sonda no `train` mostrou isso (falso positivo irreal de baixo). **Acrescentei 12 negativos difíceis** (10 que dividem vocabulário com o catálogo e 2 de outra cidade) **antes de abrir o `test`**. O `test` só foi aberto depois de fixados os padrões (de provisórios `0.30/0.05` para `0.25/0.15`, pela varredura do `train`), uma vez, e nada mudou depois.
- **Divisão:** dentro de cada grupo (com fonte, outra esfera, `none`) as linhas alternam `train`/`test`, o que dá 48/48 com 30 e 18 em cada.
- **Notebook:** só as células novas foram executadas (cópia temporária); numeração de execução 20 e 21, antes da célula final de limpeza que continua marcada 19. Importei `ServiceFinder` e as métricas na primeira célula nova, para não mexer na célula de preparação.
- **`.env.example`:** as duas variáveis ficam sem valor e o comentário cita os padrões, como a plan pediu "documentados".
- **Cobertura no CSV ignora entradas duplicadas do catálogo** de propósito: não há pedido de título de eleitor, certidão, INSS, Bolsa Família ou bombeiros, onde duas entradas do catálogo se sobrepõem e a folga as barraria. A cobertura real nesses temas deve ser menor que a medida.

**Achados fora do escopo (não corrigidos)**
- `src/triage/automation/allowlist.py:18` e `src/triage/classification/urgency.py:16` — `ruff` `UP033` (`lru_cache(maxsize=None)`); `ruff check src` dá 4 erros ao todo e o comando da §7 da plan falha por causa do de `allowlist.py`.
- `notebooks/evidence.ipynb`, seção 6 (limites): ainda diz "São 8 serviços curados à mão", mas o catálogo tem 51 entradas aprovadas.

**Pendências / riscos**
- **Falso positivo no `test` = 16,7% (3 de 18), contra 5,6% no `train`:** o critério "falso positivo baixo" não se confirmou no `test`. Na varredura do `test` (que eu abri depois de fixar os padrões) `FINDER_MIN_SCORE=0.35` com `0.15` daria falso positivo de 6% e cobertura de 27%, mas **não ajustei por isso**: seria ajustar olhando o `test`. Decisão do revisor: aceitar, ou abrir uma rodada com amostra nova.
- Amostra pequena e sintética (cada pedido vale ~2 pontos percentuais); os números não sustentam conclusão estatística.
- O localizador não distingue cidade nem estado: pedido de outra cidade recebe a fonte de São Paulo se a pontuação passar do limiar (`F095` no `train`, `F096` no `test`).
- Pedido com dois assuntos: depende das palavras de cada um; `quero pagar o iptu e o ipva` → `None` por folga (0,11), e `F055` (vacina e creche) devolveu a fonte errada no `train`.
- Sondas rápidas, com os padrões: `buraco na rua` → `sp156`; `alvará` → `gap_city_permit_property_tax`; `como faço um bolo` → `None`.
- Verificação **escopada**; suíte inteira e `ruff check run.py src tests` ficam para o commit/CI.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->

## Veredito — 2026-11-10 — 🟢 Aprovado

Verifiquei, sem confiar no resumo:
- **Escopo:** `git status` mostra só `finder.py`, `finder_metrics.py`, `finder_requests.csv`, os dois testes novos e, alterados, `config.py`, `.env.example`, `tests/test_config.py`, `README.md` e `notebooks/evidence.ipynb`, todos do §3.1. `pipeline`, `interface`, `classification` e `storage` intactos; `data/catalog.json` não foi tocado.
- **Código lido inteiro:** `ServiceFinder` filtra por `approved` e ordena por `id` (a ordem de entrada não muda o resultado), é determinístico, não usa rede nem LLM e devolve só a entrada com pontuação e folga; sem entrada, texto vazio ou sem termo conhecido → `None`.
- **Conjunto rotulado** (script próprio): 96 linhas, 48 `train` e 48 `test`; 60 com fonte (32 entradas diferentes, áreas `health`, `education`, `vehicles`, `city` e outras), 36 `none`; todo `expected_id` existe entre as 51 aprovadas; nenhuma linha repete as 418 do CSV de classificação nem é uma `keyword` literal; nenhuma duplicada.
- **Medição independente** com o catálogo real e os padrões 0,25/0,15: `train` cobertura 45,8%, 20 de 22 certos, falso positivo 1 de 18; `test` cobertura 47,9%, 20 de 23 certos, falso positivo 3 de 18 (16,7%). Bate com resumo, README e notebook. Os 3 falsos positivos do `test` são `F080` (mensalidade de faculdade particular), `F090` (saúde mental no trabalho) e `F096` (IPVA do Rio), este último o limite declarado do piloto (só SP).
- **Limiares só no `train`:** a escolha vem da varredura do `train` (menor falso positivo com vizinho estável); o executor viu a varredura do `test` depois de fixar os padrões e **não** ajustou, o que o resumo registra. O critério da plan é a escolha privilegiar falso positivo baixo e o custo estar dito; ambos atendidos, e o número do `test` é reportado sem retoque.
- **Sondas novas:** `buraco na rua` → `sp156`; `alvará` → `gap_city_permit_property_tax`; `preciso de ambulância` → `samu_192`; `vacina da gripe` → `vaccination`; `renovar a cnh` → `driver_license`; `como faço um bolo` e `qual o preço do dólar` → `None`. Fraquezas conhecidas: `certidão de nascimento`, `como me aposentar` e `luz cortada` → `None` (entradas sobrepostas derrubam a folga, ou não há fonte).
- **Testes e lint:** `python -m pytest tests/automation tests/evaluation tests/test_config.py -q` → 316 passed; `ruff` com um único erro anterior (`UP033` em `allowlist.py`, backlog item 14); `validate.py` nos 6 `.py` → 0 achados. Notebook: só as células novas (seção 5) e a renumeração da antiga 5 para 6, sem erro, sem chave nem caminho local.
- **Sinais de atalho:** nenhum TODO, teste em skip ou citação a plan.
Registrado: o falso positivo de 16,7% no `test` vira condição da plan 03.06 (texto do degrau 2 em tom de sugestão) e item de backlog.
