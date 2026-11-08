---
tipo: "processo"
titulo: "Contexto do Repositório — Briefing de Entrada"
dominio: "Governança de Specs (SDD)"
status: "🟢 Vigente"
tags: ["processo", "contexto", "sdd"]
relacionados: ["[[00-knowledge]]", "[[00-indice]]", "[[00-backlog]]", "[[00-prompt-revisor]]", "[[00-prompt-executor]]"]
---

# 0. O que é este arquivo

Esta é a **porta de entrada de qualquer agente** neste repositório. Um agente que leu esta spec — e só ela —
deve saber: **o que** o repositório é, **quais regras** governam qualquer alteração, **onde** está cada
informação e **como** se trabalha aqui.

> ⚠️ **Este arquivo é um molde com instruções embutidas.** Ele chega ao repositório **vazio de conteúdo
> específico**: cada seção traz um bloco `> **Como escrever:**` (a instrução, que **permanece** no arquivo como
> contrato de manutenção) e um bloco `<!-- PREENCHER -->` (o conteúdo real, que o **agente revisor** escreve).
> Preencher esta spec é a **primeira** plan de qualquer repositório novo.

**Quem escreve/atualiza:** exclusivamente o **agente revisor** ([[00-prompt-revisor]]).
**Quando atualizar:** sempre que uma plan aprovada mudar stack, arquitetura, fronteiras de módulo, regra
inegociável ou o mapa de roteamento. Nunca por conta própria fora de uma plan.

---

# 1. Identidade do repositório

> **Como escrever:** 3 a 6 linhas, em prosa direta. Responda: **o que este repositório é** (produto? base de
> conhecimento? biblioteca? site?), **qual problema resolve**, **quem consome** (usuário final, outros repos,
> agentes) e **o que ele explicitamente NÃO é**. Sem marketing, sem histórico. Um agente lê isto e para de
> supor. Proibido descrever a estrutura de pastas aqui — isso é da §3.

<!-- PREENCHER -->

---

# 2. Regras inegociáveis (resumo operante)

> **Como escrever:** liste **apenas** as regras que um agente pode violar sem perceber, em forma de bullets
> curtos e verificáveis. Duas fontes, nesta ordem:
> 0. **`CLAUDE.md` e `AGENTS.md` só apontam para este arquivo** — não repetem regra nem comando de verificação.
>    Uma instrução repetida lá vence esta em silêncio (mede-se: o comando antigo de lá anulou a regra nova), e
>    uma skill local de contexto paralela a este arquivo é outro ponto de divergência: não crie uma.
> 1. **Universais do ecossistema** — não reescreva: aponte para `AGENTS.md` (raiz) e para a skill
>    `padrao-escrita`. Cite no máximo os limiares que causam reprovação imediata (SRP; função ≤ 40 linhas;
>    aninhamento ≤ 3; ≤ 4 parâmetros; zero hardcoded; segredos só em `.env`; nenhuma exceção engolida).
> 1b. **Arquitetura de módulos** — se este projeto adota o template, **não descreva a anatomia**: aponte para
>    `arquitetura/04-regras.md` e diga a única coisa que o agente precisa saber sem abrir o arquivo — que ela
>    é cobrada por máquina, com `node tools/gate/validate.mjs`.
> 2. **Específicas deste repositório** — o que só vale aqui (convenções de nomes locais, uma biblioteca
>    proibida, um diretório que não se toca, um formato de retorno obrigatório).
>
> **Regra de ouro: referencie, nunca duplique.** Se uma regra já está numa spec fixa ou numa skill, escreva
> uma linha e o ponteiro. Conteúdo duplicado desatualiza e passa a mentir.

<!-- PREENCHER -->

---

# 3. Stack e arquitetura em uma página

