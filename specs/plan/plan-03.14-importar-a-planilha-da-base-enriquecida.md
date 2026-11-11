---
tipo: "plan"
familia: "03"
item: "R03.14"
titulo: "Importar a planilha da base enriquecida do usuário para o catálogo, com script reprodutível e allowlist ampliada"
dominio: "Automação"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[03.01-catalogo-e-allowlist]]", "[[03.03-localizador-de-servicos]]", "[[007-llm-redige-a-resposta-com-rag-do-catalogo]]"]
depende_de: "—"
destino_sintese: "specs/03.01-catalogo-e-allowlist.md"
---

# 1. Objetivo
Transformar a planilha que o usuário entregou, `docs/catalogo_servicos_publicos_expandido_rpa.xlsx` (72 serviços de São Paulo e federais,
com link da página específica e palavras-chave), em registros do catálogo em `data/catalog.d/sp_expanded.json`, por um **script
reprodutível** (a planilha é a fonte; o JSON é gerado), e ampliar a allowlist para os 4 domínios da planilha que não são
`gov.br`.

# 2. Contexto
A 03.12 criou a capacidade de ler `data/catalog.d/*.json`. O usuário trouxe a base em planilha, não em JSON. Ela tem 7 colunas:
`ID`, `Esfera / Órgão`, `Macro-Categoria`, `Finalidade / Descrição do Serviço`, `URL Oficial`, `Palavras-Chave / Intents (NLP)`,
`Tipo de Interação / Notas RPA`. **Não traz** texto da página (`content`), telefone nem instruções ao cidadão: melhora o **achado** do
serviço certo e o **link específico** (por exemplo IPTU e parcelamento da Prefeitura), não a profundidade do texto.

Fatos medidos pelo revisor na planilha (o executor reconfirma):
- 72 linhas: 27 municipais (`M01`–`M27`), 21 estaduais (`S01`–`S21`), 24 federais (`F01`–`F24`); 11 linhas têm o **mesmo link** de um registro do catálogo atual (`M01`, `M03`, `M12`, `M19`, `M21`, `S01`, `S02`, `S07`, `S13`,
  `F08`, `F11`); `M19` e `M21` repetem o mesmo link entre si (`sp156.prefeitura.sp.gov.br`), o que é legítimo (serviços diferentes na mesma plataforma).
- 67 dos 72 hosts já cabem na allowlist `gov.br` (inclui `*.sp.gov.br`). Fora dela: `cetsp.com.br` (M14), `sptrans.com.br` (M15, M16),
  `agenciavirtual.sabesp.com.br` (S17), `desenvolvesp.com.br` (S21). **Decisão do usuário:** todos os links da planilha são de serviços públicos confiáveis, então os quatro
  domínios entram na allowlist (a lista de sites confiáveis passa a ser ampliada).
- A planilha foi salva com `sharedStrings.xml` na versão atual e usava `inlineStr` na anterior; o leitor trata os dois formatos. **Sem dependência nova**: leitura só com a
  biblioteca padrão (`zipfile` e `xml.etree`), porque `openpyxl` não está no ambiente.
- Os três erros de digitação das palavras-chave (F02, F10, M26) já foram corrigidos pelo usuário na planilha; o script não "conserta" texto.
- Vários links são páginas profundas que o usuário trouxe sem eu poder abri-las (por exemplo `…/fazenda/parcelamento`,
  `…/licenciamento/viabilidade`, `…/saude/profissionais/ubs`, `sp156…?servico=343`); parte pode estar fora do ar ou bloqueada por
  Cloudflare. O verificador de links diz quais; **só respondem** os que passam, como em todo o catálogo.
- Muitos serviços já existem no catálogo atual com outro `id` (por exemplo IPVA, Poupatempo, Detran, SP156, Meu INSS, ENEM/SISU, Ligue 180,
  Disque 100, bombeiros). Esses pares **convivem** (ids diferentes); o relatório do script os lista e o usuário decide depois.

## 2.1 Contrato (decisão desta plan)
- **Script:** `scripts/import_catalog_xlsx.py` (CLI fino) sobre `src/triage/automation/catalog_import.py`. Entrada: o `.xlsx` (padrão
  `docs/catalogo_servicos_publicos_expandido_rpa.xlsx`) e a saída (padrão `data/catalog.d/sp_expanded.json`), ambos parâmetros. Saída
  **determinística** (ordem da planilha, JSON com `indent=2` e `ensure_ascii=False`): rodar duas vezes gera arquivos idênticos.
