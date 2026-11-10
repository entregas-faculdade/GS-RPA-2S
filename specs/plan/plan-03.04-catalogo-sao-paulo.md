---
tipo: "plan"
familia: "03"
item: "R03.4"
titulo: "Carregar no catálogo a lista aprovada de fontes públicas (saúde, educação, veículos e prefeitura de São Paulo)"
dominio: "Automação"
status: "🔴 A executar"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[003-seguranca-sem-autenticacao]]"]
depende_de: "plan-03.03-catalogo-v2 — precisa estar 🟢; e a lista do §5 aprovada pelo usuário"
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

> ⚠️ **Não despachar antes de duas coisas:** a plan-03.03 aprovada e o §5.A **substituído pela lista que o usuário
> aprovou** (hoje ele contém só a lista inicial de candidatos, escrita pelo revisor).

# 1. Objetivo
O catálogo cobre, para o piloto **estado e cidade de São Paulo**, as áreas de saúde, educação, veículos e serviços da
prefeitura, com links e telefones oficiais **aprovados pelo usuário** e verificados por máquina, e continua dando a
resposta certa às 8 categorias que já existem.

# 2. Contexto
O formato v2 (vários links e telefones, esfera, abrangência, aprovação) vem da plan-03.03
([[03.01-catalogo-e-allowlist]]). Esta plan é **só conteúdo**: dados e testes de dados. A curadoria é do usuário: ele
decide a lista, o revisor a transcreve no §5.A, o executor a carrega.

Regras de honestidade do conteúdo (valem acima de qualquer conveniência):
- **Nenhum link nem telefone é inventado.** Valem só os que estão no §5.A ou que o executor encontrou na página
  **oficial** do órgão e registrou no `source_note` (de onde veio).
- Link que não responde ou telefone `não confirmado` pelo verificador **não** vira `approved`: fica `candidate`, com o
  motivo no `source_note`, e vai listado no resumo.
- O critério do catálogo é ser **serviço público** de órgão oficial; sem esfera ou órgão claros, não entra.
- O catálogo atual tem três fragilidades já conhecidas (certidão de nascimento aponta uma notícia; título de eleitor e
  IPTU apontam o catálogo geral do gov.br; `tse.jus.br` fora da allowlist). Onde a lista aprovada trouxer uma fonte
  melhor, **acrescente** o registro novo (id diferente) e mantenha o antigo como está.

# 3. Escopo
## 3.1 Dentro
- `data/catalog.json` — registros novos conforme o §5.A (`status: approved` ou `candidate`)
- `data/allowed_domains.json` — **só** os sufixos que o §5.A marcar como aprovados, cada um com `reason`
- `tests/automation/test_catalog_content.py` (novo) — testes de conteúdo, sem rede

## 3.2 Fora
- Qualquer código em `src/` e `scripts/` (o formato e o verificador são da plan anterior).
- Domínio fora da allowlist e que o §5.A não aprovou; links de redes sociais e de aplicativos.
- Busca por texto e mensagens (planos seguintes).

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | catálogo, allowlist, verificação de links (o formato v2 está descrito na plan-03.03 e, após a síntese, na spec) |
| ADR | [[003-seguranca-sem-autenticacao]] | só domínios oficiais |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | testes |
| Skill | `test-unitario` | testes de dados |
| Código | `data/catalog.json`, `data/allowed_domains.json`, `src/triage/automation/catalog.py`, `src/triage/automation/catalog_audit.py`, `scripts/verify_catalog.py` | formato e verificador |

# 5. Instruções de execução

## 5.A Lista de fontes (entrada desta plan)
> **O revisor substitui esta tabela pela lista aprovada pelo usuário.** Colunas: área · esfera · órgão/serviço ·
> `kind` · link(s) conhecido(s) · telefone(s) · **aprovado?** Linha sem "sim" em *aprovado* entra como `candidate`.
> A lista abaixo é **inicial e não verificada**: nenhum endereço foi aberto ainda.

| Área | Esfera | Fonte | `kind` | Domínio / link conhecido | Telefone | Aprovado? |
|---|---|---|---|---|---|---|
| health | federal | Meu SUS Digital, vacinação e Farmácia Popular | portal | `gov.br/saude` | 136 | — |
| health | federal | ANVISA | portal | `gov.br/anvisa` | — | — |
| health | federal | SAMU (urgência) | channel | — | 192 | — |
| health | state | Secretaria de Estado da Saúde de SP | portal | `saude.sp.gov.br` | — | — |
| health | municipal | Secretaria Municipal da Saúde de SP (UBS, AMA, vacinação) | portal | `prefeitura.sp.gov.br` | 156 | — |
| education | federal | ENEM e SISU (INEP/MEC) | service | `inep.gov.br`, `mec.gov.br` | — | — |
| education | federal | ProUni, FIES e Pé-de-Meia (MEC) | portal | `mec.gov.br` | — | — |
| education | state | Secretaria da Educação de SP (matrícula, rede estadual) | portal | `educacao.sp.gov.br` | — | — |
| education | municipal | Secretaria Municipal de Educação de SP (matrícula, creche) | portal | `prefeitura.sp.gov.br` | 156 | — |
| vehicles | federal | Senatran: CNH, Carteira Digital de Trânsito, Renainf | portal | `gov.br/transportes` | — | — |
| vehicles | state | DETRAN-SP: licenciamento, CRLV, multas | portal | `detran.sp.gov.br` | — | — |
| vehicles | state | SEFAZ-SP: IPVA | service | `fazenda.sp.gov.br` | — | — |
| vehicles | state | Poupatempo | portal | `poupatempo.sp.gov.br` | — | — |
| city | municipal | Portal da Prefeitura de São Paulo | portal | `prefeitura.sp.gov.br` | — | — |
| city | municipal | SP156 (buraco, iluminação, lixo, poda) | channel | `prefeitura.sp.gov.br` | 156 | — |
| tax | municipal | IPTU e Secretaria Municipal da Fazenda | service | `prefeitura.sp.gov.br` | 156 | — |
| city | municipal | Alvará e MEI (Prefeitura e Receita) | service | `prefeitura.sp.gov.br`, `gov.br/receitafederal` | — | — |
| city | municipal | Ouvidoria da Prefeitura | channel | `prefeitura.sp.gov.br` | 156 | — |
| safety | federal | Polícia, bombeiros, violência e defesa civil | channel | — | 190, 193, 180, 100, 199 | — |

