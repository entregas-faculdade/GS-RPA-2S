---
tipo: "plan"
familia: "01"
item: "R01.3"
titulo: "Anonimizar CPF, telefone e e-mail antes de qualquer log ou chamada externa"
dominio: "Núcleo do robô"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[003-seguranca-sem-autenticacao]]", "[[005-llm-apenas-reformula-resposta]]"]
depende_de: ""
destino_sintese: "specs/01.03-anonimizacao-de-pii.md"
---

# 1. Objetivo
`anonymize(text)` devolve o texto com CPF, telefone e e-mail trocados por marcadores (`[CPF]`, `[TELEFONE]`,
`[EMAIL]`) e informa quantos de cada tipo foram encontrados, de modo que nenhum dado pessoal desses tipos sobreviva
depois desta etapa.

# 2. Contexto
Temas **Anonimização de PII** e **Regras/regex**; garantia de LGPD do projeto ([[003-seguranca-sem-autenticacao]]).
O texto que sai desta função é o **único** que pode ser logado, gravado ou enviado a API
([[005-llm-apenas-reformula-resposta]]). Dados de teste são sintéticos.

# 3. Escopo
## 3.1 Dentro
- `src/triage/privacy/patterns.py` — regex compilados e nomeados: CPF (com e sem pontuação), telefone BR (fixo e celular, com/sem DDD e `+55`) e e-mail
- `src/triage/privacy/validators.py` — validação dos dígitos verificadores do CPF
- `src/triage/privacy/anonymizer.py` — `anonymize(text) -> AnonymizationResult(text, counts)`
- `src/triage/privacy/__init__.py` — exporta `anonymize`, `AnonymizationResult`
- `tests/privacy/` — testes positivos e negativos de §5

## 3.2 Fora
- Nomes de pessoas, endereços, RG e outros identificadores (limite declarado, ver §8).
- Integração no pipeline (plan 04.03) e uso pelo LLM (plan 03.02).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[003-seguranca-sem-autenticacao]] | PII anonimizada antes de log/API |
| ADR | [[005-llm-apenas-reformula-resposta]] | o LLM só recebe texto anonimizado |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Spec fixa | [[01.02-ingestao-e-sanitizacao]] | contrato de `Request` e da sanitização que antecede esta etapa |
| Código | `src/triage/ingestion/` | a entrada desta etapa é a saída (texto sanitizado) da anterior |

# 5. Instruções de execução
1. [dirigido] Regex em `patterns.py` como constantes nomeadas; CPF: 11 dígitos com ou sem `.` e `-`; telefone: 8–9 dígitos com DDD opcional (entre parênteses ou separado por espaço) e `+55` opcional; e-mail: padrão pragmático.
2. [dirigido] CPF só é substituído se os dígitos verificadores forem válidos **ou** se o formato for o pontuado `000.000.000-00`; 11 dígitos inválidos e sem pontuação **não** são CPF (evita falso positivo em protocolo/código). Registrar a decisão em docstring.
3. [dirigido] Substituir com `re.sub` e função (sem deslocar índices); o resultado traz `counts` por tipo (`{"cpf": n, "phone": n, "email": n}`).
4. [dirigido] Função pura, sem log do texto. Idempotente: `anonymize(anonymize(x).text).text == anonymize(x).text`.
5. [dirigido] Testes mínimos — **positivos:** CPF pontuado; CPF só dígitos válido; `(11) 91234-5678`; `11912345678`; `+55 11 91234-5678`; e-mail em domínio de exemplo; vários PII no mesmo texto. **Negativos:** protocolo de 11 dígitos inválido; ano e valores monetários; texto sem PII (inalterado, `counts` zerado). **Idempotência.**
6. Rodar `python -m pytest tests/privacy -q` e `ruff`.

