---
tipo: "plan"
familia: "01"
item: "R01.4"
titulo: "Ampliar a anonimização para nome, endereço, CEP, RG, data e documentos"
dominio: "Núcleo do robô"
status: "🟢 Aprovada"
prioridade: "Alta"
tags: ["plan"]
relacionados: ["[[003-seguranca-sem-autenticacao]]", "[[01.03-anonimizacao-de-pii]]", "[[02.01-classificacao]]"]
depende_de: ""
destino_sintese: "specs/01.03-anonimizacao-de-pii.md"
---

# 1. Objetivo
`anonymize(text)` troca também nome de pessoa, endereço, CEP, RG, data completa e números de documento por marcadores,
de modo que nada disso chegue ao banco, ao log, à tela de revisão nem a uma API.

# 2. Contexto
Hoje a anonimização cobre só CPF, telefone e e-mail ([[01.03-anonimizacao-de-pii]]). Uma sessão de uso real mostrou o
risco: o pedido "Meu nome é Jose carlos de andrade" foi gravado com o nome em texto puro, e um pedido de teste com
"Rua das Flores, 123, CEP 01310-100" e "RG 12.345.678-9" também ficou inteiro no SQLite. É o ponto principal da
entrega (proteção de dados, [[003-seguranca-sem-autenticacao]]) e bloqueia qualquer uso de LLM sobre o texto do cidadão.

Princípios para o executor:
- **Na dúvida, mascarar.** Falso negativo (dado pessoal que passa) é a falha grave; falso positivo (palavra comum
  mascarada) é aceitável, desde que raro nos pedidos de serviço público e sem prejudicar a classificação.
- Cidade, estado e bairro/região **não** são mascarados (não identificam a pessoa sozinhos e ajudam o roteamento).
- Sem modelo de NER: a plan usa contexto, padrões e uma lista de nomes próprios. O limite continua declarado: nome fora
  de qualquer contexto e fora da lista pode passar (risco residual).
- Bancos `.db` já criados antes desta plan podem conter texto puro; eles são locais e fora do Git, e o usuário os apaga.

# 3. Escopo
## 3.1 Dentro
- `src/triage/privacy/patterns.py` — novos marcadores (`[NOME]`, `[ENDERECO]`, `[CEP]`, `[RG]`, `[DATA]`, `[DOCUMENTO]`) e padrões
- `src/triage/privacy/` — novos módulos por tipo (nome, endereço, documentos e datas), cada função dentro dos limites do Nível 0
- `src/triage/privacy/anonymizer.py` — compor os novos tipos; `counts` ganha as chaves `name`, `address`, `postal_code`, `rg`, `date`, `document`
- `data/first_names.json` — lista curada de nomes próprios comuns no Brasil (só prenomes; nenhum dado de pessoa real); caminho relativo, como os demais JSON de `data/`
- `src/triage/classification/preprocessing.py` — **só** acrescentar os novos marcadores ao conjunto removido por `fold`, para `[NOME]` não virar o termo "nome"
- `tests/privacy/` — testes dos novos tipos; ajustar os testes existentes que fixam as três chaves de `counts`
- `tests/classification/test_preprocessing.py` — só o caso dos novos marcadores
- `src/triage/privacy/__init__.py` — só a docstring do pacote (correção 1)
- `README.md` — a frase que declara que nome e endereço não são anonimizados
- `notebooks/evidence.ipynb` — só o texto da seção de limites que diz o mesmo (sem reexecutar; as saídas não mudam)

## 3.2 Fora
- `triage.pipeline`, `triage.interface`, `triage.storage`, `triage.ingestion`: já chamam `anonymize`; não mudam.
- `data/labeled/requests_labeled.csv` e o modelo treinado.
- Modelo de NER, serviço externo ou LLM para anonimizar (enviaria o dado a uma API).
- Migração ou limpeza de bancos já criados.

