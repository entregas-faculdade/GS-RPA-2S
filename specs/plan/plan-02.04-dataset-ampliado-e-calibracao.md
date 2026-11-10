---
tipo: "plan"
familia: "02"
item: "R02.4"
titulo: "Ampliar o conjunto rotulado de treino e recalibrar a confiança por validação cruzada"
dominio: "Classificação"
status: "🟢 Aprovada"
prioridade: "Média"
tags: ["plan"]
relacionados: ["[[02.01-classificacao]]", "[[02.02-confianca-e-revisao-humana]]", "[[05.01-validacao-e-entrega]]"]
depende_de: "plan-03.04-catalogo-sao-paulo e plan-02.03-urgencia-saude — precisam estar 🟢"
destino_sintese: "specs/02.01-classificacao.md"
---

# 1. Objetivo
A confiança do classificador deixa de ser "muito baixa" nos pedidos comuns: o treino passa de 14 para ao menos 40 exemplos
por categoria, os limiares são reavaliados por validação cruzada **só no treino**, e o ganho é medido no mesmo conjunto de
teste de antes.

# 2. Contexto
Em uso, a confiança ficou baixa: o modelo TF-IDF + regressão logística treina com 14 exemplos por categoria (126 no total)
([[02.01-classificacao]]) e probabilidades de um modelo tão pequeno são tímidas. O conjunto de teste (54 pedidos, 6 por
categoria) é a régua dos resultados já publicados ([[05.01-validacao-e-entrega]] §2.2: 81,5% de acerto, 57,4% de cobertura
automática) e **não muda**. Os limiares `CONFIDENCE_MIN=0,60` e `AMBIGUITY_MARGIN=0,15` foram mantidos sem ajuste por
medir no próprio teste; qualquer ajuste futuro deve usar validação cruzada do treino ([[02.02-confianca-e-revisao-humana]] §2.4).

A categoria `other` recebe, daqui em diante, também pedidos de assuntos que o catálogo de São Paulo cobre fora das 8
categorias (alvará, buraco na rua, matrícula escolar, vacina, multa de trânsito, IPVA): são os que o localizador atende. O
`CATEGORY_RULES` (regex) **não muda**.

Os exemplos novos são escritos por você (sintéticos, sem dado pessoal) e **revisados por uma pessoa** antes de valer como
verdade: no resumo, liste uma amostra de 20 linhas novas para o usuário conferir.

# 3. Escopo
## 3.1 Dentro
- `data/labeled/requests_labeled.csv` — acrescentar linhas com `split=train`; **nenhuma** linha `split=test` muda ou entra
- `src/triage/evaluation/calibration.py` (novo) — validação cruzada e tabela de limiares
- `tests/classification/test_dataset.py` e `tests/evaluation/test_calibration.py` — ajustar e criar
- `src/triage/config.py` — **só** os valores padrão dos limiares, **só** se o passo 4 provar a mudança
- `README.md` e `notebooks/evidence.ipynb` — números e a seção de limites/calibração (notebook reexecutado, saídas salvas)

## 3.2 Fora
- As linhas `split=test` e a divisão 126/54 original (as 126 de treino originais ficam intactas).
- `src/triage/classification/` (regras, modelo, pré-processamento), `triage.privacy`, `triage.pipeline`, `triage.interface`.
- Chamar LLM ou API para gerar exemplos; dados reais de usuário.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[02.01-classificacao]] | conjunto rotulado, divisão, modelo |
| Spec fixa | [[02.02-confianca-e-revisao-humana]] | limiares e como se ajustam |
| Spec fixa | [[05.01-validacao-e-entrega]] | método de medição e honestidade da amostra |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | funções puras, limiares |
| Skill | `test-unitario` | testes de dados e de métrica |
| Código | `src/triage/classification/model.py`, `classifier.py`, `decision.py`, `src/triage/evaluation/metrics.py` | como o modelo é treinado e medido |
| Código | `data/labeled/requests_labeled.csv`, `tests/classification/test_dataset.py`, `notebooks/evidence.ipynb` | dados, testes e evidências |

# 5. Instruções de execução
1. [dirigido] **Antes.** Com o conjunto **atual**, medir no `split=test` (como o notebook mede) acurácia, taxa de revisão,
   cobertura e acurácia entre os respondidos, e a confiança média dos acertos e dos erros. Guardar para o resumo.