> **Como escrever:** o mínimo para orientar, com ponteiro para o detalhe. Inclua:
> - **Stack**: linguagens + versões, frameworks, banco, runtime, gerenciador de pacotes.
> - **Camada de padrão da linguagem**: qual skill `padrao-*` se aplica (`padrao-python`, `padrao-typescript`).
>   Outra linguagem não tem camada de Nível 2, mas pode ter automação de limiar: o hook `padrao-limiares`
>   cobre `.go` e `.java` além de `.py` e `.ts`/`.js`. Registre qual dos dois cobre a stack — e, se nenhum
>   cobrir, que ali vale o Nível 0 do `padrao-escrita` conferido por leitura.
> - **Mapa de módulos/domínios**: tabela `módulo → papel → responsabilidade`. Projeto com o template de
>   módulos: os papéis são `domain` / `gateway` / `connector` (a forma do `module.json` de cada um, campo
>   `role`) — não transcreva, aponte.
> - **Fronteiras**: quem pode chamar quem, e por onde. No template, a resposta é sempre a mesma — pelo
>   **contrato HTTP** da `api/` do dono, declarado em `module.json:consumes`.
> - **Comandos vitais**: instalar, rodar, testar, lintar, buildar — copiáveis, verificados.
>
> Cada item aponta para a spec fixa em `arquitetura/` que o detalha. Esta seção é o índice, não o tratado.

<!-- PREENCHER -->

---

# 4. Mapa de roteamento — "que spec eu leio para esta tarefa?"

> **Como escrever:** esta é a seção **mais valiosa** do arquivo e a razão de ele existir. Uma tabela que
> responde à pergunta que todo agente faz ao receber uma tarefa. Uma linha por tipo de tarefa recorrente
> no repositório, com caminhos **relativos a `specs/`** e clicáveis.
>
> Preencha a coluna "Leia antes" com **specs fixas** (`arquitetura/`, `specs/`, `adr/`) — para skills e
> commands, aponte para [[00-knowledge]], que é o roteador de capacidades.
>
> As specs fixas são numeradas por **família** (`FF.NN-<slug>.md`); o catálogo é [[00-planejamento]] §1 —
> aponte para ele, nunca copie as famílias aqui.
>
> | Tipo de tarefa | Leia antes (specs fixas) | Capacidade |
> |---|---|---|
> | Alterar regra de negócio de \<módulo\> | `specs/FF.NN-<module>.md` | [[00-knowledge]] |
> | Criar/alterar endpoint | `arquitetura/FF.NN-api.md` + spec do módulo | [[00-knowledge]] |
> | Mexer em schema/migration | `arquitetura/FF.NN-dados.md` + ADR relevante | [[00-knowledge]] |
> | Container, ambientes, publicação, servidor | `arquitetura/FF.NN-operacao.md` (molde `template-operacao`) | [[00-knowledge]] |
> | Mudar decisão estrutural | todos os `adr/` + `arquitetura/` | [[00-knowledge]] |
>
> Mantenha entre 6 e 15 linhas. Se passar disso, o repositório precisa de specs melhores, não de mais linhas
> aqui. **Ponteiro órfão é defeito**: toda spec citada tem de existir.

<!-- PREENCHER -->

---

# 5. Como se trabalha aqui (ciclo SDD)

> **Como escrever:** esta seção é **universal — copie o bloco abaixo como está**. Só acrescente desvios reais
> deste repositório (por exemplo: "toda plan que toca `pagamentos/` exige ADR"). Não reescreva o ciclo.

**Toda e qualquer alteração passa pelo revisor.** Nada é alterado "direto no código" — mas nem toda alteração
vira arquivo. O revisor **tria** cada demanda ([[00-prompt-revisor]] §4):

| A demanda deixa verdade documentada para trás? | Via | O que nasce |
|---|---|---|
| **Sim** — muda regra, contrato, stack, comportamento | **plan** | `plan-FF.NN` + linha no [[00-indice]] |
| **Não** — bug sem mudança de regra, typo, conformidade, limpeza | **prompt direto** | nada; a instrução vive só na conversa |

A via direta encurta a **papelada**, nunca a **verificação**: o executor trabalha igual e o revisor confere o
diff linha por linha do mesmo jeito. O ciclo abaixo é o da **plan**; a via direta salta os passos de síntese
e expurgo, porque não há verdade a transportar.