- **Mapeamento por linha** (as tabelas vão em `data/catalog_import.json`, versionado, nunca no código):
  - `id` = `xl_` + `ID` em minúsculo (`xl_m02`); linha sem `ID`, sem URL ou com `ID` repetido é ignorada **com log** (e contada no relatório).
  - `display_name` = `Finalidade / Descrição do Serviço`; `agency` = `Esfera / Órgão`.
  - `scope` e `coverage` pelo prefixo do `ID`: `M` → `municipal`, "Município de São Paulo"; `S` → `state`, "Estado de São Paulo"; `F` → `federal`, "Brasil".
  - `area` por tabela de `Macro-Categoria` (§5.3 dá a tabela inicial); categoria sem entrada na tabela cai em `city`, com aviso no relatório.
  - `kind` = `portal` quando a finalidade começa com "Portal" ou é a raiz do site do órgão (`M01`, `F01`); os demais `service`.
  - `keywords` = `Palavras-Chave / Intents (NLP)` separado por vírgula, aparado, sem vazio e sem repetição.
  - `links` = `[{label: display_name, url}]` (um link por linha); `phones` = `[]`; `category` ausente; sem `content`.
  - `instructions` = modelo único, em português, que **não inventa fato**: diz o órgão e a finalidade e manda usar o link oficial
    (por exemplo "{agency}: {finalidade}. Acesse a página oficial para ver como fazer."). A coluna de notas **não** vira instrução nem
    `content` (traz jargão de RPA, como "Playwright com User-Agent rotativo"); vai só em `source_note`, junto da origem da linha.
  - `verified_on` = a data da importação (parâmetro, padrão a data de hoje em UTC); `status` = `approved` (base trazida pelo usuário, regra da
    03.12), **exceto** quando o host do link não está na allowlist: então `candidate`, com a razão no `source_note`.
- **Allowlist:** `data/allowed_domains.json` ganha `cetsp.com.br`, `sptrans.com.br`, `sabesp.com.br` e `desenvolvesp.com.br` (decisão do usuário: todos os
  links da planilha são de serviços públicos confiáveis), cada um com a razão (órgão e esfera). Nenhum outro domínio entra além dos da planilha.
- **Relatório do script** (saída padrão, sem dado pessoal): linhas lidas, geradas, ignoradas (com motivo), `candidate` (com motivo),
  áreas que caíram no padrão, e os **pares** de registro importado × registro do catálogo atual com o **mesmo link normalizado** (sem `www.` e sem
  barra final; os pares por host ou seção ficam fora, por ruído). Não remove nem funde nada.
- **Verificação do conjunto:** o JSON gerado passa em `scripts/verify_catalog.py --offline` sem erro; online, o verificador lista os links
  mortos ou bloqueados e o executor **entrega essa lista** (sem apagar registro: quem não passa simplesmente não responde).
- **Qualidade da recuperação (critério decidido pelo revisor em 2026-11-11, após a primeira rodada):** o localizador determinístico
  (`find`, com limiar e folga) passa a ter mais entradas parecidas disputando a folga, e o conjunto rotulado espera só os ids antigos, então
  cobertura e acerto dele **caem por construção** (46,9% → 25,0% de cobertura medidos). O que protege o fluxo principal, em que o LLM
  redige sobre as candidatas, é a **revocação das candidatas**: `hit@5` = entre os pedidos rotulados com fonte (60 dos 96, `expected_id`
  diferente de `none`), quantos têm o `expected_id` entre as 5 primeiras de `top_candidates(texto, 5)` (5 = `max_candidates` do agente). Medido pelo
  revisor: 59/60 antes e 58/60 depois. **Critério:** `hit@5` depois **não pode ser menor que 58/60**. As métricas do `find` (cobertura, acerto,
  falso positivo) continuam sendo medidas e **reportadas** antes e depois, sem barreira, e a queda de cobertura é registrada como
  limite conhecido do modo sem LLM. Não alterar palavras-chave, limiares nem o conjunto rotulado.

# 3. Escopo
## 3.1 Dentro
- `src/triage/automation/catalog_import.py` (novo) e `scripts/import_catalog_xlsx.py` (novo)
- `data/catalog_import.json` (novo) — tabelas de mapeamento e o modelo da instrução
- `data/catalog.d/sp_expanded.json` (gerado pelo script, versionado) e `data/allowed_domains.json` (4 sufixos novos)
- `docs/guia-da-base-enriquecida.md` — acrescentar a seção "Importar da planilha" (comando, colunas, o que o script faz e não faz)
- `README.md` — uma linha sobre a base importada
- `tests/automation/` — testes do importador e da allowlist
- `tests/evaluation/test_finder_metrics.py`, `tests/pipeline/conftest.py`, `tests/interface/conftest.py`, `tests/interface/test_service_tiers.py`, `tests/automation/test_resolver.py` — onde chamam `load_catalog()` sem `extra_dir=None` e fixam contagens ou áreas do catálogo piloto, passar a ler só o catálogo versionado (a base importada não pode alterar o que eles afirmam sobre o piloto)

