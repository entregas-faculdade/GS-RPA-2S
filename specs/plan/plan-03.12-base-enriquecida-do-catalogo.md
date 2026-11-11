---
tipo: "plan"
familia: "03"
item: "R03.12"
titulo: "Aceitar uma base enriquecida do catálogo (conteúdo por página, vários arquivos) e usá-la na recuperação e na resposta"
dominio: "Automação"
status: "🟡 Em execução"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[03.02-resposta-final-e-llm]]", "[[03.03-localizador-de-servicos]]", "[[007-llm-redige-a-resposta-com-rag-do-catalogo]]"]
depende_de: "—"
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

# 1. Objetivo
O catálogo passa a aceitar uma **base enriquecida** trazida pelo usuário: muitas entradas por tarefa (link da página específica) em
arquivos extras, cada uma com um **trecho oficial da página** (`content`) que o LLM usa para redigir respostas mais completas, e que
a recuperação também usa para achar a entrada certa. Tudo continua anterior ao LLM: o robô carrega, verifica e recupera; o LLM só
redige sobre o que foi recuperado.

# 2. Contexto
Hoje o catálogo (`data/catalog.json`, 55 registros, 51 aprovados) é quase só de portais, com 1 ou 2 links e uma instrução curta
por entrada, e a resposta fica rasa ("busque no portal"). O usuário vai **montar e entregar a base enriquecida** (páginas oficiais por
tarefa, com o trecho que responde), então esta plan entrega a **capacidade**, o **formato** e o **guia**, não o conteúdo. Navegação do
agente pela internet fica fora: o conteúdo é curado e verificado antes, nunca buscado na hora da pergunta.

Estado atual relevante: `ServiceEntry` tem `id, category, kind, scope, coverage, area, display_name, agency, instructions, keywords,
links, phones, source_note, verified_on, status`; `load_catalog(path=CATALOG_PATH)` lê um arquivo, ignora registro inválido e `id`
repetido com log; `ServiceFinder` indexa `keywords + display_name + agency`; `rag.py` monta o bloco de cada fonte (nome, órgão,
abrangência, instruções, links, telefones); `validate_rag_output` aceita só URL de link das fontes e só telefone das fontes (sequência
de 3+ dígitos); `scripts/verify_catalog.py` audita o catálogo; a allowlist é `gov.br` (inclui `*.sp.gov.br`).

## 2.1 Contrato (decisão desta plan)
- **Campo novo, opcional:** `content` (texto, padrão vazio): trecho oficial da página que fundamenta a resposta, até
  `MAX_CONTENT_LENGTH` = 3000 caracteres (constante do esquema, como `MAX_RESPONSE_LENGTH`); acima disso o registro é inválido,
  com log. Registro sem `content` continua válido e se comporta como hoje.
- **Vários arquivos:** `load_catalog()` lê `data/catalog.json` e depois todos os `data/catalog.d/*.json`, em ordem de nome, mesmo
  esquema (lista de registros). Pasta ausente ou vazia não é erro. `id` repetido entre arquivos: vale o primeiro, com log. A pasta
  `data/catalog.d/` nasce na entrega, sem nenhum `.json` (o exemplo vive só no guia, §5.5).
- **Regra de entrada da base trazida pelo usuário:** o registro entregue pelo usuário em `data/catalog.d/` conta como aprovado por
  ele (não precisa constar em `docs/fontes-publicas-sp-para-aprovacao.md`), mas só **responde** se `status` é `approved` **e** o
  verificador confirma domínio na allowlist e link vivo; senão fica `candidate`, como hoje.
- **Recuperação:** o documento de busca de cada entrada passa a ser `keywords + display_name + agency + content`. Sem nenhum `content`
  no catálogo, a pontuação e as métricas do localizador (`finder_metrics`, 96 pedidos) ficam **idênticas** às atuais.
