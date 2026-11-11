---
tipo: "adr"
titulo: "LLM: além de reformular, escolhe a fonte apenas entre candidatas aprovadas, em modo opt-in"
status: "🟢 Aceito"
tags: ["adr", "llm", "governanca", "privacidade"]
relacionados: ["[[005-llm-apenas-reformula-resposta]]", "[[003-seguranca-sem-autenticacao]]", "[[03.02-resposta-final-e-llm]]", "[[03.03-localizador-de-servicos]]", "[[03.04-agente-llm]]"]
substitui: "[[005-llm-apenas-reformula-resposta]] (só na parte que vedava ao LLM qualquer escolha; o resto da 005 segue valendo)"
substituido_por: ""
alternativas_consideradas:
  - "LLM só reformula, sem ajudar a localizar (a decisão da 005) — descartada como único modo porque, quando o localizador determinístico não acha a fonte, o cidadão recebe só \"não tenho a informação\" mesmo havendo uma fonte aprovada adequada."
  - "LLM escolhe livremente a fonte ou escreve link, telefone e instrução — descartada porque abre alucinação e injeção de prompt: um link ou telefone inventado chegaria ao cidadão."
---

# 1. Contexto e Problema
A [[005-llm-apenas-reformula-resposta]] fixou que o LLM só reformula a resposta já decidida e nunca escolhe categoria nem
URL. O grupo quer que ele também **ajude a localizar** a fonte quando o localizador determinístico
([[03.03-localizador-de-servicos]]) não resolve. O enunciado torna o LLM opcional e proíbe dado pessoal real em API.

# 2. Alternativas consideradas

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| LLM só reformula (005) | Superfície mínima; nenhum texto do cidadão sai | Perde pedidos que uma fonte aprovada atenderia |
| LLM escolhe livremente ou escreve a fonte | Cobertura máxima, linguagem natural | Alucinação e injeção de prompt chegariam ao cidadão |
| LLM escolhe um `id` de lista fechada (escolhida) | Ganha cobertura sem confiar no texto do LLM | Custo: o texto anonimizado sai do computador |

# 3. Decisão
- O LLM **escolhe um `id` entre até 5 fontes aprovadas** que o localizador apresenta; nunca escreve link, telefone, órgão
  ou instrução. A resposta é só `{"id": "<id da lista>"}` ou `{"id": "none"}`, validada com rigor: qualquer outra saída é
  "sem fonte" e o pedido segue para "não tenho a informação".
- Escolha válida passa pela mesma verificação de links do catálogo e responde com o **template do catálogo**.
- O modo é um **interruptor separado**, `LLM_ASSIST_LOCATE`, desligado por padrão e dependente de `LLM_ENABLED`. Sem ele,
  nenhum texto do cidadão vai ao provedor. A reformulação (modo anterior) continua sem enviar texto do cidadão.
- Só o texto **anonimizado** é enviado; o risco residual da anonimização continua declarado em
  [[01.03-anonimizacao-de-pii]]. O resto da 005 (núcleo determinístico, guarda da saída, falha segura, funcionamento
  integral sem LLM) segue valendo.

# 4. Consequências
- **Positivas:** mais pedidos respondidos sem abrir mão de a fonte, o link e o telefone virem sempre do catálogo aprovado;
  falha ou injeção no pedido não produz resposta fora da lista.
- **Negativas (Trade-offs):** no modo ligado, o texto anonimizado do cidadão sai do computador rumo ao provedor, com o risco
  residual da anonimização; há latência e custo de chamada a mais; voltar atrás tem custo, porque quem passa a depender do
  modo perde cobertura ao desligá-lo.
