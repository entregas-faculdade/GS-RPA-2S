---
tipo: "plan"
familia: "01"
item: "R01.3"
titulo: "Anonimizar CPF, telefone e e-mail antes de qualquer log ou chamada externa"
dominio: "Núcleo do robô"
status: "🟡 Em execução"
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

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