## 3.2 Fora
- Editar a planilha, o `data/catalog.json`, as palavras-chave ou o conteúdo (são do usuário); `content` de qualquer registro.
- Fundir ou remover registros duplicados do catálogo atual; mudar `FINDER_MIN_SCORE`, `FINDER_MARGIN` ou o conjunto rotulado.
- Navegação na internet para preencher conteúdo; dependência nova (`openpyxl`, `pandas`); `triage.pipeline`, `triage.interface` e o agente.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| Spec fixa | [[03.01-catalogo-e-allowlist]] | esquema do registro, allowlist, regra de entrada da base do usuário (já com o que a 03.12 sintetizou) |
| Spec fixa | [[03.03-localizador-de-servicos]] | a recuperação e as métricas que não podem piorar |
| ADR | [[007-llm-redige-a-resposta-com-rag-do-catalogo]] | só link aprovado e verificado chega ao cidadão |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` · `test-unitario` | zero hardcoded, saída determinística, testes sem rede |
| Código | `src/triage/automation/{catalog,allowlist,catalog_audit}.py`, `scripts/verify_catalog.py`, `data/allowed_domains.json` | formato do registro e da allowlist |
| Dado | `docs/catalogo_servicos_publicos_expandido_rpa.xlsx` | a fonte (somente leitura) |

# 5. Instruções de execução
1. [dirigido] **Leitor de planilha.** Função que lê a primeira aba do `.xlsx` com `zipfile` e `xml.etree.ElementTree`, aceitando `inlineStr` e
   `sharedStrings`, e devolve as linhas como dicionários pelo cabeçalho (acentos e espaços do cabeçalho tolerados por comparação normalizada).
   Arquivo ausente, não-zip ou sem aba levanta erro claro. Funções pequenas.
2. [dirigido] **Conversão.** Aplicar o mapeamento do §2.1 sobre `data/catalog_import.json`; cada registro gerado tem que passar na validação de
   `catalog.py` (é a mesma validação do carregamento). Linha inválida é ignorada com log e entra no relatório.
3. [dirigido] **Tabela de áreas.** Em `data/catalog_import.json`: Tributos, Tributos Estaduais, Tributos Federais, Finanças, Financiamento → `tax`;
   Saúde → `health`; Educação → `education`; Assistência Social, Benefícios Sociais, Habitação, Direitos Humanos, Trabalho, Previdência → `social`;
   Trânsito, Transporte, Identificação e Trânsito → `vehicles`; Identificação, Documentos, Justiça, Empresas → `documents`; Segurança,
   Segurança e Vistorias → `safety`; o resto (Institucional, Licenciamento e Obras, Urbanismo, Zeladoria Urbana, Cultura, Esportes,
   Empreendedorismo, Ouvidoria, Consumidor, Saneamento, Meio Ambiente) → `city`. O executor confere cada macro-categoria da planilha contra a tabela.
4. [dirigido] **Allowlist e `status`.** Acrescentar os 4 sufixos de §2.1 em `data/allowed_domains.json`; o importador marca `candidate` o registro cujo
   host não passa na allowlist (lê a mesma `allowlist.py`).
5. [dirigido] **Relatório e CLI.** `scripts/import_catalog_xlsx.py` com `--xlsx`, `--out`, `--date`; imprime o relatório do §2.1 e sai `0`; erro de
   leitura sai `1`. Rodar uma vez para gerar `data/catalog.d/sp_expanded.json`; rodar de novo e provar que o arquivo não muda.
6. [dirigido] **Medições.** `python scripts/verify_catalog.py --offline` (sem erro) e, com rede, `python scripts/verify_catalog.py` (entregar a lista dos
   links mortos ou bloqueados, por `id`); `finder_metrics` antes e depois, no mesmo conjunto de 96 pedidos, e o `hit@5` do §2.1 (medido por um script no scratchpad, não versionado).
7. [dirigido] **Guia e README.** A seção do guia e a linha do README (§3.1), em português, sem URL inventada.
8. [dirigido] **Testes** (sem rede; a planilha de teste é criada em pasta temporária por `zipfile`, nos dois formatos de texto): mapeamento de um
   registro de cada esfera; `area` pela tabela e o padrão `city`; `kind` portal; palavras-chave aparadas e sem repetição; linha sem `ID` ou sem URL
   ignorada; host fora da allowlist vira `candidate`; saída determinística; o `sp_expanded.json` do repositório carrega por `load_catalog()` sem
   registro rejeitado e com os 72 ids; os 4 sufixos novos na allowlist.
9. [dirigido] **Testes que fixam o piloto.** Nos cinco arquivos de teste do §3.1 que chamam `load_catalog()` sem `extra_dir=None`, passar `extra_dir=None` quando a asserção depender de contagem ou área do catálogo piloto; os demais ficam como estão.
10. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] `data/catalog.d/sp_expanded.json` existe, é gerado pelo script e tem 72 registros (menos os ignorados, se houver, listados no relatório), todos válidos em `load_catalog()`.
- [ ] Rodar o script duas vezes gera arquivos idênticos; o script não usa dependência nova.
- [ ] A coluna de notas da planilha não aparece em `instructions` nem em `content`; nenhum registro tem `content` nem telefone inventado.
- [ ] A allowlist tem os 4 sufixos novos, cada um com razão; nenhum registro da planilha fica `candidate` por domínio.
- [ ] O executor entregou o relatório do script, a lista dos links mortos ou bloqueados (online) e o `finder_metrics` antes e depois (reportado) e `hit@5` de pelo menos 58/60.
- [ ] A sondagem "Preciso negociar o IPTU em atraso" e "me passe o link correto para parcelamento" mostra `xl_m02` e `xl_m05` entre os candidatos do localizador (o executor reporta a posição de cada um).
- [ ] Guia e README atualizados; nenhum teste usa rede; ambiente e worktree limpos; `ruff` e validador sem violação nova.
- [ ] O notebook de evidências continua executando sem erro.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — acrescenta 72 registros e 4 domínios ao catálogo consumido por resolver, localizador, RAG, verificador e notebook`.
- `git diff --stat` → só arquivos de §3.1 (a planilha continua intacta).
- `python -m pytest tests/automation tests/pipeline tests/interface tests/test_config.py -q` → verde.
- `python -m ruff check src/triage/automation scripts tests/automation` → sem erro novo; `validate.py` nos `.py` tocados → sem achado.
- Rodar o script sobre a planilha em pasta do scratchpad e comparar byte a byte com `data/catalog.d/sp_expanded.json`; rodar `verify_catalog.py --offline`.
- Sondagem no localizador (sem LLM): IPTU em atraso, link de parcelamento, multa de trânsito (CET), bilhete único (SPTrans), vistoria de bombeiros, seguro-desemprego
  — cada um traz o registro `xl_*` esperado entre os candidatos; um pedido de emergência continua sem passar pelo LLM.