- **Resposta:** o bloco de cada fonte enviado ao LLM ganha `Conteúdo:` (o `content`, quando houver) depois das instruções. A guarda
  passa a aceitar, além dos telefones das fontes, as sequências de 3+ dígitos que aparecem em `instructions` ou `content` das fontes
  enviadas (números do próprio texto oficial), e continua rejeitando qualquer outra; links seguem só os `links` das fontes.
- **Verificador:** `scripts/verify_catalog.py` audita o conjunto carregado (catálogo + `catalog.d`), aponta o arquivo de origem de
  cada erro e confere `content` (tamanho e se não é vazio quando presente).

# 3. Escopo
## 3.1 Dentro
- `src/triage/automation/catalog.py` — campo `content`, validação do tamanho, leitura de `data/catalog.json` + `data/catalog.d/*.json`
- `src/triage/automation/finder.py` — `content` no documento de busca
- `src/triage/automation/rag.py` — `Conteúdo:` no bloco da fonte
- `src/triage/automation/response_guard.py` — dígitos do texto das fontes aceitos
- `src/triage/automation/catalog_audit.py` e `scripts/verify_catalog.py` — auditar o conjunto e o `content`
- `data/catalog.d/` (nova pasta, só com um `README.md`) e `docs/guia-da-base-enriquecida.md` (novo)
- `README.md` — um parágrafo curto sobre a base enriquecida e o guia
- `tests/automation/` — testes de catálogo, finder, rag, guarda e auditoria

