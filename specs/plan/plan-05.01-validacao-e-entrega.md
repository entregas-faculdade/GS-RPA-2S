---
tipo: "plan"
familia: "05"
item: "R05.1"
titulo: "Validar com amostra rotulada, documentar evidências e preparar a entrega"
dominio: "Validação e entrega"
status: "🔴 A executar"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
