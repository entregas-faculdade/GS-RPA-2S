---
tipo: "plan"
familia: "FF" # Opcional; só com famílias declaradas.
item: "" # Opcional; só com panorama; ID do item do horizonte.
titulo: "Título curto no infinitivo (Ex: Extrair validação de CPF para o domínio)"
dominio: "Nome do Módulo (Ex: Autenticação)"
status: "🔴 A executar" # 🔴 A executar · 🟡 Em execução · 🟠 Em revisão · 🔵 Em correção · 🟢 Aprovada · ⛔ Bloqueada
prioridade: "Alta"
tags: ["plan"]
relacionados: [] # Ex: [[arquitetura/02.03-api]], [[specs/01.02-login]]
depende_de: "" # Ex: plan-02.04-extrair-contrato — precisa estar 🟢 antes
destino_sintese: "" # arquitetura/<nome>.md · adr/NNN-*.md · specs/<nome>.md · 00-contexto.md · — (nenhum)
---

> **Molde de plan.** Escrita pelo **agente revisor** ([[00-prompt-revisor]]), executada pelo **agente
> executor** ([[00-prompt-executor]]). Nome: `plan-<número>-<slug-kebab>.md` (padrão `plan-NN`; `plan-FF.NN` com famílias).
> O esquema declarado no `00-contexto` define o contador único ou por família em `00-indice`. Vive em `plan/`
> até ser sintetizada — nunca muda de pasta; o que muda é o `status`. Ao criar,
> adicione a linha correspondente na tabela do [[00-indice]].
>
> ⚠️ **Esta plan é temporária.** No ato da síntese ela é **removida** junto com a linha do índice: sua
> verdade passa a viver na spec fixa de destino (§8) e o rastro, no Git. Nada de código deve apontar para
> ela — comentário não cita plan (`padrao-escrita`, `references/comentarios.md`).
>
> **Critério de qualidade:** um executor **sem nenhum contexto prévio** consegue realizar esta plan lendo
> apenas ela e o que ela aponta. Se não consegue, a plan está incompleta.

# 1. Objetivo

Uma frase: o **resultado observável** quando isto estiver pronto. Não a tarefa — o efeito no sistema.

# 2. Contexto

Por que agora, o que existe hoje, o que a leitura do repositório revelou. Inclua o que evita que o executor
repita a investigação já feita. Sem história longa.

# 3. Escopo

## 3.1 Dentro (o que pode ser tocado)
- `caminho/do/arquivo.ext` — o que muda nele
- `caminho/do/modulo/` — o que muda nele

> **Plan que CRIA regra de gate lista o conjunto inteiro aqui, e ele é maior do que parece:** a regra
> em si, a linha no catálogo (`arquitetura/04-regras.md`), o caso de teste, **e toda contagem de
> regras citada em prosa** — inclusive fora da árvore do template, onde nenhuma catraca automática as
> alcança. Ache-as varrendo (`grep`), nunca de memória.

## 3.2 Fora (o que NÃO pode ser tocado)
- `caminho/intocavel.ext` — motivo
- Qualquer refactor não listado em §5, mesmo que pareça óbvio.

> Esta seção previne a maioria das reprovações. Seja explícito.

# 4. Referências obrigatórias

| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | `arquitetura/<nome>.md` | regra estrutural que restringe a solução |
| Spec fixa | `specs/<nome>.md` | regra de negócio afetada |
| Contexto | `00-contexto.md` · `00-knowledge.md` | sempre |
| **Skill** | `padrao-escrita` + `padrao-<linguagem>` | sempre |
| **Skill** | `<skill-específica>` | o que ela resolve aqui |
| Código | `caminho/arquivo.ext` | ler antes de editar |

> **Referencie, nunca copie.** Nada de conteúdo de skill ou de spec fixa reproduzido aqui.
>
> ⚠️ **Esta seção é exaustiva.** O prompt que leva o executor até esta plan é um **ponteiro** e não repete
> nada daqui — logo, o que não estiver nesta tabela não será carregado. Contexto que existe só no prompt se
> perde na primeira rodada de correção; o que está aqui é versionado e relido a cada rodada.

# 5. Instruções de execução

