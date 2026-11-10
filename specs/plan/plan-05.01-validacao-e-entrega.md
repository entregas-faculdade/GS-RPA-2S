---
tipo: "plan"
familia: "05"
item: "R05.1"
titulo: "Validar com amostra rotulada, documentar evidências e preparar a entrega"
dominio: "Validação e entrega"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[00-fundacao-tecnologica]]", "[[005-llm-apenas-reformula-resposta]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "plan-04.02-interface-streamlit"
destino_sintese: "specs/05.01-validacao-e-entrega.md"
---

# 1. Objetivo
O repositório contém tudo que o enunciado exige como entrega: notebook de evidências com métricas medidas sobre o
conjunto rotulado, pelo menos um caso de falha demonstrado, `README.md` completo, quadro de temas e o parágrafo de
proteção de dados, ética e ODS.

# 2. Contexto
Pesos do barema: temas 30%, ponta a ponta 25%, resiliência 20%, **evidências 15%**, dados/ética/organização 10%. O
enunciado pede "resultado medido (acertos e erros em uma amostra)", "análise dos erros e limites" e honestidade sobre
tamanho de amostra. O conjunto de teste é o `split=test` de `data/labeled/requests_labeled.csv` (plan 02.01), nunca
usado no treino. Os limiares da plan 02.02 podem ser **ajustados aqui**, justificados pelo resultado medido.

# 3. Escopo
## 3.1 Dentro
- `notebooks/evidence.ipynb` — executável do início ao fim; usa os pacotes de `src/triage` (não reimplementa lógica)
- `src/triage/evaluation/metrics.py` — acurácia, precisão/recall/F1 por classe, matriz de confusão, taxa de revisão humana, cobertura automática (o notebook importa daqui; ver §5.1)
- `src/triage/evaluation/__init__.py`
- `tests/evaluation/` — testes de `metrics.py` com dados pequenos
- `README.md` — conteúdo exigido por §5.5
- `docs/quadro-de-temas.md` — tabela dos temas (ou seção do README, se preferir)
- `data/labeled/README.md` — ajustar, se necessário, a descrição do conjunto
- ajuste de `CONFIDENCE_MIN`/`AMBIGUITY_MARGIN` em `src/triage/config.py`, **somente** se justificado pela medição

## 3.2 Fora
- Mudança de arquitetura, nova funcionalidade ou novo pacote além de `evaluation`.
- Alterar o conjunto de teste para melhorar a nota (proibido; o `split` é fixo).
- Deploy, CI/CD, qualquer dado pessoal real.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Enunciado | `GS2026_2_Enunciado_Final_RPA_IA(2).pdf` §3, §5, §6 | entregáveis e barema |
| Spec fixa | [[00-fundacao-tecnologica]] | fluxo e temas |
| ADR | [[005-llm-apenas-reformula-resposta]] | LLM desligado na medição de acerto |
| ADR | [[003-seguranca-sem-autenticacao]] | base do parágrafo de proteção de dados |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `src/triage/pipeline/`, `src/triage/classification/`, `data/labeled/requests_labeled.csv` | o que será medido |

# 5. Instruções de execução
1. [dirigido] `metrics.py`: funções puras sobre listas de rótulos reais/previstos; testadas com exemplos de resultado conhecido. O notebook só orquestra e exibe.
2. [dirigido] Notebook, seções nesta ordem: (a) **Execução ponta a ponta** — roda o pipeline sobre `data/samples` e mostra o relatório de execução; (b) **Métricas** — classificação sobre `split=test` **sem LLM**: tamanho da amostra, acurácia, P/R/F1 por classe, matriz de confusão, taxa de pedidos enviados à revisão e cobertura automática; (c) **Análise de erros** — tabela com os pedidos errados (texto anonimizado), causa provável e agrupamento; (d) **Casos de falha tratados** — demonstrar pelo menos: arquivo ausente, JSON inválido, link fora do ar (simulado), resposta vazia do LLM (simulada) e modelo ausente, cada um com o log e o caminho seguro; (e) **Limites da solução** — escrever com honestidade: amostra pequena e sintética, sem nomes/endereços anonimizados, catálogo estático, ambiguidade, sem multi-turno.
3. [dirigido] Se os limiares da 02.02 forem alterados, mostrar no notebook o antes/depois (taxa de revisão × erro automático) e registrar o motivo; senão, declarar que se mantiveram.
4. [dirigido] **Executar o notebook** do início ao fim (`jupyter nbconvert --to notebook --execute`) para que as saídas fiquem salvas e versionadas; nenhuma saída pode conter PII ou chave.
5. [dirigido] `README.md` com: integrantes (placeholder `<preencher>`), descrição do problema e do público (recorte A), fluxo em 3 etapas com o diagrama de [[00-fundacao-tecnologica]], **como instalar e rodar** (`pip install -r requirements.txt`, `python run.py`, `streamlit run app.py`, notebook), **como configurar chaves** (`.env.example`, LLM opcional e desligado por padrão), estrutura de pastas, **quadro de temas** (Automação/RPA, NLP, Regras/regex, Anonimização de PII — qual é, onde entra no fluxo e o que resolve, mínimo 3), resultados resumidos com ponteiro ao notebook, e o parágrafo curto de **proteção de dados, ética e ODS** (LGPD e anonimização; revisão humana e limites do robô; ODS 16 e ODS 10 como candidatos, a confirmar com o grupo).
6. [dirigido] Conferir o checklist do enunciado §5 e §6 e anotar no resumo da execução o que cobre cada critério do barema.

# 6. Critérios de aceite
- [ ] O notebook executa do início ao fim em ambiente limpo e as saídas estão salvas.
- [ ] Métricas reportadas com **tamanho da amostra** e por classe; matriz de confusão presente.
- [ ] Pelo menos 3 casos de falha demonstrados com log e caminho seguro (arquivo ausente, JSON inválido, link fora do ar ao menos).
- [ ] Análise de erros e seção de limites escritas, sem afirmação não medida.
- [ ] README permite a um avaliador instalar e rodar sem ajuda (testar seguindo-o passo a passo).
- [ ] Quadro de temas com ≥ 3 temas, cada um com função real no fluxo.
- [ ] Nenhuma chave, PII real ou `.env` no repositório; `git status` limpo ao fim.
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `completa — entrega final; esta plan fecha o produto`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest -q` (suíte inteira) e `python -m ruff check .` → verdes.
- `jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output <saída temporária>` → conclui sem erro.
- Conferência cruzada: os números do notebook batem com `python -c` independente sobre o CSV de teste.
- Seguir o README em um diretório temporário com ambiente virtual novo → `python run.py --input data/samples` funciona.
- `grep -rn -i "api_key\|secret\|password" --include=* .` fora de `.env.example`/testes → nada com valor real.
- Verificação visual da interface: `streamlit run app.py`; encerrar o processo; `git status` limpo.
- **Gate:** `nenhum — a verificação é a execução e a conferência cruzada`.

# 8. Destino da síntese
**Destino:** `specs/05.01-validacao-e-entrega.md`

Levar: método de validação (conjunto, `split`, métricas, sem LLM); **resultados finais medidos** e os limiares
adotados com a justificativa; os casos de falha demonstrados; os limites declarados; a estrutura de entrega (README,
notebook, quadro de temas). Se os limiares mudaram, atualizar também `specs/02.02-confianca-e-revisao-humana.md`.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído com pendências

**O que foi feito**
- `src/triage/evaluation/metrics.py` — funções puras: `accuracy`, `confusion_matrix`, `per_class_metrics` (precisão/recall/F1/suporte), `review_rate`, `automatic_coverage`, `automatic_accuracy`; entrada inconsistente (tamanhos, amostra vazia, rótulo fora das classes) levanta `ValueError`. `__init__.py` reexporta.
- `tests/evaluation/test_metrics.py` — 16 testes com amostras de resultado conhecido (valores calculados à mão), incluindo classe sem previsão/sem exemplo e entradas inválidas.
- `notebooks/evidence.ipynb` — seções na ordem da §5.2: (1) ponta a ponta sobre `data/samples` (+ segunda execução provando idempotência), (2) métricas sobre `split=test` sem LLM, (3) análise de erros, (4) cinco casos de falha, (5) limites. Executado com `jupyter nbconvert --execute --inplace`; 0 células sem execução, 0 erros; o notebook treina o modelo em memória e remove `output/notebook-evidence` ao fim.
- Limiares: **mantidos** (0,60 / 0,15); motivo registrado no notebook (0 erro entre os 31 respondidos sozinhos; ajustar olhando o próprio teste o contaminaria). `config.py` não foi tocado.
- `README.md` — integrantes `<preencher>`, problema e público, diagrama da fundação, instalar/rodar, chaves (`.env.example`), estrutura de pastas, quadro de temas, resultados com ponteiro ao notebook, parágrafo de proteção de dados, ética e ODS (16 e 10 "a confirmar com o grupo").
- `docs/quadro-de-temas.md` — 4 temas (Automação/RPA, NLP, Regras/regex, Anonimização de PII) com onde entram, o que resolvem e a justificativa da combinação.
- `data/labeled/README.md` — não alterado: a descrição (180 pedidos, 14 train/6 test por categoria) confere com o arquivo.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/evaluation/__init__.py` | criado | reexporta as métricas |
| `src/triage/evaluation/metrics.py` | criado | métricas puras |
| `tests/evaluation/test_metrics.py` | criado | 16 testes das métricas |
| `notebooks/evidence.ipynb` | criado | notebook de evidências, executado, com saídas salvas |
| `README.md` | criado | documentação de entrega |
| `docs/quadro-de-temas.md` | criado | quadro de temas |
| `specs/plan/plan-05.01-validacao-e-entrega.md` | alterado | este resumo e `status: "🟠 Em revisão"` |

**Verificações executadas**
- `python -m pytest tests/evaluation -q` → 16 passed.
- `python -m pytest -q` (suíte inteira, por ser a plan de fechamento; nível `completa` da §7) → 376 passed.
- `python -m ruff check src/triage/evaluation tests/evaluation notebooks` → All checks passed.
- `python -m ruff check run.py src tests` → **9 erros em 8 arquivos que esta plan não tocou** (ver Achados); nos arquivos criados: 0.
- `padrao-python/scripts/validate.py src/triage/evaluation` e `tests/evaluation` → `findings: []` (após anotar `-> None` nos testes).
- `jupyter nbconvert --to notebook --execute --inplace notebooks/evidence.ipynb` → concluiu; 1ª tentativa falhou por `ZMQError: timed out` ao subir o kernel (infraestrutura do Jupyter, nada do notebook) e a repetição passou.
- Conferência cruzada independente (script à parte sobre o CSV, modelo treinado com `scripts/train_model.py`): 54 pedidos, acurácia 0,8148, revisão 0,4259, 31 respondidos sozinhos com acerto 1,0, motivos `low_confidence` 16 / `out_of_catalog` 6 / `urgent` 1 → idênticos aos do notebook.
- README seguido em cópia do repositório (sem `.git` e sem `output/`) com venv nova: `pip install -r requirements.txt` → `python scripts/train_model.py` → `python run.py --input data/samples --output out` → exit 0, `answered 4 / queued_for_review 4 / rejected 7`.
- `grep -rn -i "api_key|secret|password"` em README, docs, notebook, `evaluation` e testes → só os nomes de variável `LLM_API_KEY` no README e a palavra "Secretaria" na saída do notebook; nenhum valor. Notebook sem caminho absoluto nem nome de usuário (grep em `Igor`, `Users`: 0).

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`, limpa).

**Ambiente após a verificação:** a tarefa criou `output/` (modelo treinado por `scripts/train_model.py` para a conferência cruzada; `output/notebook-evidence` do notebook), a cópia + venv do teste do README no scratchpad, e `.pytest_cache`/`.ruff_cache`. Tudo removido ao fim (`output/` não existia antes). Nenhum servidor, contêiner ou banco largado. `snapshot` da skill `code-limpeza-ambiente`: não rodado (nada subiu em segundo plano; confirmei à mão). A verificação visual de `streamlit run app.py` (§7) **não foi feita**: é do revisor, e o Streamlit não foi iniciado.

**Critérios de aceite**
- [x] Notebook executa do início ao fim e as saídas estão salvas — evidência: `nbconvert --execute` sem erro, 0 células sem execução. Ressalva: o kernel `python3` desta máquina é o 3.11.9 (`language_info` do notebook), não o 3.14 do projeto; deu os mesmos números.
- [x] Métricas com tamanho da amostra (54), por classe, matriz de confusão — evidência: células 7–9 do notebook.
- [x] ≥ 3 casos de falha com log e caminho seguro — evidência: seção 4 (pasta ausente → exit 2; JSON inválido → `invalid_input`; link fora do ar → `link_unavailable`; resposta vazia do LLM → template + `llm_invalid_response`; modelo ausente → revisão).
- [x] Análise de erros e limites sem afirmação não medida — evidência: seções 3 e 5; a "causa provável" está rotulada como hipótese e apoiada na coluna "fora do vocabulário", medida.
- [x] README permite rodar sem ajuda — evidência: teste em venv nova acima. Ressalva: segui os passos de instalação e do robô; o `streamlit run app.py` não foi aberto.
- [x] Quadro de temas com 4 temas, cada um com função no fluxo — `docs/quadro-de-temas.md`.
- [x] Nenhuma chave, PII real ou `.env` no diff — evidência: greps acima; `git status` só com os arquivos da §3.1 e a plan.
- [x] Ambiente e worktree limpos — evidência: `output/` e caches removidos; `git status --short` lista só os 5 itens novos e a plan.
- [ ] Testes do escopo verdes; `ruff` sem violação — motivo: testes e `ruff` dos arquivos alterados verdes, mas `python -m ruff check run.py src tests` falha em arquivos fora do escopo (9 erros; ver Achados).
- [x] Nenhum dado pessoal real, chave ou `.env` no diff.

**Decisões e suposições**
- Limiares mantidos e sem tabela antes/depois: não rodei varredura de limiares sobre o `split=test` para não ajustar no próprio teste; se o revisor quiser a varredura, deve ser sobre validação cruzada do treino (fora desta plan).
- O notebook treina o modelo em memória (`train`) em vez de depender de `output/models/classifier.joblib`, para rodar em ambiente limpo sem tocar `output/`. O README manda treinar o modelo antes do robô porque `run.py` o lê do disco.
- Caso "link fora do ar": usei o `check_link` real contra `http://127.0.0.1:9/` (retorna `ConnectTimeout`, com retry real) em vez de um verificador falso; "arquivo ausente" foi a pasta de entrada inexistente via `run.main` (exit 2), que é o caso de arquivo ausente que o código trata.
- A seção 1 verifica os links do catálogo na rede de verdade; sem rede os pedidos vão à revisão (dito no notebook). As saídas salvas são de uma execução com rede (4 links "no ar").
- Os 5 grupos de causa da análise de erros são interpretação minha; marcada como hipótese no notebook.
- Os números do README (81,5%, 42,6%, 57,4%, 100% de 31) são texto fixo copiado da execução; se o modelo ou o CSV mudarem, README e notebook precisam ser atualizados juntos.
- Python: o README diz "verificado com 3.14", conforme `00-contexto` §8.

**Achados fora do escopo (não corrigidos)**
- `python -m ruff check run.py src tests` falha em 9 pontos pré-existentes: `src/triage/automation/allowlist.py:18` e `src/triage/classification/urgency.py:16` (UP033), `src/triage/ingestion/sanitizer.py:3` (I001), `src/triage/storage/repository.py:38` (UP017), `tests/classification/test_decision.py:3`, `tests/classification/test_model.py:3`, `tests/ingestion/test_sanitizer.py:3`, `tests/storage/test_repository.py:1` (I001) e `tests/storage/test_repository.py:158` (SIM117). `ruff check .` acusa 14 (inclui `scripts/`/outros). Isso impede o "ruff verde" do §7 da plan e do `00-contexto`; a correção toca código de plans anteriores.
- `.env.example` não lista `CONFIDENCE_MIN` e `AMBIGUITY_MARGIN`, que `config.py` lê; o README os documenta como opcionais.
- Os `specs/02.02` e `specs/05.01` ainda dependem da síntese do revisor; como os limiares não mudaram, `02.02` não precisa de atualização.

**Pendências / riscos**
- Os 9 erros de `ruff` acima precisam de decisão do revisor (corrigir em demanda própria ou aceitar).
- Verificação visual do Streamlit não feita (item de §7, uso do revisor).
- O kernel do notebook foi o Python 3.11.9; reexecutar em 3.14 (versão do projeto) pode alterar saídas se houver diferença de biblioteca. Os números conferiram com o script rodado no 3.14.
- A amostra é pequena e sintética (54 pedidos); o README e o notebook dizem isso, mas a nota de "evidências" depende de o grupo aceitar essa limitação.
- Placeholders `<preencher>` (integrantes) e ODS "a confirmar com o grupo" continuam abertos por instrução da plan.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-10 — 🟢 Aprovado

**Verificado (nível completa, como a §7 declara), com saída real:** `git status`/`git diff` (só `README.md`, `docs/quadro-de-temas.md`, `notebooks/evidence.ipynb`, `src/triage/evaluation/` e `tests/evaluation/`; `config.py` e `data/labeled/README.md` intactos, coerente com limiares mantidos) · leitura integral de `metrics.py`, do README, do quadro de temas e das células de texto do notebook · `python -m pytest -q` (suíte inteira) → 376 passed · `python -m ruff check --no-cache src/triage/evaluation tests/evaluation notebooks` → All checks passed · `python -m ruff check .` → 14 erros, **todos fora do escopo** (`.githooks/verify_commit.py` e 8 arquivos das plans 01 a 04, já nos itens 1 e 14 do `00-backlog`), nenhum em arquivo desta plan · `padrao-python/scripts/validate.py` em `src/triage/evaluation` e `tests/evaluation` → `findings: []` · **notebook:** `jupyter nbconvert --execute` para arquivo temporário concluiu sem erro e reproduziu as saídas do versionado; versionado com 16 células de código, todas executadas e 0 erros; busca por nome de usuário, caminho absoluto, chave, CPF e e-mail nas saídas → 0 · **conferência cruzada independente** (script à parte sobre o `split=test`, modelo treinado por `scripts/train_model.py`): 54 pedidos, acurácia 0,8148, revisão 0,4259, 31 respondidos sozinhos com 31 acertos, motivos `low_confidence` 16 / `out_of_catalog` 6 / `urgent` 1 → idênticos ao notebook e ao README · **README em ambiente novo:** cópia do repositório, venv Python 3.14.0 novo, `pip install -r requirements-dev.txt` sem erro, `python scripts/train_model.py`, `python run.py --input data/samples --output out` → código 0 com `answered 4 / queued_for_review 4 / rejected 7`, segunda execução com `skipped_duplicate 15`, relatórios gerados, e `pytest -q` na cópia → 376 passed · `streamlit run app.py` na cópia → `/_stcore/health` 200 e `/` 200, processo encerrado e nenhum restou · textos de análise de erros e de limites escritos só com o que foi medido, a causa dos erros marcada como hipótese, e o aviso de amostra pequena e sintética no README e no notebook · limiares mantidos com motivo registrado (nenhum erro entre os respondidos sozinhos; ajustar olhando o próprio teste o contaminaria), então `specs/02.02` não precisa mudar · removi `output/`, caches e `__pycache__` do repositório.

**Limites da verificação:** a conferência visual da interface em navegador real não foi feita (só saúde do servidor e o `AppTest` da 04.02); o kernel do notebook versionado é o Python 3.11.9, e o projeto verifica com 3.14, mas os números conferem no 3.14.

**Decisões do executor aceitas:** notebook treina o modelo em memória para rodar em ambiente limpo; caso "arquivo ausente" demonstrado pela pasta de entrada inexistente; limiares mantidos sem tabela antes/depois, para não ajustar no conjunto de teste; placeholders `<preencher>` e ODS "a confirmar com o grupo" mantidos por instrução da plan.

**Achados:** nenhum que reprove.