# 4. Referências obrigatórias
| Tipo | Referência | Por quê |
|---|---|---|
| ADR | [[003-seguranca-sem-autenticacao]] | só texto anonimizado é gravado, logado ou enviado |
| Spec fixa | [[01.03-anonimizacao-de-pii]] | contrato atual de `anonymize`, ordem de aplicação e limites |
| Spec fixa | [[02.01-classificacao]] | `normalize`/`fold` removem os marcadores de anonimização |
| Contexto | [[00-contexto]] · [[00-knowledge]] | sempre |
| Skill | `padrao-escrita` + `padrao-python` | identificadores em inglês; comentários e textos ao usuário em português; limiares de clean code |
| Skill | `cyber-dados` | inventário de PII e mascaramento |
| Skill | `test-unitario` | testes de tabela por tipo |
| Código | `src/triage/privacy/anonymizer.py`, `patterns.py`, `validators.py` | o que será estendido |
| Código | `src/triage/classification/preprocessing.py` | onde os marcadores são removidos |
| Código | `data/labeled/requests_labeled.csv` | texto realista para checar falso positivo |

# 5. Instruções de execução
1. [dirigido] **Nome.** Mascarar com `[NOME]`: (a) a sequência de palavras após uma introdução explícita ("meu nome é",
   "me chamo", "chamo-me", "nome:", "nome completo:", "Sr./Sra./Dr./Dra./senhor/senhora"), mesmo em minúsculas ou sem
   acento, até pontuação, dígito ou palavra que não seja parte de nome (a sequência aceita conectores `de/da/do/dos/das`;
   `e` encerra o nome); (b) em qualquer posição, prenome da lista `data/first_names.json` seguido dos sobrenomes
   (palavras iniciadas por maiúscula e conectores seguidos de maiúscula). A lista deve ter pelo menos 300 prenomes e ser
   lida uma vez, com falha segura: arquivo ausente ou inválido → log de erro e só o caminho (a) funciona, nunca erro para
   quem chamou. "Sou" sozinho **não** é introdução (evita mascarar "sou aposentado").
2. [dirigido] **Endereço e CEP.** `[ENDERECO]` para logradouro com nome próprio, com ou sem número (rua, avenida, alameda,
   travessa, praça, rodovia, estrada, largo, também abreviados), incluindo complementos que o sigam (número, apto, bloco,
   casa); `[CEP]` para `00000-000` e para oito dígitos precedidos de "CEP". "Rua" ou "buraco na rua" sem nome próprio não
   são mascarados.
3. [dirigido] **Documentos e datas.** `[RG]` para o número após "RG" (com ou sem pontuação, dígito `X`) e para o formato
   `0.000.000-0`; `[DOCUMENTO]` para sequência numérica de 9 a 15 dígitos (com espaços, pontos ou hífens) precedida de
   "título de eleitor", "CNH", "NIS", "PIS", "cartão SUS", "CNPJ", "passaporte" ou "matrícula", e para CNPJ no formato
   pontuado; `[DATA]` para data completa (`dd/mm/aaaa`, `dd-mm-aaaa`, `dd.mm.aaaa`). "RG" ou "CNH" sem número ficam.
4. [dirigido] **Composição.** Ordem fixa e documentada no docstring, de modo que um tipo não consuma o dígito de outro
   (e-mail, CPF, depois os novos tipos com contexto, por último telefone). A função continua pura, idempotente (os
   marcadores novos não contêm dígito nem `@`) e sem registrar o texto em log. `counts` traz sempre todas as chaves.
5. [dirigido] **Classificação intacta.** Acrescentar os marcadores novos ao que `fold` remove e testar que
   `normalize("Meu nome é [NOME], CEP [CEP]")` não contém "nome" nem "cep" como termos vindos do marcador.
6. [dirigido] **Testes.** Tabela por tipo com positivos e negativos. Os casos abaixo são o mínimo e devem passar
   exatamente; acrescente pelo menos 20 casos próprios de pessoa fictícia (formal, minúsculas, sem acento, nome no meio
   da frase, só prenome da lista).

   | Entrada | Saída esperada |
   |---|---|
   | `Meu nome é Jose carlos de andrade` | `Meu nome é [NOME]` |
   | `Me chamo Ana, moro na Av. Paulista 1000 apto 52` | `Me chamo [NOME], moro na [ENDERECO]` |
   | `Sou Maria da Silva Souza e preciso da segunda via do RG` | sem `Maria da Silva Souza`; `[NOME]` no lugar; `segunda via do RG` intacto |
   | `RG 12.345.678-9` | `RG [RG]` |
   | `nascido em 12/03/1985` | `nascido em [DATA]` |
   | `CEP 01310-100` | `CEP [CEP]` |
   | `título de eleitor 1234 5678 9012` | `título de eleitor [DOCUMENTO]` |
   | `Rua das Flores, 123` | `[ENDERECO]` |
   | `joão pereira precisa renovar a cnh` | `[NOME] precisa renovar a cnh` |

   Devem permanecer **idênticos**: `Quero saber sobre o Bolsa Família e o Cadastro Único` · `Preciso da Receita Federal e
   da Justiça Eleitoral` · `Moro em São Paulo, na região do Ipiranga` · `Meu protocolo é 2024/0001 e a taxa é de R$ 120,50`
   · `Quero renovar minha CNH` · `Preciso do RG` · `Sou aposentado e quero saber do INSS` · `Há um buraco na rua em frente à
   escola` · `dia 12/03` (data sem ano).