- Conferir por amostra (8 linhas) a planilha contra o JSON gerado (nome, órgão, escopo, área, palavras-chave, link, `status`).
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` sem erro; comparar as métricas do localizador com as de antes.
- **Gate:** `nenhum — coberto por testes e sondagem`.

# 8. Destino da síntese
**Destino:** `specs/03.01-catalogo-e-allowlist.md`.

Escrever: a base trazida pelo usuário pode vir de planilha e é convertida por `scripts/import_catalog_xlsx.py` em `data/catalog.d/sp_expanded.json` (mapeamento,
`status` por allowlist, notas de RPA fora da resposta); a allowlist inclui `gov.br` e os 4 domínios acrescentados (CET, SPTrans, Sabesp, Desenvolve SP); registros
importados convivem com os do catálogo atual (ids diferentes) e o relatório lista os pares. Levar também o número de registros do catálogo (`00-contexto`), se citado.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Decisão do revisor — 2026-11-11 — execução retomada (critério de qualidade ajustado)

A primeira rodada parou, como a plan mandava, porque as métricas do `find` caíram (cobertura 46,9% → 25,0%, acerto entre respondidos
88,9% → 79,2%). O revisor reproduziu a medição num script no scratchpad, sem tocar no repositório: pular as 11 linhas de mesmo link, ou
ignorar entradas de mesmo link na folga, ou baixar a folga não devolve o resultado antigo (o melhor, pulando 22 equivalentes, chega a 36,5%),
porque o catálogo triplicou de tamanho e o conjunto rotulado só conhece os ids antigos; já o `hit@5` das candidatas que o LLM recebe
praticamente não muda (59/60 → 58/60). Decisão: manter as 72 linhas da planilha (é a base do usuário), trocar a barreira pelo `hit@5` e
reportar o `find` sem barreira (§2.1, "Qualidade da recuperação"); pares só por mesmo link (§2.1, relatório). Restante da plan inalterado:
terminar os passos 5 a 10 (testes, ajuste dos testes que fixam o piloto, guia, README, `verify_catalog.py` online, notebook, `ruff`).
O arquivo `data/catalog.d/sp_expanded.json` deve ser gerado de novo e ficar no worktree.

## Resumo da execução — 2026-11-11

**Resultado:** Bloqueado (a medição do `finder_metrics` piorou; a plan manda parar e reportar, §2.1 "Qualidade da recuperação").

**O que foi feito**
- `src/triage/automation/catalog_import.py` (novo): leitor de `.xlsx` só com `zipfile`/`xml.etree` (`sharedStrings` e `inlineStr`, células vazias por referência de coluna), conversão pelo mapeamento do §2.1, `find_pairs`, saída JSON determinística e relatório.
- `scripts/import_catalog_xlsx.py` (novo): CLI com `--xlsx`, `--out`, `--date` (e `--config`); sai `0`, ou `1` se a planilha não pôde ser lida.
- `data/catalog_import.json` (novo): colunas, esferas, tabela de áreas (a do §5.3), modelos de instrução e de `source_note`.
- `data/allowed_domains.json`: +4 sufixos (`cetsp.com.br`, `sptrans.com.br`, `sabesp.com.br`, `desenvolvesp.com.br`), cada um com razão.
- Gerei `data/catalog.d/sp_expanded.json` (72 registros) para medir e **removi o arquivo do worktree** depois da medição ruim, para o app não rodar degradado; regenera-se com `python scripts/import_catalog_xlsx.py --date 2026-11-11`.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/automation/catalog_import.py` | criado | leitor, conversão, pares, relatório |
| `scripts/import_catalog_xlsx.py` | criado | CLI fino |
| `data/catalog_import.json` | criado | tabelas de mapeamento |
| `data/allowed_domains.json` | alterado | 4 sufixos novos |

