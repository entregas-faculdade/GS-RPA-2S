# Fontes públicas (piloto São Paulo) — lista para aprovação

**Estado: lista aprovada pelo usuário em 2026-11-10** (todas as linhas `[x]`; as quatro da prefeitura com HTTP 403 ficam `[?]`).

Documento de trabalho: **não é o catálogo** (`data/catalog.json`). Ele reúne a lista que você enviou, o que o
revisor acrescentou e o resultado da verificação automática. Nada daqui entra no catálogo sem a sua marca. A lista
aprovada já está carregada no catálogo (`data/catalog.d/sp_expanded.json`); as quatro fontes da Prefeitura (M04 a M07)
seguem `candidate` no catálogo e não respondem ao cidadão (ver a nota da seção 3).

- **Verificação:** feita em 2026-11-10 com o `check_link` do projeto (HEAD, depois GET; cliente sem disfarce de
  navegador). `✓` = respondeu 200–399; `✗` = falhou (motivo ao lado). Telefone `confirmado` = o número aparece no texto
  da página; `não confirmado` = a página abriu mas não mostra o número (pode estar em outra página ou carregar por script).
- **Origem:** `usuário` = veio da sua lista; `revisor` = sugestão do revisor, cujo link foi verificado.
- **Nenhum link foi deduzido:** vieram da sua lista, de páginas oficiais que o revisor abriu ou de teste direto. Várias
  URLs que o revisor tentou deduzir (CTPS digital, MEI, segunda via de certidão, pontos da CNH) deram 404 e **não** estão aqui.

## Como responder
Em cada linha, na coluna **Decisão**: `[x]` aprovada, `[-]` cortada, `[?]` pendente de decisão sua. Acrescente linhas no fim de
cada seção para fontes novas (órgão, link, telefone). Se um telefone ou link não estiver certo, escreva a correção na
coluna **Notas**.

---

## 1. Federal

| ID | Fonte | O que é | Link(s) | Telefone | Verificação | Origem | Decisão | Notas |
|---|---|---|---|---|---|---|---|---|
| F01 | Portal gov.br | portal geral dos serviços federais | `https://www.gov.br/pt-br` | — | link ✓ | usuário | [x] | O 135 que veio na lista é do INSS, não do portal |
| F02 | Ministério da Saúde | SUS, cadastros nacionais, campanhas | `https://www.gov.br/saude/pt-br`; `https://www.gov.br/saude/pt-br/sus` | 136 | links ✓; 136 **confirmado** | usuário | [x] | |
| F03 | Meu SUS Digital | histórico de saúde e carteira de vacinação | `https://www.gov.br/saude/pt-br/composicao/seidigi/meususdigital`; `https://meususdigital.saude.gov.br` | — | links ✓ | revisor | [x] | |
| F04 | Farmácia Popular | medicamentos gratuitos ou com desconto | `https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular` | — | link ✓ | revisor | [x] | |
| F05 | Vacinação | calendário e dúvidas | `https://www.gov.br/saude/pt-br/vacinacao`; `https://www.gov.br/saude/pt-br/vacinacao/calendario`; `https://www.gov.br/saude/pt-br/vacinacao/faq` | — | links ✓ | revisor | [x] | |
| F06 | Ouvidoria-Geral do SUS | reclamações e sugestões sobre o SUS | `https://www.gov.br/saude/pt-br/canais-de-atendimento/ouvsus` | 136 | link ✓; 136 não testado nesta página | revisor | [x] | |
| F07 | ANVISA | medicamentos, alimentos, cosméticos | `https://www.gov.br/anvisa/pt-br` | 0800 642 9782 | link ✓; telefone **não confirmado** | usuário | [x] | Aprovar o telefone mesmo sem confirmação? |
| F08 | INEP | exames nacionais (ENEM) | `https://www.gov.br/inep/pt-br` | 0800 61 61 61 | link ✓; telefone **não confirmado** | usuário | [x] | |
| F09 | MEC | educação, programas de acesso e bolsas | `https://www.gov.br/mec/pt-br` | 0800 61 61 61 | **✗ erro de conexão** (2 rodadas) | usuário | [x] | Fica `candidate` até o link responder |
| F10 | ENEM | página do exame | `https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem` | — | link ✓ | revisor | [x] | |
| F11 | SISU, ProUni e FIES | acesso ao ensino superior e financiamento | `https://acessounico.mec.gov.br/sisu`; `https://acessounico.mec.gov.br/prouni`; `https://acessounico.mec.gov.br/fies` | — | 3 links ✓ | revisor | [x] | |
| F12 | Pé-de-Meia | bolsa para estudantes do ensino médio | `https://www.gov.br/mec/pt-br/pe-de-meia` | — | **✗ erro de conexão** | usuário | [x] | Fica `candidate` até responder |
| F13 | Senatran | trânsito nacional: CNH, CDT, Renainf | `https://www.gov.br/transportes/pt-br/assuntos/senatran`; `https://www.gov.br/transportes/pt-br/cnh-do-brasil`; `https://www.gov.br/transportes/pt-br/assuntos/transito/senatran/veiculos` | — | 3 links ✓ | usuário (+ revisor) | [x] | |
| F14 | Receita Federal | CPF, CNPJ, imposto de renda, certidões | `https://www.gov.br/receitafederal/pt-br`; `https://www.gov.br/receitafederal/pt-br/assuntos/meu-cpf`; `https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda` | — | 3 links ✓ | usuário (+ revisor) | [x] | |
| F15 | Certidão negativa de débitos | emissão pelo gov.br | `https://www.gov.br/pt-br/servicos/emitir-certidao-negativa-de-debitos` | — | link ✓ | revisor | [x] | |
| F16 | Trabalho e Emprego | CTPS digital, seguro-desemprego, abono | `https://www.gov.br/trabalho-e-emprego/pt-br` | — | link ✓ | usuário | [x] | |
| F17 | Meu INSS | aposentadoria e benefícios | `https://meu.inss.gov.br` | 135 | link ✓; 135 **confirmado** em `gov.br/inss` (já no catálogo) | revisor | [x] | |
| F18 | Bolsa Família e Cadastro Único | benefícios sociais | `https://www.gov.br/pt-br/servicos/receber-o-bolsa-familia`; `https://www.gov.br/pt-br/servicos/consultar-dados-do-cadastro-unico-cadunico` | — | 2 links ✓ | revisor | [x] | |
| F19 | MEI | emissão do DAS do MEI | `https://www.gov.br/pt-br/servicos/emitir-das-para-pagamento-de-tributos-do-mei` | — | link ✓ | revisor | [x] | Cobre só o pagamento; abertura de MEI não achada |

