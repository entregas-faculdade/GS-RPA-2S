---
tipo: "adr"
titulo: "Stack principal: Python com interface Streamlit"
status: "🟢 Aceito"
tags: ["adr", "stack"]
relacionados: ["[[002-persistencia-sqlite-e-arquivos]]", "[[004-infra-execucao-local]]"]
substitui: ""
substituido_por: ""
alternativas_consideradas:
  - "Flask/FastAPI + HTML/JS — descartada porque exige escrever e manter o front separado, ampliando o escopo de um protótipo cujo valor está no robô."
  - "Node/TypeScript ponta a ponta — descartada porque o ecossistema de NLP clássico (TF-IDF, classificadores) é mais pobre e a equipe/disciplina trabalham em Python."
---

# 1. Contexto e Problema
O enunciado (AI for RPA, GS 2026.2) pede um robô que rode do início ao fim a partir de um ponto de entrada
claro, com NLP e regras, só com ferramentas gratuitas. O usuário também quer uma interface para o cidadão
enviar o pedido e avaliar a resposta (👍/👎).

# 2. Alternativas consideradas

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| Flask/FastAPI + HTML/JS | Controle total da UI e da API | Dois códigos (back e front) para manter num protótipo curto |
| Node/TypeScript | Um só idioma no front e no back | NLP clássico mais fraco; fora do ecossistema da disciplina |

# 3. Decisão
- **Linguagem:** Python.
- **Núcleo do robô:** módulos Python puros (ingestão, sanitização/PII, classificação, automação), sem
  dependência da interface, para rodar também por linha de comando (`python run.py`).
- **NLP/ML:** `scikit-learn` (TF-IDF + classificador linear) e `re` da biblioteca padrão.
- **Interface:** Streamlit, sobre o mesmo núcleo, para entrada do pedido, resposta e feedback 👍/👎.

# 4. Consequências
- **Positivas:** uma linguagem só; interface em poucas linhas; núcleo testável sem UI.
- **Negativas (Trade-offs):** Streamlit tem pouco controle de layout e não se publica na Vercel (ver
  [[004-infra-execucao-local]]); a interface é de demonstração, não de produção.
