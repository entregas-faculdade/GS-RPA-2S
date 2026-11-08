---
tipo: "processo"
titulo: "Knowledge — Roteador de Capacidades (skills, commands, agents, hooks, MCP)"
dominio: "Governança de Specs (SDD)"
status: "🟢 Vigente"
tags: ["processo", "roteamento", "skills", "commands"]
relacionados: ["[[00-contexto]]", "[[00-prompt-revisor]]", "[[00-prompt-executor]]"]
---

# 1. O que é este arquivo

O **roteador de capacidades** do ecossistema Sarak: dado *o que preciso fazer*, diz *qual artefato usar*.

> **As capacidades listadas aqui NÃO vivem neste repositório.** Elas vêm da base de inteligência Sarak,
> instalada na memória do agente (plugin `sarak@knowledge-agentics` no Claude Code; `sync_ide.py` nos demais
> provedores). Este arquivo é o **índice de roteamento** delas — não a implementação. Nunca copie o conteúdo
> de uma skill para cá nem para uma plan: **cite o nome** e o agente carrega o resto.

**Leia junto:** [[00-contexto]] (o que este repositório é e suas regras) — esta spec cobre *como fazer*,
aquela cobre *o que respeitar*.

> **Uma fonte por assunto.** O `00-contexto` é o único lugar das regras do repositório; `CLAUDE.md` e `AGENTS.md`
> só apontam para ele, e uma skill local de contexto paralela a ele não deve existir: cada cópia é um ponto de
> divergência, e a instrução antiga vence a nova em silêncio.

---

# 2. Como cada bloco dispara (a regra de ouro)

| Bloco | Como entra em ação | Consequência prática |
|---|---|---|
| **skill** | O **modelo decide** pela `description`, **ou** você cita o nome | Citar a skill numa plan é o que garante que ela seja aplicada |
| **command** | **Manual** — você digita `/nome` | Um agente **não** dispara command; a plan pede ao humano, ou executa a skill equivalente; num harness sem commands (Codex), a skill `meta-fluxos` executa o fluxo pelo nome |
| **agent** | O modelo **delega** (subagente com contexto próprio) | Isola varredura pesada e devolve resumo |
| **hook** | **Automático e determinístico** no evento do harness | Roda sempre — é a única garantia mecânica |
| **AGENTS.md** (o `CLAUDE.md` o importa no Claude) | Sempre no contexto | Os inegociáveis; nunca precisa ser citado |

**Trava de disparo:** critério, não lista de nomes — skill **mutativa** (edita/gera/apaga arquivo) ou de
**varredura** (audita/relata sem julgamento novo) termina a `description` com *NÃO acione proativamente*; o
agente só a aciona se a tarefa (ou a plan) pedir. Disparo **proativo é exceção declarada**, reservada a quem
precisa agir sem pedido para cumprir o papel — hoje três: as normas sempre-referenciadas (`padrao-*`,
`spec-write`) e o gatekeeper de fim de tarefa (`code-auditoria-padrao`).

---

# 3. Roteamento por situação (a tabela que resolve 90% dos casos)

