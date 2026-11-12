---
tipo: "adr"
titulo: "Infraestrutura: execução local/Colab, sem deploy em nuvem"
status: "🟢 Aceito"
tags: ["adr", "infra"]
relacionados: ["[[001-stack-principal]]", "[[002-persistencia-sqlite-e-arquivos]]"]
substitui: ""
substituido_por: ""
alternativas_consideradas:
  - "Deploy na Vercel — descartada porque a função serverless tem disco efêmero (SQLite não persiste) e não hospeda uma aplicação Streamlit."
  - "Docker em servidor próprio — descartada porque exige servidor e operação fora do escopo e do prazo de um protótipo acadêmico."
---

# 1. Contexto e Problema
Havia a ideia de publicar na Vercel pela simplicidade. O estado operacional (fila de revisão, feedback e
idempotência) está em SQLite local ([[002-persistencia-sqlite-e-arquivos]]) e a interface é Streamlit
([[001-stack-principal]]); ambos conflitam com o modelo serverless.

# 2. Alternativas consideradas

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| Vercel | Publicação simples e link público | Disco efêmero apaga o estado; sem suporte a Streamlit |
| Docker em servidor | Persistência e controle | Servidor e operação fora do escopo |

# 3. Decisão
Execução **local** com ponto de entrada claro (`python run.py` para o robô; `streamlit run app.py` para a
interface), mais um notebook (Colab/Jupyter) como alternativa de reprodução. Instruções no README. Sem CI/CD
e sem deploy em nuvem.

# 4. Consequências
- **Positivas:** qualquer avaliador reproduz com o README; nenhuma conta ou custo.
- **Negativas (Trade-offs):** sem link público para demonstração; apresentar exige rodar localmente ou
  gravar a execução como evidência.
