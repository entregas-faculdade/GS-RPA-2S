---
tipo: "plan"
familia: "01"
item: "R01.1"
titulo: "Montar a estrutura do projeto, dependências e ponto de entrada mínimo"
dominio: "Núcleo do robô"
status: "🟢 Aprovada"
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

## Resumo da execução — 2026-11-09

**Resultado:** Concluído com pendências

**O que foi feito**
- Árvore `src/triage/` com 7 subpacotes, cada um com `__init__.py` e docstring de uma linha em português — passo 1.
- `src/triage/config.py`: `Settings` (`dataclass(frozen=True)`) e `load_settings(dotenv_path=Path(".env"))`; `.env` ausente não é erro; `output_dir` fixo em `output` — passo 2.
- `src/triage/logging_setup.py`: `configure_logging(settings)` (arquivo `<output_dir>/logs/run.log` + console, formato `timestamp nível módulo mensagem`), `shutdown_logging()` e filtro que mascara `llm_api_key` se aparecer numa mensagem — passo 3.
- `run.py`: `main(argv)` com `--input` (padrão `data/samples`) e `--output` (padrão `output`); pasta inexistente → log de erro e retorno `2`; pasta existente → aviso "pipeline ainda não implementado" e retorno `0` — passo 4.
- `tests/test_config.py`, `tests/test_logging_setup.py`, `tests/test_run.py` (11 testes) — passo 5.
- `requirements.txt` e `requirements-dev.txt` com versões exatas (`==`, exigência do `padrao-python`), `pytest.ini`, `.env.example`, `.gitignore` (+4 linhas), `data/.gitkeep`, `notebooks/.gitkeep`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `requirements.txt` | criado | scikit-learn, pandas, requests, python-dotenv, streamlit fixados |
| `requirements-dev.txt` | criado | `-r requirements.txt` + pytest, ruff, nbformat, jupyter fixados |
| `pytest.ini` | criado | `pythonpath = src`, `testpaths = tests` |
| `.env.example` | criado | 5 chaves sem valor secreto |
| `.gitignore` | alterado | + `output/`, `*.db`, `.venv/`, `.ipynb_checkpoints/` |
| `src/triage/__init__.py` + 7 `__init__.py` de subpacotes | criado | docstrings |
| `src/triage/config.py` | criado | `Settings`, `load_settings` |
| `src/triage/logging_setup.py` | criado | `configure_logging`, `shutdown_logging` |
| `run.py` | criado | ponto de entrada com argparse |
| `tests/test_config.py`, `tests/test_logging_setup.py`, `tests/test_run.py` | criado | 11 testes |
| `data/.gitkeep`, `notebooks/.gitkeep` | criado | placeholders |
| `specs/plan/plan-01.01-setup-projeto.md` | alterado | `status` e este resumo |

**Verificações executadas**
- `pip install -r requirements-dev.txt` em venv limpo (`c:/tmp/v3`) → concluiu; `pip check`: sem requisitos quebrados; jupyter 1.1.1, jupyterlab 4.6.6, pandas 3.1.1, scikit-learn 1.9.1, streamlit 1.67.0 etc.
- `python -m pytest -q` → `11 passed` (também no venv limpo).
- `python -m ruff check run.py src tests` → `All checks passed!`. Em `python -m ruff check .` há 5 erros, todos em `.githooks/verify_commit.py` (ver achados).
- `python -I <skill padrao-python>/scripts/validate.py` sobre `run.py`, `src`, `tests` → 0 achados (depois de renomear a constante de máscara e anotar os testes).
- `python run.py --help` → lista `--input` e `--output`.
- `python run.py --input pasta-que-nao-existe` → código de saída `2`, linha `ERROR triage.run Pasta de entrada não encontrada: pasta-que-nao-existe` no console e em `output/logs/run.log`, sem traceback.
- `import triage.<ingestion|privacy|classification|automation|storage|pipeline|interface>` → ok.
- `git check-ignore output .env` → ambos ignorados.

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** criei venvs (scratchpad e `c:/tmp/v3`), `output/`, `.pytest_cache`, `.ruff_cache`, `__pycache__` → todos removidos por caminho explícito. Nenhum processo, servidor ou contêiner foi iniciado. `snapshot` da skill `code-limpeza-ambiente` não rodado (conferência manual). `git status` final mostra só os arquivos do escopo.