| Preciso… | Use |
|---|---|
| Escrever/revisar qualquer código | `padrao-escrita` **+** a `padrao-<linguagem>` do alvo |
| **Criar um módulo, ou estruturar um sistema em módulos** | `code-modulo` — detecta sozinha se é sistema novo ou módulo novo |
| **Transformar um módulo existente em módulo genérico reutilizável** | `code-generalizacao-modulo` — repositório próprio, sem rastro da origem |
| Iniciar um repositório do zero (git, specs, projeto, 1º módulo, hooks) | `meta-iniciar-repositorio` |
| Fechar uma tarefa de escrita/refactor antes de dizer "pronto" | `code-auditoria-padrao` (gate obrigatório) |
| Saber se um código legado está conforme | `code-diagnostico` (read-only) · em escala: `/code1-auditar` |
| Adequar legado ao padrão sem mudar comportamento | `code-adequacao` · fluxo completo: `/code2-caracterizar` → `/code3-adequar` |
| Levar um legado (já em produção) ao **template de módulos** (Nível 1) | `meta-adequacao-modular` — duas conversas: planejar (Fase A) e conferir (Fase B) |
| Cortar o sistema para produção (limpeza integral, tag `v1.0.0`, `develop`) | `meta-marco-0` — quatro fases: planejar, limpar, conferir (outra conversa), publicar |
| Cobrir código novo com testes | `test-unitario` |
| Testar endpoint com banco real efêmero | `test-integracao-api` |
| Testar contrato de API em runtime (provider/consumer, payload entre versões) | `test-api-contrato` |
| Testar jornada de usuário ponta a ponta | `test-e2e` |
| Testar WebSocket/SSE, tempo real, reconexão | `test-ws-realtime` |
| Medir limite de carga, concorrência, N+1 | `test-carga` |
| Criar/alterar schema ou escrever migration | `db-migrations` |
| Caçar segredo vazado no código ou no bundle | `cyber-segredos` |
| Caçar segredo no **histórico** do git | `git-especialista-repositorio` · fluxo: `/git1-auditar` → `/git2-adequar` |
| Auditar CVEs e supply chain das dependências | `cyber-dependencias` |
| Auditoria de segurança ampla (7 domínios) | `/cyber1-auditar` → `/cyber2-adequar` |
| Revisar um diff/PR antes do commit | `git-revisao-diff` · perspectiva independente: agent `code-revisor` |
| Instalar o gate de segredos por commit | `git-verificacao-commit` |
| Criar repositório do zero / primeiro commit | `git-commit-inicial` |
| Deixar o app mais rápido sem gastar nada | `otimizacao-nivel-1` |
| Estruturar logging / métricas e alertas | `obs-logs` · `obs-monitoramento` |
| Publicar na Vercel | `/deploy-vercel` |
| Implementar, auditar, adequar ou publicar com Docker | `/docker1-implementar` · `/docker2-auditar` · `/docker3-adequar` · `/docker4-publicar` |
| Limpar o Docker de um projeto | `/docker-limpar` |
| Escrever ou padronizar uma spec | `spec-write` |
| Conferir se as specs ainda batem com o código | `spec-revisao` |
| Ver ou atualizar panorama, se adotado (resumo e progresso) | `spec-panorama` |
| Registrar um achado que não é para agora | `00-backlog.md` — o revisor escreve; ninguém executa |
| Definir o alicerce arquitetural de um repo novo | `spec-fundacao` |
| Criar/revisar uma skill | `meta-create-skill` · `/meta-criar-skill` |
| Preparar o projeto para entrega (assinatura, licença, docs) | `/code-entregar` (orquestra `code-assinatura` → `code-licenca` → `code-documentacao`) |
| Faxina de projeto (órfãos, código morto, deps não usadas) | `code-limpeza-projeto` |
| Medir e limpar processos e artefatos temporários do ambiente | `code-limpeza-ambiente` |
| Faxina ou análise de consumo da máquina inteira (processos órfãos, MCPs multiplicados, Docker/VHDX, caches, %TEMP%, inicialização) | `maquina-limpeza-otimizacao` |
| Identificar o que pesa na máquina por janela/sessão, lentidão, travamento ou superaquecimento | `maquina-monitor-recursos` |
| Varredura de malware, invasão ou pacotes maliciosos na máquina inteira | `maquina-ameacas` |

---

# 4. Catálogo de skills

> **Inventário completo.** Este índice lista **todas** as skills, agents e commands da base — não é
> subconjunto curado. Ausência aqui é **defeito**, não decisão editorial, e a checagem inversa do
> `pointers.py` (skill `meta-verificacao-base`) a cobra por máquina.

## 4.0 Os três níveis de norma — quem é dono de quê

Cada regra tem **um** dono. Quem não é dono, aponta; ninguém copia.

| Nível | Assunto | Dono | Verificador |
|---|---|---|---|
| **0** | escrita: SRP, limiares, zero hardcoded, segredos, erro, log | `padrao-escrita` | validador da `padrao-<linguagem>` + hook `padrao-limiares` |
| **1** | arquitetura de módulos: anatomia, manifesto, contrato, dados, isolamento | a spec de regras de módulo **do projeto** (no template de módulos, `arquitetura/04-regras.md`) | `node tools/gate/validate.mjs` |
| **2** | idiomas de cada linguagem | `padrao-<linguagem>` | linter configurado da linguagem |

O Nível 1 só existe em projeto que adota o **template de módulos**. Onde ele não existe, o padrão em vigor é
o Nível 0 mais o Nível 2 — não improvise meia estrutura modular.

## 4.1 `padrao-` — normas de escrita (proativas; não as únicas — critério e as demais exceções em §2)

