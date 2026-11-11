---
tipo: "plan"
familia: "03"
item: "R03.14"
titulo: "Importar a planilha da base enriquecida do usuário para o catálogo, com script reprodutível e allowlist ampliada"
dominio: "Automação"
status: "🟡 Em execução"
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
  áreas que caíram no padrão, e os **pares** de registro importado × registro do catálogo atual com o mesmo link normalizado ou o mesmo
  host e primeiro trecho do caminho. Não remove nem funde nada.
- **Verificação do conjunto:** o JSON gerado passa em `scripts/verify_catalog.py --offline` sem erro; online, o verificador lista os links
  mortos ou bloqueados e o executor **entrega essa lista** (sem apagar registro: quem não passa simplesmente não responde).
- **Qualidade da recuperação:** com a base importada, o executor mede o `finder_metrics` (96 pedidos) antes e depois e reporta; a medição
  **não pode piorar** (a acurácia da recuperação nos 96 pedidos igual ou maior que a de antes). Se piorar, o executor **para e reporta** os
  pedidos que mudaram, sem alterar as palavras-chave (elas são do usuário).

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
   links mortos ou bloqueados, por `id`); `finder_metrics` antes e depois, no mesmo conjunto de 96 pedidos.
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
- [ ] O executor entregou o relatório do script, a lista dos links mortos ou bloqueados (online) e o `finder_metrics` antes e depois, sem piora.
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
