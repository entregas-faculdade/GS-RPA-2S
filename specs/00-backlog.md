---
tipo: "processo"
titulo: "Backlog — Achados Registrados, Não Agendados"
dominio: "Governança de Specs (SDD)"
status: "🟢 Vigente"
tags: ["processo", "backlog", "achados", "sdd"]
relacionados: ["[[00-indice]]", "[[00-prompt-revisor]]", "[[00-prompt-executor]]"]
---

# 0. O que é este arquivo

O lugar onde um achado **descansa**. Nem executado, nem esquecido.

Antes deste arquivo existir, um problema encontrado no meio do caminho tinha só dois destinos: virar
trabalho **agora** (uma plan nova, um ciclo inteiro) ou se perder. Como a doutrina proíbe perder, tudo
virava trabalho — e cada execução gerava as próximas, sem caso-base. Este arquivo é o caso-base.

**Um item aqui não é uma plan.** Não tem `NN`, não tem status, não entra em fila, ninguém o executa. É uma
linha dizendo *"isto existe e alguém olhou"*. Só vira trabalho quando **o usuário** manda — e aí passa pela
triagem normal ([[00-prompt-revisor]] §4) como qualquer outra demanda.

**Quem escreve:** o **revisor**, sempre. O executor **relata** achados no resumo dele (é o formato da
[[00-prompt-executor]] §5); quem transcreve para cá é o revisor, no veredito.
**Quem promove:** só o **usuário**. Nenhum agente decide sozinho que chegou a hora de um item.
**Quem remove:** quem promoveu (o item sai daqui quando vira plan ou prompt direto) — ou o revisor, ao
registrar um achado novo (§4), quando encontra um antigo que deixou de valer. O usuário pode podar a
qualquer momento.

---

# 1. A regra que este arquivo sustenta

> **Achado descoberto durante a execução da plan-N não vira trabalho antes da plan-N fechar.**

Sem exceção. Ele desce para cá, e o ciclo em andamento termina primeiro. Isso é o que impede o aninhamento:
uma execução nunca abre outra execução por dentro.

Três coisas alimentam este arquivo:

| Origem | Quem traz | Quando |
|---|---|---|
| Achado fora do escopo | executor, no resumo | o revisor transcreve no veredito |
| Divergência entre spec fixa e código | revisor, no ritual de entrada | ao encontrar |
| Ressalva relevante que não reprova a execução | revisor, no veredito | ao aprovar |

**Nada aqui é urgente por estar aqui.** Se um achado é grave a ponto de não poder esperar, ele não é backlog
— é uma demanda que o revisor leva ao usuário na hora, em texto livre, e que vira plan ou prompt direto pela
via normal.

---

# 2. A tabela

> **Como escrever:** uma linha por achado, e **uma linha só**. Se você precisa de um parágrafo, o item não é
> achado — é uma demanda; leve ao usuário.
>
> - **#** — sequencial simples. Reaproveitável: sai um, o número volta a ficar livre. Isto **não** é `plan-FF.NN`.
> - **Achado** — o que há de errado, em uma frase, com `arquivo:linha` quando existir.
> - **Origem** — `execução`, `via direta` ou `ritual`. **Nunca `plan-FF.NN`**: a plan é removida na síntese e a
>   referência morre. Saber que o achado veio de uma execução basta; de qual plan, não ajuda depois que ela sai.
> - **Registrado em** — data absoluta (`AAAA-MM-DD`).
> - **Peso** — `alto` · `médio` · `baixo`. É uma dica ao usuário, não uma fila: nada aqui é agendado.

| # | Achado | Origem | Registrado em | Peso |
|---|---|---|---|---|
| 1 | `ruff check .` falha em `.githooks/verify_commit.py:204` (E731, arquivo vindo da base) e os critérios das plans 04.03 e 05.01 usam `ruff check .`; falta um `ruff.toml` do repositório que fixe as regras e exclua `.githooks/` | execução | 2026-11-09 | médio |
| 2 | `pip install -r requirements-dev.txt` falha no Windows em ambiente virtual com caminho longo (jupyterlab, "Long Path support"); passou em caminho curto — registrar no README de entrega | execução | 2026-11-09 | baixo |
| 3 | `sanitizer.py:36-38` — `MAX_TEXT_LENGTH` é checado no texto bruto antes da normalização NFKC, que pode expandir caracteres (ex.: `ﷺ` vira 18 caracteres): o texto sanitizado pode passar de 2000, e quem consumir `Request.text` não deve presumir esse teto | execução | 2026-11-09 | baixo |
| 4 | `privacy/patterns.py` — formas raras deixam resíduo: DDD com zero (`011 91234-5678` → `011 [TELEFONE]`) e e-mail com letra acentuada na parte local (`joão@exemplo.com` → `joã[EMAIL]`); `4 dígitos-4 dígitos` como protocolo (`2024-1234`) vira `[TELEFONE]` (precisão aceita a favor da garantia) | execução | 2026-11-09 | baixo |
| 5 | `tests/storage/test_hashing.py:13` — `test_hash_ignores_unicode_composition` compara "ã" composto com "a" + acento combinante, indistinguíveis no editor; escrever as duas formas com escapes Unicode para a intenção ficar legível | execução | 2026-11-09 | baixo |

---

# 3. Promover um item

Só o usuário dispara. Ao promover, o **revisor**:

1. Tria o item pela [[00-prompt-revisor]] §4 — plan se deixa verdade documentada, prompt direto se não.
2. Conduz a via escolhida como qualquer outra demanda.
3. **Remove a linha daqui**, na mesma ação. Item promovido não fica de lembrança: a partir daí quem responde
   por ele é o [[00-indice]] (se virou plan) ou a própria conversa (se virou prompt direto).

Promover **não** é obrigatório e não tem prazo. Um item pode ficar aqui indefinidamente sem que isso seja
dívida — é exatamente para isso que ele existe.

---

# 4. Regras de manutenção

- **Este arquivo não cresce sem limite, e o dreno tem gatilho.** Ele registra o que **ainda** é verdade.
  **Ao registrar um achado, o revisor relê os que já estão aqui** — é a única vez em que alguém abre o
  arquivo inteiro, e por isso é onde ele se drena. Achado corrigido de passagem por outra tarefa, código que
  deixou de existir, problema que a spec fixa passou a permitir: a linha **sai** na mesma ação, e o revisor
  diz isso na resposta. Regra de limpeza sem gatilho não roda — foi assim que o índice virou cemitério.
- **Não duplique.** Antes de registrar, procure — o mesmo achado visto em duas execuções é uma linha só.
- **Sem status, sem dono, sem prazo.** Se você sentiu falta de um desses campos, o item não é backlog: é
  plan. Promova ou deixe.
- **Nunca referencie um item daqui dentro do código.** Vale a mesma regra da plan: comentário não cita
  `backlog #3` (norma completa em `padrao-escrita`, `references/comentarios.md`).
- **Item que já está numa plan não fica aqui.** Um dos dois é a verdade — e é o [[00-indice]].