| Skill | Quando |
|---|---|
| `padrao-escrita` | **Porta de entrada e dona do Nível 0**: clean code, limiares, zero hardcoded, segredos. Toda outra skill referencia esta. |
| `padrao-python` | Código Python — idiomas + validador de limiares (`scripts/validate.py`). |
| `padrao-typescript` | Código TS/JS — idiomas + validador via API do compilador TS. |

> **Bindings do template de módulos:** `typescript`, `javascript`, `python` — e a camada de **Nível 2**
> (idioma documentado + validador Sarak) existe só para TS/JS e Python. **Isso não é o mesmo que
> automação de limiar:** o hook `padrao-limiares` cobra função ≤40, aninhamento ≤3 e ≤4 parâmetros em
> `.py`, `.ts`/`.js`, `.go` e `.java`, sem depender de skill nenhuma. Linguagem sem nenhum dos dois segue
> o **Nível 0** do `padrao-escrita`, conferido por leitura — ausência de automação, não de norma.

## 4.2 `code-` — operações sobre código

| Skill | Quando |
|---|---|
| `code-modulo` | **Criar módulo ou sistema modular** conforme o template. Dois fluxos, detecção automática, HITL antes do scaffold, gate verde ao final. |
| `code-generalizacao-modulo` | **Destilar um módulo existente** num módulo genérico, em repositório próprio — sem negócio e sem origem, com seis degraus de verificação. |
| `code-auditoria-padrao` | **Gate de fechamento**: invoca os validadores de AST antes de declarar uma tarefa concluída. |
| `code-diagnostico` | Diagnosticar conformidade de legado (read-only) e gerar backlog priorizado. |
| `code-adequacao` | Adequar legado item por item, com rede de caracterização, **preservando comportamento**. |
| `code-limpeza-projeto` | Remover órfãos, código morto, backups, deps não usadas (HITL + Grep antes de deletar). |
| `code-limpeza-ambiente` | Fotografar, comparar e limpar IDs explícitos de processos e artefatos temporários do ambiente. |
| `code-assinatura` | Detectar, triar e remover assinaturas/créditos não autorizados; acertar metadados de autoria. |
| `code-licenca` | Apresentar o catálogo de licenças no HITL, aplicar `LICENSE` + SPDX id. |
| `code-documentacao` | Padronizar a superfície do repo: README (raiz), CONTRIBUTING, CHANGELOG, CODEOWNERS — **não** doc técnica (é do SDD, em `specs/`). |
| `code-entrega` | Orquestrador fino de pré-entrega: chama as três acima na ordem, consolida o log. Command: `/code-entregar`. |

## 4.3 `spec-` — governança de especificações

| Skill | Quando |
|---|---|
| `spec-write` | Traduzir ideia/requisito em spec padronizada (usa os moldes de `_templates/`). |
| `spec-fundacao` | Wizard HITL do alicerce arquitetural/tecnológico de um repo novo → gera os ADRs. |
| `spec-site-fundacao` | Idem, para projeto de site (institucional/marketing). |
| `spec-revisao` | Contraprova de paridade specs × código (e specs × specs) — read-only, aponta divergência e propõe o canal. |
| `spec-panorama` | Gerar `panorama/00-resumo.md` e validar famílias e itens, se o repositório adota panorama. |

## 4.4 `test-` — testes

| Skill | Quando |
|---|---|
| `test-unitario` | Código **novo**: caminhos críticos pela borda pública, mock só de I/O externo (~80%). |
| `test-integracao-api` | Endpoint com infraestrutura real efêmera (Testcontainers/Docker), sem UI. |
| `test-api-contrato` | Contract testing onde o gate estático não alcança: resposta real contra o schema, mock derivado do contrato, compatibilidade de payload entre versões. |
| `test-e2e` | Jornadas críticas na UI (Playwright/Cypress) ou API ponta a ponta. |
| `test-ws-realtime` | Conexões com estado: WebSocket/SSE, heartbeat, broadcast, pub/sub, reconexão. |
| `test-carga` | Estresse, concorrência e gargalos (k6/Artillery). **HITL obrigatório.** |

## 4.5 `cyber-` — segurança por domínio