**Critérios de aceite**
- [x] `pip install -r requirements-dev.txt` conclui em venv limpo — evidência: venv `c:/tmp/v3`, `pip check` limpo.
- [x] `python run.py --help` lista `--input` e `--output` — evidência: saída acima.
- [x] `--input pasta-que-nao-existe` → código 2, log, sem traceback — evidência: `exit=2`.
- [x] `.env.example` sem valor secreto; `.env` no `.gitignore` — evidência: `git check-ignore .env` (regra já existente).
- [x] Subpacotes importáveis — evidência: import dos 7.
- [x] Ambiente e worktree limpos — evidência: item acima.
- [x] Testes verdes; `ruff` e validador sem violação nos arquivos alterados — evidência: 11 passed; ruff e validate.py zerados em `run.py`, `src`, `tests`.
- [x] Sem dado pessoal, chave ou `.env` no diff.

**Decisões e suposições**
- Versões exatas (`==`) nos `requirements*.txt`, resolvidas num venv com Python 3.14.0 em 2026-11-09: a plan não fixou versões e o `padrao-python` exige `==`. O `00-contexto` §8 dá "versão do Python" como pendente; o projeto foi verificado apenas em 3.14.0.
- `load_settings(dotenv_path)` recebe o caminho do `.env` (padrão `.env` no diretório atual) para os testes não lerem um `.env` real; `output_dir` não vem de variável de ambiente (a plan só o lista como padrão `output`, e `.env.example` não tem a chave).
- `run.py` insere `src/` no `sys.path` para `python run.py` funcionar sem instalar o pacote; `pytest.ini` fica como a plan manda (`pythonpath = src`), então `test_run.py` carrega `run.py` por caminho (`importlib`).
- `run.py` com pasta existente devolve `0` e loga aviso (a plan só define o caso de erro).
- `shutdown_logging()` e o filtro de máscara não estão na plan: o primeiro libera o arquivo de log (necessário no Windows e nos testes), o segundo impõe "nunca logar a chave" (§5.3) em vez de só testar a ausência.
- Os testes anotam tipos e a constante de máscara foi nomeada `REDACTION_PLACEHOLDER` só para o validador de `padrao-python` não sinalizar falso positivo de segredo.
- `ruff format` não foi aplicado (a plan pede só `ruff check`).

**Achados fora do escopo (não corrigidos)**
- `.githooks/verify_commit.py` — `ruff check .` reporta 5 erros (I001, 2× PLW1510, FLY002, RUF013) com a configuração de ruff desta máquina; o critério "ruff sem erro" da §7 (`python -m ruff check .`) falha por causa deles, não do escopo.
- `ruff check` aplica regras além das padrão (PLW/RUF/FLY) vindas de configuração fora do repositório; não investiguei a origem.

**Pendências / riscos**
- `python -m ruff check .` (comando literal da §7) não fica verde por causa de `.githooks/`; o revisor decide se o escopa a `run.py src tests` ou se abre demanda.
- No Windows, `pip install -r requirements-dev.txt` falha em venv com caminho longo (jupyterlab, "Long Path support"); passou em `c:/tmp/v3`. Vale registrar no README (plan 05.01).
- Python 3.14.0 como único ambiente verificado.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-09 — 🔴 Reprovado

**Verificado (nível escopada), com saída real:** `git status`/`git diff --stat` (só arquivos de §3.1 + `.gitignore`; nada fora do escopo, nada faltando) · leitura integral de `run.py`, `config.py`, `logging_setup.py`, dos três arquivos de teste e dos `requirements*`, `.env.example`, `pytest.ini`, `.gitignore` · `python -m pytest -q` → 11 passed · `python -m ruff check run.py src tests` → All checks passed · `padrao-python/scripts/validate.py` em `run.py`, `src` e `tests` → 0 achados · `python run.py --input pasta-que-nao-existe` → código 2, uma linha de erro, sem traceback · limpeza: `output/`, caches e `__pycache__` removidos, `git status` volta a só o escopo. Os demais critérios de aceite da §6 estão atendidos pelas evidências acima.