7. [dirigido] **Sem regressão no texto do projeto.** Aplicar `anonymize` aos 180 textos de
   `data/labeled/requests_labeled.csv`: nenhum deles pode mudar além dos marcadores que já trazem. Se a lista de nomes
   mascarar palavra comum desses textos, ajustar a lista ou a regra e registrar o motivo no resumo.
8. [dirigido] **Documentação.** README e a seção de limites do notebook passam a declarar o que é coberto e o limite
   residual (nome fora de contexto e fora da lista; endereço sem logradouro; cidade e bairro não mascarados).
9. Rodar a verificação do §7.

# 6. Critérios de aceite
- [ ] Os nove casos da tabela do passo 6 produzem exatamente a saída esperada, e os de "idênticos" não mudam.
- [ ] Pelo menos 20 casos de pessoa fictícia testados, cobrindo nome por introdução, nome por lista e endereço.
- [ ] `anonymize` é idempotente e pura, e `counts` traz as nove chaves.
- [ ] Os 180 textos do CSV rotulado não mudam.
- [ ] `normalize` não deixa o marcador virar termo; a classificação dos testes existentes não muda.
- [ ] Lista de nomes ausente ou inválida não levanta exceção: log de erro e segue só com o contexto.
- [ ] Nenhum dado pessoal real no diff (a lista só tem prenomes; os casos de teste são fictícios).
- [ ] Ambiente e worktree limpos (sem processo, arquivo temporário ou banco largado pela tarefa).
- [ ] Testes do escopo verdes; `ruff` e o validador de `padrao-python` sem violação nos arquivos alterados.
- [ ] Nenhuma chave e nenhum `.env` no diff.

# 7. Como verificar (uso do revisor)
- **Nível:** `ampla — altera `classification/preprocessing.py` e `anonymize`, que pipeline, interface e avaliação consomem`.
- `git diff --stat` → só arquivos de §3.1.
- `python -m pytest tests/privacy tests/classification tests/pipeline tests/interface tests/evaluation -q` → verde.
- `python -m ruff check src/triage/privacy src/triage/classification/preprocessing.py tests/privacy` → sem erro.
- `validate.py` do `padrao-python` em `src/triage/privacy`, `preprocessing.py` e `tests/privacy` → sem achado.
- Sondagem do revisor com pessoas fictícias novas (nome em minúsculas, sobrenome composto, endereço com complemento) e com
  os negativos acima.
- `anonymize` sobre o CSV rotulado: nenhuma linha muda.
- **Gate:** `nenhum — coberto por teste de tabela e pela checagem do CSV`.

# 8. Destino da síntese
**Destino:** `specs/01.03-anonimizacao-de-pii.md`

Levar, **substituindo** o que a spec diz hoje (que só três tipos são cobertos e que nome e endereço passam): a tabela de
tipos e marcadores ampliada com as chaves de `counts`; a regra "na dúvida, mascarar"; o que não é mascarado (cidade,
estado, bairro); a ordem de aplicação; a lista de nomes e sua falha segura; e o limite residual declarado.

---

# 9. Resumo da execução

<!-- Preenchido pelo EXECUTOR. Append-only: cada rodada acrescenta um bloco novo; nada é removido. -->

## Resumo da execução — 2026-11-10

**Resultado:** Concluído

**O que foi feito**
- `patterns.py:30-122` — marcadores novos, `ALL_MARKERS`, constantes `KIND_*` (movidas do anonymizer) e os padrões de CEP, RG, documento, data, introdução de nome/tratamento e endereço.
- `names.py` (novo) — nome por introdução e por lista de prenomes; lista lida uma vez (`lru_cache`), falha segura com `logger.error` só com o caminho.
- `address.py`, `identifiers.py`, `substitution.py` (novos) — endereço; CEP/RG/documentos/data; helper `substitute` (antes `_substitute` no anonymizer).
- `anonymizer.py` — composição na ordem e-mail, CPF, documentos, CEP, RG, data, endereço, nome, telefone (docstring); `counts` com as nove chaves.
- `data/first_names.json` — 346 prenomes (só prenomes, sem dado de pessoa real).
- `preprocessing.py:6,11` — `fold` remove `ALL_MARKERS`.
- Testes, README e texto de limites do notebook (sem reexecutar) atualizados.