# 6. Critérios de aceite
- [ ] Todo caso positivo de §5.5 tem PII substituída por marcador e `counts` correto.
- [ ] Todo caso negativo de §5.5 permanece inalterado.
- [ ] A função é idempotente (teste).
- [ ] Nenhum dado pessoal real nos testes (CPFs gerados por algoritmo, e-mails em domínio de exemplo).
- [ ] Limites declarados na docstring do módulo (nomes, endereços e RG **não** cobertos).
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/privacy -q` → verde.
- `python -m ruff check src/triage/privacy tests/privacy` → sem erro.
- Execução manual: `anonymize("meu cpf 529.982.247-25 tel (11) 91234-5678 a@exemplo.com")` → três marcadores e `counts` 1/1/1.
- **Gate:** `nenhum — coberto por teste; o scanner de segredos não substitui este teste`.

# 8. Destino da síntese
**Destino:** `specs/01.03-anonimizacao-de-pii.md`

Levar: tipos cobertos (CPF, telefone, e-mail) e marcadores; regra de validação do CPF; garantia de idempotência;
**limites declarados** (nomes, endereços e RG não são anonimizados — risco residual a citar no README, plan 05.01);
regra de que só o texto anonimizado pode ser logado, gravado ou enviado a API.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-09

**Resultado:** Concluído

**O que foi feito**
- `src/triage/privacy/patterns.py` — regex nomeados de CPF (pontuado/11 dígitos), telefone BR (5 formas) e e-mail, mais os marcadores.
- `src/triage/privacy/validators.py` — `is_valid_cpf` (dígitos verificadores módulo 11; rejeita dígitos todos iguais).
- `src/triage/privacy/anonymizer.py` — `anonymize(text) -> AnonymizationResult(text, counts)` com `re.sub` por função; ordem e-mail → CPF → telefone; docstring do módulo com decisão do CPF, limites e regra de só logar texto anonimizado.
- `src/triage/privacy/__init__.py` — exporta `anonymize` e `AnonymizationResult`.
- `tests/privacy/test_anonymizer.py` — positivos, negativos, vários PII, idempotência e validador.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/privacy/patterns.py` | criado | regex e marcadores |
| `src/triage/privacy/validators.py` | criado | validação de CPF |
| `src/triage/privacy/anonymizer.py` | criado | `anonymize` e resultado |
| `src/triage/privacy/__init__.py` | alterado | exporta a API pública |
| `tests/privacy/test_anonymizer.py` | criado | 15 casos de teste |

**Verificações executadas**
- `python -m pytest tests/privacy -q` → 15 passed.
- `python -m ruff check src/triage/privacy tests/privacy` → All checks passed (ruff 0.14.2 local; o pinado é 0.17.4).
- `validate.py` de `padrao-python` em `src/triage/privacy` e `tests/privacy` → `findings: []`.
- Manual: `anonymize("meu cpf 529.982.247-25 tel (11) 91234-5678 a@exemplo.com")` → `meu cpf [CPF] tel [TELEFONE] [EMAIL]`, counts 1/1/1.
- Gate `nenhum` na §7: limites cobertos por teste (protocolo `12345678901` e `11111111111` inalterados; `R$ 1.234,56`, `R$ 150,00`, `2024`, `03/2025` inalterados; sem PII → counts zerado).

**Estado inicial do worktree:** `git status --short` vazio (branch `develop`).

**Ambiente após a verificação:** nada criado (apenas `.pytest_cache` e `.ruff_cache`, ignorados pelo Git).

**Critérios de aceite**
- [x] Positivos substituídos e `counts` correto — `test_positive_cases_are_replaced`, `test_several_pii_in_same_text`.
- [x] Negativos inalterados — `test_negative_cases_stay_unchanged`.
- [x] Idempotência — `test_idempotent`.
- [x] Sem dado real — CPF `52998224725` gerado por algoritmo; e-mails em `exemplo.com`.
- [x] Limites na docstring — `anonymizer.py:1-10`.
- [x] Ambiente e worktree limpos — só os arquivos de §3.1 no `git status`.
- [x] Testes, ruff e validador verdes — ver verificações.
- [x] Nenhum dado real, chave ou `.env` no diff.

**Decisões e suposições**
- Telefone exige marca (`+55`, parênteses, separador `-`/espaço ou celular de 11 dígitos soltos começando com DDD+9); fixo de 8–10 dígitos soltos não é anonimizado, para não apagar protocolos.
- Ordem e-mail → CPF → telefone, para um CPF válido solto não ser lido como celular.
- CPF solto com todos os dígitos iguais é inválido; contagem só conta trocas efetivas.