Passos numerados, verificáveis, sem ambiguidade. Um passo = uma ação com critério de pronto. Cada passo
declara seu **grau** ([[00-prompt-revisor]] §5.5): `[mecânico]` (antes e depois literais, lidos do arquivo
agora) ou `[dirigido]` (resultado e restrições, nunca o código).

1. [dirigido] <resultado esperado e restrições — o executor escolhe a implementação>
2. [mecânico] `caminho/arquivo.ext`
   antes:  `<trecho exato>`
   depois: `<trecho exato>`
3. Rodar `<comando de teste/validação>` e garantir verde.

# 6. Critérios de aceite

- [ ] Critério objetivo e verificável.
- [ ] …
- [ ] Ambiente e worktree limpos (sem processo, contêiner, volume, imagem ou arquivo largado criado pela tarefa).
- [ ] Testes **do escopo** verdes; checagem estática e validadores sem violação nova nos arquivos alterados.

# 7. Como verificar (uso do revisor)

Escrito **antes** da execução. Os comandos e checagens exatos do veredito:

- **Nível:** `escopada` | `ampla — <motivo>` ([[00-prompt-revisor]] §5.4). Escopada é o padrão; **não
  escreva a suíte completa aqui** — ela é do commit, do push e da CI. Executor e revisor rodam os
  mesmos comandos abaixo, nomeados e restritos ao escopo.
- `git diff --stat` → só os arquivos de §3.1 aparecem.
- `<comando de teste restrito ao módulo/arquivo>` → verde.
- `<checagem estática dos arquivos tocados>` → sem erro novo.
- `<validador restrito aos arquivos alterados>` → sem violação nova.
- Se a verificação sobe processo, container ou arquivo temporário: `<o que sobe>` e como é encerrado; o revisor refaz o `diff` do ambiente.
- Leitura de `<arquivo:linha>` → confirma \<o que\>.
- **Gate:** `<id da regra nova>` | `nenhum — <motivo em meia linha>`. **Obrigatória sempre** — a
  obrigatoriedade está em DECLARAR, não em preencher: `nenhum` é a resposta mais comum e legítima, a
  mesma economia do §8 (Destino da síntese). Critério de qual das três formas a verificação toma —
  teste, regra de gate ou `--check` do gerador — vive em [[00-prompt-revisor]] §5.4; não repita aqui.
  **Se a resposta não for `nenhum`, o "como verificar" acima não basta:** para cada limite que a regra
  declara e cada falso positivo que promete não ter, exija a entrada exata e o resultado — suíte verde
  não distingue "a regra está certa" de "a lei está mentindo sobre a regra".

# 8. Destino da síntese

**Destino:** `<valor do frontmatter>`

O que deve ser levado para a spec fixa depois (texto pronto para transporte, se aplicável). Se o destino é
`—`, escreva o motivo: esta execução não altera nenhuma verdade documentada.

> A síntese é feita pelo **revisor**, depois do commit do veredito, **sem pedir autorização**
> ([[00-prompt-revisor]] §7.4). Esta seção apenas a prepara — **escreva aqui o texto pronto para
> transporte**, porque no ato da síntese esta plan deixa de existir.
>
> `adr/NNN-*.md` como destino? Passe antes o portão de `_templates/template-adr.md`: sem duas alternativas
> reais descartadas, com custo nomeado, **não é ADR**.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

> **Não há seção de síntese nesta plan.** A síntese é feita pelo revisor, depois do commit do veredito, e o arquivo
> sai do disco (`git rm`) na mesma ação em que a spec fixa é atualizada: um bloco escrito aqui nunca chegaria
> a um diff. O rastro (o transportado e o não transportado, com o motivo) vai na resposta do revisor, pronto
> para a mensagem do commit — [[00-prompt-revisor]] §7.4.
>
> **Nota:** os prompts de execução, de correção e de conclusão (o texto que o usuário cola numa conversa nova
> com o executor ou com o revisor) **não vivem nesta plan**. São gerados e entregues sempre direto na conversa,
> em bloco ` ```md `, como **ponteiros** para esta plan — ver [[00-prompt-revisor]] §5.3 e §7.3, e
> [[00-prompt-executor]] §6.1.