**Arquivos alterados**
| Arquivo | Natureza | O que mudou |
|---|---|---|
| `src/triage/privacy/patterns.py` | alterado | marcadores, kinds, padrões novos |
| `src/triage/privacy/anonymizer.py` | alterado | compõe os novos tipos; nove chaves em `counts` |
| `src/triage/privacy/names.py` | criado | anonimização de nome |
| `src/triage/privacy/address.py` | criado | anonimização de endereço |
| `src/triage/privacy/identifiers.py` | criado | CEP, RG, documento, data |
| `src/triage/privacy/substitution.py` | criado | helper de substituição com contagem |
| `data/first_names.json` | criado | lista de prenomes |
| `src/triage/classification/preprocessing.py` | alterado | remove todos os marcadores |
| `tests/privacy/test_extended_pii.py` | criado | tabelas por tipo, 40 casos fictícios, falha segura, CSV |
| `tests/privacy/test_anonymizer.py` | alterado | `_counts` com as nove chaves |
| `tests/classification/test_preprocessing.py` | alterado | caso dos novos marcadores |
| `README.md` | alterado | declara o coberto e o limite residual (3 trechos que citavam só CPF/telefone/e-mail) |
| `notebooks/evidence.ipynb` | alterado | só o texto de limites (JSON válido; sem reexecutar) |

**Verificações executadas**
- `python -m pytest tests/privacy tests/classification tests/pipeline tests/interface tests/evaluation -q` → 296 passed.
- `python -m ruff check src/triage/privacy src/triage/classification/preprocessing.py tests/privacy tests/classification/test_preprocessing.py` → All checks passed.
- `validate.py` (padrao-python) em `src/triage/privacy`, `preprocessing.py`, `tests/privacy` → 0 achados.
- `anonymize` sobre os 180 textos do CSV → nenhum muda (`test_labeled_csv_is_unchanged`). Na primeira passada o L167 ("rua da minha casa") mudou; ajustei o padrão de endereço (possessivos/"casa"/"frente"/"vila" após conector não formam nome de rua) e ele voltou ao original.
- `git diff --stat` → só arquivos de §3.1 (mais os `specs/` que já estavam modificados antes).

**Estado inicial do worktree:** ` M specs/00-indice.md`, ` M specs/panorama/00-planejamento.md`, ` M specs/panorama/00-resumo.md`, `?? specs/plan/plan-01.04-anonimizacao-ampliada.md`.

**Ambiente após a verificação:** nada criado (sem processo, servidor nem banco; o script de sondagem em `%TEMP%` foi removido). `snapshot` da skill `code-limpeza-ambiente` não foi rodado: a verificação foi só pytest/ruff locais.

**Critérios de aceite**
- [x] Nove casos da tabela e os "idênticos" — `test_required_cases`, `test_negative_cases_stay_unchanged`.
- [x] ≥ 20 casos fictícios (40) — `FICTITIOUS_CASES`.
- [x] Idempotente, pura, nove chaves — `test_idempotent_for_new_types`, `test_anonymize_is_pure`, `test_counts_have_all_nine_keys`.
- [x] 180 textos do CSV não mudam — `test_labeled_csv_is_unchanged`.
- [x] `normalize` não deixa marcador virar termo — `test_normalize_drops_every_anonymization_marker` (`"nome cep rg cnh"`, só as palavras reais); testes de classificação existentes passam.
- [x] Lista ausente/inválida sem exceção — `test_missing_or_invalid_first_names_fail_safe`, `test_context_masks_names_even_without_the_list`.
- [x] Sem dado pessoal real no diff — lista só de prenomes; casos fictícios.
- [x] Ambiente e worktree limpos.
- [x] Testes do escopo verdes; ruff e validador sem violação nos arquivos alterados.
- [x] Sem chave nem `.env` no diff.