| Skill | Quando |
|---|---|
| `cyber-segredos` | Segredo hardcoded, no bundle do front ou em log. Dono do catálogo canônico de padrões. |
| `cyber-dependencias` | CVEs, pacote abandonado, typosquatting, script de instalação malicioso. |
| `cyber-codigo` | SAST: injeção, XSS, `eval`, desserialização insegura, cripto/random fracos. |
| `cyber-auth` | Hashing de senha, JWT (alg/exp/assinatura), cookies, MFA, brute-force. |
| `cyber-api` | Autorização (IDOR/BOLA), rate limiting, CORS, SSRF/CSRF, exposição de dados. |
| `cyber-config` | Headers de segurança, TLS, paths sensíveis expostos (DAST leve). |
| `cyber-dados` | LGPD: inventário de PII, minimização, mascaramento, retenção, direitos do titular. |
| `cyber-ia` | Prompt injection, insecure output handling, data poisoning, model DoS. |
| `cyber-infra` | IaC e CI/CD: Docker/K8s, Terraform, envenenamento de pipeline. |

## 4.6 `git-` — versionamento e repositório

| Skill | Quando |
|---|---|
| `git-commit-inicial` | Repo do zero: `init`, `.gitignore`, gate, primeiro commit, remoto, tag, branch de dev. |
| `git-verificacao-commit` | Gate rápido por commit: varre só o **staged** e bloqueia (pre-commit, exit 1). |
| `git-revisao-diff` | Qualidade do diff staged contra o padrão + debug/TODO/conflito esquecidos. |
| `git-especialista-repositorio` | Auditoria do **histórico inteiro** e remediação (reescrita + rotação). HITL severo. |

## 4.7 Demais áreas

| Skill | Área | Quando |
|---|---|---|
| `db-migrations` | `db-` | Schema conforme o padrão; migrations versionadas, reversíveis, expand-contract. |
| `deploy-vercel` | `deploy-` | Preparar e publicar na Vercel (preview → produção), env por CLI. |
| `docker-padrao` | `docker-` | Norma Docker: separar imagens, tamanho, tags, compose, redes e banco, com validadores. |
| `docker-desenvolvimento` | `docker-` | Containerizar e montar `dev`, `dev:docker` e `docker:up`, com alterações em tempo real. |
| `docker-producao` | `docker-` | CI, Grype, publicação por digest, agente com reversão, servidor, backup e alertas. |
| `docker-seguranca` | `docker-` | Privilégios, chaves em runtime, socket, imagens base e vulnerabilidades. |
| `docker-higiene` | `docker-` | Inventário, retenção e limpeza Docker de um projeto, sem tocar em dados. |
| `otimizacao-nivel-1` | `otimizacao-` | Performance de **custo zero** (Core Web Vitals; índices, N+1, cache em memória). |
| `otimizacao-nivel-2` | `otimizacao-` | Performance por **concessão** (troca fidelidade/consistência por velocidade). HITL decisivo. |
| `otimizacao-nivel-3` | `otimizacao-` | Performance por **infra paga** (CDN/edge/ISR, replicas, filas). HITL de faturamento. |
| `obs-logs` | `obs-` | Logger JSON, níveis, correlation-id, agregação, retenção — sem segredo/PII. |
| `obs-monitoramento` | `obs-` | RED/USE, healthchecks, tracing OTel, dashboards, alertas/SLO. |
| `maquina-limpeza-otimizacao` | `maquina-` | Diagnosticar e limpar a **máquina** (processos órfãos, MCPs, Docker/VHDX, caches, %TEMP%, inicialização) com aprovação item a item e prova de obsolescência refeita na hora. Só sob pedido. |
| `maquina-monitor-recursos` | `maquina-` | Medir CPU, memória, disco e temperatura atribuindo o consumo a cada janela, sessão ou app e registrar picos. Só leitura, só sob pedido. |
| `maquina-ameacas` | `maquina-` | Procurar sinais de comprometimento e pacotes maliciosos na **máquina**, com remediação separada, reversível e aprovada item a item. Só sob pedido. |
| `site-organizacao` | `site-` | Rotas hierárquicas, abas × páginas, a11y. **Só em sites.** |
| `site-criacao` | `site-` | Preencher as specs vazias geradas pela `spec-site-fundacao` (formulário inteligente). |
| `site-seo` | `site-` | SEO técnico + GEO local + AEO/GSO (robots/sitemap, JSON-LD, OG, NAP). |
| `meta-create-skill` | `meta-` | Criar/revisar skill: 3 camadas, `description`-gatilho, scaffold, checklist. |
| `meta-iniciar-repositorio` | `meta-` | Preparar um repo-alvo para receber inteligência local (`.agents/`, entrypoints, hook de índice). |
| `meta-adequacao-modular` | `meta-` | Levar um legado ao template de módulos — diagnóstico, gate instalado antes do refactor, plans `xx-*`, conferência em conversa separada. |
| `meta-marco-0` | `meta-` | Marco-0: limpa o legado para produção (comentários e migrations obsoletos), prova a paridade do schema, fecha as specs sem ADRs de evolução e publica `v1.0.0` + `develop`. |
| `meta-atualizar-base` | `meta-` | Atualizar a Fonte da Verdade Sarak e espelhar para as IDEs (`sync_ide.py`). |
| `meta-verificacao-base` | `meta-` | Verificar integridade da base: YAML, contratos JSON, ponteiros órfãos. |
| `meta-fluxos` | `meta-` | Executar um fluxo de `commands/` pelo nome num harness sem commands (Codex) — roteia, não copia. |
| `meta-propagar-base` | `meta-` | Propagar atualizações da base aos sistemas do `mapa.json` — hoje, só o plano por sistema (somente leitura). |

