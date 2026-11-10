---
tipo: "plan"
familia: "02"
item: "R02.4"
titulo: "Ampliar o conjunto rotulado de treino e recalibrar a confiança por validação cruzada"
dominio: "Classificação"
status: "🔴 A executar"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->
