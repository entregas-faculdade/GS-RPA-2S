---
tipo: "plan"
familia: "04"
item: "R04.2"
titulo: "Criar a interface Streamlit de atendimento, fila de revisão e feedback"
dominio: "Operação e interface"
status: "🔴 A executar"
prioridade: "Média"
tags: ["plan"]
relacionados: ["[[001-stack-principal]]", "[[003-seguranca-sem-autenticacao]]", "[[004-infra-execucao-local]]"]
depende_de: "plan-04.03-orquestracao-rpa"
destino_sintese: "specs/04.02-interface.md"
---

# 1. Objetivo
`streamlit run app.py` abre uma tela onde o cidadão digita um pedido, recebe a resposta (ou o aviso de encaminhamento
humano) e avalia com 👍/👎, e onde há uma aba de revisão com a fila pendente.

# 2. Contexto
Decisão de interface local ([[001-stack-principal]], [[004-infra-execucao-local]]): Streamlit roda **localmente**; o
Colab não o suporta sem túnel, então a avaliação remota usa `run.py` e o notebook (plan 05.01). A interface é **fina**:
chama `triage.pipeline.process_request` e `triage.storage`; **não** contém regra de negócio. Sem autenticação
([[003-seguranca-sem-autenticacao]]); a aba de revisão fica sem login (limite declarado).

# 3. Escopo
## 3.1 Dentro
- `app.py` — ponto de entrada Streamlit (apenas montagem e chamada das telas)
- `src/triage/interface/service.py` — `AppService`: monta as dependências (`Repository`, modelo, catálogo, cliente LLM opcional) e expõe `submit(text)`, `pending_reviews()`, `resolve(id, note)`, `send_feedback(hash, rating)`
- `src/triage/interface/views.py` — funções de renderização (`render_citizen_tab`, `render_review_tab`)
- `src/triage/interface/__init__.py`
- `tests/interface/` — testes do `AppService` (a UI em si é conferida manualmente)

## 3.2 Fora
- Autenticação, perfis e deploy (ADRs 003 e 004).
- Qualquer regra de classificação, revisão ou resposta (já nos pacotes do núcleo).
- Edição do catálogo pela interface.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[001-stack-principal]] | Streamlit como interface |
| ADR | [[004-infra-execucao-local]] | execução local, sem deploy |
| ADR | [[003-seguranca-sem-autenticacao]] | limites de acesso e proteção de PII |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Código | `src/triage/pipeline/processor.py`, `src/triage/storage/` | o que a interface chama |

# 5. Instruções de execução
1. [dirigido] `AppService.submit(text)`: sanitiza (via ingestão), cria `Request` com id gerado, chama `process_request` e devolve `ProcessingResult` + o `hash` do pedido (para o feedback). Entrada vazia/inválida → mensagem amigável, sem exceção para a UI.
2. [dirigido] Aba **Cidadão**: caixa de texto, botão enviar, exibição da resposta **ou** do aviso "encaminhamos seu pedido para atendimento humano" (sem expor o motivo técnico), botões 👍/👎 que chamam `send_feedback` uma única vez por resposta.
3. [dirigido] Aba **Revisão**: lista de `pending_reviews()` com categoria sugerida, confiança, motivo e texto **anonimizado**; botão para marcar como resolvido com nota. Aviso visível: "dados de demonstração; não envie dados pessoais reais".
4. [dirigido] Banner na tela inicial: protótipo acadêmico, dados sintéticos, sem dado pessoal real.
5. [dirigido] Dependências e modelo montados uma vez (`st.cache_resource`); falha ao montar (modelo ausente, banco inacessível) → mensagem clara na tela e log, sem traceback.
6. [dirigido] Testes do `AppService` com dependências simuladas: pedido respondido; pedido para revisão; entrada vazia; feedback duplicado ignorado; resolução de revisão.
7. Rodar `python -m pytest tests/interface -q`, `ruff` e **abrir a interface manualmente** (`streamlit run app.py`), percorrendo os fluxos de §6.

# 6. Critérios de aceite
- [ ] `streamlit run app.py` sobe sem erro e a aba Cidadão responde a "onde tiro minha CNH?" com o link do catálogo.
- [ ] Pedido com termo de urgência mostra o aviso de encaminhamento humano e aparece na aba Revisão.
- [ ] 👍/👎 grava um feedback por resposta (verificar no SQLite de teste).
- [ ] Texto exibido na aba Revisão é o anonimizado; nenhum PII aparece em tela ou log.
- [ ] `app.py` não contém regra de negócio (só montagem e renderização).
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhum dado pessoal real, nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/interface -q` → verde.
- `python -m ruff check app.py src/triage/interface tests/interface` → sem erro.
- Verificação **visual no navegador**: `streamlit run app.py`; enviar (1) pedido de CNH, (2) pedido urgente, (3) texto vazio, (4) texto com um CPF fictício; conferir resposta, aviso, aba Revisão e que o CPF aparece como `[CPF]`.
- Encerrar o processo do Streamlit ao final; o revisor confirma que nada ficou rodando e que não há `.db` no worktree.
- **Gate:** `nenhum — a UI é conferida visualmente; a lógica está nos pacotes testados`.

# 8. Destino da síntese
**Destino:** `specs/04.02-interface.md`

Levar: telas (Cidadão e Revisão) e o comportamento de cada uma; regra "interface fina, sem regra de negócio";
mensagens ao cidadão para resposta e encaminhamento; limite declarado de que a revisão não tem autenticação; como
iniciar (`streamlit run app.py`) e por que não roda no Colab.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