## 3.2 Fora
- O **conteúdo** da base (é do usuário) e qualquer entrada real nova em `data/catalog.json`.
- Navegação do LLM, busca na internet em tempo de pergunta, scraping automático, rastreador (crawler).
- `triage.pipeline`, `triage.interface`, `triage.classification`, o agente (`data/agents/`) e as ADRs.
- Mudar `FINDER_MIN_SCORE`, `FINDER_MARGIN` ou o conjunto rotulado do localizador.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | esquema do catálogo, regras de entrada, verificador |
| Spec fixa | [[03.02-resposta-final-e-llm]] · [[03.03-localizador-de-servicos]] | mensagem ao LLM, guarda e documento de busca |
| ADR | [[007-llm-redige-a-resposta-com-rag-do-catalogo]] · [[003-seguranca-sem-autenticacao]] | o catálogo é o RAG; só link aprovado e verificado |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` · `cyber-ia` | zero hardcoded, saída não confiável |
| Skill | `test-unitario` | testes sem rede |
| Código | `src/triage/automation/{catalog,finder,rag,response_guard,catalog_audit,resolver}.py`, `scripts/verify_catalog.py`, `data/catalog.json` | o que muda e o formato dos registros |
| Código | `tests/automation/`, `docs/fontes-publicas-sp-para-aprovacao.md` | testes a ajustar e o formato de fonte já usado |

# 5. Instruções de execução
1. [dirigido] **Esquema e leitura.** `content` opcional em `ServiceEntry` e na validação (§2.1); `load_catalog()` lê `data/catalog.json` e
   `data/catalog.d/*.json`. Funções pequenas; arquivo ilegível ou JSON inválido em `catalog.d` é registrado e ignorado, sem derrubar os
   demais (como o catálogo único já faz). O caminho da pasta é parâmetro com padrão, para os testes usarem uma pasta temporária.
2. [dirigido] **Recuperação.** `ServiceFinder` indexa o `content`; sem `content` em nenhuma entrada, as pontuações e o resultado da medição de
   `finder_metrics` não mudam (teste prova, com o conjunto de 96 pedidos).
3. [dirigido] **RAG e guarda.** `Conteúdo:` no bloco da fonte; a guarda aceita os dígitos de `instructions` e `content` das fontes enviadas,
   mantendo `foreign_phone` para o resto, e a rejeição de URL e endereço alheios sem alteração.
4. [dirigido] **Verificador.** `scripts/verify_catalog.py` audita catálogo + `catalog.d`, informa o arquivo de cada achado, confere o `content` e
   segue com código de saída `0` sem erro e `1` com erro; o catálogo atual continua passando exatamente como hoje.
5. [dirigido] **Guia.** `docs/guia-da-base-enriquecida.md`, em português, para o usuário preencher a base: onde colocar os arquivos
   (`data/catalog.d/<nome>.json`), cada campo do registro (obrigatório ou opcional, o que escrever), como escrever `keywords` (o que o
   cidadão diz) e `content` (trecho oficial copiado da página, curto, sem dado pessoal), uma entrada de exemplo completa **marcada como
   exemplo** (use uma das entradas reais já existentes no catálogo como modelo, sem inventar URL), a regra de aprovação do §2.1, o
   comando de verificação (`python scripts/verify_catalog.py`) e como ler o resultado.
6. [dirigido] **Pasta e exemplo.** Criar `data/catalog.d/` com um `README.md` de uma linha apontando o guia; **nenhum** arquivo `.json` de
   exemplo fica na pasta (para não virar fonte real); o exemplo vive só no guia.
7. [dirigido] **Testes** (sem rede): `content` válido, vazio e acima do limite; carga de `catalog.json` + `catalog.d` (ordem, `id` repetido entre
   arquivos, JSON inválido num arquivo sem derrubar os outros, pasta ausente); recuperação acha a entrada pelo texto do `content`; recuperação
   idêntica sem `content`; bloco do RAG com `Conteúdo:`; guarda aceita dígito do `content` e rejeita dígito fora das fontes; verificador aponta o
   arquivo e o limite do `content`.
8. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Registro com `content` válido carrega; acima de `MAX_CONTENT_LENGTH` é rejeitado com log; sem `content` nada muda.
- [ ] `data/catalog.d/*.json` é lido além de `data/catalog.json`, com `id` repetido resolvido pelo primeiro e falha de um arquivo isolada.
- [ ] A recuperação usa `content`; sem `content`, as pontuações e as métricas do localizador são idênticas às atuais.
- [ ] O bloco de cada fonte no RAG traz `Conteúdo:`; a guarda aceita só dígitos do texto das fontes ou telefones delas e continua rejeitando URL e telefone alheios.
- [ ] `verify_catalog.py` audita o conjunto, indica o arquivo de origem e continua verde para o catálogo atual.
- [ ] O guia existe, está em português, é suficiente para o usuário montar a base, e não contém URL inventada.
- [ ] Nenhum teste faz chamada real; ambiente e worktree limpos; `ruff` e validador sem violação nova.
- [ ] O notebook de evidências continua executando sem erro (ele usa o catálogo e o localizador).

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — muda o esquema do catálogo, consumido por resolver, localizador, RAG, guarda, verificador e notebook`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py -q` → verde.
- `python -m ruff check src/triage/automation scripts tests/automation` → sem erro novo.
- `validate.py` do `padrao-python` nos `.py` tocados → sem achado.
- `python scripts/verify_catalog.py --offline` → sem erro; o revisor cria, no scratchpad, uma pasta com um registro com `content` (e outro acima do limite)
  e confere o resultado e o arquivo apontado.
- Sondagem: cliente falso, fonte com `content` contendo "30 dias" e "156": saída com esses números passa; saída com um número que não está nas fontes é rejeitada.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` sem erro.
- **Gate:** `nenhum — coberto por testes e sondagem`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md` (esquema, leitura de vários arquivos, regra de entrada da base do usuário, verificador) e, no que for
regra de resposta, `specs/03.02-resposta-final-e-llm.md` (`Conteúdo:` no bloco e dígitos aceitos pela guarda) e `specs/03.03-localizador-de-servicos.md` (documento de busca com `content`).

Escrever, **substituindo** o que hoje diz que cada fonte consta no documento de aprovação: a base entregue pelo usuário em `data/catalog.d/` vale como aprovada por ele, e só
responde com `status` aprovado, domínio na allowlist e link vivo.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->
