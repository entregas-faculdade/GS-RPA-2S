---
tipo: "arquitetura"
familia: "FF" # Opcional; só com famílias declaradas.
titulo: "Operação — ambientes, publicação e servidor"
dominio: "Infraestrutura"
status: "🟢 Vigente" # Opções: 🟢 Vigente, 🔴 Obsoleto
tags: ["arquitetura", "operacao", "docker"]
relacionados: [] # SÓ specs fixas (specs/ · arquitetura/ · adr/). NUNCA uma plan — ela some na síntese.
---

> **Molde da spec de operação.** Sem famílias, `arquitetura/operacao.md`; com famílias,
> `arquitetura/FF.NN-operacao.md`. Nasce em `/docker1-implementar prod` (skill `docker-producao`), que grava aqui as
> decisões aprovadas. Descreva como o sistema **é** operado; nunca guarde segredo, só o nome da variável e onde mora.
> Seção que não se aplica fica com "Não se aplica" e o motivo.

# 1. Ambientes

| Ambiente | Onde roda | Como sobe | Dados |
|---|---|---|---|
| Desenvolvimento | máquina do desenvolvedor | `npm run dev` · `npm run dev:docker` | banco em container, volume nomeado |
| Ensaio | máquina do desenvolvedor | `npm run docker:up` | idem |
| Homologação | <espelho local ou servidor> | <comando> | <origem> |
| Produção | <servidor> | publicação (§3) | <banco gerenciado ou container> |

# 2. Imagens

| Imagem | Dockerfile | Registry | Orçamento |
|---|---|---|---|
| `<project>-app` | `Dockerfile` | `ghcr.io/<owner>/<project>-app` | <MB> |
| `<project>-front` | `front.Dockerfile` | `ghcr.io/<owner>/<project>-front` | <MB> |

Versão = hash curto do commit. Varredura: Grype, bloqueio em alta ou crítica com correção disponível.

# 3. Publicação

- **Construção:** `.github/workflows/build.yml`, uma vez por commit verde na `main`.
- **Publicação:** `.github/workflows/publish.yml`, manual. Publicadores: variável `PUBLISHERS` (<logins>).
- **Pré-voo:** migrations, `.env.example` e `deploy/` desde a versão no ar.
- **Confirmação:** rota de estado `<URL>`; só `applied` é sucesso.
- **Reversão:** automática pelo agente; manual pela publicação da versão anterior. O banco não volta.

# 4. Servidor

| Item | Valor |
|---|---|
| Provedor e região | <...> |
| Sistema e acesso | <Linux>, SSH só por chave |
| Entrada | <túnel / Caddy / Traefik>; portas abertas: <nenhuma / 80, 443> |
| Pasta | `/opt/<project>/` |
| Agente | `<project>-publication-agent` (systemd), consulta a cada <N> s |
| Limites | memória do app `DEPLOY_APP_MEMORY`; log 10 MB × 3 |
| Retenção | servidor: versão no ar + anterior · registry: produção + 3 construções |

# 5. Banco e backup

| Item | Valor |
|---|---|
| Banco de produção | <gerenciado / container> |
| Migrations | aditivas e compatíveis com a versão anterior (`db-migrations`) |
| Backup | <frequência, destino> |
| Última restauração provada | <AAAA-MM-DD> |

# 6. Chaves

| Arquivo ou cofre | Conteúdo | Quem lê |
|---|---|---|
| Cofre <nome> | origem de todos os segredos | pessoas autorizadas |
| `/opt/<project>/.env` | segredos do processo (permissão 600) | `app` |
| `/opt/<project>/.env.deploy` | registry, digests, limites | só o compose e o agente |

# 7. Observação e alertas

| Sinal | Ferramenta | Destino |
|---|---|---|
| Disponibilidade | monitor externo de `<URL>/healthz` | <canal> |
| Publicação revertida ou falha | `ALERT_WEBHOOK_URL` do agente | <canal> |
| Logs | <agregador> (`obs-logs`) | <...> |
| Métricas | <ferramenta> (`obs-monitoramento`) | <...> |

# 8. Rotina

| Tarefa | Frequência | Comando ou skill |
|---|---|---|
| Auditoria Docker | <mensal> | `/docker2-auditar prod` |
| Limpeza local | <semanal> | `/docker-limpar` |
| Atualização de imagens base | mensal ou por alerta do Grype | `docker-seguranca` |
| Prova de restauração | <trimestral> | `docker-padrao/references/banco.md` |
