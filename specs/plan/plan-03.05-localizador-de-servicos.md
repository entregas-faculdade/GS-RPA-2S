---
tipo: "plan"
familia: "03"
item: "R03.5"
titulo: "Criar o localizador determinístico de fontes aprovadas por texto do pedido, com medição"
dominio: "Automação"
status: "🟡 Em execução"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->