**Verificações executadas**
- `python scripts/import_catalog_xlsx.py --date 2026-11-11` → 72 lidas, 72 geradas, 0 ignoradas, 0 `candidate`, 0 áreas no padrão (as 33 macro-categorias da planilha estão na tabela), 158 pares.
- `python scripts/verify_catalog.py --offline` (com o JSON gerado) → 127 registros, sem erro.
- `finder_metrics`, 96 pedidos, limiares padrão (`finder.min_score` 0,25 e `finder.margin` 0,15), antes (55 entradas) → depois (127 entradas):

| Divisão | Cobertura antes → depois | Acerto entre respondidos antes → depois | Falso positivo antes → depois |
|---|---|---|---|
| todos (96) | 46,9% → 25,0% | 88,9% → **79,2%** | 11,1% → 5,6% |
| `train` (48) | 45,8% → 22,9% | 90,9% → 81,8% | 5,6% → 5,6% |
| `test` (48) | 47,9% → 27,1% | 87,0% → 76,9% | 16,7% → 5,6% |

- Pedidos que mudaram (id: esperado; antes → depois): 18 respondidos certo viraram `None` (F004 vaccination, F011 enem, F012 enem, F013/F014 pe_de_meia, F015/F016 higher_education_access, F017 seduc_sp, F019 sme_sp, F022 detran_sp, F025 driver_license, F027 sp156, F031/F032/F051 sefaz_sp_ipva, F043 cpf_registration, F048 women_helpline_180, F050 police_190); 3 certos viraram `xl_*` (F040 esperado gap_city_permit_property_tax → xl_m06; F044 labor_ministry → xl_f06; F045 labor_ministry → xl_f05); 2 pedidos `none` ganharam fonte (F072 passaporte → xl_f18; F075 previsão do tempo → xl_f10); 6 melhoraram (F055 errado → `None`; F080, F090, F095, F096 falso positivo → `None`).
- Sondagem (`top_candidates`, 1ª posição = 1): "Preciso negociar o IPTU em atraso" → `xl_m02` em 1º; "me passe o link correto para parcelamento" → `xl_m05` em 1º; multa de trânsito → `xl_m14` em 2º; bilhete único → `xl_m15` em 1º; vistoria de bombeiros → `xl_s06` em 1º; seguro-desemprego → `xl_f06` em 1º.
- `python -m pytest tests/automation -q` (sem o JSON gerado) → 326 passed.
- Não rodei `verify_catalog.py` online (lista de links mortos), os testes novos nem `ruff`/`validate.py` (ruff não está instalado no ambiente): parei na medição.

**Estado inicial do worktree:** limpo (`git status --short` vazio, branch `develop`).

**Ambiente após a verificação:** nada criado no repositório além dos arquivos acima; scripts de medição e cópia do JSON gerado ficaram só no scratchpad da sessão. Nenhum processo, servidor ou contêiner iniciado.

**Critérios de aceite**
- [ ] `sp_expanded.json` existe com 72 registros — gerado e válido (72/72 em `load_catalog`), mas removido do worktree após a medição ruim.
- [x] Duas execuções idênticas, sem dependência nova — evidência: saída JSON com `indent=2`, ordem da planilha e `
`; só `zipfile`/`xml.etree` (a comparação byte a byte não foi feita, pois parei na medição).
- [ ] Notas fora de `instructions`/`content`, sem `content` nem telefone — por construção em `catalog_import.py`; sem teste ainda (não escritos).
- [x] Allowlist com 4 sufixos; nenhum registro `candidate` — evidência: relatório (0 `candidate`).
- [ ] Relatório, links mortos online e `finder_metrics` **sem piora** — relatório e métricas entregues; **houve piora** e a lista online não foi gerada.
- [ ] Sondagem — `xl_m02` e `xl_m05` em 1º lugar cada (atendido), mas o critério geral depende da medição.
- [ ] Guia, README, testes, `ruff`/validador, notebook — não feitos (parada por piora).

