---
tipo: "plan"
familia: "03"
item: "R03.10"
titulo: "Mover a configuração para um JSON versionado e deixar só a chave do LLM no .env"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.04-agente-llm]]", "[[03.02-resposta-final-e-llm]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "—"
destino_sintese: "arquitetura/01.01-estrutura-do-projeto.md"
---

# 1. Objetivo
O `.env` guarda **só a chave do LLM** (`LLM_API_KEY`); todo o resto da configuração (liga/desliga do LLM, provedor, modelos,
agente, assistente de localização, nível de log, limiares e identificação do verificador de links) vive num JSON versionado
lido por `load_settings`, como no template de agentes do grupo.

# 2. Contexto
O grupo tem um template de agente (`C:\\Users\\Igor\\Desktop\\Sarak\\X - Trabalho\\Code\\Agentes\\Chat\\Template-Py`) em que o
`.env` traz só chaves e conexões, e provedor, modelo, temperatura e retries ficam em JSON (`src/config/agents/*/config.json`,
`src/config/shared/defaults.json`). Este projeto fez diferente por engano: `LLM_ENABLED`, `LLM_BASE_URL`, `LLM_MODEL`,
`LLM_FALLBACK_MODELS`, `LLM_AGENT_ID`, `LLM_ASSIST_LOCATE`, `LOG_LEVEL`, `CONFIDENCE_MIN`, `AMBIGUITY_MARGIN`,
`FINDER_MIN_SCORE`, `FINDER_MARGIN` e `LINK_CHECK_USER_AGENT` são lidos do ambiente por `triage.config.load_settings`.
A regra do usuário prevalece sobre a regra geral de "valor por ambiente vai ao `.env`": **só a chave fica no `.env`**.

Estado atual: `Settings` é um `dataclass(frozen=True)` consumido por `triage.classification.decision`,
`triage.automation` (`resolver`, `llm_client`, `finder`), `triage.pipeline`, `run.py`, `app.py` e `scripts/verify_catalog.py`;
os testes de pipeline e interface montam `load_settings(tmp_path / "sem.env")` e trocam campos com `dataclasses.replace`. Os nomes
dos campos de `Settings` **não mudam**: só a origem dos valores.

## 2.1 Contrato (decisão desta plan)
Arquivo `config/settings.json` (novo, na raiz do repositório, localizado a partir do arquivo do módulo e não do diretório
corrente, como `data/agents/`):

```json
{
  "log_level": "INFO",
  "llm": {
    "enabled": false,
    "base_url": "https://openrouter.ai/api/v1",
    "model": "deepseek/deepseek-v4-flash",
    "fallback_models": ["deepseek/deepseek-v4-flash-0731", "deepseek/deepseek-v3.2", "minimax/minimax-m3:free", "openrouter/free"],
    "agent_id": "triage-assistant",
    "assist_locate": false
  },
  "triage": { "confidence_min": 0.60, "ambiguity_margin": 0.15 },
  "finder": { "min_score": 0.25, "margin": 0.15 },
  "link_check": { "user_agent": "GS-RPA-Triagem/1.0 (projeto academico FIAP)" }
}
```

- `load_settings(dotenv_path=Path(".env"), config_path=<padrão acima>)`: `load_dotenv` continua, e **só** `LLM_API_KEY` é lido do
  ambiente; nenhuma outra variável de ambiente altera a configuração (as antigas passam a ser ignoradas).
- **Arquivo ausente, ilegível ou JSON inválido** → `ConfigError` (erro próprio, causa preservada, mensagem acionável): a
  configuração é do repositório, e falta dela derruba o boot em vez de rodar com valores adivinhados.
- **Campo ausente ou inválido** (tipo errado, limiar fora de [0, 1]) → o padrão do código, com `WARNING`, como já é hoje para
  limiares. Os padrões em código (`CONFIDENCE_MIN` etc.) permanecem como o valor de reserva, e um teste garante que o
  `settings.json` entregue é igual a eles.
- `LLM_API_KEY` vazio com `llm.enabled` verdadeiro mantém o comportamento atual: aviso e template (sem cliente).
- Os modelos do §2.1 são a escolha do usuário (os mesmos do chat do site dele) e **não se alteram**. O `enabled: false` de entrega
  só mantém o projeto funcional sem LLM, como o enunciado pede.

# 3. Escopo
## 3.1 Dentro
- `config/settings.json` (novo)
- `src/triage/config.py` — leitura do JSON, `ConfigError`, `Settings` com os mesmos campos, só a chave no ambiente
- `run.py` e `app.py` — tratar `ConfigError` como falha de infraestrutura (log do erro e código de saída 1 no `run.py`; mensagem na
  tela, sem traceback, no `app.py`); a ajuda de `--llm` deixa de citar `LLM_ENABLED` do `.env`
- `.env.example` — só `LLM_API_KEY=`, com um comentário de que o resto está em `config/settings.json`
- `README.md` — tabela de configuração e seções "Agente LLM"/dois modos reescritas para a nova fronteira; como ligar o LLM
- `tests/test_config.py` (reescrito para o JSON), `tests/classification/test_decision.py` (o caso que usa `monkeypatch.setenv`
  de limiares passa a usar um JSON temporário) e os testes de `tests/automation/` que citarem as variáveis antigas

## 3.2 Fora
- Os arquivos do agente (`data/agents/`), o catálogo e a allowlist; `max_candidates` e os parâmetros de chamada continuam
  no `config.json` do agente.
- Mudar valores (limiares, modelos além do que o §2.1 lista, comportamento do LLM): só se muda a origem.
- `output_dir` e `--output`/`--db`: continuam como estão (argumento de linha de comando).
- Qualquer chave real em arquivo; chamada real de rede nos testes.
- Specs, ADRs e índice (o revisor os atualiza na síntese).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | `specs/03.04-agente-llm.md` §2.4 · `specs/03.02-resposta-final-e-llm.md` §2.5 | fronteira atual `.env` × versionado, a ser substituída |
| Spec fixa | `specs/arquitetura/01.01-estrutura-do-projeto.md` · `specs/03.03-localizador-de-servicos.md` §2.2 · `specs/03.01-catalogo-e-allowlist.md` §2.3 | onde as variáveis de ambiente aparecem hoje |
| ADR | [[003-seguranca-sem-autenticacao]] | segredo só em `.env`, fora do Git |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | zero hardcoded, falta de config derruba o boot, erros com causa preservada |
| Skill | `test-unitario` | testes sem rede e sem depender do `.env` do desenvolvedor |
| Código | `src/triage/config.py`, `run.py`, `app.py`, `scripts/verify_catalog.py`, `.env.example`, `README.md` | o que muda |
| Código | `tests/test_config.py`, `tests/classification/test_decision.py`, `tests/pipeline/conftest.py`, `tests/interface/conftest.py` | testes a ajustar e conftests que chamam `load_settings` |
| Template externo (só leitura) | `C:\\Users\\Igor\\Desktop\\Sarak\\X - Trabalho\\Code\\Agentes\\Chat\\Template-Py` — `.env.example`, `src/config/shared/defaults.json` | origem da fronteira; nada é copiado sem adaptar (inglês no código, sem hardcode) |

# 5. Instruções de execução
1. [dirigido] **Arquivo.** Criar `config/settings.json` exatamente com o conteúdo e as chaves do §2.1.
2. [dirigido] **Leitura.** Reescrever `load_settings` conforme o §2.1: JSON do arquivo, `ConfigError` para arquivo ausente,
   ilegível ou inválido, padrão de reserva com `WARNING` para campo inválido, e só `LLM_API_KEY` do ambiente. Funções
   pequenas, sem exceção engolida. `Settings` mantém todos os campos e padrões atuais.
3. [dirigido] **Chamadores.** `run.py` e `app.py` tratam `ConfigError` como falha de infraestrutura (§3.1); `scripts/verify_catalog.py`
   e `triage.automation.resolver` continuam chamando `load_settings()` sem argumento e funcionando de qualquer diretório.
4. [dirigido] **`.env.example` e README.** `.env.example` só com `LLM_API_KEY=` e o comentário; README: a tabela de configuração
   passa a dizer que o `.env` tem só a chave e que o resto está em `config/settings.json` (cada chave e o que faz), o exemplo
   de uso vira edição do JSON (`llm.enabled` = `true`) mais a chave no `.env`, com os modelos do §2.1 (sem trocá-los por outros),
   e os dois modos do LLM mantêm o que cada um envia. Dizer que o projeto roda sem LLM.
5. [dirigido] **Testes** (sem rede, sem ler o `.env` real): JSON válido completo; cada seção; arquivo ausente e JSON inválido →
   `ConfigError`; campo ausente ou de tipo errado → padrão com `WARNING`; limiar fora de [0, 1]; `fallback_models` vazia,
   uma e várias; `LLM_API_KEY` só vem do ambiente e as variáveis antigas (`LLM_ENABLED`, `LLM_MODEL`, `LOG_LEVEL`,
   `FINDER_MIN_SCORE` etc.) **não** alteram a configuração; o `config/settings.json` entregue carrega sem aviso e é igual aos
   padrões do código; `load_settings()` funciona de outro diretório; `run.py` sai com 1 e `app.py` mostra a mensagem quando
   a configuração está quebrada.
6. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] `config/settings.json` existe com as chaves do §2.1 e carrega sem aviso; é igual aos padrões em código.
- [ ] O único valor lido do ambiente é `LLM_API_KEY`; as variáveis antigas são ignoradas (teste prova).
- [ ] Arquivo de configuração ausente ou inválido → `ConfigError`, `run.py` sai com `1` e `app.py` mostra mensagem sem traceback.
- [ ] Campo inválido → padrão com `WARNING`; nenhum valor é adivinhado em silêncio.
- [ ] `Settings` mantém os mesmos campos; pipeline, interface, classificação, localizador e verificador seguem passando sem
      alteração de código fora do §3.1.