## 2. Estadual — Estado de São Paulo

| ID | Fonte | O que é | Link(s) | Telefone | Verificação | Origem | Decisão | Notas |
|---|---|---|---|---|---|---|---|---|
| E01 | Portal de serviços do Estado de SP | serviços estaduais unificados | `https://servicos.sp.gov.br`; `https://www.gov.br/pt-br/servicos-estaduais` | — | 2 links ✓ | usuário (+ revisor) | [x] | |
| E02 | Portal do Governo de SP | institucional | `https://www.sp.gov.br` | — | link ✓ | revisor | [x] | |
| E03 | Poupatempo | documentos pessoais (RG, antecedentes etc.) | `https://www.poupatempo.sp.gov.br`; `https://www.poupatempo.sp.gov.br/servicos`; `https://www.poupatempo.sp.gov.br/orgaos/` | — | 3 links ✓ | usuário (+ revisor) | [x] | |
| E04 | DETRAN-SP | veículos, habilitação, multas | `https://www.detran.sp.gov.br`; `https://www.detran.sp.gov.br/wps/portal/portaldetran/cidadao/veiculos`; `https://www.detran.sp.gov.br/wps/portal/portaldetran/cidadao/habilitacao` | — | 3 links ✓ | usuário (+ revisor) | [x] | |
| E05 | SEFAZ-SP e IPVA | IPVA, notas fiscais paulistas | `https://portal.fazenda.sp.gov.br`; `https://portal.fazenda.sp.gov.br/servicos/ipva`; `https://www.ipva.fazenda.sp.gov.br` | — | 3 links ✓ | usuário (+ revisor) | [x] | |
| E06 | Secretaria de Estado da Saúde | hospitais estaduais, diretrizes | `https://www.saude.sp.gov.br` | — | link ✓ | usuário | [x] | |
| E07 | Secretaria da Educação (SEDUC-SP) | rede estadual e matrícula | `https://www.educacao.sp.gov.br`; `https://www.educacao.sp.gov.br/matricula` | — | 2 links ✓ | usuário (+ revisor) | [x] | |
| E08 | JUCESP | registro de empresas | `https://www.jucesponline.sp.gov.br` | — | link ✓ | revisor | [x] | Relevante para abrir empresa; não é o alvará municipal |

