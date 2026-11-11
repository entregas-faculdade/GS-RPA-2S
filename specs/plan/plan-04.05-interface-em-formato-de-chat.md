---
tipo: "plan"
familia: "04"
item: "R04.5"
titulo: "Mostrar a aba Cidadão como um chat, com a conversa na tela e avaliação por resposta"
dominio: "Interface"
status: "🟡 Em execução"
prioridade: "Média"
tags: ["plan"]
relacionados: ["[[04.02-interface]]", "[[04.03-orquestracao-rpa]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "—"
destino_sintese: "specs/04.02-interface.md"
---

# 1. Objetivo
A aba **Cidadão** passa a ser um chat: o usuário escreve numa caixa de mensagem, a conversa fica visível na tela (pergunta e resposta, em ordem) e cada
resposta tem sua própria avaliação 👍/👎. Cada mensagem continua sendo um pedido **independente** para o pipeline.

# 2. Contexto
O usuário quer a interação direta por chat. Hoje a aba tem uma caixa de texto, o botão "Enviar pedido" e uma única resposta na tela
(`render_citizen_tab` em `src/triage/interface/views.py`); a decisão e a persistência estão no `AppService.submit`, que **não muda**. Nesta plan o
**histórico não vai ao LLM nem ao pipeline**: ele existe só para exibição, na memória da sessão do Streamlit, e some ao recarregar. Conversa de várias
voltas (contexto entre mensagens) fica fora de escopo.

# 3. Escopo
## 3.1 Dentro
- `src/triage/interface/views.py` — `render_citizen_tab` em formato de chat (`st.chat_input`, `st.chat_message`), histórico de exibição na sessão e avaliação por resposta
- `app.py` — só se a montagem da aba exigir ajuste mínimo
- `tests/interface/` — testes do novo formato (com `streamlit.testing.v1.AppTest` ou o padrão já usado ali)

## 3.2 Fora
- `AppService`, `triage.pipeline`, `triage.storage`, o LLM e o catálogo: nenhuma regra de negócio muda.
- A aba **Revisão**, o banner e os textos de aviso.
- Enviar o histórico ao pipeline ou ao LLM; gravar a conversa em disco ou em banco; qualquer log do texto do usuário.
- `README.md` (a síntese e o ajuste do texto do README são do revisor, depois).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | `specs/04.02-interface.md` | comportamento atual da aba, desfechos e avaliação |
| Spec fixa | `specs/arquitetura/04.03-orquestracao-rpa.md` | desfechos que o `AppService` devolve |
| ADR | [[003-seguranca-sem-autenticacao]] | aviso de dado pessoal e nenhum texto em log |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | limiares e zero hardcoded |
| Skill | `test-unitario` | testes da interface |
| Código | `src/triage/interface/views.py`, `src/triage/interface/service.py`, `app.py`, `tests/interface/` | o que muda e como é testado hoje |

# 5. Instruções de execução
1. [dirigido] **Chat.** `render_citizen_tab` mostra o histórico (pares pergunta/resposta, em ordem de chegada) com `st.chat_message` e recebe a mensagem por `st.chat_input`.
   Cada envio chama `AppService.submit(texto)` uma única vez e acrescenta ao histórico a pergunta digitada e o desfecho (resposta, encaminhamento ou aviso), com o mesmo estilo
   de mensagem que a aba tem hoje para cada tipo de desfecho (respondido, encaminhado, inválido, erro). Texto em branco não envia.
2. [dirigido] **Avaliação por resposta.** Cada resposta com `request_hash` tem seus botões 👍/👎 com chave própria; avaliar uma não afeta as outras; a avaliação duplicada mostra o aviso
   que já existe; o encaminhamento à revisão e o inválido não mostram avaliação, como hoje. Nenhum botão "Enviar pedido" resta.
3. [dirigido] **Privacidade.** O histórico vive só em `st.session_state`; nada dele vai a log, arquivo ou banco, e o banner de dado pessoal permanece.
4. [dirigido] **Testes** (sem rede): pergunta respondida aparece com a resposta; duas perguntas mantêm a ordem; avaliação de uma não marca a outra; encaminhado e inválido sem avaliação;
   texto em branco não chama `submit`; cada envio chama `submit` com **só** o texto da mensagem (sem histórico); recarregar a sessão limpa a conversa.
5. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] A aba Cidadão mostra a conversa em formato de chat, com a ordem das mensagens preservada e a resposta de cada pergunta logo abaixo dela.
- [ ] Cada envio chama `AppService.submit` com apenas o texto digitado; o histórico nunca chega ao núcleo.
- [ ] A avaliação 👍/👎 é por resposta e independente.
- [ ] Nenhum texto do usuário em log, arquivo ou banco além do que o `AppService` já grava; o banner de aviso permanece.
- [ ] `AppService` e o núcleo não foram alterados; testes do escopo verdes; `ruff` e validador sem violação nova.
- [ ] Ambiente e worktree limpos.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/interface -q` → verde.
- `python -m ruff check src/triage/interface app.py tests/interface` → sem erro novo.
- `validate.py` do `padrao-python` em `src/triage/interface/views.py` e nos testes alterados → sem achado.
- Leitura de `views.py` → confirma que não há `print`, log de texto do usuário nem escrita em disco.
- **Gate:** `nenhum — coberto por testes`.

# 8. Destino da síntese
**Destino:** `specs/04.02-interface.md`

Escrever, no lugar do que a spec diz hoje da aba Cidadão: a aba é um chat (`st.chat_input`/`st.chat_message`); o histórico é só de exibição, mora na sessão e some ao recarregar;
cada mensagem é um pedido independente (nenhum contexto entre mensagens); a avaliação 👍/👎 é por resposta; encaminhamento e inválido não têm avaliação.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
