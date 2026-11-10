---
tipo: "plan"
familia: "02"
item: "R02.3"
titulo: "Detectar urgência de saúde e parar de tratar \"urgente\" de cortesia como emergência"
dominio: "Classificação"
status: "🟡 Em execução"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[02.02-confianca-e-revisao-humana]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: ""
destino_sintese: "specs/02.02-confianca-e-revisao-humana.md"
---

# 1. Objetivo
Um pedido que descreve emergência de saúde ("dores no peito", "falta de ar") vai à revisão como `urgent`, e a palavra
"urgente" usada só como pressa ou cortesia ("quero renovar a CNH, é urgente") deixa de bloquear a resposta automática.

# 2. Contexto
Em uso real, o pedido "dores no peito…" foi classificado como `driver_license` com confiança 0,17 e motivo
`low_confidence`, **não** como urgente: o léxico `data/urgency_terms.json` não tem sintomas de saúde, e o casamento é por
palavra inteira, então "dor no peito" não casa "dores no peito". No sentido oposto, "Quero abrir uma reclamação.
Urgente obrigado." foi marcado `urgent` só pela palavra solta "urgente".

`is_urgent` ([[02.02-confianca-e-revisao-humana]] §2.5) normaliza com `fold` (sem acento, minúsculas) e procura os termos
do léxico por palavra ou expressão inteira; léxico ausente ou inválido devolve `True` (falha segura, **não mudar**). A
revisão humana por urgência vale mesmo com confiança 1,0. O CSV rotulado tem a coluna `urgent` (11 linhas = 1); só duas
delas contêm "urgente", ambas como "ajuda urgente".

Princípio: **na dúvida, revisão**. Termo de saúde ambíguo é aceito como urgente; a palavra "urgente" sozinha não é sinal
de risco.

# 3. Escopo
## 3.1 Dentro
- `data/urgency_terms.json` — remover o termo solto `urgente`; acrescentar termos de saúde (passo 1)
- `tests/classification/test_urgency.py` — casos novos (passo 3)
- `src/triage/classification/urgency.py` — **só** se o léxico não bastar para um caso obrigatório do passo 3 (justificar no resumo)
- `README.md` e `notebooks/evidence.ipynb` — **só** os números medidos, e **só** se a medição do passo 4 mudar

## 3.2 Fora
- `triage_decision`, limiares e ordem dos gatilhos; `data/labeled/` e o modelo treinado.
- Mensagem mostrada ao cidadão em caso de urgência (outra plan).
- Qualquer lista de telefones de emergência.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[02.02-confianca-e-revisao-humana]] | contrato de `is_urgent`, falha segura e ordem dos gatilhos |
| Spec fixa | [[05.01-validacao-e-entrega]] | números medidos que podem mudar |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | limiares de clean code |
| Skill | `test-unitario` | testes de tabela |
| Código | `src/triage/classification/urgency.py`, `data/urgency_terms.json` | o que será alterado |
| Código | `tests/classification/test_urgency.py`, `tests/classification/test_dataset.py` | testes existentes |
| Dados | `data/labeled/requests_labeled.csv` | coluna `urgent` e texto realista para falso positivo |

# 5. Instruções de execução
1. [dirigido] **Léxico.** Em `data/urgency_terms.json`, no mesmo formato (termos sem acento, minúsculos): remover
   `urgente`; manter `ajuda urgente`; acrescentar, com as variantes de singular e plural que fizerem sentido, termos para:
   dor no peito (`dor no peito`, `dores no peito`, `dor forte no peito`, `aperto no peito`), falta de ar e dificuldade
   para respirar, desmaio, convulsão, hemorragia, queimadura grave, intoxicação, engasgo, parada cardíaca, mal súbito,
   `urgencia medica`, `pronto socorro`, `ambulancia`, `samu`. O casamento é por palavra inteira: liste as flexões.
2. [dirigido] **Sem regressão de falso positivo.** Nenhum dos 180 textos do CSV com `urgent=0` pode virar urgente, e
   todos com `urgent=1` continuam urgentes. Se um termo novo casar um texto `urgent=0`, remova ou especialize o termo e
   registre o motivo no resumo.
3. [dirigido] **Testes.** Em `test_urgency.py`, tabela com no mínimo estes casos (os demais ficam a seu critério):

   | Texto | `is_urgent` |
   |---|---|
   | `dores no peito e falta de ar` | `True` |
   | `meu pai teve um desmaio e precisa de ambulância` | `True` |
   | `preciso de ajuda urgente` | `True` |
   | `Quero renovar a CNH, é urgente` | `False` |
   | `Quero abrir uma reclamação. Urgente obrigado.` | `False` |
   | `preciso do IPTU com urgência de entrega` | `False` |
   | `como tirar a segunda via do RG` | `False` |

   Mais um teste que percorre o CSV rotulado e confere `is_urgent(texto) == bool(urgent)` para as 180 linhas (ou
   documenta, linha a linha no teste, as exceções que já existiam antes desta plan).
4. [dirigido] **Medição.** Rodar a avaliação do conjunto `split=test` como o notebook `notebooks/evidence.ipynb` a
   executa (`triage.evaluation`, modelo treinado em memória). Se **algum** dos números do README mudar (acurácia, taxa de
   revisão, cobertura, acurácia entre os respondidos), atualizar README e notebook (reexecutar o notebook com saídas
   salvas, sem PII nem chave) e dizer no resumo o antes e o depois. Se nada mudar, não tocar nesses dois arquivos.
5. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Os sete casos da tabela do passo 3 passam.
- [ ] `urgente` não está mais no léxico como termo solto; `ajuda urgente` continua.
- [ ] Para as 180 linhas do CSV, `is_urgent` coincide com a coluna `urgent`.
- [ ] Léxico ausente ou inválido continua devolvendo `True`.
- [ ] README e notebook coerentes com a medição (atualizados se e só se os números mudaram).
- [ ] Ambiente e worktree limpos; testes do escopo verdes; `ruff` e validador sem violação nos arquivos alterados.
- [ ] Nenhuma chave e nenhum dado pessoal no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/classification -q` → verde.
- `python -m ruff check src/triage/classification tests/classification` → sem erro.
- `validate.py` do `padrao-python` nos arquivos `.py` alterados → sem achado.
- Sondagem do revisor com frases novas de saúde e de cortesia, e `is_urgent` sobre o CSV.
- **Gate:** `nenhum — coberto por teste de tabela e pela checagem do CSV`.

# 8. Destino da síntese
**Destino:** `specs/02.02-confianca-e-revisao-humana.md`

Levar, **substituindo** a §2.5: o léxico cobre também emergência de saúde; "urgente" sozinho não é gatilho (cortesia),
só expressões de risco; a regra "na dúvida, revisão" e a coerência com a coluna `urgent` do CSV rotulado.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->