## 3. Municipal — cidade de São Paulo

| ID | Fonte | O que é | Link(s) | Telefone | Verificação | Origem | Decisão | Notas |
|---|---|---|---|---|---|---|---|---|
| M01 | SP156 | zeladoria (buraco, poda, iluminação) e serviços da cidade | `https://sp156.prefeitura.sp.gov.br`; `https://sp156.prefeitura.sp.gov.br/portal/servicos`; `https://sp156.prefeitura.sp.gov.br/portal/perguntas-frequentes` | 156 | 3 links ✓; 156 **confirmado** | usuário (+ revisor) | [x] | |
| M02 | Secretaria Municipal de Educação (SME) | matrícula e vaga em creche | `https://educacao.sme.prefeitura.sp.gov.br` | 156 | link ✓ | revisor | [x] | |
| M03 | Nota Fiscal Paulistana (NF-e) | notas fiscais municipais | `https://nfe.prefeitura.sp.gov.br` | — | link ✓ | revisor | [x] | |
| M04 | Portal da Prefeitura | institucional | `https://www.prefeitura.sp.gov.br` | — | **✗ HTTP 403** | usuário | [?] | Bloqueio ao cliente automatizado |
| M05 | Secretaria Municipal da Fazenda | IPTU, alvará, taxas | `https://www.prefeitura.sp.gov.br/cidade/secretarias/fazenda` | 156 | **✗ HTTP 403** | usuário | [?] | |
| M06 | Secretaria Municipal da Saúde | UBS, AMA, vacinação | `https://www.prefeitura.sp.gov.br/cidade/secretarias/saude` | 156 | **✗ HTTP 403** | usuário | [?] | |
| M07 | Secretaria Municipal de Educação (página da secretaria) | matrícula | `https://www.prefeitura.sp.gov.br/cidade/secretarias/educacao` | 156 | **✗ HTTP 403** | usuário | [?] | M02 cobre o mesmo assunto em outro endereço |

> **Prefeitura (M04 a M07):** em 2026-11-10, `www.prefeitura.sp.gov.br` recusou (HTTP 403) o cliente automatizado, e as
> quatro linhas ficaram `candidate`. O verificador agora se identifica com o User-Agent descritivo do projeto
> (`link_check.user_agent` em `config/settings.json`); em 2026-11-12, `check_link` com esse identificador devolveu **HTTP
> 200** nas quatro páginas. Mesmo assim, o catálogo ainda as guarda como `candidate`, e só uma decisão sua as promove a
> `approved`. Enquanto isso, essas quatro linhas **não respondem ao cidadão**, e "alvará" e "IPTU municipal" seguem o
> caminho geral da seção 5.

## 4. Emergência e direitos (transversais)

Canais de telefone usados também quando o pedido é urgente. Um telefone sem página que o cite só pode ser `approved` por
decisão sua, pois o verificador não consegue confirmá-lo.

| ID | Canal | Telefone | Página para conferir | Verificação | Origem | Decisão | Notas |
|---|---|---|---|---|---|---|---|
| S01 | Polícia Militar | 190 | `https://www.policiamilitar.sp.gov.br` | link ✓; número não testado | usuário | [x] | |
| S02 | Corpo de Bombeiros | 193 | `https://www.corpodebombeiros.sp.gov.br` | **✗ erro de SSL** | usuário | [x] | Sem página verificável hoje |
| S03 | SAMU | 192 | `https://www.gov.br/saude/pt-br/composicao/saes/samu-192` | link ✓; número não testado | usuário | [x] | |
| S04 | Defesa Civil | 199 | `https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil`; `https://www.defesacivil.sp.gov.br` | 2 links ✓; 199 **não confirmado** | usuário (+ revisor) | [x] | |
| S05 | Disque Direitos Humanos | 100 | `https://www.gov.br/mdh/pt-br` | **✗ HTTP 403** | usuário | [x] | |
| S06 | Central de Atendimento à Mulher | 180 | `https://www.gov.br/mulheres/pt-br/ligue180` | link ✓; 180 **confirmado** | usuário (+ revisor) | [x] | |