2. [dirigido] **Exemplos novos.** Acrescentar ao menos 26 linhas `split=train` por categoria (as 9, incluindo `other`), de
   modo que cada categoria fique com **≥ 40** de treino. Variedade obrigatória: frase curta, longa, coloquial, com erro de
   digitação e sem acento, com marcadores já anonimizados (`[CPF]`, `[TELEFONE]`, `[NOME]`) em parte das linhas, e
   perguntas e afirmações. `other`: assuntos de saúde, educação, veículos e prefeitura da lista do catálogo de São Paulo,
   mais assuntos sem relação. A coluna `urgent` segue a regra de `is_urgent` (a plan de urgência exige que as duas
   coincidam em todas as linhas); inclua alguns exemplos urgentes novos. `id` novos e sequenciais; sem duplicata exata nem
   quase-duplicata de qualquer linha de `test` (o teste do passo 5 prova).
3. [dirigido] **Calibração.** `calibration.py` (funções puras sobre rótulos e probabilidades, injetando o treino do
   modelo): validação cruzada estratificada de 5 partes **só sobre o `train`**; para uma grade de limiares de confiança
   de 0,40 a 0,80, a cobertura automática e a acurácia entre os respondidos; a confiança média dos acertos e dos erros.
4. [dirigido] **Decisão dos limiares.** Mudar o padrão de `CONFIDENCE_MIN` **só** se a validação cruzada mostrar cobertura
   maior com acurácia entre os respondidos **não pior** que a do padrão atual; senão manter 0,60 e dizer que se manteve e
   por quê. `AMBIGUITY_MARGIN` idem. Nunca decidir olhando o `test`.
5. [dirigido] **Testes.** `test_dataset.py` ajustado (novos mínimos por categoria, as 126 originais e as 54 de teste
   intactas por `id` e por texto, sem sobreposição treino × teste, `urgent` binário). Teste novo: nenhuma linha de treino tem
   similaridade (cosseno TF-IDF) ≥ 0,85 com uma de teste. `test_calibration.py`: casos de tabela, entrada vazia e tamanhos
   diferentes levantando `ValueError`, como em `metrics.py`.
6. [dirigido] **Depois.** Repetir a medição do passo 1 (mesmo teste, modelo treinado no conjunto ampliado). Atualizar README
   e notebook com antes e depois, o tamanho das amostras (treino ampliado, 54 de teste, validação cruzada no treino) e a
   frase: "descreve esta amostra sintética, não pedidos reais". Se a acurácia caiu ou a cobertura não subiu, dizer
   exatamente isso; **não** reescrever o resultado.
7. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Cada categoria tem ≥ 40 linhas de treino; as 126 originais de treino e as 54 de teste estão idênticas.
- [ ] Nenhuma linha de treino é quase-duplicata de uma de teste; `is_urgent` coincide com `urgent` nas linhas novas.
- [ ] A calibração roda só no treino; a tabela de limiares está no resumo e no notebook.
- [ ] Os limiares só mudaram se a validação cruzada justificar, e o resumo diz qual foi a decisão.
- [ ] Antes e depois no mesmo teste estão no resumo, no README e no notebook, com tamanho de amostra e limite; números
      conferem com uma reexecução do revisor.