**Decisões e suposições**
- Parei no ponto em que a plan manda: não mexi em palavras-chave, limiares nem no conjunto rotulado, e não escrevi testes, guia nem README.
- Causa provável (hipótese; não testei remédios): os pares convivem com ids diferentes e as palavras-chave são quase iguais, então a folga (`margin`) do melhor cai e o `find` devolve `None`; o conjunto rotulado também espera os ids antigos (F040, F044, F045 viraram `xl_*`).
- `kind` portal só pela regra "finalidade começa com Portal" (cobre M01 e F01); a "raiz do site" não é regra própria, pois outras raízes (M14, M15, S01) são serviços.
- Pares: implementei literalmente "mesmo link normalizado ou mesmo host e primeiro trecho do caminho" e o relatório ficou ruidoso (158 pares): hosts como `gov.br/pt-br/...` e `prefeitura.sp.gov.br/cidade/...` casam por seção com dezenas de registros.
- `verified_on` = 2026-11-11 (data da sessão), por `--date`; `source_note` leva as notas de RPA da planilha (nenhum código em `src` lê `source_note`; conferido por grep).
- Cabeçalhos e macro-categorias são comparados sem acento e sem diferença de caixa.

**Achados fora do escopo (não corrigidos)**
- A planilha lida pelo console do Windows aparece com acentos quebrados na saída do script (só no terminal; o arquivo é UTF-8).

**Pendências / riscos**
- Decisão do revisor: como evitar a piora (reclassificar o conjunto rotulado, aposentar duplicatas do catálogo atual, ou ignorar duplicatas de mesmo link na folga do localizador). Sem isso a base importada reduz a cobertura de 46,9% para 25%.
- Falta: testes (§5.8), ajuste dos 5 arquivos de teste (§5.9), guia e README, `verify_catalog.py` online, notebook, `ruff` (não instalado).

## Resumo da execução (retomada) — 2026-11-11

**Resultado:** Concluído com pendências (29 registros importados têm link morto ou bloqueado no verificador online; falha pré-existente em `tests/test_config.py`).