```
revisor escreve  specs/plan/plan-FF.NN-<slug>.md  +  linha no 00-indice
      ↓
executor lê  00-prompt-executor  +  plan-FF.NN  e executa
      ↓
alterações ficam no worktree (o executor não commita)
      ↓
revisor VERIFICA diretamente (não confia no resumo do executor)
      ├─ reprovado → prompt de correção → executor corrige → repete
      └─ aprovado  → status 🟢 + revisor entrega o veredito e o comando de commit (só commit)
      ↓
usuário commita o código e a plan com o veredito, e avisa
      ↓
revisor confere o veredito em HEAD, sintetiza nas specs fixas (adr/ · arquitetura/ · specs/) sem pedir
autorização, tira a linha do índice e entrega o comando completo; o rastro vai na resposta dele
      ↓
usuário roda o comando completo — git rm da plan, spec fixa, índice, commit e push
```

**A plan é temporária**: vive em `specs/plan/` enquanto o trabalho está aberto e **some no ato da síntese**.
Não há estado "sintetizada aguardando limpeza" — o rastro passa a viver no Git. Por isso o [[00-indice]] tem
tamanho limitado pelo trabalho em andamento, e não pela idade do repositório.

Achado fora do escopo, em qualquer ponto, desce para o [[00-backlog]] — **nunca** vira plan nova no meio do
caminho.

| Papel | Spec de entrada | Pode escrever | Nunca faz |
|---|---|---|---|
| **Revisor** | [[00-prompt-revisor]] | plans, `00-indice`, `00-backlog`, specs fixas (na síntese), prompts | tocar código · commitar ou fazer push em branch protegida |
| **Executor** | [[00-prompt-executor]] | código + resumo (na plan, ou na conversa) | criar/alterar outras specs · commitar · mover ou remover plan |
| **Usuário** | — | qualquer coisa | — (é quem commita, confirma o commit do veredito e promove itens do backlog) |

> **O executor nunca commita.** O revisor só commita e mescla em branch local não protegida, com panorama
> autorizado ([[00-prompt-revisor]], "Git e ramificações"); commit e push em branch protegida são do usuário.
> **Nenhum agente adiciona co-autoria**: sem `Co-Authored-By` e sem qualquer outra marca de autoria de agente
> na mensagem.

<!-- PREENCHER: desvios específicos deste repositório, se houver -->

### O ciclo neste repositório

O prompt da base manda; esta seção acrescenta obrigações de execução e verificação e só afrouxa os pontos que os prompts marcam como [parâmetro].

> **Os prompts e o `00-knowledge` são fixos.** Eles permanecem iguais aos da base e a base os atualiza sozinha quando mudam: não os edite aqui. Qualquer peculiaridade deste repositório (comandos, terminal, autorização, branches, obrigações) mora nesta seção e nas anteriores.