---

# 5. Commands (17) — disparo manual pelo humano

| Command | Fase | O que faz |
|---|---|---|
| `/code1-auditar` | 1 | Fan-out de `code-auditor` por módulo → plano de adequação em `.sarak/audit`. Read-only. |
| `/code2-caracterizar` | 2 | Rede de testes de caracterização nos módulos sem teste (só adiciona testes). |
| `/code3-adequar` | 3 | Caminha o backlog onda a onda, roteando por risco. **Mutativo.** |
| `/cyber1-auditar` | 1 | Fan-out de `cyber-auditor` pelos 7 domínios → relatório em `.sarak/security/`. |
| `/cyber2-adequar` | 2 | Adequa achados por severidade, HITL por achado, re-scan. **Mutativo.** |
| `/git1-auditar` | 1 | Varre todo o histórico (branches + tags) caçando vazamentos. Read-only. |
| `/git2-adequar` | 2 | Expurga vazamentos do histórico + rotação. **IRREVERSÍVEL**, HITL severo. |
| `/deploy-vercel` | — | Publica na Vercel. |
| `/docker1-implementar` | 1 | Pergunta o ambiente e cria a estrutura Docker. **Mutativo.** |
| `/docker2-auditar` | 2 | Pergunta o ambiente, faz fan-out de `docker-auditor` e grava em `.sarak/docker/`. Read-only. |
| `/docker3-adequar` | 3 | Pergunta o ambiente e corrige achados pela skill dona, com HITL. **Mutativo.** |
| `/docker4-publicar` | 4 | Publica ou reverte com pré-voo e confirmação do servidor. **Produção.** |
| `/docker-limpar` | — | Mostra ou aplica a retenção Docker do projeto. **Destrutivo com aprovação.** |
| `/site-organizar` | — | Estrutura arquitetura e navegação do site. |
| `/site-seo` | — | Torna o site encontrável e indexável. |
| `/meta-criar-skill` | — | Cria/revisa uma skill no padrão. |
| `/code-entregar` | — | Orquestra `code-assinatura` → `code-licenca` → `code-documentacao`. **Mutativo.** |

> **Um agente não digita `/comando`.** Se uma plan depende de um command, ela **instrui o humano** a rodá-lo
> (ou o executor aplica diretamente a **skill** equivalente, que é onde a lógica vive).

---

# 6. Agents (6) — subagentes de contexto isolado

| Agent | Papel | Disparado por | Escreve? |
|---|---|---|---|
| `code-auditor` | Auditoria de conformidade de **um** módulo (12 dimensões) | `/code1-auditar` | só `.sarak/audit` |
| `code-adequador` | Executa **uma** tarefa de adequação de risco baixo/médio | `/code3-adequar` | sim (código) |
| `code-revisor` | Revisão **independente** de um diff/PR (gate + caça-bugs) | sob demanda / orquestrador | não |
| `cyber-auditor` | Auditoria de **um** domínio de segurança | `/cyber1-auditar` | só `.sarak/security/` |
| `git-auditor` | Varredura do histórico Git completo | `/git1-auditar` | só `.sarak/git-audit` |
| `docker-auditor` | Auditoria de **um** domínio Docker | `/docker2-auditar` | só `.sarak/docker/` |

