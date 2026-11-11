# Guia da base enriquecida do catálogo

Este guia é para **quem monta a base**: páginas oficiais por tarefa, cada uma com o trecho que responde ao cidadão. O robô
carrega esses arquivos, **verifica** os links e usa o trecho (`content`) em duas etapas: para **achar** a fonte certa e para
o LLM **redigir** uma resposta mais completa. O LLM nunca navega na internet: ele só escreve sobre o que está aqui.

## 1. Onde colocar os arquivos

- Um ou mais arquivos `data/catalog.d/<nome>.json`, cada um com **uma lista** de registros (`[ {...}, {...} ]`).
- O robô lê primeiro `data/catalog.json` e depois cada `*.json` da pasta, **em ordem de nome** (`a.json` antes de `b.json`).
  Outros arquivos da pasta (como o `README.md`) são ignorados.
- Se o mesmo `id` aparecer duas vezes, **vale o primeiro** e o segundo é ignorado com aviso. Use sempre um `id` novo.
- Um arquivo com JSON quebrado é ignorado e registrado, sem derrubar os outros. O verificador (§6) aponta qual foi.
- Sugestão: um arquivo por tema ou órgão (`saude.json`, `veiculos.json`), para achar e revisar com facilidade.

## 2. Os campos de um registro

Todos são **obrigatórios**, exceto os marcados como opcionais. Texto nunca pode ficar vazio.

| Campo | O que escrever |
|---|---|
| `id` | nome único, em minúsculas e sem espaço (`popular_pharmacy_como_funciona`) |
| `category` | `null` na base enriquecida (as categorias do classificador já têm entrada em `data/catalog.json`) |
| `kind` | `service` (página específica de um serviço; exige ao menos um link), `portal` (portal geral de um órgão) ou `channel` (canal de atendimento, em geral telefone). `portal` e `channel` exigem um link **ou** um telefone |
| `scope` | `federal`, `state` ou `municipal` |
| `coverage` | onde vale, como o cidadão lê: `Brasil`, `Estado de São Paulo`, `Cidade de São Paulo` |
| `area` | uma de `health`, `education`, `vehicles`, `city`, `documents`, `social`, `tax`, `safety` |
| `display_name` | nome do serviço, como o órgão o chama |
| `agency` | órgão responsável |
| `instructions` | 1 ou 2 frases de orientação (o essencial; o detalhe vai em `content`) |
| `keywords` | lista de termos que o **cidadão diz** (veja §3) |
| `links` | lista de `{"label": "...", "url": "..."}` com a URL **exata** da página oficial. Opcional em cada link: `manual_check_on` (data `AAAA-MM-DD` em que uma pessoa abriu a página e atestou; só vale para link que responde HTTP 403 ao robô) |
| `phones` | lista de `{"label": "...", "number": "..."}`, como o cidadão disca (`156`, `0800 61 61 61`); pode ser `[]`. Só número confirmado em página oficial |
| `source_note` | de onde veio a informação (página, data de consulta) |
| `verified_on` | data `AAAA-MM-DD` em que você conferiu a página |
| `status` | `approved` ou `candidate` (veja §5) |
| `content` | **opcional.** O trecho oficial da página (veja §4); até 3000 caracteres |

Não invente URL: se o serviço não tem página própria, use a página do tema no portal oficial e diga isso no `source_note`.

## 3. Como escrever `keywords`

São as palavras que o cidadão digitaria ao pedir aquilo: **linguagem de rua**, não o nome técnico. Entre 5 e 10 termos, cada
um curto, em minúsculas.

- Bom: `remedio de graca`, `remedio pra pressao`, `farmacia popular`, `medicamento gratuito`.
- Evite termos genéricos que outras entradas também usam (`saude`, `documento`): quando duas entradas competem pelo mesmo
  termo, o robô prefere não apontar nenhuma a apontar a errada.
- Acento e maiúscula não importam na busca.

## 4. Como escrever `content`

O `content` é o texto que **fundamenta** a resposta. Ele também entra na busca: se o cidadão usa uma palavra que só aparece
no trecho, a entrada ainda é encontrada.

1. **Copie da própria página oficial**, sem reescrever: o trecho que responde (quem pode, o que levar, prazo, valor, onde ir).
2. **Curto e direto**: até **3000 caracteres**. Acima disso o registro é recusado. Texto só, sem HTML.
3. **Sem dado pessoal** de ninguém (CPF, telefone de pessoa, e-mail pessoal, nome, endereço residencial).
4. **Números** que o cidadão precisa (prazo, valor, telefone) devem estar no trecho: o LLM só pode repetir número que
   aparece no `content`, em `instructions` ou em `phones`; qualquer outro é barrado e a resposta cai no texto-modelo.
5. **Endereços de site não entram no trecho**: link só vale se estiver em `links`. Se precisar citar uma página, cadastre-a
   em `links`.
6. Se a página mudou, atualize o `content` **e** o `verified_on`.

## 5. Quando uma entrada responde ao cidadão

O registro que você coloca em `data/catalog.d/` **conta como aprovado por você**: não precisa constar em
`docs/fontes-publicas-sp-para-aprovacao.md`. Mas ele só **responde** se as três condições valem ao mesmo tempo:

1. `status` é `approved`;
2. o domínio de cada link está na allowlist (`gov.br` e subdomínios, mais `cetsp.com.br`, `sptrans.com.br`, `sabesp.com.br` e `desenvolvesp.com.br`, em `data/allowed_domains.json`);
3. o verificador confirma que o link está no ar.