**Pelo menos os canais `safety` precisam estar aprovados** (a plan de mensagens os usa em caso de urgência).

## 5.B Passos
1. [dirigido] **Registros.** Para cada linha do §5.A, um registro v2 em `data/catalog.json`: `id` curto e único (sem
   reutilizar um id existente), `category` só quando o serviço corresponde **exatamente** a uma das 8 categorias do
   classificador (senão `null`), `kind`, `scope`, `coverage` verdadeiro (ex.: `Cidade de São Paulo`), `area`,
   `display_name`, `agency`, `instructions` (1 a 2 frases em português claro, sem prometer nada que a página não diga),
   `keywords` (6 a 12 termos **como o cidadão escreve**, sem acento, com variações: `buraco na rua`, `tapa buraco`,
   `lampada queimada`), `links`, `phones`, `source_note`, `verified_on` (a data da verificação) e `status`.
2. [dirigido] **Links.** Quando o §5.A traz só o domínio, abrir o site **oficial** e escolher a página mais específica
   que existir para o serviço; registrar no `source_note` como foi achada. Se não for possível abrir ou achar, o
   registro fica `candidate`. **Proibido** adivinhar caminho de URL.
3. [dirigido] **Allowlist.** Os sufixos de `*.sp.gov.br` e `*.prefeitura.sp.gov.br` já cabem em `gov.br`. Qualquer outro
   domínio entra em `data/allowed_domains.json` **somente** se o §5.A o aprovou, com `reason`.
4. [dirigido] **Verificação.** Rodar `python scripts/verify_catalog.py` **com rede**. Todo erro (link fora da allowlist, sem
   link vivo) corrige o dado ou rebaixa o registro a `candidate`. Colar no resumo a saída resumida e a lista de
   registros rebaixados e de telefones `não confirmados`. Telefone `não confirmado` **só** fica `approved` se o §5.A o
   trouxer como aprovado pelo usuário; mesmo assim, dizer no resumo.
5. [dirigido] **Testes de conteúdo** (sem rede, em `test_catalog_content.py`): todo registro carrega no v2; `id` único;
   todo link dos `approved` está na allowlist; todo `approved` tem `keywords` com ao menos 5 termos; as 8 categorias
   originais ainda resolvem para a mesma URL de antes; para cada área (`health`, `education`, `vehicles`, `city`,
   `safety`) existe ao menos um `approved`; há ao menos um `approved` com `phones` em `safety`; nenhum `keywords` repete
   um termo de outro registro de **área diferente** sem estar em uma lista de exceções documentada no teste.
6. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Cada linha aprovada do §5.A virou registro `approved` ou, com motivo registrado, `candidate`; nenhuma linha não aprovada virou `approved`.
- [ ] Nenhum link ou telefone foi inventado: todo item vem do §5.A ou de página oficial citada no `source_note`.
- [ ] `scripts/verify_catalog.py` (com rede) roda sem erro; avisos listados no resumo.
- [ ] As 8 categorias originais resolvem como antes; os canais `safety` aprovados têm telefone.
- [ ] Testes de conteúdo verdes e sem rede; `ruff` sem erro no arquivo de teste; nenhuma chave no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `escopada`.
- `git diff --stat` → só `data/catalog.json`, `data/allowed_domains.json` e o teste de conteúdo.
- `python -m pytest tests/automation -q` → verde.
- `python -m ruff check tests/automation` e `validate.py` do `padrao-python` no teste novo → sem achado.
- `python scripts/verify_catalog.py` (com rede, uma vez) → sem erro; o revisor abre uma amostra de links e confere
  cada telefone `approved` contra a página citada no `source_note`.
- Conferência linha a linha entre o §5.A e o catálogo (aprovado × `approved`).
- **Gate:** `nenhum — coberto pelo verificador e pelos testes de conteúdo`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md`

Levar, **substituindo** a descrição do conteúdo ("oito serviços, uma URL por categoria"): o piloto SP (estado e cidade),
as áreas cobertas, que a lista é **aprovada pelo usuário** antes de entrar e que o conteúdo exige verificação por máquina;
os domínios de allowlist acrescentados, se houver; o limite declarado (apenas SP; outras cidades e estados ficam sem fonte).

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only. -->
