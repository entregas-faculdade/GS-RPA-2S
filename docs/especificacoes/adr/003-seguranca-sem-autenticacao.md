---
tipo: "adr"
titulo: "Segurança: sem login; proteção por sanitização, anonimização de PII e allowlist"
status: "🟢 Aceito"
tags: ["adr", "seguranca", "governanca"]
relacionados: ["[[001-stack-principal]]", "[[005-llm-apenas-reformula-resposta]]"]
substitui: ""
substituido_por: ""
alternativas_consideradas:
  - "Login simples (usuário/senha ou OAuth) — descartada porque o protótipo usa só dados sintéticos e o custo de gestão de contas e segredos supera o ganho."
  - "Chave de API única na interface — descartada porque dá falsa sensação de proteção, sem separar perfis, e é mais uma credencial a vazar."
---

# 1. Contexto e Problema
O protótipo roda local, com dados sintéticos e públicos, sem dado pessoal real. O risco real não é acesso
indevido, e sim entrada maliciosa, vazamento de PII em log/API e link para domínio não confiável.

# 2. Alternativas consideradas

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| Login (senha/OAuth) | Separa perfis (cidadão × revisor) | Complexidade e segredos sem retorno num protótipo local |
| Chave de API única | Barra acesso casual | Falsa proteção; mais uma credencial |

# 3. Decisão
Sem autenticação nem autorização. A segurança é feita por controles do próprio fluxo:
1. **Sanitização da entrada:** limite de tamanho, normalização de encoding, remoção/neutralização de
   HTML/SQL/controle; entrada inválida vai para log e caminho seguro, sem derrubar a execução.
2. **Anonimização de PII** (CPF, telefone, e-mail) por regex **antes** de qualquer log ou envio a API.
3. **Allowlist de domínios** (`.gov.br` e órgãos oficiais): o robô só responde com link dessa lista.
4. **Segredos** (ex.: chave de LLM) só em `.env` fora do repositório; `.env.example` sem valor.
5. **Revisão humana** para baixa confiança, ambiguidade, urgência/sensibilidade e fora do catálogo.

# 4. Consequências
- **Positivas:** nada de contas ou senhas; a governança fica explícita e auditável no fluxo.
- **Negativas (Trade-offs):** qualquer pessoa com acesso à máquina vê a fila de revisão; perfis de revisor
  ficam declarados como limite e evolução.