**Achados fora do escopo (não corrigidos)**
- `ruff` instalado localmente (0.14.2) difere do pinado em `requirements-dev.txt` (0.17.4).

**Pendências / riscos**
- Protocolo solto de 11 dígitos no formato DDD+9+8 dígitos será anonimizado como telefone (ambiguidade inerente).

## Resumo da execução (correção 1) — 2026-11-09

**Resultado:** Concluído

**Achado 1 — CPF com pontuação parcial**
- `src/triage/privacy/patterns.py:6` — `CPF_PATTERN` passa a aceitar `.` e `-` opcionais (`\d{3}\.?\d{3}\.?\d{3}-?\d{2}`). `_replace_cpf` (`anonymizer.py`) não mudou: só o formato totalmente pontuado dispensa validação; as demais formas exigem dígitos verificadores válidos (§5.2 preservada).
- Evidência (execução manual): `529982247-25`, `529.982.24725`, `529.98224725` → `[CPF]`, `cpf` 1. Com dígito inválido (`529982247-26`) → inalterado, counts zerado.
- Testes: positivos nas 3 formas e negativos inválidos nas 3 formas em `tests/privacy/test_anonymizer.py:30-32` e `:46-48`; as formas entram também em `test_idempotent`.

**Achado 2 — telefone com espaço entre os blocos**
- `src/triage/privacy/patterns.py:15-16` — nas alternativas com `+55` e com DDD entre parênteses, o separador entre os blocos passa de `-?` para `[-\s]?`. As alternativas sem marca forte não mudaram, então número solto não é ampliado.
- Evidência (execução manual): `(11) 91234 5678`, `(11) 3234 5678`, `+55 11 91234 5678`, `+55 (11) 3234-5678` → `[TELEFONE]`, `phone` 1; `2024 1234` → inalterado.
- Testes: positivos em `test_anonymizer.py:26-29`; negativo `"ano 2024 1234 e senha 1234 5678"` em `:49`.

**Verificações executadas**
- `python -m pytest tests/privacy -q` → 26 passed.
- `python -m ruff check src/triage/privacy tests/privacy` → All checks passed.
- `validate.py` de `padrao-python` em `src/triage/privacy` e `tests/privacy` → 0 achados.

**Ambiente após a verificação:** removi `.pytest_cache`, `.ruff_cache` e os `__pycache__` de `privacy` que a verificação gerou; nada criado. Os arquivos de `specs/` modificados no worktree (`00-backlog`, `00-indice`, `panorama/00-resumo`) não são meus.

**Decisões e suposições**
- O número solto com espaço (`1234 5678`, `11 91234 5678` sem marca) segue sem anonimização, como o achado exige.

**Pendências / riscos**
- Nenhuma além da ambiguidade de protocolo DDD+9+8 já declarada.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-09 — 🔴 Reprovado

**Verificado (nível escopada), com saída real:** `git status`/`git diff --stat` (só `src/triage/privacy/` e `tests/privacy/` mais esta plan; nada fora do escopo, nada faltando; resumo confere com o diff) · leitura integral de `patterns.py`, `validators.py`, `anonymizer.py`, `__init__.py` e `test_anonymizer.py` · `python -m pytest tests/privacy -q` → 15 passed · `python -m ruff check src/triage/privacy tests/privacy` → All checks passed · `padrao-python/scripts/validate.py` → 0 achados em `src/triage/privacy` e `tests/privacy` · execução manual da §7 → `meu cpf [CPF] tel [TELEFONE] [EMAIL]`, counts 1/1/1 · sem `TODO`, `print`, `noqa`, skip nem comentário citando plan · sondagem com entradas além dos casos da §5.5 (abaixo). Sobraram `.pytest_cache`, `.ruff_cache` e `__pycache__` (o resumo diz só os dois primeiros); removi, e não reprovo por isso.