## 5. Lacunas e o caminho oficial que o sistema informa

Assuntos sem fonte própria verificada. Decisão do usuário: **se houver caminho pelos links oficiais, o sistema o informa**,
dizendo ao cidadão que é o caminho geral e não o serviço específico. O caminho usa só fontes já listadas acima.

| Assunto | Caminho oficial informado | Fontes usadas | Decisão |
|---|---|---|---|
| Alvará de funcionamento e IPTU municipal | ligar para o **156** ou usar o SP156 (atende os serviços da cidade); a Fazenda municipal (M05) assume quando o link puder ser verificado | M01 | [x] |
| Abrir MEI ou empresa | pagamento do MEI no gov.br; registro de empresas na JUCESP | F19, E08 | [x] |
| Título de eleitor | buscar "título de eleitor" no catálogo de serviços do gov.br (caminho que o catálogo atual já usa) | F01 | [x] |
| Certidão de nascimento e segunda via | buscar "certidão" no catálogo de serviços do gov.br; a segunda via é pedida ao cartório | F01 | [x] |
| Assistência social (CRAS) | Cadastro Único e Bolsa Família no gov.br; atendimento municipal pelo **156** | F18, M01 | [x] |
| Antecedentes criminais e segunda via do RG (SP) | Poupatempo | E03 | [x] |
| Bombeiros | telefone **193** (sem página verificável hoje) | S02 | [x] |

## 6. Decisões do usuário (2026-11-10)
1. **Prefeitura (M04 a M07):** decisão **pendente**; ficam `candidate` até lá (o bloqueio HTTP 403 não se repetiu com o
   identificador do projeto: nota da seção 3).
2. **Telefones:** só números **oficiais**. Valem os confirmados numa página oficial da própria fonte e os códigos oficiais
   de emergência e atendimento (190, 192, 193, 199, 100, 180, 136 e 156). O restante só entra se o executor o achar e
   confirmar na página de contato do órgão; senão fica de fora.
3. **Propostas do revisor:** aprovadas (todas as linhas `[x]`).
4. **Lacunas:** informar o caminho oficial, conforme a seção 5.

## 7. Validação manual (páginas que o robô não consegue abrir)

O usuário valida estas páginas **à mão**, num navegador. Para cada uma: abra o link, confira que é do órgão certo e que o
conteúdo corresponde ao assunto, e marque `[x]` (e escreva a data de hoje em **Data**) ou `[-]` (não aprovar). Link que
você aprovar aqui e que o robô continuar sem conseguir abrir (HTTP 403) será aceito **por atestado manual, com validade de
180 dias**. Link com erro de conexão ou de SSL, ou 404, **não** pode ser aceito por atestado.

| ID | Página | O que conferir | Erro do robô | Validada? | Data |
|---|---|---|---|---|---|
| M04 | `https://www.prefeitura.sp.gov.br` | portal oficial da Prefeitura de São Paulo | HTTP 403 | [ ] | |
| M05 | `https://www.prefeitura.sp.gov.br/cidade/secretarias/fazenda` | Secretaria Municipal da Fazenda: IPTU, alvará, taxas | HTTP 403 | [ ] | |
| M06 | `https://www.prefeitura.sp.gov.br/cidade/secretarias/saude` | Secretaria Municipal da Saúde: UBS, AMA, vacinação | HTTP 403 | [ ] | |
| M07 | `https://www.prefeitura.sp.gov.br/cidade/secretarias/educacao` | Secretaria Municipal de Educação | HTTP 403 | [ ] | |
| S05 | `https://www.gov.br/mdh/pt-br` | Ministério dos Direitos Humanos (Disque 100) | HTTP 403 | [ ] | |
| F09 | `https://www.gov.br/mec/pt-br` | Ministério da Educação | erro de conexão (não aceitável por atestado) | [ ] | |
| F12 | `https://www.gov.br/mec/pt-br/pe-de-meia` | programa Pé-de-Meia | erro de conexão (não aceitável por atestado) | [ ] | |
| S02 | `https://www.corpodebombeiros.sp.gov.br` | Corpo de Bombeiros de SP | erro de SSL (não aceitável por atestado) | [ ] | |

As três últimas linhas servem só para você conferir **se a página existe e é a certa**; se o robô continuar sem abri-las
depois do novo identificador, elas ficam `candidate` (o canal pode ficar só com o telefone, conforme as regras do catálogo).