**O que foi feito**
- `catalog_import.py`: `find_pairs` passou a casar só o **mesmo link normalizado** (sem `www.` e sem barra final), como a decisão do revisor; `Pair` perdeu o campo `reason`. Relatório: 16 pares (eram 158).
- `data/catalog.d/sp_expanded.json` gerado de novo (`python scripts/import_catalog_xlsx.py --date 2026-11-11`): 72 lidas, 72 geradas, 0 ignoradas, 0 `candidate`, 0 áreas no padrão. Fica no worktree.
- `tests/automation/test_catalog_import.py` (novo, 21 testes, sem rede, planilhas criadas por `zipfile` em `tmp_path` nos dois formatos de texto): leitura com célula vazia, cabeçalho sem acento nem caixa, erros (ausente, não-zip, sem aba, sem coluna), um registro por esfera, tabela de áreas e padrão `city`, `kind` portal, palavras-chave, notas só no `source_note`, linhas ignoradas, `candidate`, determinismo, pares só por mesmo link, relatório, os 4 sufixos da allowlist e o JSON do repositório (72 ids, nada rejeitado, sem `content` nem telefone).
- Cinco arquivos que fixam o piloto passaram a ler `load_catalog(extra_dir=None)`: `tests/evaluation/test_finder_metrics.py:154`, `tests/pipeline/conftest.py:50`, `tests/interface/conftest.py:48`, `tests/interface/test_service_tiers.py:55`, `tests/automation/test_resolver.py:221-222`. Nenhum deles falhava antes da mudança (preventivo, como o §5.9 pede).
- `tests/automation/test_catalog.py`: o teste `test_versioned_extra_dir_has_no_json_so_it_never_becomes_a_real_source` afirmava a pasta `data/catalog.d` sem JSON, o que a plan torna falso; virou `test_versioned_extra_dir_has_only_the_imported_spreadsheet_base` (a pasta só tem `sp_expanded.json`).
- `docs/guia-da-base-enriquecida.md`: nova §8 "Importar da planilha" e a §5 cita os 4 domínios novos. `README.md`: uma frase sobre a base importada.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/automation/catalog_import.py` | criado (1ª rodada) e alterado | pares só por mesmo link |
| `scripts/import_catalog_xlsx.py` | criado (1ª rodada) | sem mudança nesta rodada |
| `data/catalog_import.json` | criado (1ª rodada) | sem mudança nesta rodada |
| `data/allowed_domains.json` | alterado (1ª rodada) | 4 sufixos |
| `data/catalog.d/sp_expanded.json` | criado | 72 registros gerados |
| `tests/automation/test_catalog_import.py` | criado | 21 testes |
| `tests/automation/test_catalog.py` | alterado | teste da pasta `catalog.d` |
| `tests/automation/test_resolver.py`, `tests/evaluation/test_finder_metrics.py`, `tests/interface/conftest.py`, `tests/interface/test_service_tiers.py`, `tests/pipeline/conftest.py` | alterados | `extra_dir=None` |
| `docs/guia-da-base-enriquecida.md`, `README.md` | alterados | seção e linha da base importada |
| `specs/plan/plan-03.14-...md` | alterado | este resumo |

**Verificações executadas**
- `python -m pytest tests/automation tests/pipeline tests/interface tests/evaluation tests/test_config.py -q` → 585 passed, 1 failed: `tests/test_config.py::test_shipped_config_equals_the_code_defaults` (`llm_enabled` é `True` no `config/settings.json`; vem do commit `9cc58c7`, que não toquei).
- Reprodutibilidade: duas execuções em sequência e uma em `--out` no scratchpad → `cmp` byte a byte idêntico ao `data/catalog.d/sp_expanded.json`.
- `python scripts/verify_catalog.py --offline` (1ª rodada, mesmo conjunto de registros) → 127 registros, sem erro.
- `python scripts/verify_catalog.py` (online) → 127 registros, **com erro**: 29 `xl_*` com "nenhum link vivo" (todos `approved`; só resolvem quando o link voltar): `xl_m04 xl_m05 xl_m07 xl_m08 xl_m10 xl_m11 xl_m20 xl_m24 xl_s04 xl_s05 xl_s06 xl_s09 xl_s10 xl_s14 xl_s18 xl_s21 xl_f02 xl_f03 xl_f04 xl_f05 xl_f06 xl_f09 xl_f10 xl_f14 xl_f15 xl_f16 xl_f17 xl_f21 xl_f24`. Causa por link: HTTP 404 (xl_m04, m05, m07, m08, m10, m11, m20, m24, s04, s09, s14, f03, f04, f05, f06, f09, f10, f16, f17, f21, f24), HTTP 403 (xl_s21 `desenvolvesp.com.br`, xl_f15 `prouni.mec.gov.br`), falha de DNS (xl_s05, xl_s10, xl_f02), erro de certificado (xl_s06, xl_s18) e timeout (xl_f14). Nenhum registro do catálogo anterior tem erro. Nenhum registro foi apagado.
- `finder_metrics` (96 pedidos, limiares padrão), antes (55 entradas) → depois (127): cobertura 46,9% → 25,0%; acerto entre respondidos 88,9% → 79,2%; falso positivo 11,1% → 5,6% (`train` 22,9% / 81,8% / 5,6%; `test` 27,1% / 76,9% / 5,6%). Reportado, sem barreira, como a decisão do revisor.
- **hit@5** (script no scratchpad, 60 pedidos rotulados com fonte, `top_candidates(texto, 5)`): antes 59/60 (perde F055 vaccination); depois **58/60** (perde F055 vaccination e F024 detran_sp). Critério ≥ 58/60: atendido.
- Sondagem (posição entre `top_candidates`): IPTU em atraso → `xl_m02` em 1º; parcelamento → `xl_m05` em 1º; multa de trânsito → `xl_m14` em 2º (`detran_sp` em 1º); bilhete único → `xl_m15` em 1º; vistoria de bombeiros → `xl_s06` em 1º; seguro-desemprego → `xl_f06` em 1º. **Atenção:** `xl_m05`, `xl_s06` e `xl_f06` têm link morto (404, certificado e 404): o localizador os acha, mas `resolve_entry` os descarta e o cidadão não os recebe enquanto o link não voltar. Não retestei o pedido de emergência (o fluxo não foi tocado).
- `python -m ruff check src/triage/automation scripts tests/automation` → 1 erro, pré-existente e fora do escopo: `src/triage/automation/allowlist.py:18` UP033 (`lru_cache(maxsize=None)`). Um I001 de import no meu teste foi corrigido com `--fix`. Não rodei `ruff format`.
- `validate.py` (padrao-python): `scripts/import_catalog_xlsx.py` sem achado; `catalog_import.py` e o teste só com `hardcoded` de confiança baixa nas URIs de namespace XML (`http://schemas.openxmlformats.org/...`), que identificam o formato e nunca são acessadas.
- `python -m jupyter nbconvert --to notebook --execute notebooks/evidence.ipynb --output-dir <scratchpad>` → 40 células, 0 erros na segunda execução (a primeira terminou com `zmq.error.ZMQError: timed out`, transitório do ambiente). Métricas do localizador no notebook, as de depois: 123 aprovadas; treino 22,9% / 81,8% / 5,6%; teste 27,1% / 76,9% / 5,6%.

**Estado inicial do worktree:** o da 1ª rodada (`git status --short`: `M data/allowed_domains.json`, `M` na plan e `??` nos três arquivos do importador); o worktree original estava limpo.

**Ambiente após a verificação:** nada criado no repositório além dos arquivos da tabela; o notebook e os scripts de medição escreveram só no scratchpad (`output/notebook-evidence` não existe). Nenhum processo, servidor ou contêiner deixado.