Fora disso a entrada fica `candidate` (ou o link é descartado) e nunca chega ao cidadão. Use `candidate` enquanto estiver
rascunhando.

## 6. Como verificar

Na raiz do repositório:

```powershell
python scripts/verify_catalog.py            # confere esquema, allowlist, links no ar e telefones (usa a rede)
python scripts/verify_catalog.py --offline  # só esquema, allowlist e datas (sem rede)
```

Cada linha é um resultado: `OK`, `AVISO` ou `ERRO`, o `id` do registro, o que foi conferido entre colchetes e o detalhe. Para
`AVISO` e `ERRO` o fim da linha traz `(arquivo: ...)`, com o arquivo de origem. A última linha resume o total.

- `ERRO` precisa ser corrigido: campo faltando ou do tipo errado, `content` vazio ou acima de 3000 caracteres, `id` repetido,
  link fora da allowlist, entrada `approved` sem nenhum link no ar, arquivo ilegível.
- `AVISO` merece uma olhada: um dos links não responde, telefone não confirmado na página, `verified_on` com mais de 180 dias.
- O código de saída é `0` sem erro e `1` com erro. O verificador **nunca altera** seus arquivos.

## 7. Exemplo completo (modelo; não copie o `id`)

Baseado na entrada real `popular_pharmacy` de `data/catalog.json` (mesma URL oficial). O `content` abaixo é um
**marcador**: troque pelo trecho copiado da página.

```json
[
  {
    "id": "exemplo_farmacia_popular_como_funciona",
    "category": null,
    "kind": "service",
    "scope": "federal",
    "coverage": "Brasil",
    "area": "health",
    "display_name": "Farmácia Popular",
    "agency": "Ministério da Saúde",
    "instructions": "Programa que oferece medicamentos gratuitos ou com desconto. A página explica como funciona.",
    "keywords": [
      "farmacia popular",
      "remedio gratuito",
      "medicamento gratuito",
      "remedio com desconto",
      "remedio de graca",
      "medicamento pelo sus"
    ],
    "links": [
      {
        "label": "Farmácia Popular",
        "url": "https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular"
      }
    ],
    "phones": [],
    "source_note": "Página oficial do programa, consultada em AAAA-MM-DD.",
    "verified_on": "AAAA-MM-DD",
    "status": "candidate",
    "content": "EXEMPLO: cole aqui o trecho oficial copiado da página (quem pode, o que levar, prazo, onde ir), até 3000 caracteres."
  }
]
```

Troque `AAAA-MM-DD` pela data real, o `id` por um novo, o `content` pelo trecho oficial, rode o verificador e só então mude
`status` para `approved`.

## 8. Importar da planilha

A base também pode vir de uma planilha. O script `scripts/import_catalog_xlsx.py` lê a **primeira aba** do `.xlsx` e gera
`data/catalog.d/sp_expanded.json`: a planilha é a fonte e o JSON é gerado, então **não edite o JSON à mão**; corrija a planilha e
rode de novo. Na raiz do repositório:

```powershell
python scripts/import_catalog_xlsx.py                          # usa docs/catalogo_servicos_publicos_expandido_rpa.xlsx
python scripts/import_catalog_xlsx.py --xlsx outra.xlsx --out data/catalog.d/outra.json --date 2026-11-11
```

`--date` é o `verified_on` dos registros (padrão: hoje, em UTC). Rodar duas vezes com a mesma planilha e a mesma data gera arquivos idênticos.

**Colunas esperadas** (acento e maiúscula do cabeçalho não importam): `ID`, `Esfera / Órgão`, `Macro-Categoria`,
`Finalidade / Descrição do Serviço`, `URL Oficial`, `Palavras-Chave / Intents (NLP)` e `Tipo de Interação / Notas RPA`.

**O que o script faz por linha** (as tabelas ficam em `data/catalog_import.json`):

| Registro | Vem de |
|---|---|
| `id` | `xl_` + `ID` em minúsculas (`M02` vira `xl_m02`) |
| `scope` e `coverage` | prefixo do `ID`: `M` municipal ("Município de São Paulo"), `S` estadual ("Estado de São Paulo"), `F` federal ("Brasil") |
| `area` | tabela da `Macro-Categoria`; categoria fora da tabela cai em `city` e vem avisada no relatório |
| `kind` | `portal` se a finalidade começa com "Portal"; senão `service` |
| `display_name`, `agency`, `keywords`, `links` | finalidade, órgão, palavras-chave (aparadas, sem vazio e sem repetição) e a URL (um link por linha) |
| `instructions` | frase-modelo com o órgão e a finalidade, mandando usar a página oficial |
| `source_note` | arquivo, linha e `ID` de origem, mais a coluna de notas |
| `status` | `approved`; `candidate` se o domínio do link não está na allowlist |

**O que o script não faz:** não escreve `content` nem telefone (a planilha não os traz), não copia a coluna de notas para a resposta
(ela é jargão de RPA e fica só no `source_note`), não navega na internet, não conserta texto e não remove nem funde registros. Linha
sem `ID`, sem URL ou com `ID` repetido é ignorada com aviso. Os registros importados **convivem** com os de `data/catalog.json` (ids
diferentes); o relatório lista os pares que apontam para o mesmo link, e quem decide o que fazer com eles é você.

O relatório impresso traz as linhas lidas e geradas, as ignoradas (com o motivo), os `candidate`, as áreas que caíram no padrão e os
pares. Depois de importar, rode `python scripts/verify_catalog.py`: link que não responde nunca chega ao cidadão, mesmo `approved`.