**Decisões e suposições**
- Tratamento ("Sr./Dra./senhor"...) só mascara se a palavra seguinte for capitalizada: "o senhor pode ajudar" é frase comum. As introduções "meu nome é/me chamo/nome:" valem em minúsculas.
- O fim do nome é decidido por uma lista de palavras que não são nome (`NON_NAME_WORDS` em `names.py`: verbos e palavras comuns de pedido) e por um teto de 7 palavras; por isso nome por lista aceita sobrenome em minúsculas ("joão pereira", exigido pelo caso da tabela), e o conjunto é heurístico.
- Prenome da lista precedido de "São/Santa/Santo" ou "João Pessoa" não é mascarado (topônimos); retirei da lista prenomes que são palavra/cidade comum (Clara, Salvador, Vitória etc.).
- Adicionei "nome do pai/mãe/filho/titular:" como introdução (também é PII).
- Endereço: abreviações de logradouro exigem ponto (`r.`, `al.`, `tv.`), exceto `av`; nome após conector aceita qualquer palavra que não seja posse/lugar comum; sem conector exige maiúscula e não aceita "em/na/sem..." (inclusive em caixa alta).
- Documento rotulado só mascara com 9–15 dígitos; sequência maior que 15 após o rótulo fica inalterada.
- Constantes `KIND_*` foram para `patterns.py` para evitar import circular com os módulos novos; `anonymizer.py` continua importando-as.

**Achados fora do escopo (não corrigidos)**
- `tests/classification/test_decision.py:3` e `tests/classification/test_model.py:3` — `ruff` I001 (imports não ordenados), preexistente; fora do comando de §7.
- `src/triage/privacy/__init__.py:1` — docstring ainda diz "CPF, telefone, e-mail"; não está em §3.1.
- `specs/00-contexto.md` §2/§3 e `specs/01.03-anonimizacao-de-pii.md` ainda dizem só CPF/telefone/e-mail: são da síntese do revisor.

**Pendências / riscos**
- Falso positivo possível: nome por lista com sobrenome em minúsculas pode engolir uma palavra comum que não esteja na lista de parada (ex.: "Maria da Penha" é mascarado inteiro; ausente do CSV). Falso negativo residual: nome fora de contexto e fora da lista; endereço sem logradouro.
- Gate declarado `nenhum`; sem sondagem de entrada/saída adicional além dos testes de tabela.

---

# 10. Veredito

<!-- Preenchido pelo REVISOR. Append-only: um bloco por rodada, com o que foi verificado e como. -->

## Veredito — 2026-11-10 — 🔴 Reprovado

**Verificado (nível ampla, como a §7 declara), com saída real:** `git status`/`git diff` (só arquivos de §3.1; `README.md` e a célula de limites do notebook coerentes com o que a plan pede) · leitura integral de `names.py`, `address.py`, `identifiers.py`, `substitution.py`, `patterns.py` e da lista de 359 prenomes (únicos, sem dado de pessoa real) · `python -m pytest tests/privacy tests/classification tests/pipeline tests/interface tests/evaluation -q` → 296 passed · `python -m ruff check --no-cache` nos arquivos do escopo → All checks passed · `padrao-python/scripts/validate.py` em `src/triage/privacy`, `preprocessing.py` e `tests/privacy` → `findings: []` · sondagem com 16 pessoas fictícias novas (formal, minúsculas, sobrenome composto, mãe e filho no pedido, CNPJ, ISO date, "Sr./Dra.", nome só pela lista): todas tiveram nome, CPF, telefone, RG, data, CEP e CNPJ mascarados como a plan pede, inclusive o pedido real da sessão ("Meu nome é Jose carlos de andrade" → `Meu nome é [NOME]`) · 13 negativos reais (Justiça Eleitoral, Bolsa Família, Santa Maria, Receita Federal, "buraco na rua", "A Rua está sem iluminação", "dores no peito… região do Ipiranga", data sem ano, protocolo numérico) → idênticos · idempotência dos 16 positivos → `anonymize(anonymize(x)) == anonymize(x)` · entradas adversariais de 2000 caracteres (nome repetido, "Rua Maria Maria…", "de de de…", RG repetido) → até 0,008 s, sem backtracking · os 180 textos do CSV não mudam.

**Decisões do executor aceitas:** tratamento ("Sr./Dra.") só com inicial maiúscula; `NON_NAME_WORDS` e teto de 7 palavras para delimitar o nome; topônimos "São/Santa/Santo" e "João Pessoa" fora; "nome do pai/mãe/filho/titular" como introdução; documento rotulado só entre 9 e 15 dígitos; `KIND_*` movidas para `patterns.py` (import circular).