**Achados**
1. `tests/test_config.py:12-15` (fixture `clean_env`) e `tests/test_config.py:40-47` (`test_reads_dotenv_file`) — `load_dotenv` grava no `os.environ` real e a fixture só remove as chaves **antes** de cada teste, sem restaurá-las depois: o teste do `.env` deixa `LOG_LEVEL=WARNING` e `LLM_BASE_URL=http://exemplo.invalido` vazando para todos os testes seguintes (confirmado: após rodar só `tests/test_config.py`, `os.environ` mantém as duas chaves). `test_run.py` já roda com `LOG_LEVEL` poluído, e as plans seguintes (03.02, 04.03) que lerem `load_settings()` herdariam o vazamento. Critério violado: §6, testes do escopo verdes **e isolados**; `padrao-escrita` (teste não depende de estado deixado por outro).

   **Correção exata** — `tests/test_config.py`
   antes:
   ```
       for key in ENV_KEYS:
           monkeypatch.delenv(key, raising=False)
   ```
   depois:
   ```
       for key in ENV_KEYS:
           monkeypatch.setenv(key, "")
           monkeypatch.delenv(key)
   ```
   (o `setenv` faz o `monkeypatch` registrar o estado original e removê-lo no teardown, desfazendo o que o `load_dotenv` gravar.)
   Verificação (única): `python -c "import os, pytest; pytest.main(['-q','tests/test_config.py']); print(os.environ.get('LOG_LEVEL'), os.environ.get('LLM_BASE_URL'))"` → última linha `None None`; e `python -m pytest -q` continua com 11 passed.

**Sobre o resumo:** confere com o diff, com uma ressalva — o resumo diz que `ruff check .` acusa 5 erros em `.githooks/verify_commit.py`; na minha máquina acusa 1 (E731, `.githooks/verify_commit.py:204`). Não reproduzi os outros 4 (configuração de ruff distinta entre as máquinas). Fora do escopo desta plan; vai ao backlog.

---

## Resumo da execução (correção 1) — 2026-11-09

**Resultado:** Concluído

**Achado 1 — vazamento de `os.environ` em `tests/test_config.py`:** aplicado o antes→depois do revisor em `tests/test_config.py:14-15` (fixture `clean_env`): `monkeypatch.delenv(key, raising=False)` virou `monkeypatch.setenv(key, "")` + `monkeypatch.delenv(key)`, de modo que o `monkeypatch` restaura o estado original no teardown.

**Verificação (a nomeada no achado):**
- `python -c "import os, pytest; pytest.main(['-q','tests/test_config.py']); print(os.environ.get('LOG_LEVEL'), os.environ.get('LLM_BASE_URL'))"` → `4 passed`; última linha `None None`.
- `python -m pytest -q` → `11 passed`.
- Venv temporário (`c:/tmp/v4`, pytest 9.2.0 + python-dotenv 1.2.4) criado e removido, junto com `.pytest_cache` e `__pycache__`. O ruff não foi reinstalado: a mudança são duas linhas de teste sem nova sintaxe, e o hook avisou só que ele estava ausente.

**Arquivos alterados:** `tests/test_config.py` (alterado, 1 linha → 2) e `status` desta plan.

**Achados fora do escopo:** o apontamento do revisor sobre o ruff (1 erro E731 vs. 5 no meu resumo) já está tratado por ele; nada novo.

## Veredito — 2026-11-09 — 🟢 Aprovado

**Rodada 2 (correção do achado 1), nível escopada.** Verificado no worktree: `tests/test_config.py:12-15` traz exatamente o "depois" do veredito anterior (`setenv` + `delenv`); a sonda `python -c "import os, pytest; pytest.main(['-q','tests/test_config.py']); print(os.environ.get('LOG_LEVEL'), os.environ.get('LLM_BASE_URL'))"` → `4 passed` e última linha `None None` (vazamento sanado) · `python -m pytest -q` → 11 passed · `python -m ruff check run.py src tests` → All checks passed · `padrao-python/scripts/validate.py` em `tests/test_config.py` → 0 achados · `python run.py --input nao-existe` → código 2, sem traceback · `git status` → só arquivos do escopo (nada novo além da correção) e ambiente limpo (`output/`, caches e `__pycache__` removidos por mim após a verificação). O resumo da correção confere com o diff.

Critérios da §6 todos atendidos (evidências nos blocos desta e da rodada anterior). Achados fora do escopo (ruff em `.githooks/`, instalação no Windows com caminho longo) estão no `00-backlog`.

