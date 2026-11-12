---
tipo: "adr"
titulo: "LLM: apenas reformula a resposta final; classificação e link são determinísticos"
status: "🟢 Aceito"
tags: ["adr", "llm", "governanca"]
relacionados: ["[[003-seguranca-sem-autenticacao]]", "[[001-stack-principal]]"]
substitui: ""
substituido_por: "[[007-llm-redige-a-resposta-com-rag-do-catalogo]] (parcial: só quanto a o LLM apenas reformular)"
alternativas_consideradas:
  - "LLM como classificador/roteador — descartada porque torna a decisão não determinística, difícil de medir e de auditar, e aumenta risco de alucinação e injeção de prompt."
  - "Sem LLM — descartada como padrão porque a interação em linguagem natural foi um desejo explícito do grupo, e o LLM é opcional e permitido pelo enunciado."
---

# 1. Contexto e Problema
O enunciado torna o LLM opcional, mas exige, se usado, tratar resposta vazia ou inválida e ter caminho
seguro na falha, sem enviar dado pessoal real a nenhuma API. O grupo quer uma resposta em linguagem natural.

# 2. Alternativas consideradas

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| LLM classifica e roteia | Entende pedidos muito livres | Não determinístico, difícil de medir, risco de alucinação/injeção |
| Sem LLM | Máxima segurança e reprodutibilidade | Perde a interação natural pedida pelo grupo |

# 3. Decisão
- O **núcleo é determinístico**: regex + TF-IDF classificam; o catálogo com allowlist fornece o link
  ([[003-seguranca-sem-autenticacao]]).
- O **LLM só reformula** a resposta final em linguagem natural. Recebe somente texto **já anonimizado** e a
  resposta/link **já decididos**; não escolhe categoria nem inventa URL.
- **Validação da saída:** qualquer URL na resposta do LLM deve estar na allowlist e igualar o link decidido;
  caso contrário, descarta-se a saída.
- **Falha segura:** timeout, erro, resposta vazia ou inválida → resposta-padrão em template, com log.
- **Provedor e chave:** a definir em plan, apenas free tier; chave em `.env` fora do repositório.
- O sistema funciona integralmente com o LLM desligado (flag de configuração).

# 4. Consequências
- **Positivas:** acerto medível sem depender do LLM; falha do LLM não derruba nada; superfície de ataque menor.
- **Negativas (Trade-offs):** a "conversa" é limitada a reformular — não esclarece nem desambigua pedidos;
  há latência e dependência de rede/cota quando o LLM está ligado.
