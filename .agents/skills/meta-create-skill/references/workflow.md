# Workflow Detalhado: Criar uma Skill

Versão expandida do workflow resumido no `SKILL.md`. Leia este arquivo quando precisar do detalhe
de um passo específico — sintomas a detectar, ação concreta e exemplos **antes/depois**. Para o
caminho comum, o resumo do `SKILL.md` basta.

Trate **uma skill por vez**. Não avance sem concluir o passo atual.

---

## Passo 1: Definir o escopo (antes de criar qualquer arquivo)

**Objetivo:** garantir responsabilidade única e ausência de duplicação.

Responda, por escrito, antes de tocar em arquivos:

1. **Qual problema específico esta skill resolve?** Descreva em **uma** frase. Se a frase precisar de
   "e" para ligar dois problemas, a skill faz coisa demais — divida.
2. **Já existe skill similar?** Leia o `SKILL.md` (e, se houver, o `references/` ) das skills
   existentes. Sobreposição ≥ 70% → expanda a existente, não crie outra.
3. **Qual o gatilho de uso?** Defina com precisão quando ela é acionada (ex.: "ao detectar acoplamento
   entre módulos").
4. **Como é acionada?** Escolha **um**:
   - **Proativa** — o agente aciona sozinho ao detectar o gatilho durante o trabalho.
   - **Sob demanda** — só roda quando o usuário pede explicitamente.
   - **Por command/orquestração** — chamada dentro de um slash command ou por outra skill.

> ❌ Erro comum: pular este passo e "descobrir o escopo enquanto escreve". O resultado é uma skill que
> faz três coisas pela metade.

---

## Passo 2: Escrever a `description` *(o passo que decide se a skill dispara)*

A `description` no frontmatter é o **campo mais importante** de toda skill. É ela, e só ela, que faz o
agente acionar a skill no momento certo. Uma `description` fraca = skill que nunca dispara, por melhor
que seja o conteúdo interno.

### Fórmula

```
<O QUE faz, em 1 frase> + <QUANDO usar / gatilhos: "Use ao…", "ao mencionar…"> + [<trava, se sob demanda>]
```

1. **O quê** — a ação concreta da skill.
2. **Quando + gatilhos** — situações e palavras que devem acioná-la.
3. **Trava** — **apenas** para skills sob demanda: termine com
   `Use APENAS quando o usuário solicitar explicitamente. NÃO acione proativamente.`

### Proativa vs. sob demanda

- **Proativa** → linguagem de detecção: `Use ao escrever/revisar código quando detectar <sintoma>.`
- **Sob demanda** → linguagem de trava (acima).

### Antes / Depois

**❌ Antes (não dispara):**
```yaml
description: Especialista em código limpo.
```
Título, não gatilho. Falta o quando e as palavras-gatilho.

**✅ Depois (proativa):**
```yaml
description: Refatora para Clean Code (SRP, guard clauses, tratamento de erros). Use ao escrever ou revisar código com funções longas, nomes ruins ou lógica aninhada.
```

**✅ Depois (sob demanda):**
```yaml
description: Otimização de performance custo zero (Core Web Vitals, imagens, cache). Use APENAS quando o usuário pedir otimização de performance explicitamente. NÃO acione proativamente.
```

---

## Passo 3: Criar a estrutura de pastas

Nome da pasta = `name` da skill, em **kebab-case, sem prefixo** (`code-padronizacao`, nunca
`skill-code-padronizacao` nem `CodePadronizacao`).

```
<skill-name>/
├── SKILL.md            # denso, auto-suficiente (Camada 2)
├── references/         # completos, lidos sob demanda (Camada 3) — condicional
│   ├── workflow.md
│   ├── templates.md
│   └── examples.md
├── scripts/            # automação determinística na linguagem do repositório — condicional
│   └── *.<ext>
└── assets/             # binários / boilerplate copiável — condicional
```

`references/`, `scripts/` e `assets/` são **condicionais**: crie só quando houver conteúdo. Sem pastas
vazias. Use `scripts/scaffold_skill.py` para gerar o esqueleto automaticamente.

---

## Passo 4: Escrever o `SKILL.md` denso (Camada 2)

O corpo do `SKILL.md` deve ser **auto-suficiente para ~90% das execuções**. Seções, na ordem:

1. **Frontmatter** — `name` + `description` (Passo 2).
2. **O que é / diferencial** — 1–2 linhas.
3. **Quando usar** — situações que disparam, coerentes com a `description`.
4. **Workflow (caminho comum)** — passos numerados e acionáveis. Cada passo verboso aponta para este
   `references/workflow.md`.
5. **Regras e limites** — proibições (NÃO/NUNCA), curtas; cabem inteiras aqui.
6. **Checklist "pronta"** — itens objetivos sim/não; cabe inteiro aqui.
7. **Referências (Camada 3)** — ponteiros para `references/*` e `scripts/*`.

**Critério de densidade:** ~40–80 linhas (a média medida do catálogo hoje é 68, com 80% das
skills abaixo de 70). Se passar muito disso, mova o verboso (exemplos longos, templates) para
`references/`. Se ficar curto demais e exigir abrir outro arquivo para o caminho comum, está
roteador demais — traga o essencial de volta.

### Acionabilidade dos passos

Cada passo do workflow deve declarar **ferramenta + ação + critério/output**.

**❌ Antes:** "Analise o código."
**✅ Depois:** "Use `Read` para ler o arquivo e classifique cada import como interno, externo ou de
outro módulo; liste no formato `<arquivo>: <import> → <categoria>`."

### Passo HITL (obrigatório antes da 1ª ação mutativa)

Toda skill que **modifica** algo deve ter, no workflow, um passo de confirmação antes da primeira
alteração:

```markdown
## Passo N: Apresentação e Confirmação (HITL)

## ✅ Plano de Execução — [Nome da Operação]
**O que será modificado:** [arquivos/componentes]
**Por que:** [justificativa técnica]
**Como:** [método]
**Expectativa:** [resultado esperado]

⚠️ Confirma para prosseguir?
```

Não execute nenhuma alteração antes da confirmação explícita.

---

## Passo 5: Preencher `references/` (Camada 3) — condicional

Crie um arquivo de `references/` **somente** se o conteúdo for verboso demais para o `SKILL.md` ou raro
o suficiente para ser lido sob demanda:

- **`workflow.md`** — passos detalhados com antes/depois (como este).
- **`templates.md`** — templates de preenchimento de output (relatórios, configs, docs). Campos em
  `[PLACEHOLDER]` com valor de exemplo. Crie só se a skill produz output.
- **`examples.md`** — exemplo bom (cenário → antes → depois → correções) e exemplo ruim (estado
  incorreto → violações ⚠️ → impacto).

Cada arquivo criado **precisa** ter um ponteiro correspondente no `SKILL.md`. Sem ponteiro = arquivo
órfão que ninguém lê.

---

## Passo 6: Criar script em `scripts/` *(condicional)*

Crie um script **quando a tarefa é determinística e repetível** — mesma entrada, mesma saída (varrer
arquivos, detectar padrões, contar, converter, validar, gerar estrutura).

**Atenção:** Se a skill precisar de um script, ele deve ser criado **na linguagem principal do repositório** onde a skill será utilizada (ex.: Node.js para repositórios TypeScript, Python para repositórios Python).

**Critério de decisão:**
- Mecânica, determinística → **script** (ex.: scanner de segredos, scaffold de pastas).
- Exige julgamento/contexto → **não** vira script; fica nas instruções (ex.: decidir como modularizar).

**Padrões (alinhados à `padrao-escrita`):**
- Escrito na linguagem do repositório (multiplataforma preferencialmente).
- **Zero hardcoded:** caminhos/limites/padrões vêm de argumentos ou de `config.json`, nunca embutidos.
- Zero segredos.
- Responsabilidade única; saída clara (texto ou JSON) para o agente consumir.
- Comentário/Docstring no topo: o que faz, como rodar, o que retorna.

---

## Passo 7: Verificação final

Aplique o **checklist "pronta"** do `SKILL.md` desta própria skill (`meta-create-skill`) à skill recém-criada
antes de considerá-la operacional. Confirme também que nenhum ponteiro aponta para arquivo inexistente.

---

## Passo 8: Registro (opcional)

Só se houver um sistema de registro/orquestração ativo na sessão (ex.: GSD). Caso não exista, omita —
**não** referencie skills de registro inexistentes.
