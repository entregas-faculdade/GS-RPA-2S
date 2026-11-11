---
tipo: "adr"
titulo: "LLM: redige a resposta sobre fontes recuperadas do catálogo (RAG), com guarda na saída"
status: "🟢 Aceito"
tags: ["adr", "llm", "rag", "governanca", "privacidade"]
relacionados: ["[[003-seguranca-sem-autenticacao]]", "[[03.02-resposta-final-e-llm]]", "[[03.03-localizador-de-servicos]]", "[[03.04-agente-llm]]"]
substitui: "[[006-llm-escolhe-apenas-entre-fontes-aprovadas]] e a parte da [[005-llm-apenas-reformula-resposta]] que limitava o LLM a reformular a resposta já decidida"
substituido_por: ""
alternativas_consideradas:
  - "LLM escolhe um id de lista fechada e o texto vem do catálogo (a 006) — descartada porque a resposta fica engessada e não responde à pergunta específica do cidadão, além de exigir um modo opt-in separado."
  - "Agente livre com ferramentas, sem recuperação nem guarda — descartada porque inventa link e telefone, não se mede e não cabe no prazo."
---

# 1. Contexto e Problema
As ADRs 005 e 006 deixaram o LLM de lado: ele reformulava um template ou, em modo opt-in, escolhia um id. O grupo definiu o sistema
como **um fluxo só**: a pergunta é anonimizada antes de qualquer envio, o LLM participa da formulação da resposta que volta ao
usuário e o catálogo com suas informações é o RAG do agente. O enunciado continua tornando o LLM opcional e proibindo dado pessoal
real em API.

# 2. Alternativas consideradas

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| LLM escolhe um id, texto do catálogo (006) | Superfície mínima: o LLM não escreve nada mostrado | Resposta engessada, não atende à pergunta específica |
| Agente livre com ferramentas | Máxima fluência e autonomia | Inventa link e telefone, não se mede, não cabe no prazo |
| LLM redige sobre fontes recuperadas, com guarda (escolhida) | Resposta natural e específica, ancorada no catálogo | Custo: texto livre do LLM (mitigado pela guarda) e toda pergunta anonimizada sai do computador |

# 3. Decisão
- **Recuperação determinística:** as fontes enviadas ao LLM são entradas aprovadas do catálogo com link vivo (o serviço resolvido e as
  candidatas do localizador); o LLM não vê nada fora delas.
- **O LLM redige** a resposta a partir da pergunta **anonimizada** e dessas fontes; quando nenhuma serve, responde `NENHUMA_FONTE`.
- **Guarda na saída:** todo link e todo telefone da resposta têm de pertencer às fontes enviadas, e ao menos um deles tem de
  aparecer; saída vazia, longa demais ou com link ou telefone alheio é descartada.
- **Falha segura:** indisponibilidade, resposta inválida ou saída rejeitada voltam ao fluxo determinístico (template do catálogo ou
  "não tenho a informação"); sem LLM o sistema funciona integralmente.
- **Fora do LLM:** a mensagem de emergência, a revisão de pedido ambíguo e o caso de modelo ausente nunca chamam o LLM.
- Um único interruptor (`llm.enabled`); não há modo de localização separado.

# 4. Consequências
- **Positivas:** respostas naturais e específicas, ainda ancoradas no catálogo aprovado; falha ou injeção no pedido não produz link
  ou telefone fora das fontes; o caminho determinístico segue como base e como fallback.
- **Negativas (Trade-offs):** com o LLM ligado, **toda** pergunta anonimizada sai do computador rumo ao provedor, com o risco residual
  da anonimização ([[01.03-anonimizacao-de-pii]] §2.7); o texto da resposta passa a ser livre, e a guarda só garante link e telefone,
  não a exatidão das instruções redigidas; há latência e custo de chamada em toda resposta; voltar atrás tem custo, porque quem passa
  a depender das respostas redigidas perde naturalidade ao desligar o LLM.