**Achados**
1. `src/triage/privacy/patterns.py:104-120` (`ADDRESS_PATTERN`, `_STREET_NAME`) — endereço com logradouro em minúsculas e **sem conector** passa inteiro, mesmo com número. Entradas reais testadas e devolvidas **sem alteração**: `moro na rua augusta 500`, `av paulista 1000 apto 52`, `moro na praca sao joao 12`, `rua sao joao, 45`, `Rua augusta 500`, `moro na rua 7 de setembro, 12`, `mudei para a rua tres 45 centro`. Só passam quando há conector em minúsculas (`rua das flores 123`) ou nome capitalizado. Quem escreve pelo teclado costuma digitar tudo em minúsculas (os pedidos da própria sessão são assim), então o endereço completo, com número, fica gravado em texto puro: é o falso negativo grave que a plan manda evitar ("na dúvida, mascarar"; §5.2 "logradouro com nome próprio, com ou sem número"). Critério violado: §2 (princípio) e §5.2. Exigido: logradouro seguido de uma ou mais palavras (em qualquer caixa, aceitando número ou numeral por extenso no nome, como "7 de setembro" e "tres") **e de número ou complemento** é mascarado como `[ENDERECO]` mesmo em minúsculas; sem número nem complemento, continua exigindo nome capitalizado, para não mascarar "rua em frente à escola", "a rua da minha casa" nem "A Rua está sem iluminação". Testes novos com as sete entradas acima (mascaradas) e com esses três negativos e os demais já existentes (idênticos); os 180 textos do CSV continuam sem mudar.
2. `src/triage/privacy/__init__.py:1` — a docstring do pacote ainda diz "CPF, telefone, e-mail"; o resumo do executor já apontava. Passa a fazer parte do escopo desta correção (a §3.1 ganha esse arquivo): atualizar a docstring para os nove tipos cobertos. Critério violado: documentação coerente com o que o pacote faz (§5.8).

**Itens para o `00-backlog` (não reprovam):** prenome da lista dentro de nome de lugar ("Vila Madalena" vira "Vila [NOME]"); a ampliação para prefixos como "Vila", "Jardim" e "Parque" fica para depois.

---

## Resumo da execução (correção 1) — 2026-11-10

**Resultado:** Concluído

**Achado 1 — endereço em minúsculas sem conector**
- `src/triage/privacy/patterns.py` (`_PLAIN_WORD`, `_STREET_PLAIN_NAME`, `ADDRESS_PATTERN`) — nova alternativa: logradouro + 1 a 5 palavras em qualquer caixa (aceita numeral, como "7 de setembro") **e** número, `s/n` ou complemento obrigatórios. A alternativa antiga (nome capitalizado ou conector, número opcional) ficou como estava; sem número nem complemento, minúscula sem conector continua sem casar.
- Evidência (entrada → saída): `moro na rua augusta 500` → `moro na [ENDERECO]` · `av paulista 1000 apto 52` → `[ENDERECO]` · `moro na praca sao joao 12` → `moro na [ENDERECO]` · `rua sao joao, 45` → `[ENDERECO]` · `Rua augusta 500` → `[ENDERECO]` · `moro na rua 7 de setembro, 12` → `moro na [ENDERECO]` · `mudei para a rua tres 45 centro` → `mudei para a [ENDERECO] centro`.
- Negativos idênticos (testados): `rua em frente à escola`, `a rua da minha casa`, `A Rua está sem iluminação`, mais os anteriores.
- `tests/privacy/test_extended_pii.py` — as sete entradas entram em `FICTITIOUS_CASES` (positivos e idempotência) e os três negativos em `test_negative_cases_stay_unchanged`; `test_labeled_csv_is_unchanged` segue verde (180 textos sem mudança).

**Achado 2 — docstring do pacote**
- `src/triage/privacy/__init__.py:1` — docstring lista os nove tipos cobertos.

**Verificações executadas**
- `python -m pytest tests/privacy tests/classification tests/pipeline tests/interface tests/evaluation -q` → 313 passed.
- `python -m ruff check src/triage/privacy src/triage/classification/preprocessing.py tests/privacy` → All checks passed.
- `validate.py` em `src/triage/privacy` e `tests/privacy` → `findings: []`.

