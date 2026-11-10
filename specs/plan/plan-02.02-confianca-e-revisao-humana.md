---
tipo: "plan"
familia: "02"
item: "R02.2"
titulo: "Calcular a confiança e decidir quando enviar o pedido à revisão humana"
dominio: "Classificação"
status: "🟢 Aprovada"
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

## Resumo da execução — 2026-11-09

**Resultado:** Concluído com pendências

**O que foi feito**
- `ReviewReason` (Enum com os seis valores), `Decision` e `triage_decision` — `src/triage/classification/decision.py`. Ordem (a) urgência → (b) `other` → (c) confiança → (d) ambiguidade, documentada na docstring de `triage_decision`; fonte `rule` usa `max(prob, RULE_CONFIDENCE_FLOOR=0.90)`.
- `is_urgent` — `src/triage/classification/urgency.py`: normaliza com `fold`, casa palavra/expressão inteira (``), léxico compilado uma vez (`lru_cache`); arquivo ausente, JSON inválido, não-lista ou vazio → log `ERROR` e `True` (falha segura).
- Léxico — `data/urgency_terms.json` (38 termos em português, sem dado pessoal).
- Limiares — `src/triage/config.py`: `CONFIDENCE_MIN=0.60`, `AMBIGUITY_MARGIN=0.15`, campos `confidence_min`/`ambiguity_margin` em `Settings` (com padrão) lidos das variáveis de ambiente de mesmo nome; valor não numérico ou fora de [0, 1] volta ao padrão com `WARNING`.
- Exports em `src/triage/classification/__init__.py`.
- Testes: `tests/classification/test_decision.py` e `test_urgency.py`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/classification/decision.py` | criado | `ReviewReason`, `Decision`, `triage_decision` |
| `src/triage/classification/urgency.py` | criado | `is_urgent` com léxico e falha segura |
| `data/urgency_terms.json` | criado | léxico de urgência/sensibilidade |
| `src/triage/config.py` | alterado | constantes e campos de limiar, leitura do ambiente |
| `src/triage/classification/__init__.py` | alterado | exporta `Decision`, `ReviewReason`, `triage_decision`, `is_urgent` |
| `tests/classification/test_decision.py` | criado | tabela por `reason`, precedência, regra tímida, bordas, léxico ausente, config |
| `tests/classification/test_urgency.py` | criado | léxico real, palavra inteira, acentos, falha segura, carga única |

**Verificações executadas**
- `python -m pytest tests/classification tests/test_config.py tests/test_logging_setup.py -q` → 105 passed (1 falha inicial por "ameaçou" fora do léxico; corrigida no léxico; reexecução de `tests/classification` → 98 passed).
- `python -m ruff check src/triage/classification tests/classification src/triage/config.py` → All checks passed.
- `validate.py` de `padrao-python` em decision.py, urgency.py, config.py e nos dois testes → 0 achados.

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** nada criado (só pytest/ruff de curta duração; `snapshot` da skill `code-limpeza-ambiente` não rodado, confirmado à mão: nenhum processo, servidor ou arquivo temporário iniciado por mim; `git status` mostra só o escopo).

**Critérios de aceite**
- [x] Cada `ReviewReason` produzido tem teste — `test_decision.py::test_each_trigger_sends_the_request_to_human_review` (urgent, out_of_catalog, low_confidence, ambiguous); `invalid_input`/`link_unavailable` só declarados (`test_review_reason_values_are_the_closed_set`).
- [x] Urgente com confiança 1.0 → revisão — `test_urgent_text_goes_to_review_even_with_full_confidence`.
- [x] Léxico ausente/inválido → revisão — `test_missing_lexicon_sends_to_review`, `test_invalid_lexicon_is_urgent`, `test_missing_lexicon_is_urgent_and_logs_error`.
- [x] Limiares vêm de configuração — `decision.py` lê `settings.confidence_min`/`ambiguity_margin`; único literal é a constante nomeada `RULE_CONFIDENCE_FLOOR`.
- [x] Ordem documentada em docstring e testada — `decision.py` (`triage_decision`), `test_precedence_...`.
- [x] Ambiente e worktree limpos — ver acima.
- [x] Testes verdes; ruff e validador sem violação.
- [x] Sem dado pessoal, chave ou `.env` no diff.

**Decisões e suposições**
- `triage_decision(request_text, classification, settings=None)`: terceiro parâmetro opcional para injetar limiares (padrão `load_settings()`); a assinatura da plan continua válida.
- Ambiguidade = confiança considerada da categoria escolhida menos a maior probabilidade entre as **demais** categorias. Com fonte `rule`, a confiança já está elevada pelo piso, então um atalho inequívoco não cai em `ambiguous` por modelo tímido.
- `confidence` da `Decision` é a confiança considerada (com piso, se regra).
- `RULE_CONFIDENCE_FLOOR` fica como constante nomeada em `decision.py`, **não** sobrescrevível por ambiente (a plan só pede isso para `CONFIDENCE_MIN` e `AMBIGUITY_MARGIN`); a §8 menciona "como sobrescrever" o piso — o revisor decide se vira configurável.
- Limiares inválidos no ambiente voltam ao padrão com `WARNING` (falha previsível não derruba a execução).
- Caminho do léxico relativo ao diretório de trabalho (`data/urgency_terms.json`), como `DEFAULT_MODEL_PATH`; fora da raiz do repositório, cai na falha segura (revisão).
- Termos do léxico foram escritos já sem acento e casam por palavra inteira; "arma", "fome" e "avc" são amplos e podem gerar revisão extra (falso positivo aceitável: na dúvida, humano).
- Alterei `classification/__init__.py` (fora da lista literal de §3.1) só para exportar a API nova, no padrão do pacote.
- `.env.example` **não** foi tocado (fora do escopo), logo as duas variáveis novas não estão documentadas lá.

**Achados fora do escopo (não corrigidos)**
- `.env.example` — não lista `CONFIDENCE_MIN` e `AMBIGUITY_MARGIN`.
- `ruff format --check` acusa 12 arquivos do pacote (inclusive anteriores a esta tarefa) — não é comando de verificação do repositório; não formatei.

**Pendências / riscos**
- `snapshot`/`diff` da skill `code-limpeza-ambiente` não executados (ambiente confirmado à mão).
- Valores finais de limiar dependem da validação (plan 05.01).

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-09 — 🟢 Aprovado

**Verificado (nível escopada), com saída real:** `git status`/`git diff` (só `decision.py`, `urgency.py`, `data/urgency_terms.json`, `config.py`, os dois testes e o `__init__.py` do pacote, que só ganhou exports; nada fora do escopo, nada faltando) · leitura integral de `decision.py`, `urgency.py`, do léxico e do diff de `config.py` · `python -m pytest tests/classification tests/test_config.py tests/test_logging_setup.py -q` → 106 passed · `python -m ruff check --no-cache src/triage/classification tests/classification src/triage/config.py` → All checks passed · `padrao-python/scripts/validate.py` nos cinco arquivos alterados → `findings: []` em todos · sondagem: confiança 0.7 com folga → `auto_answer`; 0.60 contra 0.45 → `ambiguous`; 0.59 → `low_confidence`; confiança 0.3 com fonte `rule` → `auto_answer` (piso 0.90); texto com "fome" e confiança 1.0 → `urgent`; rótulo `other` → `out_of_catalog`; `CONFIDENCE_MIN=abc` → padrão 0.6 com `WARNING`, `AMBIGUITY_MARGIN=0.5` → 0.5; "ele me ameaçou" → urgente, "alarmante" → não (palavra inteira) · léxico ausente ou inválido → urgente com log `ERROR` (testes e leitura de `urgency.py`) · ordem (a)–(d) na docstring de `triage_decision` e em `test_precedence_...` · único literal numérico solto é `RULE_CONFIDENCE_FLOOR`, constante nomeada que a plan pede · léxico: 38 termos em português, sem dado pessoal · sem `TODO`/`FIXME`/skip/`print` nem citação a plan · caches e `__pycache__` removidos.

**Decisões do executor aceitas:** `triage_decision(request_text, classification, settings=None)` com `settings` opcional (compatível com a assinatura da plan); ambiguidade medida contra a melhor das demais categorias, com a confiança já elevada pelo piso quando a fonte é regra; `RULE_CONFIDENCE_FLOOR` fica constante, sem variável de ambiente (a §5 só pede isso para `CONFIDENCE_MIN` e `AMBIGUITY_MARGIN`; a síntese registra assim); limiar inválido volta ao padrão com aviso. O toque em `classification/__init__.py` é só export, no padrão do pacote.

**Achados:** nenhum que reprove. A ausência das duas variáveis no `.env.example` foi para o `00-backlog`.