| Parâmetro | Padrão (sem declaração) | Este repositório declara |
|---|---|---|
| Git e ramificações | `main` (produção) e `master` protegidas; `develop` é a branch de trabalho e integração, e toda branch nasce dela e volta para ela; prefixos plan/ e sarak/; equipe com vários desenvolvedores pode ter outras branches de trabalho; nunca se trabalha em `main` | declarado em config/verification.json (git) |
| Autorização permanente dos commits do fluxo | Não: panorama e autorização a cada escrita. | <!-- `sim` se o dono autorizou, de uma vez, os dois commits do fluxo (o do veredito e o da síntese); o push continua do usuário. --> |
| Terminal padrão dos comandos para o usuário | O da sessão, dito a cada comando. | <!-- `powershell` ou `bash`. --> |
| Verificação escopada | Testes e análise estática do escopo tocado, gate do módulo e gate do commit sobre o diff. | `node tools/gate/validate.mjs <módulo>`; <!-- Acrescente comandos reais de teste e análise estática do binding. --> |
| Verificação ampla | Escopo tocado, consumidores afetados e gate do repositório. | `node tools/gate/validate.mjs --all`; <!-- Acrescente comandos reais dos testes dos consumidores afetados. --> |
| Verificação completa | Suíte inteira, build, ponta a ponta no navegador e container. | <!-- Comandos reais da suíte, build, navegador e container; vazio: a plan nomeia. --> |
| Gate do commit | Checagem equivalente ao hook sobre o diff staged. | `node tools/verify-commit.mjs pre-commit` |
| Navegador | Verificação visual no navegador, se houver superfície visual. | <!-- Comando real; sem superfície visual, declare — e o motivo. --> |
| Numeração das plans | `plan-NN`, contador único no `00-indice`. | `plan-FF.NN`, contador por família no `00-indice`. |
| Panorama | Não adota. | Sim; este molde traz `panorama/` e o `00-indice` por família. |
| Spec de regras e geradores `--check` | `arquitetura/04-regras.md` e os geradores do template de módulos: `node tools/sync-env.mjs --check`, `node tools/sync-deploy.mjs --check`, `node tools/generate-port-schemas.mjs --check` e `node tools/generate-lint-config.mjs --check`. | `arquitetura/04-regras.md`; os mesmos quatro comandos do template de módulos. |
| Uso de ADR | Sim, somente com duas opções reais, custo da escolhida e alto custo de reversão. | Sim, sob esses critérios. |
| Obrigações acrescentadas | Nenhuma. | Nenhuma. <!-- Exemplo: execução que cria migration entrega antes/depois/rollback. --> |
| Medição do ambiente | Comandos da skill `code-limpeza-ambiente`. | subcomandos `snapshot` e `diff` da skill `code-limpeza-ambiente` (`environment.py`), com `--out <snapshot.json> --tmp-prefix <prefixo>` e `--from <snapshot.json>`; caminho da skill conforme a instalação do plugin. |

Se uma declaração de comando ficar vazia, a plan nomeia os comandos, como no legado.

---

# 6. Capacidades disponíveis

> **Como escrever:** seção **universal — não a preencha com conteúdo**. Apenas mantenha o ponteiro. As
> skills, commands, agents e hooks **não vivem neste repositório**: vêm da memória/plugin do agente. O
> catálogo e as regras de roteamento estão em [[00-knowledge]].

Antes de escolher **como** fazer algo, leia **[[00-knowledge]]** — é o roteador de capacidades
(situação → skill/command/agent/hook) e o único lugar onde esse catálogo é mantido.

---

# 7. Fronteiras — o que nunca fazer neste repositório

> **Como escrever:** bullets no imperativo negativo, cada um com o **porquê** em meia linha. Só o que é
> específico deste repositório (as proibições de papel já estão na §5 e nas specs de prompt). Exemplos do
> tipo de item: diretórios gerados que não se editam à mão; arquivos que só o usuário altera; operações
> irreversíveis que exigem confirmação; integrações que não podem ser chamadas em desenvolvimento.

<!-- PREENCHER -->

---

# 8. Estado e pendências conhecidas

> **Como escrever:** o que um agente descobriria do jeito difícil. Dívidas técnicas aceitas, áreas em
> migração, incoerências conhecidas entre código e spec, decisões em aberto. **Datas sempre absolutas**
> (`2026-07-31`, nunca "semana passada"). Item resolvido sai daqui — esta seção não é histórico; o histórico
> é o `git` e os `adr/`.

<!-- PREENCHER -->

---

# 9. Contrato de manutenção desta spec

- **Alvo de tamanho:** ≤ 200 linhas preenchidas. Estourou? O conteúdo pertence a uma spec fixa — mova e aponte.
- **Referencie, nunca duplique.** Esta spec é um **mapa**, não território.
- **Ponteiro órfão é defeito.** Toda spec citada existe; todo comando citado roda.
- **Só o revisor edita**, e só no contexto de uma plan aprovada.
- **Sincronia obrigatória:** se uma plan mudou stack, fronteira ou regra, a mesma plan atualiza esta spec.
  Contexto desatualizado é pior que contexto ausente — o agente confia nele.