**Ambiente após a verificação:** nada criado.

**Decisões e suposições**
- Troquei um caractere de tabulação literal por `\t` em `patterns.py` (efeito de edição, sem mudar o comportamento).
- Sondei `buraco na rua em frente 3 dias`: permanece inalterado (o filtro de "em/na/sem..." vale no primeiro termo do nome).

**Achados fora do escopo (não corrigidos):** nenhum novo.

## Veredito — 2026-11-10 — 🔴 Reprovado (correção 1)

**Verificado (nível ampla), com saída real:** `git status` (só arquivos de §3.1, mais o `__init__.py` do pacote que a correção autorizou) · leitura do `ADDRESS_PATTERN` e do resumo da correção · `python -m pytest tests/privacy tests/classification tests/pipeline tests/interface tests/evaluation -q` → 313 passed · `python -m ruff check --no-cache` nos arquivos do escopo → All checks passed · `padrao-python/scripts/validate.py` em `src/triage/privacy` e `tests/privacy` → `findings: []` · **achado 2 da rodada anterior:** docstring do pacote lista os nove tipos → atendido · **achado 1 da rodada anterior (endereço em minúsculas):** as sete entradas voltaram mascaradas (`moro na rua augusta 500` → `moro na [ENDERECO]`, `av paulista 1000 apto 52`, `praca sao joao 12`, `rua sao joao, 45`, `Rua augusta 500`, `rua 7 de setembro, 12`, `rua tres 45 centro`), e os demais endereços de sondagem (`rua das flores 123`, `Rua Dom Pedro II, 45, apto 301, bloco B`, `avenida brasil s/n`, `estrada do sol km 12`) também · entradas adversariais de 2000 caracteres → até 0,005 s.

**Achados**
1. `src/triage/privacy/patterns.py` (`_STREET_PLAIN_NAME`, `ADDRESS_PATTERN`) — a alternativa nova aceita de 1 a 5 palavras quaisquer entre o logradouro e **qualquer número**, e passou a mascarar frases comuns de reclamação que não são endereço, apagando justamente o assunto do pedido. Entradas reais testadas e **alteradas**: `A rua está sem iluminação há 3 dias` → `A [ENDERECO] dias`; `moro nesta rua há 10 anos` → `moro nesta [ENDERECO] anos`; `a rua ficou alagada 2 vezes esta semana` → `a [ENDERECO] vezes esta semana`; `Na rua da escola passam 20 ônibus por dia` → `Na [ENDERECO] passam 20 ônibus por dia`; `o buraco na rua de casa tem 2 metros` → `o buraco na [ENDERECO] metros`; `avenida lotada 3 horas` → `[ENDERECO] horas`. Reclamação de rua com número ou duração é o tipo de pedido mais provável de aparecer fora do catálogo, e o texto mascarado perde a informação que o robô e o revisor humano precisam. Critério violado: §2 ("falso positivo ... aceitável, desde que raro nos pedidos de serviço público e sem prejudicar a classificação"). Exigido: manter mascarados os endereços do achado anterior e os de sondagem acima, mas **não** mascarar quando o trecho entre o logradouro e o número tem verbo, preposição ou palavra comum de frase (por exemplo "está", "há", "ficou", "passam", "tem", "sem", "desde", "lotada") ou quando o número vem seguido de unidade de tempo ou quantidade ("dias", "anos", "vezes", "horas", "metros", "ônibus"); o nome sem conector em minúsculas deve ter no máximo 3 palavras. Testes: os seis negativos acima mais `quero reclamar da rua que está esburacada há 15 dias`, `rua sem asfalto desde 2020` e `Preciso de 2 vias da certidão na rua` (idênticos), e as sete entradas do achado anterior e `rua dos pinheiros n 200` (mascaradas); os 180 textos do CSV continuam sem mudar.

---

## Resumo da execução (correção 2) — 2026-11-10

**Resultado:** Concluído

**Achado 1 — falso positivo em reclamação de rua**
- `src/triage/privacy/patterns.py` (bloco de endereço, `_SENTENCE_WORDS`, `_NOT_QUANTITY`, `_PLAIN_*`, `ADDRESS_PATTERN`):
  - Nome sem conector em minúsculas: no máximo 3 palavras, e nenhuma pode ser palavra de frase (verbo, preposição, posse, tempo: "está", "há", "ficou", "passam", "tem", "sem", "desde", "lotada", "nesta"...). Conectores seguem permitidos dentro do nome ("7 de setembro", "dos pinheiros").
  - O número dessa alternativa não pode vir seguido de unidade ou quantidade ("dias", "anos", "vezes", "horas", "metros", "ônibus"...).
  - A alternativa de nome capitalizado também passou a recusar palavras de frase, e o conector só abre nome se a palavra seguinte for capitalizada.
