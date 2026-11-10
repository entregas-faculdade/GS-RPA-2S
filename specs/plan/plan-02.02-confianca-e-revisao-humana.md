---
tipo: "plan"
familia: "02"
item: "R02.2"
titulo: "Calcular a confiança e decidir quando enviar o pedido à revisão humana"
dominio: "Classificação"
status: "🟡 Em execução"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[003-seguranca-sem-autenticacao]]", "[[00-fundacao-tecnologica]]"]
depende_de: "plan-02.01-dataset-e-classificador"
destino_sintese: "specs/02.02-confianca-e-revisao-humana.md"
---

# 1. Objetivo
`triage_decision(request_text, classification)` devolve `Decision(action, category, confidence, reason)` onde
`action` é `auto_answer` ou `human_review`, e `reason` é um motivo do conjunto fechado de §5.1.

# 2. Contexto
A governança do projeto: o robô só responde sozinho quando é seguro. Cinco gatilhos de revisão (discutidos e
aprovados pelo usuário) mais o link indisponível, que vem da plan 03.01:

| `reason` | Gatilho |
|---|---|
| `low_confidence` | probabilidade da melhor categoria abaixo de `CONFIDENCE_MIN` |
| `ambiguous` | diferença entre as duas melhores abaixo de `AMBIGUITY_MARGIN` |
| `urgent` | texto contém termo de urgência/sensibilidade (sempre revisão, mesmo com confiança alta) |
| `out_of_catalog` | melhor categoria é `other` |
| `invalid_input` | pedido rejeitado na ingestão |
| `link_unavailable` | link do serviço fora do ar (definido em 03.01; esta plan só declara o valor) |

# 3. Escopo
## 3.1 Dentro
- `src/triage/classification/decision.py` — `Decision`, `ReviewReason` (enum) e `triage_decision`
- `src/triage/classification/urgency.py` — `is_urgent(text)` lendo o léxico de `data/urgency_terms.json`
- `data/urgency_terms.json` — lista de termos/expressões (violência, risco de vida, emergência médica, ameaça, suicídio, desastre) em português
- `src/triage/config.py` — constantes `CONFIDENCE_MIN` (0.60) e `AMBIGUITY_MARGIN` (0.15), sobrescrevíveis por variável de ambiente
- `tests/classification/test_decision.py`, `tests/classification/test_urgency.py`

## 3.2 Fora
- Gravar na fila (plan 04.01/04.03) e responder ao cidadão (família 03).
- Calibração estatística do modelo; os limiares são parâmetros ajustados na validação (plan 05.01).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[003-seguranca-sem-autenticacao]] | revisão humana como controle |
| Spec fixa | [[00-fundacao-tecnologica]] | fluxo e fila de revisão |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `src/triage/classification/classifier.py` | saída (`Classification`) a ser consumida |

# 5. Instruções de execução
1. [dirigido] `ReviewReason` como `Enum` com exatamente: `low_confidence`, `ambiguous`, `urgent`, `out_of_catalog`, `invalid_input`, `link_unavailable`.
2. [dirigido] `is_urgent`: normaliza o texto e procura termos do JSON (match por palavra/expressão inteira); lista carregada uma vez; arquivo ausente ou JSON inválido → log `ERROR` e tratar **como urgente** (falha segura: na dúvida, humano).
3. [dirigido] `triage_decision`: ordem de avaliação fixa — (a) urgência, (b) `out_of_catalog`, (c) confiança baixa, (d) ambiguidade; a primeira que dispara define o `reason`. Se nenhuma dispara → `auto_answer` com `reason=None`. Quando a fonte é `rule`, a confiança considerada é `max(prob_modelo, RULE_CONFIDENCE_FLOOR)` com `RULE_CONFIDENCE_FLOOR = 0.90` (constante nomeada), para que um atalho inequívoco não seja barrado por um modelo tímido.
4. [dirigido] Constantes de limiar lidas de `load_settings()`/`config.py`, nunca números soltos.
5. [dirigido] Testes de tabela: um caso por `reason`; caso `auto_answer`; ordem de precedência (urgente com confiança alta → `urgent`); regra com modelo tímido → `auto_answer`; limiar exato (borda); léxico ausente → urgente.
6. Rodar `python -m pytest tests/classification -q` e `ruff`.

# 6. Critérios de aceite
- [ ] Cada valor de `ReviewReason` produzido pelo `triage_decision` tem teste (`link_unavailable` só é declarado).
- [ ] Texto urgente vai para revisão mesmo com confiança 1.0.
- [ ] Léxico ausente ou inválido resulta em revisão, não em resposta automática.
- [ ] Limiares vêm de configuração (sem literal numérico solto).
- [ ] Ordem de avaliação documentada em docstring e coberta por teste.
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/classification -q` → verde.
- `python -m ruff check src/triage/classification tests/classification` → sem erro.
- Leitura de `src/triage/classification/decision.py` → ordem (a)–(d) e ausência de número solto.
- Leitura de `data/urgency_terms.json` → termos coerentes, sem dado pessoal.
- **Gate:** `nenhum — coberto por teste de tabela`.

# 8. Destino da síntese
**Destino:** `specs/02.02-confianca-e-revisao-humana.md`

Levar: tabela de `reason` e seus gatilhos; ordem de precedência; valores padrão e como sobrescrever `CONFIDENCE_MIN`,
`AMBIGUITY_MARGIN`, `RULE_CONFIDENCE_FLOOR`; regra de falha segura do léxico; observação de que os limiares são
ajustáveis e a justificativa do valor final vem da validação (plan 05.01).

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
