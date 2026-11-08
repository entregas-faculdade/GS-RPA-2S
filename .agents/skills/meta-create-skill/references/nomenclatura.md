# Nomenclatura — o vocabulário fechado de prefixos de área

> Camada 3 da skill `meta-create-skill`. **Fonte ÚNICA** do vocabulário de prefixos de área que
> nomeia skill, command, agent e hook — `<prefixo>-<nome>`, kebab-case. O `SKILL.md` desta skill e
> o `README.md` da raiz da base **apontam** para aqui; nenhum dos dois repete a tabela. Antes deste
> arquivo existir, os dois tinham cópia própria e divergiam (`README.md` §6 tinha `spec-` e não
> tinha `api-`; `SKILL.md` tinha `api-` — exemplificado com uma skill que já foi renomeada — e não
> tinha `spec-`). `skills/meta-verificacao-base/scripts/audit_base.py` cobra, por máquina, que todo
> `skills/*`, `commands/*` e `agents/*` comece por um prefixo daqui.

## O vocabulário

| Prefixo | Área | Exemplos |
|---|---|---|
| `padrao-` | Normas de escrita/organização (sempre referenciadas) | `padrao-escrita`, `padrao-python`, `padrao-typescript` |
| `code-` | Operações sobre código (inclui criação de módulo/sistema modular) | `code-diagnostico`, `code-adequacao`, `code-assinatura`, `code-licenca` |
| `spec-` | Especificações e fluxo SDD | `spec-write`, `spec-fundacao`, `spec-site-fundacao` |
| `test-` | Testes (inclui contract testing de API) | `test-unitario`, `test-e2e`, `test-api-contrato` |
| `db-` | Banco de dados | `db-migrations` |
| `deploy-` | Publicação/entrega fora de Docker | `deploy-vercel` |
| `docker-` | Docker em desenvolvimento e produção | `docker-padrao`, `docker-desenvolvimento`, `docker-producao`, `docker-seguranca`, `docker-higiene` |
| `otimizacao-` | Performance (back+front) | `otimizacao-nivel-1`, `otimizacao-nivel-2`, `otimizacao-nivel-3` |
| `obs-` | Observabilidade | `obs-logs`, `obs-monitoramento` |
| `site-` | Construção de site (web) | `site-organizacao`, `site-seo`, `site-criacao` |
| `git-` | Versionamento/repositório | `git-commit-inicial`, `git-verificacao-commit`, `git-revisao-diff`, `git-especialista-repositorio` |
| `cyber-` | Segurança (por domínio) | `cyber-segredos`, `cyber-dependencias`, `cyber-codigo`, `cyber-auth`, `cyber-api`, `cyber-config`, `cyber-dados`, `cyber-ia`, `cyber-infra` |
| `maquina-` | A máquina de desenvolvimento inteira (manutenção, monitoramento de recursos e ameaças), sem vínculo com projeto | `maquina-limpeza-otimizacao`, `maquina-monitor-recursos`, `maquina-ameacas` |
| `meta-` | Ecossistema/governança das próprias funcionalidades | `meta-create-skill`, `meta-verificacao-base`, `meta-iniciar-repositorio`, `meta-adequacao-modular`, `meta-atualizar-base` |

## Regras

- Vale para **skill, command, agent e hook** — a área é a mesma nos quatro blocos; só a **classe
  gramatical** do nome muda por bloco (descritivo/verbo/substantivo de papel — ver `README.md` §6).
- Crie um **prefixo novo** quando uma área nova ganhar tração (≥3 skills **ou** roadmap explícito
  já declarado) — evita prefixo prematuro que nunca vinga. Exceção registrada: `maquina-` foi aberto com
  **uma** skill por decisão do dono em 2026-10-27, por ser uma área distinta (a máquina inteira, não um
  projeto nem uma tarefa).
- **Proibido** o prefixo redundante `skill-` (não agrupa nada — o tipo do bloco já vem da pasta).
- `scripts/scaffold_skill.py` valida prefixo + kebab-case no momento da criação; o vocabulário dele
  precisa bater com o desta tabela.