- [ ] Amostra de 20 linhas novas listada no resumo para revisão humana.
- [ ] Ambiente e worktree limpos (sem modelo largado); testes do escopo verdes; `ruff` e validador sem violação; nenhum dado pessoal ou chave no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — o CSV é treinado por fixtures de pipeline e interface`.
- `git diff --stat` → só arquivos de §3.1; `git diff` do CSV mostra só linhas **acrescentadas** (nenhuma remoção ou edição).
- `python -m pytest tests/classification tests/evaluation tests/pipeline tests/interface -q` → verde.
- `python -m ruff check src/triage/evaluation tests/classification tests/evaluation` → sem erro.
- `validate.py` do `padrao-python` em `calibration.py` e testes → sem achado.
- O revisor recalcula antes/depois, a calibração e a quase-duplicata; amostra aleatória de linhas novas para checar rótulo e PII.
- **Gate:** `nenhum — coberto por testes de dados e pela reexecução da medição`.

# 8. Destino da síntese
**Destino:** `specs/02.01-classificacao.md`

Levar, **substituindo** o tamanho do conjunto e as contagens: ≥ 40 por categoria de treino e o total novo; o conteúdo de
`other`; a validação cruzada e a decisão sobre os limiares; os números antes e depois no mesmo teste, com o limite. A spec
05.01 terá os resultados atualizados pelo revisor na síntese.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências (um comando do §7 falha por achado pré-existente fora do escopo; ver Pendências)

**O que foi feito**
- Passo 1 (antes): mediu-se o `split=test` com o conjunto original (126 de treino) — acurácia 81,5% (44/54), revisão 42,6% (23/54), cobertura 57,4% (31/54), acurácia entre respondidos 100% (31/31), confiança média dos acertos 0,729 (44) e dos erros 0,257 (10).
- Passo 2: `data/labeled/requests_labeled.csv` ganhou 238 linhas `split=train` (`L181`–`L418`), só acrescentadas: 26 por categoria (30 em `other`). Variedade: frases curtas ("renovar cnh"), longas, coloquiais, sem acento/erro de digitação, perguntas e afirmações, marcadores `[CPF]`/`[TELEFONE]`/`[NOME]` em parte das linhas; `other` cobre alvará, buraco/iluminação, matrícula e creche, vacina, multa de trânsito, IPVA, licenciamento, passaporte e assuntos sem relação. 13 linhas novas são urgentes (`urgent=1`), todas com termo do léxico.
- Passo 3: `src/triage/evaluation/calibration.py` (novo): `out_of_fold_probabilities` (validação cruzada estratificada de 5 partes, semente 42, treino injetado por `fit_predict`), `clone_fit_predict`, `classifications_from_probabilities`, `threshold_table` (usa o `triage_decision` real, então regra, urgência, `other`, confiança e folga entram), `confidence_grid`/`margin_grid`, `mean_confidence_by_outcome`.
- Passo 4: decisão dos limiares — **mantidos** `CONFIDENCE_MIN=0,60` e `AMBIGUITY_MARGIN=0,15`; `src/triage/config.py` **não foi tocado** (tabela abaixo).
- Passo 5: `tests/classification/test_dataset.py` ajustado e `tests/evaluation/test_calibration.py` criado (14 testes).
- Passo 6: README e `notebooks/evidence.ipynb` atualizados com antes/depois, tamanhos de amostra, tabela de limiares e a frase "descreve esta amostra sintética, não pedidos reais"; notebook reexecutado com saídas salvas.

**Medição antes × depois (mesmo teste de 54 pedidos, sem LLM)**
| Métrica | Antes (126 de treino) | Depois (364 de treino) |
|---|---|---|
| Acurácia geral | 81,5% (44/54) | 88,9% (48/54) |
| Revisão humana | 42,6% (23/54) | 33,3% (18/54): 10 `low_confidence`, 7 `out_of_catalog`, 1 `urgent` |
| Cobertura automática | 57,4% (31/54) | 66,7% (36/54) |
| Acurácia entre respondidos | 100% (31/31) | 100% (36/36) |
| Confiança média acertos / erros | 0,729 / 0,257 | 0,766 / 0,308 |

Os 6 erros restantes foram todos à revisão (nenhum respondido sozinho errado). Treino depois: 40 por categoria e 44 em `other`.

**Calibração (validação cruzada de 5 partes só no `train`, 364 pedidos; acurácia fora da amostra 92,9%; confiança média acertos 0,77 / erros 0,41)**
| `CONFIDENCE_MIN` (folga 0,15) | Cobertura automática | Acurácia entre respondidos |
|---|---|---|
| 0,40 | 76,9% | 96,8% |
| 0,45 | 75,3% | 96,7% |
| 0,50 | 72,0% | 97,3% |
| 0,55 | 71,2% | 97,7% |
| **0,60 (padrão)** | **69,2%** | **98,0%** |
| 0,65 | 67,9% | 98,0% |
| 0,70 | 65,9% | 98,3% |
| 0,75 | 64,8% | 98,7% |
| 0,80 | 63,7% | 98,7% |

`AMBIGUITY_MARGIN` em 0,05 / 0,10 / 0,15 / 0,20 / 0,25 (com `CONFIDENCE_MIN=0,60`): as cinco linhas dão 69,2% de cobertura e 98,0% de acurácia, idênticas.

**Decisão sobre os limiares:** a regra do passo 4 exige cobertura maior com acurácia entre respondidos não pior que a do padrão. Todo valor abaixo de 0,60 aumenta a cobertura mas reduz a acurácia (97,7% em 0,55; 96,8% em 0,40), então 0,60 se mantém. A folga não produziu nenhuma diferença na tabela, então 0,15 se mantém. Nada olhou o `test`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `data/labeled/requests_labeled.csv` | alterado | +238 linhas `train` acrescentadas; nenhuma linha removida ou editada (`git diff --stat`: 238 inserções, 0 remoções) |
| `src/triage/evaluation/calibration.py` | criado | validação cruzada e tabela de limiares |
| `tests/evaluation/test_calibration.py` | criado | tabela conhecida, bordas inclusivas, `other`/urgência, `ValueError` de vazio/tamanhos/grade/classe pequena |
| `tests/classification/test_dataset.py` | alterado | mínimos (≥ 40 de treino por categoria, 6 de teste por categoria, ≥ 414 linhas, ≥ 20 urgentes); 180 originais por SHA-256 e por `id`; `urgent` novo = `is_urgent`; sem sobreposição treino × teste; similaridade cosseno TF-IDF < 0,85 |
| `README.md` | alterado | seção Resultados com antes/depois, calibração, tamanhos e limite |
| `notebooks/evidence.ipynb` | alterado | células de antes/depois e calibração; textos de análise de erros e limites atualizados; célula 4.4 corrigida (ver Decisões); reexecutado com saídas salvas |

**Verificações executadas**
- `python -m pytest tests/classification tests/evaluation tests/pipeline tests/interface -q` → 182 passed.
- `python -m ruff check src/triage/evaluation/calibration.py tests/evaluation tests/classification/test_dataset.py` → All checks passed. O comando literal do §7 (`ruff check src/triage/evaluation tests/classification tests/evaluation`) → 2 erros `I001` em `tests/classification/test_decision.py:3` e `tests/classification/test_model.py:3`, arquivos que não toquei (ver Achados).
- `validate.py` do `padrao-python` em `calibration.py`, `test_calibration.py` e `test_dataset.py` → `findings: []` nos três.
- `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/evidence.ipynb` → executou sem erro; saídas salvas.
- Checagem das linhas novas (script de scratchpad): 238 linhas, sem duplicata exata, similaridade máxima com o teste 0,75 (< 0,85), `is_urgent` = `urgent` em todas, `anonymize` sem PII.
- Gate `nenhum` na §7: não há limite de regra a demonstrar.

**Estado inicial do worktree:** `git status --short` vazio (limpo), branch `develop`.

**Ambiente após a verificação:** o notebook cria `output/notebook-evidence/` e a última célula o remove; uma primeira execução falhou antes dessa célula e eu removi a pasta à mão. Ficaram em `output/` (git-ignorado) `logs/`, `models/classifier.joblib` e `reports/`, com data 13:36 de hoje, **anteriores a esta conversa**: não são meus e não foram removidos. `snapshot`/`diff` da skill `code-limpeza-ambiente`: não rodei (indisponível nesta sessão: não localizei `environment.py`); a conferência foi manual por data e listagem de `output/`. Nenhum processo, servidor ou contêiner foi iniciado.

**Critérios de aceite**
- [x] Cada categoria ≥ 40 de treino; 126 originais de treino e 54 de teste idênticas — evidência: tabela do notebook (40 × 8 e 44 em `other`); `test_original_rows_are_untouched` (SHA-256 das 180 linhas originais = o do arquivo antes da edição).
- [x] Sem quase-duplicata treino × teste; `is_urgent` coincide com `urgent` nas linhas novas — `test_no_train_row_is_a_near_duplicate_of_a_test_row`, `test_new_rows_urgent_flag_matches_the_lexicon`.
- [x] Calibração só no treino; tabela no resumo e no notebook — acima e células de calibração do notebook.
- [x] Limiares só mudariam se a validação justificasse: não justificou, `config.py` intacto, decisão registrada acima.
- [x] Antes e depois no resumo, README e notebook, com amostras e limite — o revisor deve reexecutar para conferir.
- [x] Amostra de 20 linhas listada abaixo.
- [ ] Ambiente/worktree limpos; `ruff` sem violação — motivo: o comando do §7 falha por 2 `I001` pré-existentes em arquivos fora do escopo; os arquivos que toquei estão limpos. `output/` tem restos anteriores a esta conversa (git-ignorado).

**Amostra de 20 linhas novas para revisão humana** (rótulo e `urgent` a conferir)
| id | text | label | urgent |
|---|---|---|---|
| L190 | como faço para tirar a suspensão da minha cnh | `driver_license` | 0 |
| L193 | segunda via cnh | `driver_license` | 0 |
| L195 | meu CPF é [CPF], quero consultar a situação da minha cnh | `driver_license` | 0 |
| L198 | pra renovar a carteira de motorista preciso fazer exame de vista? | `driver_license` | 0 |
| L199 | como faço a transferência da minha cnh de outro estado para São Paulo? | `driver_license` | 0 |
| L203 | posso fazer as aulas da autoescola online para a primeira habilitação? | `driver_license` | 0 |
| L205 | meu marido sofreu um infarto dirigindo e a cnh dele foi apreendida, preciso de ajuda | `driver_license` | 1 |
| L219 | vendi o imóvel mas o iptu continua no meu nome, como resolver | `property_tax` | 0 |
| L235 | meu rg foi roubado, preciso fazer boletim de ocorrência antes? | `id_card` | 0 |
| L263 | cpf de criança: quais documentos precisa levar? | `cpf_registration` | 0 |
| L274 | tem taxa para regularizar o cpf? | `cpf_registration` | 0 |
| L282 | titular do cpf faleceu, como cancelar o cadastro? | `cpf_registration` | 0 |
| L288 | onde faço a biometria para o título de eleitor? | `voter_id` | 0 |
| L292 | título de eleitor | `voter_id` | 0 |
| L310 | como saber se meu título está regular | `voter_id` | 0 |
| L318 | bolsa familia | `social_benefits` | 0 |
| L330 | a família que mora de aluguel tem direito ao bolsa família? | `social_benefits` | 0 |
| L347 | oi, meu telefone é [TELEFONE], queria saber do andamento do meu pedido de aposentadoria | `social_security` | 0 |
| L391 | tem buraco na calçada da minha rua, como peço o conserto na prefeitura? | `other` | 0 |
| L413 | licenciamento anual do veículo: onde consulto o valor? | `other` | 0 |

**Decisões e suposições**
- **Quase-duplicata:** medida com TF-IDF (mesmo `normalize`, n-gramas `(1, 2)`, `sublinear_tf`) ajustado sobre todas as linhas do CSV; limite 0,85 do passo 5, estrito (`<`). A linha mais próxima de um teste ficou em 0,75.
- **`urgent` nas linhas originais:** a plan de urgência prevê `is_urgent == urgent` em todas as linhas, mas seis originais (L031, L052, L125, L131, L150, L178) divergem e as 126 de treino originais não podem mudar. O teste novo cobre só as linhas novas (`id` > L180), como o critério de aceite desta plan diz.
- **Sem alterar `classification/`:** como `_build_pipeline` é privado, a validação cruzada clona o modelo já treinado (`sklearn.base.clone`), que traz os mesmos hiperparâmetros.
- **Antes medido dentro do notebook:** treinando um modelo com as 180 primeiras linhas do CSV (as originais) gravadas em arquivo temporário em `output/notebook-evidence/`, para o "antes" ser reproduzível e não texto fixo.
- **Notebook, célula 4.4:** `load_catalog()["driver_license"]` quebrava (`TypeError`) porque o catálogo agora devolve uma lista de `ServiceEntry`; sem corrigir não havia como reexecutar o notebook com saídas salvas, que o escopo exige. Troquei por `next(entry for entry in approved_only(load_catalog()) if entry.category == "driver_license")`, só nessa célula e no import.
- **Textos de análise de erros do notebook** (tabela "Agrupamento e causa provável") reescritos para os 6 erros atuais (L010, L094, L100, L130, L140, L164); as causas continuam hipóteses, sem experimento.
- **Rótulos `other`:** pedidos urgentes de saúde e desastre (pronto socorro, desmaio, enchente, abuso infantil, ambulância) entram como `other` com `urgent=1`, como as linhas originais L171, L172 e L178; a verdade dos rótulos depende da conferência humana da amostra.
- A plan estava com `status: "🔴 A executar"` e não `🟡 Em execução` ao começar; não alterei o status até o fim (só o `🟠` final).

**Achados fora do escopo (não corrigidos)**
- `tests/classification/test_decision.py:3` e `tests/classification/test_model.py:3` — `ruff` `I001` (import fora de ordem), pré-existente; faz o comando de ruff do §7 sair com erro.
- `data/labeled/README.md` — ainda descreve "180 pedidos, 20 por categoria" e "14 train e 6 test por categoria"; fica desatualizado com o treino ampliado (arquivo fora do §3.1).
- `specs/02.01-classificacao.md` §2.5 e `specs/05.01-validacao-e-entrega.md` §2.2/2.3 — números antigos; já previstos para a síntese do revisor.
- `AMBIGUITY_MARGIN=0,15` é inerte com `CONFIDENCE_MIN ≥ 0,60` (a folga mínima já é 0,20), então o parâmetro hoje não altera decisões; vale uma linha na spec 02.02.
- Seis linhas originais `urgent=1` sem termo no léxico (citadas acima).

**Pendências / riscos**
- Rótulos e flags das 238 linhas novas precisam de conferência por uma pessoa (amostra acima); o revisor deve checar também uma amostra aleatória por PII.
- A medição "depois" mudou o teste de 6 para 6 erros restantes, mas com 54 pedidos cada pedido vale 1,9 ponto: a melhora de 81,5% para 88,9% (4 pedidos a mais) é indicativa, não conclusiva.
- Não rodei a suíte inteira nem a verificação completa (conforme §3 do prompt do executor).
- O notebook foi reescrito pelo `nbconvert` (metadados e formatação), então o diff dele é grande; o conteúdo novo está nas seções 2 (antes/depois, calibração) e na tabela de causas.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->

## Veredito — 2026-11-10 — 🟢 Aprovado

Verifiquei, sem confiar no resumo:
- **Escopo:** `git status` mostra só `README.md`, `data/labeled/requests_labeled.csv`, `notebooks/evidence.ipynb`, `tests/classification/test_dataset.py` e os dois arquivos novos (`calibration.py`, `test_calibration.py`), todos do §3.1. `config.py`, `classification/`, `pipeline/` e `interface/` intactos.
- **CSV:** `git diff --numstat` → 238 inserções, 0 remoções. As 180 linhas do `HEAD` são idênticas às 180 primeiras do arquivo (`DataFrame.equals`) e as 54 de `test` não mudaram. Treino por categoria: 40 em cada uma das 8 e 44 em `other`.
- **Medição independente** (script próprio, `triage_decision` real, limiares padrão 0,60/0,15): antes 81,5% de acurácia, 23 em revisão, 31 respondidos, 31/31 certos, confiança média 0,729 acertos / 0,257 erros; depois 88,9%, 18 em revisão (10 `low_confidence`, 7 `out_of_catalog`, 1 `urgent`), 36 respondidos, 36/36, confiança 0,766 / 0,308. Bate com resumo, README e notebook.
- **Calibração independente** (validação cruzada de 5 partes só no `train`, 364 pedidos): acurácia fora da amostra 92,9%; tabela de 0,40 a 0,80 idêntica à do resumo (0,60 → 69,2% de cobertura e 98,0%; 0,55 → 71,2% e 97,7%; 0,40 → 76,9% e 96,8%). A decisão de manter 0,60 e 0,15 decorre da regra do passo 4; `config.py` não foi tocado.
- **Amostra e PII:** 238 linhas novas passadas por `anonymize` → nenhuma muda (zero PII residual). Amostra aleatória de 30 linhas conferida: rótulos coerentes. `is_urgent` coincide com `urgent` em todas as novas (13 urgentes).
- **Testes e lint:** `python -m pytest tests/classification tests/evaluation tests/pipeline tests/interface -q` → 182 passed. `ruff` nos arquivos tocados limpo; o comando literal do §7 falha só por `I001` em `test_decision.py` e `test_model.py`, arquivos não tocados e já registrados no backlog (item 14), então o comando da plan estava largo demais, não a execução. `validate.py` em `calibration.py`, `test_calibration.py` e `test_dataset.py` → 0 achados.
- **Notebook:** 35 células, todas executadas, nenhuma com erro, sem chave nem caminho local; as saídas de antes/depois e calibração coincidem com a minha reexecução. A correção da célula 4.4 (`load_catalog()` agora devolve lista) é necessária para o notebook executar e está no escopo (notebook). `output/notebook-evidence/` não existe; `output/` é git-ignorado e anterior.
- **Sinais de atalho:** nenhum TODO, nenhum teste em skip, nenhuma plan citada em código, teste ou spec.
Registrado no backlog: linhas L372 e L409 (o marcador `[CPF]` aciona a regra de CPF, que vence o rótulo), `AMBIGUITY_MARGIN` inerte, `data/labeled/README.md` desatualizado.
