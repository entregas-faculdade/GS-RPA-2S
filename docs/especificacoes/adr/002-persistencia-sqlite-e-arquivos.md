---
tipo: "adr"
titulo: "Persistência: arquivos (CSV/JSON) + SQLite local, sem cache"
status: "🟢 Aceito"
tags: ["adr", "persistencia"]
relacionados: ["[[001-stack-principal]]", "[[004-infra-execucao-local]]"]
substitui: ""
substituido_por: ""
alternativas_consideradas:
  - "Postgres gerenciado (ex.: Supabase free tier) — descartada porque exige conta, rede e chaves em variável de ambiente, e quebra a execução offline e a reprodução sem ajuda."
  - "Só arquivos (CSV/JSON), sem banco — descartada porque idempotência, fila de revisão e feedback precisam de escrita incremental e consulta, frágeis em arquivo plano."
---

# 1. Contexto e Problema
O robô precisa (a) ler entradas e o catálogo de serviços, (b) garantir idempotência (não reprocessar o mesmo
pedido), (c) manter a fila de revisão humana e (d) guardar o feedback 👍/👎. O enunciado exige que rode do
início ao fim e seja reprodutível pelo README.

# 2. Alternativas consideradas

| Alternativa | Por que era defensável | Por que foi descartada |
|---|---|---|
| Postgres gerenciado | Persiste online, multiusuário | Dependência externa e chaves; piora a reprodutibilidade |
| Só arquivos | Zero dependência | Sem transação nem consulta; idempotência e fila ficam frágeis |

# 3. Decisão
- **Entradas e saídas:** CSV/JSON em `data/` (dados sintéticos, nunca pessoais reais).
- **Catálogo de serviços:** `catalogo.json` versionado (categoria → órgão → URL oficial → fonte → data de verificação).
- **Estado operacional:** um arquivo SQLite local com as tabelas de pedidos processados (hash para
  idempotência), fila de revisão e feedback. O arquivo `.db` não é versionado.
- **Cache:** nenhum.

# 4. Consequências
- **Positivas:** zero infraestrutura; reprodutível com `python run.py`; transações e consulta simples.
- **Negativas (Trade-offs):** sem acesso multiusuário nem persistência online; migrar para Postgres no
  futuro custa a troca da camada de acesso (isolá-la atrás de um módulo `storage`).