> Agent **não faz HITL** — quem confirma com o humano é a thread principal. Auditor não recebe `Edit`/`Write`:
> o read-only é travado mecanicamente pelas ferramentas.

---

# 7. Hooks (2) — as garantias determinísticas

| Hook | Evento | Garante |
|---|---|---|
| `pre-tool-bash` | PreToolUse `Bash` | Despachante único: só age em comandos Git e `docker`. Aplica `cyber-git-seguro` (comando git perigoso, commit com segredo) e, no push, `cyber-dependencias` (instalação de pacote suspeito/vulnerável) e `test-cobertura` (exigência de teste antes de operações de entrega). |
| `post-tool-edit` | PostToolUse `Write\|Edit\|MultiEdit\|apply_patch` | Despachante único, nesta ordem: `padrao-format` (formata o que foi escrito, sem reformatar legado fora do formatador), `padrao-limiares` (limiares objetivos: linhas, aninhamento, parâmetros) e `padrao-idioma` (avisa identificador do arquivo editado que bate o vocabulário fechado de português; (o código é em inglês — `ADR-023`); nunca bloqueia por padrão. |

Cada hook continua existindo como módulo e rodável à mão (`node hooks/<nome>.js`); os despachantes só os combinam em um processo.

Ativação: nativa ao instalar o plugin (`hooks/hooks.json`) — no Claude Code entra ativa; no Codex, depois de
autorizar os hooks do plugin no app. Modo manual (só Claude Code): mesclar `hooks/settings.template.json` no
`.claude/settings.json` do projeto.

> **Hook bloqueou? Não contorne.** O bloqueio é informação: corrija a causa. Executor que burla um hook tem a
> execução reprovada automaticamente pelo revisor.

---

# 8. MCP — ferramentas externas

Servidores configurados na base (cada `config.json` é local e **fora do versionamento** — contém tokens):

| Servidor | Para |
|---|---|
| `github` | Repos, PRs, issues, Actions |
| `vercel` | Deploys, logs de runtime, projetos |
| `supabase` · `neon` · `postgres-local` | Banco de dados (gerenciado e local) |
| `docker` | Containers e imagens |
| `puppeteer` | Automação de navegador |
| `sequential-thinking` | Raciocínio estruturado em problemas longos |
| `StitchMCP` | Geração/integração de UI |

Ferramenta MCP só existe se o servidor estiver conectado **nesta sessão**. Uma plan que dependa de MCP deve
declarar isso e prever o caminho alternativo (CLI) — execução headless pode não ter os servidores
autenticados interativamente.

---

# 9. Regras de roteamento

1. **Cite, não copie.** Numa plan, escreva "aplique `db-migrations`" — jamais reproduza o conteúdo da skill.
   Conteúdo copiado desatualiza e passa a contradizer a fonte.
2. **Skill certa > esforço improvisado.** Existe skill para o assunto? Use. Não reinvente o fluxo dela.
3. **`padrao-escrita` + `padrao-<linguagem>` são o piso** de qualquer tarefa que toque código — sempre, sem
   precisar ser pedido.
4. **`code-auditoria-padrao` é o teto**: nenhuma tarefa de escrita/refactor é declarada concluída antes dela.
5. **Mutativo e sensível exige HITL.** `otimizacao-nivel-2/3`, `/git2-adequar`, `test-carga`, deploys: pare e
   pergunte. Um agente nunca decide sozinho o que é irreversível ou custa dinheiro.
6. **Auditar antes de adequar.** Nas áreas `code-`/`cyber-`/`git-`, a fase 1 é read-only e produz o plano; a
   fase 2 é mutativa e consome esse plano. Não pule a fase 1.
7. **Nada de commit por agente.** Nenhuma skill autoriza commit no ciclo SDD — quem commita é o usuário.

---

# 10. Contrato de manutenção desta spec

- Esta spec é **universal**: idêntica em todos os repositórios. Não a personalize por projeto — o que é
  específico do repositório vive em [[00-contexto]].
- Atualize quando a **base Sarak** mudar (skill/command/agent/hook criado, renomeado ou removido) — via plan,
  como qualquer outra alteração.
- Contagens declaradas (§4 e cabeçalhos) fazem parte do conteúdo: se o número mudar, corrija o número.
- **Ponteiro órfão é defeito**: skill citada aqui tem de existir na base instalada.
