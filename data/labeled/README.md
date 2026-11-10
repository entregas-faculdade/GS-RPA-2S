# Conjunto rotulado — `requests_labeled.csv`

> **Conjunto 100% sintético.** Nenhuma linha vem de um pedido real nem contém dado pessoal real: os textos
> foram escritos à mão para este protótipo acadêmico. Onde o pedido teria CPF, telefone ou e-mail, aparecem
> só os marcadores `[CPF]`, `[TELEFONE]` e `[EMAIL]`, como o texto chega ao classificador depois da anonimização.

## Como foi construído

- 180 pedidos em português, 20 por categoria (8 serviços + `other`), com variações de linguagem: formal,
  informal, frases curtas e longas, erros leves de digitação (acento ou cedilha faltando) e perguntas soltas.
- Alguns textos citam duas categorias de propósito (por exemplo, CPF e CNH na mesma frase), para exercitar o
  caso em que duas regras casam e a decisão cai no modelo.
- `other` reúne assuntos fora do catálogo: passaporte, imposto de renda, reclamações, conversa solta e
  situações de emergência.

## Colunas

| Coluna | Conteúdo |
|---|---|
| `id` | identificador da linha (`L001`…) |
| `text` | pedido, já no formato anonimizado |
| `label` | `driver_license`, `property_tax`, `id_card`, `cpf_registration`, `voter_id`, `social_benefits`, `social_security`, `birth_certificate` ou `other` |
| `split` | `train` ou `test` |
| `urgent` | `1` se o texto descreve emergência ou risco (fome, doença, violência, perda da moradia), senão `0` |

## Divisão treino/teste

Fixa e gravada no próprio arquivo: por categoria, 14 linhas `train` e 6 `test` (70/30 estratificado). O treino
(`scripts/train_model.py`) usa só `split=train`; as linhas `test` ficam reservadas para a avaliação.
