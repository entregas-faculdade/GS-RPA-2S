---
tipo: "spec"
familia: "FF" # Opcional; só com famílias declaradas.
titulo: "Nome da Funcionalidade"
dominio: "Nome do Módulo (Ex: Autenticação)"
status: "🟢 Vigente" # Opções: 🟢 Vigente, 🔴 Obsoleto — a spec fixa descreve a verdade no presente, depois da síntese; não é backlog
prioridade: "Alta"
tags: ["spec"]
relacionados: [] # Ex: [[02.01-banco-de-dados]]. SÓ specs fixas (specs/ · arquitetura/ · adr/).
                 # NUNCA uma plan: ela é removida na síntese e o ponteiro morre junto.
---

> **Molde de spec.** Sem famílias, use `specs/<slug>.md`; (com famílias) `specs/FF.NN-<slug>.md` (o próximo
> número soma `specs/` e `arquitetura/`). O campo `familia` só existe com famílias.

# 1. Visão Geral
Descreva brevemente o objetivo desta funcionalidade e o problema que ela resolve.

# 2. Regras de Negócio
- **Regra 1:** ...
- **Regra 2:** ...

# 3. Critérios de Aceite
- [ ] Cenário A funciona conforme esperado.
- [ ] Cenário B lança o erro X.

# 4. Plano de Testes (Quality Gate)
Mapeamento obrigatório dos testes que as skills (`test-unitario`, `api-contrato` ou `test-e2e`) deverão implementar para considerar esta spec "Concluída".

## Testes Unitários
- [ ] **Deve** ...
- [ ] **Deve** ...

## Testes de Contrato (API)
- [ ] **Endpoint** `GET /api/v1/...`: Deve retornar o payload no formato X sem quebrar o contrato.

## Testes E2E (Integração)
- [ ] Fluxo feliz: ...
