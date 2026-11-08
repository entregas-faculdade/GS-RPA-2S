# Exemplos: Criar Skills

Leia quando estiver em dúvida se uma skill está bem-feita. O exemplo bom mostra o alvo; o ruim mostra
os erros que matam uma skill.

---

## Exemplo bom — skill completa e operacional

**Skill de referência:** `code-padronizacao`

### `SKILL.md` e `description`
- ✅ `name` em kebab-case, sem prefixo, igual ao nome da pasta: `code-padronizacao`.
- ✅ `description` com **o quê + quando/gatilhos**:
  `Refatora para Clean Code (SRP, guard clauses, tratamento de erros). Use ao escrever ou revisar código com funções longas, nomes ruins ou lógica aninhada.`
- ✅ Proativa → usa linguagem de detecção (sem trava de sob demanda).

### Corpo denso (Camada 2)
- ✅ Responsabilidade única clara: "aplicar padronização de código".
- ✅ Workflow com 5 categorias de ação acionáveis (SRP, guard clauses, erros, dead code, DRY), cada uma
  com o que detectar + como corrigir; o detalhamento com antes/depois fica em `references/workflow.md`.
- ✅ Ferramentas declaradas (`Read`, `Grep`, `Edit`).
- ✅ Passo HITL antes da primeira alteração mutativa.
- ✅ Regras (7 itens, todos NÃO/NUNCA, com item de escopo) e checklist objetivo cabem no `SKILL.md`.

### Camada 3
- ✅ Refatoração exige julgamento de contexto → corretamente **não** vira script.
- ✅ Não produz output documental → corretamente **não** tem `templates.md` vazio.

**Por que funciona:** qualquer agente executa a skill sem intervenção constante — a `description`
dispara na hora certa, cada passo é preciso, e os limites de escopo estão explícitos. O caminho comum
se resolve só com o `SKILL.md`; `references/workflow.md` é mergulho opcional.

---

## Exemplo ruim — skill vaga e inutilizável

**Skill fictícia:** `skill-melhorar-codigo`

### Estado incorreto

```
skill-melhorar-codigo/
└── SKILL.md   ← arquivo único, vago
```

```markdown
# Skill: Melhorar Código

Você é um especialista em código limpo. Quando solicitado, melhore o código
seguindo as melhores práticas. Garanta qualidade e escalabilidade.

- Analise o código
- Faça melhorias onde necessário
- Garanta que está dentro dos padrões
```

### Por que é ruim

| Problema | Impacto |
|----------|---------|
| Nome com prefixo `skill-` | Viola o naming (deveria ser `melhorar-codigo`, kebab-case sem prefixo). |
| Sem `description` no frontmatter | Sem `description`, **a skill não dispara** — é o campo de gatilho. |
| `description` seria "Melhorar Código" | Título, não gatilho: falta o quando/palavras-gatilho. |
| "Analise o código" | Qual ferramenta? Quais critérios? O que procurar? Não acionável. |
| "Faça melhorias onde necessário" | "Onde necessário" é subjetivo — cada agente interpreta diferente. |
| "Dentro dos padrões" | Que padrões? Sem referência concreta a `AGENTS.md`, `padrao-escrita` ou `04-regras.md`. |
| Sem regras nem checklist | O agente não sabe o que evitar nem quando a tarefa terminou. |
| Sem delimitação de escopo | O agente pode fazer qualquer coisa em nome de "melhorar". |

### Consequência

Um agente executando essa skill faz refatorações aleatórias, não sabe quando parar, introduz mudanças
de comportamento acidentais e produz resultado diferente a cada execução.

> **Uma skill ruim é pior do que nenhuma skill** — dá falsa sensação de controle.