**Critérios de aceite**
- [x] `sp_expanded.json` existe, gerado pelo script, 72 registros válidos — evidência: `test_repository_sp_expanded_loads_with_the_72_ids_and_nothing_rejected` e relatório (0 ignoradas).
- [x] Duas execuções idênticas, sem dependência nova — evidência: `cmp` e testes de determinismo; só `zipfile` e `xml.etree`.
- [x] Notas fora de `instructions` e `content`, sem `content` nem telefone — evidência: `test_rpa_notes_stay_out_of_instructions_and_only_go_to_the_source_note` e o teste do JSON do repositório.
- [x] 4 sufixos com razão, nenhum `candidate` por domínio — evidência: `test_the_four_new_suffixes_are_in_the_allowlist_with_a_reason` e relatório.
- [x] Relatório, `finder_metrics` antes e depois e hit@5 ≥ 58/60 entregues — evidência acima; a lista de links mortos online foi entregue e é grande (29).
- [x] Sondagem: `xl_m02` e `xl_m05` em 1º — com a ressalva do link morto de `xl_m05`.
- [ ] `ruff` sem violação nova — sem violação nova minha; resta o UP033 pré-existente em `allowlist.py`. Falha pré-existente em `tests/test_config.py`.
- [x] Guia e README atualizados; nenhum teste usa rede.
- [x] Notebook executa sem erro (na segunda tentativa).

**Decisões e suposições**
- O teste de `test_catalog.py` foi reescrito porque a premissa dele ("a pasta não tem JSON") é negada pela própria plan; a plan não o listava no §3.1, mas ele está em `tests/automation/`.
- Os cinco arquivos do §5.9 receberam `extra_dir=None` mesmo sem falhar, porque todos afirmam sobre o catálogo piloto (categorias, áreas, ids do conjunto rotulado).
- `Pair` ficou sem `reason`, pois há um único motivo.
- Não alterei palavras-chave, limiares, conjunto rotulado nem a planilha.
- No resumo da 1ª rodada, o item "Duas execuções idênticas" saiu com uma quebra de linha no lugar do texto `\n` (erro meu ao gravar o bloco); ele permanece intacto por ser append-only.

**Achados fora do escopo (não corrigidos)**
- `tests/test_config.py::test_shipped_config_equals_the_code_defaults` falha por `llm.enabled: true` no `config/settings.json` (commit `9cc58c7`).
- `src/triage/automation/allowlist.py:18` — UP033 do ruff 0.17.4.
- 29 links da planilha que o verificador acusa; a correção é da planilha (do usuário): ver lista acima.

**Pendências / riscos**
- Com 29 dos 72 registros importados sem link vivo, o ganho real do achado (IPTU, parcelamento, seguro-desemprego, bombeiros) só existe quando esses links forem corrigidos na planilha e o importador rodado de novo.
- `verify_catalog.py` sai `1` por causa deles; o fluxo do robô não é afetado (link morto nunca chega ao cidadão).
- Não conferi por amostra as 8 linhas da planilha contra o JSON (§7, uso do revisor); os testes cobrem o mapeamento.

## Veredito — 2026-11-11 — 🟢 Aprovado

**Verificado pelo revisor (sem confiar no resumo):**
- `git status`/`diff --stat`: arquivos do §3.1 (importador, CLI, `data/catalog_import.json`, `sp_expanded.json`, allowlist, guia, README, testes) mais o ajuste de `test_catalog.py` (teste da pasta `catalog.d`, que a própria plan tornava falso; dentro de `tests/automation/`). `config/settings.json` não aparece como modificado.
- `pytest tests/automation tests/pipeline tests/interface tests/evaluation tests/test_config.py -q` → 585 passed, 1 failed: `test_shipped_config_equals_the_code_defaults` (`llm.enabled: true` do `config/settings.json` já commitado, fora do escopo).
- `ruff check src/triage/automation scripts tests/automation` → 1 erro, UP033 em `allowlist.py:18`, pré-existente. `validate.py`: CLI sem achado; `catalog_import.py` e o teste só com `hardcoded` de confiança baixa (URIs de namespace XML).
- Determinismo: rodei o importador no scratchpad e `cmp` com `data/catalog.d/sp_expanded.json` → idêntico (72 lidas, 72 geradas, 0 ignoradas, 0 `candidate`, 16 pares por mesmo link).
- `verify_catalog.py --offline` → 127 registros, sem erro. Online, repeti: 29 registros `xl_*` sem link vivo (conferido por contagem), nenhum do catálogo anterior.
- Amostra de 5 registros contra a planilha (escopo, área, tipo, palavras-chave, link, `instructions` em modelo, notas de RPA só no `source_note`); nenhum `content` nem telefone; todos `approved`.
- `hit@5` reproduzido pelo revisor antes da retomada (59/60 → 58/60); `nbconvert --execute notebooks/evidence.ipynb` → sem erro. Ambiente limpo (nada criado fora do escopo).

**Fora do escopo, para o backlog:** o fluxo com LLM toma as 5 primeiras candidatas e só depois descarta as de link morto (os mortos ocupam vagas); 29 links da planilha estão mortos ou bloqueados (404 em 21, 403 em 2, DNS em 3, certificado em 2, tempo esgotado em 1) e a correção é da planilha.