**Achados**
1. `src/triage/privacy/patterns.py:5` e `src/triage/privacy/anonymizer.py:44-48` (`_replace_cpf`) — CPF **válido** com pontuação parcial não é anonimizado: `529982247-25`, `529.982.24725` e `529.98224725` saem intactos e `counts` fica zerado (o regex só reconhece o CPF totalmente pontuado ou os 11 dígitos colados). Critérios violados: §1 (nenhum CPF sobrevive depois desta etapa) e §5.1 ("11 dígitos com ou sem `.` e `-`"). Exigido: essas formas, quando os dígitos verificadores são válidos, viram `[CPF]` e contam; as mesmas formas com dígitos inválidos continuam inalteradas (regra de §5.2 preservada); teste positivo e negativo para cada forma; idempotência mantida.
2. `src/triage/privacy/patterns.py:11-20` (`PHONE_PATTERN`) — telefone com marca forte (DDD entre parênteses ou `+55`) e **espaço entre os blocos do número** vaza: `(11) 91234 5678`, `(11) 3234 5678` e `+55 11 91234 5678` saem intactos; `+55 (11) 3234-5678` (hífen) é substituído. Critérios violados: §1 e §5.1 (telefone com DDD entre parênteses ou separado por espaço e `+55` opcional). Exigido: com `+55` ou DDD entre parênteses presente, o espaço também separa os blocos do número, sem ampliar para números soltos (não passa a apagar `2024 1234`); teste positivo para cada forma e negativo para o número solto com espaço.

**Sobre o resumo:** confere com o diff, com a ressalva do cache acima. O achado do executor sobre a versão local do ruff (0.14.2 contra 0.17.4 pinado) é da máquina, não do repositório: descartado, sem item no backlog.

## Veredito (correção 1) — 2026-11-09 — 🟢 Aprovado

**Verificado (nível escopada), com saída real:**
- `git status` / `git diff --stat` → só `src/triage/privacy/` (`__init__.py` alterado; `anonymizer.py`, `patterns.py`, `validators.py` criados), `tests/privacy/` e esta plan; fora o que é meu (`00-indice`, `00-backlog`, `panorama/00-resumo`), nada fora do escopo de §3.1. O resumo da correção confere com o código: `patterns.py:6` (`CPF_PATTERN` com `.` e `-` opcionais) e `patterns.py:15-16` (`[-\s]?` só nas alternativas com `+55` e com DDD entre parênteses).
- `python -m pytest tests/privacy -q` → 26 passed.
- `python -m ruff check src/triage/privacy tests/privacy` → All checks passed.
- `padrao-python/scripts/validate.py` → 0 achados em `src/triage/privacy` e `tests/privacy`.
- Execução manual da §7 → `meu cpf [CPF] tel [TELEFONE] [EMAIL]`, counts 1/1/1.

**Achado 1 (CPF com pontuação parcial) — resolvido.** `529982247-25`, `529.982.24725`, `529.98224725` → `[CPF]`, `cpf` 1; as mesmas formas com dígito verificador inválido (`...-26`, `...24726`, `.98224726`) permanecem inalteradas; o formato totalmente pontuado segue sempre CPF (§5.2). Testes: positivos e negativos das três formas em `tests/privacy/test_anonymizer.py`.

**Achado 2 (telefone com espaço entre blocos) — resolvido.** `(11) 91234 5678`, `(11) 3234 5678`, `+55 11 91234 5678` e `+55 (11) 3234-5678` → `[TELEFONE]`, `phone` 1. Sem ampliação indevida: `ano 2024 1234`, `1234 5678`, `R$ 1.234.567,89`, `123.456.789.01`, `12.345.678-90`, `01310-100` e `529.982.247,25` ficam inalterados.

**Idempotência:** `anonymize(anonymize(x).text).text == anonymize(x).text` para um texto com CPF parcial, dois telefones com espaço e e-mail → `True`.

**Critérios de aceite (§6):** todos atendidos — positivos e negativos de §5.5 (e os novos) nos testes, idempotência, dados sintéticos (CPF `529.982.247-25` gerado por algoritmo, e-mails em `exemplo.com`), limites declarados na docstring de `anonymizer.py`, sem dado real, chave ou `.env`.

**Ambiente:** restava `src/triage/__pycache__/` (ignorado pelo Git); removido, e `git status --ignored` voltou limpo. Sem processo nem arquivo temporário.

**Achados novos:** nenhum. Resíduos de formas raras já estão no backlog (item 4).