- Evidência: os seis negativos do veredito, mais `quero reclamar da rua que está esburacada há 15 dias`, `rua sem asfalto desde 2020` e `Preciso de 2 vias da certidão na rua`, ficam idênticos; as sete entradas da correção 1, `rua dos pinheiros n 200` e as de sondagem (`rua das flores 123`, `Rua Dom Pedro II, 45, apto 301, bloco B`, `avenida brasil s/n`, `estrada do sol km 12`) seguem mascaradas.
- `tests/privacy/test_extended_pii.py` — nove negativos novos em `test_negative_cases_stay_unchanged`, `rua dos pinheiros n 200` em `FICTITIOUS_CASES`; `test_labeled_csv_is_unchanged` verde (180 textos sem mudança).

**Verificações executadas**
- `python -m pytest tests/privacy tests/classification tests/pipeline tests/interface tests/evaluation -q` → 324 passed.
- `python -m ruff check src/triage/privacy src/triage/classification/preprocessing.py tests/privacy` → All checks passed.
- `validate.py` em `src/triage/privacy` e `tests/privacy` → `findings: []`.

**Ambiente após a verificação:** nada criado (script de sondagem em `%TEMP%` removido).

**Decisões e suposições**
- Efeito colateral aceito: logradouro **em minúsculas, com conector e sem número** (`rua das flores` sozinho) deixou de ser mascarado, porque `rua da escola passam 20 ônibus` (negativo exigido) usava essa mesma regra. Com número, `s/n` ou complemento continua mascarado; sem número, só nome capitalizado (`Rua das Flores`, `Praça da Sé`). Fica como risco residual declarado.

**Achados fora do escopo (não corrigidos):** nenhum novo.
## Veredito — 2026-11-10 — 🟢 Aprovado (correção 2)

**Verificado (nível ampla, como a §7 declara), com saída real:** `git status` (só arquivos de §3.1, o `__init__.py` do pacote autorizado e os arquivos de spec do revisor) · leitura do bloco de endereço de `patterns.py` e do resumo da correção · `python -m pytest tests/privacy tests/classification tests/pipeline tests/interface tests/evaluation -q` → 324 passed · `python -m ruff check --no-cache` nos arquivos do escopo → All checks passed · `padrao-python/scripts/validate.py` em `src/triage/privacy` e `tests/privacy` → `findings: []` · **positivos:** 21 endereços de sondagem em várias caixas (`rua augusta 500`, `av paulista 1000 apto 52`, `praca sao joao 12`, `rua 7 de setembro, 12`, `rua dos pinheiros n 200`, `avenida brasil s/n`, `Praça da Sé 10`, `moro na alameda santos 200`, `Rua Dom Pedro II, 45, apto 301, bloco B`, entre outros) → todos mascarados · **negativos:** 27 frases comuns de reclamação e de pedido (`A rua está sem iluminação há 3 dias`, `moro nesta rua há 10 anos`, `a rua ficou alagada 2 vezes esta semana`, `Na rua da escola passam 20 ônibus por dia`, `o buraco na rua de casa tem 2 metros`, `rua sem asfalto desde 2020`, `dores no peito… região do Ipiranga`, `Bolsa Família`, `Justiça Eleitoral`, `dia 12/03`, entre outras) → todas idênticas · os 180 textos do CSV → 0 alterados · nome, RG, CPF e demais tipos seguem mascarados (`Meu nome é Jose carlos de andrade` → `Meu nome é [NOME]`) · entradas adversariais de 2000 caracteres → até 0,006 s · caches removidos.

**Decisão do executor aceita:** logradouro **em minúsculas, com conector e sem número** (`rua das flores` sozinho) deixou de ser mascarado, porque colide com um negativo exigido; com número, `s/n` ou complemento continua mascarado, e sem número só o nome capitalizado (`Rua das Flores`, `Praça da Sé`) é mascarado. Fica como risco residual declarado na síntese.

**Achados:** nenhum que reprove.