- [ ] `.env.example` só com `LLM_API_KEY`; README descreve o JSON, o `.env` e como ligar o LLM; nenhuma chave no diff.
- [ ] O notebook de evidências continua executando sem erro.
- [ ] Ambiente e worktree limpos; `ruff` e validador sem violação nova nos arquivos tocados.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — muda o contrato de Settings, consumido por classificação, automação, pipeline, interface e scripts`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/test_config.py tests/classification tests/automation tests/pipeline tests/interface tests/agent -q` → verde.
- `python -m ruff check src/triage/config.py run.py app.py tests/test_config.py tests/classification` → sem erro novo.
- `validate.py` do `padrao-python` em `src/triage/config.py`, `run.py`, `app.py` e `tests/test_config.py` → sem achado.
- Sondagem: `LLM_ENABLED=true LLM_MODEL=x python -c "from triage.config import load_settings; print(load_settings().llm_enabled)"` → `False`
  (variável antiga ignorada); renomear o JSON numa cópia e conferir `ConfigError` e `run.py` com código `1`.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` sem erro (o notebook
  chama `load_settings`); `output/notebook-evidence/` não sobra.
- **Gate:** `nenhum — coberto por testes e sondagem`.

# 8. Destino da síntese
**Destino:** `arquitetura/01.01-estrutura-do-projeto.md` (a parte "Ambiente" e "Configuração").

Escrever: `.env` só com `LLM_API_KEY`, o resto em `config/settings.json` (estrutura, `ConfigError`, campo inválido → padrão com
aviso, localização independente do diretório corrente); substituir, **no lugar**, a fronteira de `specs/03.04-agente-llm.md` §2.4,
`specs/03.02-resposta-final-e-llm.md` §2.5, `specs/03.03-localizador-de-servicos.md` §2.2 e `specs/03.01-catalogo-e-allowlist.md`
§2.3 (onde citam variáveis de ambiente), `specs/00-contexto.md` (regra "Segredos só em `.env`" passa a "só a chave") e a
ADR 003 item 4 só se ela citar valores além da chave. Sem ADR nova: a escolha é uma convenção do grupo, não um trade-off.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído

**O que foi feito**
- `config/settings.json` criado com o conteúdo e as chaves do §2.1 — fonte única da configuração.
- `src/triage/config.py`: `load_settings(dotenv_path, config_path)` lê o JSON; `ConfigError` (causa preservada) para arquivo ausente, ilegível, JSON inválido ou raiz que não é objeto; campo ausente ou inválido → padrão do código com `WARNING` (`config.py:_pick`); só `LLM_API_KEY` vem do ambiente; `DEFAULT_CONFIG_PATH` é resolvido a partir do arquivo do módulo. `Settings` e os padrões não mudaram.
- `run.py`: `ConfigError` em `_settings_from` → log de erro e saída `1`; ajuda de `--llm` cita `llm.enabled` de `config/settings.json`.
- `app.py`: `ConfigError` em `_load_service` → `None` e mensagem na tela, sem traceback; a mensagem passou a dizer "configuração ou banco de dados inacessível".
- `.env.example` só com `LLM_API_KEY=` e o comentário; README: seção de chaves, tabela de configuração, dois modos e exemplo reescritos para a nova fronteira (modelos do §2.1 mantidos).
- `tests/test_config.py` reescrito (JSON); `tests/classification/test_decision.py`: o caso de limiares usa JSON temporário em vez de `monkeypatch.setenv`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `config/settings.json` | criado | configuração versionada (§2.1) |
| `src/triage/config.py` | alterado | leitura do JSON, `ConfigError`, só a chave no ambiente |
| `run.py` | alterado | `ConfigError` → saída 1; ajuda de `--llm` |
| `app.py` | alterado | `ConfigError` → mensagem na tela; texto da mensagem |
| `.env.example` | alterado | só `LLM_API_KEY` |
| `README.md` | alterado | configuração, modos do LLM e exemplo |
| `tests/test_config.py` | alterado | reescrito para o JSON (inclui testes de `run.py` e `app.py`) |
| `tests/classification/test_decision.py` | alterado | limiares vindos de JSON temporário |

**Verificações executadas**
- `python -m pytest tests/test_config.py tests/classification tests/automation tests/pipeline tests/interface tests/agent -q` → 640 passed.
- `python -m ruff check src/triage/config.py run.py app.py tests/test_config.py` → All checks passed. Com `tests/classification` (comando literal do §7): 2 erros `I001` de ordem de imports em `tests/classification/test_decision.py:7-9` e `tests/classification/test_model.py:3-10`, em linhas que não toquei.
- `validate.py` (`padrao-python`) em `config.py`, `run.py`, `app.py`, `tests/test_config.py` → `findings: []` (o primeiro `config.py` acusou falso positivo de segredo no nome de uma constante com `KEY`; removi a constante e usei `os.getenv("LLM_API_KEY", "")` como antes).
- Sondagem: `LLM_ENABLED=true LLM_MODEL=x … load_settings()` → `llm_enabled=False`, modelo do JSON (variáveis antigas ignoradas). Cópia do projeto com o JSON renomeado: `python run.py --input in --output out` → mensagem de erro e `exit=1`, sem criar `out/`.
- `jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` → sem erro; `output/` segue com `logs`, `models`, `reports` e não tem `notebook-evidence/`.

**Estado inicial do worktree:** ` M specs/00-indice.md`, ` M specs/panorama/00-planejamento.md`, ` M specs/panorama/00-resumo.md`, `?? specs/plan/plan-03.10-configuracao-em-json-e-so-a-chave-no-env.md` (branch `develop`).

**Ambiente após a verificação:** a cópia temporária do projeto e a saída do notebook ficaram no scratchpad e foram removidas; nenhum processo, servidor ou contêiner subido. `snapshot`/`diff` da skill `code-limpeza-ambiente` não foram rodados: conferido à mão (nada criado fora do scratchpad).

**Critérios de aceite**
- [x] `config/settings.json` com as chaves do §2.1, carrega sem aviso e é igual aos padrões em código — `test_shipped_config_loads_without_warning`, `test_shipped_config_equals_the_code_defaults`.
- [x] Só `LLM_API_KEY` é lido do ambiente; variáveis antigas ignoradas — `test_old_environment_variables_do_not_change_the_configuration` e a sondagem.
- [x] Arquivo ausente ou inválido → `ConfigError`, `run.py` sai com 1, `app.py` mostra mensagem sem traceback — `test_missing_config_file_raises_config_error`, `test_invalid_json_raises_config_error_with_the_cause`, `test_run_exits_with_1_when_the_config_is_broken`, `test_app_shows_a_message_without_traceback_when_the_config_is_broken`.
- [x] Campo inválido → padrão com `WARNING` — `test_missing_field_…`, `test_field_of_the_wrong_type_…`, `test_threshold_outside_zero_one_…`.
- [x] `Settings` mantém os campos; pipeline, interface, classificação, localizador e verificador passam sem alteração de código fora do §3.1 — 640 passed.
- [x] `.env.example` só com `LLM_API_KEY`; README descreve JSON, `.env` e como ligar o LLM; nenhuma chave no diff.
- [x] Notebook de evidências executa sem erro.
- [x] Ambiente e worktree limpos; `ruff` e validador sem violação nova nos arquivos tocados (os 2 `I001` acima são anteriores).

**Decisões e suposições**
- "Igual aos padrões do código": só `llm.base_url`, `llm.model` e `llm.fallback_models` não têm padrão útil em código (reserva `""`/`()`, como os campos obrigatórios de `Settings` já eram); o teste compara com o código todos os campos que têm padrão e confere esses três contra os valores do §2.1.
- Campo **ausente** também gera `WARNING` (o §2.1 trata ausente e inválido juntos); texto em branco volta ao padrão só onde o padrão não é vazio (`agent_id`, `user_agent`, `log_level`); itens vazios de `fallback_models` são descartados em silêncio, como antes.
- Inteiro em limiar (por exemplo `1`) é aceito e vira `float`; booleano e string numérica são inválidos.
- Os testes de `run.py` e `app.py` ficaram em `tests/test_config.py` (e não em `tests/test_run.py`) para manter o diff dentro do §3.1; o de `app.py` usa `streamlit.testing.v1.AppTest`.
- `run.py` registra o `ConfigError` antes de `configure_logging` (que precisa de `Settings`): a mensagem sai no console pelo handler padrão do `logging`, sem arquivo de log.
- A mensagem de erro do `app.py` ficou única para configuração e banco ("configuração ou banco de dados inacessível"); o detalhe vai para o log.

**Achados fora do escopo (não corrigidos)**
- `src/triage/automation/llm_client.py:126` — o aviso ainda cita `LLM_BASE_URL, LLM_MODEL ou LLM_API_KEY`; agora os dois primeiros são `llm.base_url` e `llm.model` no JSON.
- `src/triage/pipeline/processor.py:165` — docstring cita `LLM_ENABLED`, `LLM_ASSIST_LOCATE`.
- `tests/classification/test_decision.py:7-9` e `tests/classification/test_model.py:3-10` — `I001` (ordem de imports) já existente.
- `README.md` (seções de limiares, por volta das linhas 204–212) e `notebooks/evidence.ipynb` seguem citando `CONFIDENCE_MIN`, `FINDER_MIN_SCORE` etc. como nomes de limiar, não como variáveis de ambiente; não alterei.
- `ruff` do hook do harness acusava "não instalado", mas `python -m ruff` (0.17.4) funciona; não afeta o resultado.

**Pendências / riscos**
- Um `.env` antigo de quem já usava o projeto deixa de ter efeito (como a plan define): quem tinha `LLM_ENABLED=true` precisa editar o JSON.
- Specs e ADRs (§8 da plan) não foram tocadas, como mandado; a síntese é do revisor.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-11 — 🟢 Aprovado

Verifiquei, sem confiar no resumo: o diff bate com o resumo e fica dentro do §3.1 (`config/settings.json`, `config.py`, `run.py`, `app.py`, `.env.example`, `README.md`, `tests/test_config.py`, `tests/classification/test_decision.py`). `config/settings.json` tem as chaves e os modelos do §2.1, sem alteração. `python -m pytest tests/test_config.py tests/classification tests/automation tests/pipeline tests/interface tests/agent -q` → 640 passed; `ruff` em `config.py`, `run.py`, `app.py` e `tests/test_config.py` → limpo; em `tests/classification` → 2 `I001` anteriores (confirmei no `HEAD` que `test_decision.py` já tinha o desvio de imports); `validate.py` nos quatro `.py` → `findings: []`. Sondagem: `LLM_ENABLED=true LLM_MODEL=x LOG_LEVEL=DEBUG FINDER_MIN_SCORE=0.9` → `False`, modelo do JSON, `INFO`, `0.25` (variáveis antigas ignoradas); `load_settings()` chamado de outro diretório funciona; cópia do projeto com o JSON renomeado → `python run.py` imprime o erro e sai `1`. `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` termina sem erro; `output/` só com `logs`, `models` e `reports`. Código de `config.py` lido inteiro: `ConfigError` com causa preservada, campo ausente ou inválido volta ao padrão com `WARNING`, só `LLM_API_KEY` vem do ambiente. Achados do executor fora do escopo (mensagem de `llm_client.py:126` e docstring de `processor.py:165` que citam as variáveis antigas) viram escopo da plan seguinte, que reescreve esses dois arquivos; `I001` anteriores ficam no backlog 14.
