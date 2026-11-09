---
tipo: "plan"
familia: "01"
item: "R01.1"
titulo: "Montar a estrutura do projeto, dependências e ponto de entrada mínimo"
dominio: "Núcleo do robô"
status: "🟡 Em execução"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[00-fundacao-tecnologica]]", "[[001-stack-principal]]", "[[004-infra-execucao-local]]"]
depende_de: ""
destino_sintese: "arquitetura/01.01-estrutura-do-projeto.md"
---

# 1. Objetivo
Ao final, `python run.py --help` e `python -m pytest -q` funcionam em um clone limpo, com a árvore de pacotes
`src/triage/` pronta, dependências fixadas e `.env.example` sem valores.

# 2. Contexto
Repositório novo, só com `specs/`, `.agents/` e `.githooks/`. Decisões já tomadas: Python, SQLite, Streamlit local,
sem CI/CD, sem deploy ([[001-stack-principal]], [[004-infra-execucao-local]]). Esta plan cria o esqueleto sobre o
qual todas as outras trabalham; **nenhuma lógica de negócio** entra aqui.

# 3. Escopo
## 3.1 Dentro
- `requirements.txt` — dependências de execução: `scikit-learn`, `pandas`, `requests`, `python-dotenv`, `streamlit`
- `requirements-dev.txt` — `-r requirements.txt`, `pytest`, `ruff`, `nbformat`, `jupyter`
- `pytest.ini` — `pythonpath = src`, `testpaths = tests`
- `.env.example` — chaves vazias: `LLM_ENABLED=false`, `LLM_BASE_URL=`, `LLM_MODEL=`, `LLM_API_KEY=`, `LOG_LEVEL=INFO`
- `.gitignore` — acrescentar `output/`, `*.db`, `.venv/`, `.ipynb_checkpoints/`
- `src/triage/__init__.py` e subpacotes com `__init__.py`: `ingestion/`, `privacy/`, `classification/`,
  `automation/`, `storage/`, `pipeline/`, `interface/`
- `src/triage/config.py` — leitura única de configuração (variáveis de ambiente + constantes nomeadas)
- `src/triage/logging_setup.py` — `configure_logging()`: log em arquivo (`output/logs/run.log`) e console, nível por `LOG_LEVEL`
- `run.py` — ponto de entrada com `argparse` (`--input`, `--output`, `--help`); por enquanto só valida argumentos e loga que o pipeline ainda não foi implementado
- `tests/test_config.py`, `tests/test_logging_setup.py`, `tests/test_run.py`
- `data/.gitkeep`, `notebooks/.gitkeep`

## 3.2 Fora
- Qualquer lógica de ingestão, PII, classificação, catálogo ou LLM (plans seguintes).
- `app.py` (plan 04.02) e o `README.md` final (plan 05.01).
- `.githooks/`, `.agents/` e `specs/` (exceto o que a síntese fizer).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[001-stack-principal]] | stack e interface |
| ADR | [[004-infra-execucao-local]] | ponto de entrada e ausência de deploy |
| Spec fixa | [[00-fundacao-tecnologica]] | mapa de pacotes e fluxo |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |

# 5. Instruções de execução
1. [dirigido] Criar a árvore descrita em §3.1 com layout `src/`; cada subpacote com `__init__.py` e docstring de uma linha em português.
2. [dirigido] `config.py`: expor `load_settings()` que lê `.env` (se existir) via `python-dotenv` e devolve um objeto imutável (`dataclass(frozen=True)`) com `llm_enabled` (bool, padrão `False`), `llm_base_url`, `llm_model`, `llm_api_key`, `log_level`, `output_dir` (padrão `output`). Nenhum valor padrão secreto; ausência de `.env` não é erro.
3. [dirigido] `logging_setup.py`: `configure_logging(settings)` cria `output/logs/` se faltar e configura handlers de arquivo e console com formato `timestamp nível módulo mensagem`. **Nunca** logar a chave de API nem texto bruto do cidadão ([[003-seguranca-sem-autenticacao]]).
4. [dirigido] `run.py`: `main(argv)` retorna código de saída inteiro; `--input` (pasta, padrão `data/samples`) e `--output` (pasta, padrão `output`). Pasta de entrada inexistente → log de erro e retorno `2`, sem traceback.
5. [dirigido] Testes: `load_settings` com e sem variáveis; `configure_logging` cria o arquivo de log e não escreve a chave de API; `run.main(["--input", "nao-existe"])` retorna `2`.
6. Rodar `python -m pytest -q` e `python -m ruff check .` e garantir verde.

# 6. Critérios de aceite
- [ ] `pip install -r requirements-dev.txt` conclui em ambiente virtual limpo.
- [ ] `python run.py --help` lista `--input` e `--output`.
- [ ] `python run.py --input pasta-que-nao-existe` encerra com código 2 e mensagem em log, sem traceback.
- [ ] `.env.example` não contém valor secreto; `.env` está no `.gitignore`.
- [ ] Todos os subpacotes de §3.1 importáveis (`import triage.ingestion` etc.).
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest -q` → verde.
- `python -m ruff check .` → sem erro.
- `python run.py --input pasta-que-nao-existe` → código de saída `2`.
- Leitura de `.env.example` e `.gitignore` → sem valor secreto; `output/` e `*.db` ignorados.
- Se a verificação cria `output/`: confirmar que está ignorado pelo Git (`git status` limpo).
- **Gate:** `nenhum — repositório sem binding; o gate de segredos do pre-commit cobre o diff`.

# 8. Destino da síntese
**Destino:** `arquitetura/01.01-estrutura-do-projeto.md`

Levar: layout `src/triage/` e função de cada subpacote; arquivos de configuração (`requirements*.txt`, `pytest.ini`,
`.env.example`); `load_settings()` como ponto único de configuração; regra de log sem PII e sem chave; comandos
`python run.py`, `python -m pytest -q`, `python -m ruff check .`. Atualizar também a §3 do `00-contexto`, trocando
"previstos" por comandos verificados.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
