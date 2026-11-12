# Especificações técnicas

Documentação técnica do robô de triagem: o que cada parte faz, as regras de negócio, as decisões de arquitetura e como o
projeto foi validado. Cada arquivo descreve o sistema **como ele é**.

## Arquitetura
| Arquivo | Assunto |
|---|---|
| [arquitetura/00-fundacao-tecnologica.md](arquitetura/00-fundacao-tecnologica.md) | stack, fluxo em três etapas e restrições do projeto |
| [arquitetura/01.01-estrutura-do-projeto.md](arquitetura/01.01-estrutura-do-projeto.md) | pastas, dependências, configuração e ambiente |
| [arquitetura/04.01-persistencia.md](arquitetura/04.01-persistencia.md) | banco SQLite: idempotência, fila de revisão, feedback e catalogação |
| [arquitetura/04.03-orquestracao-rpa.md](arquitetura/04.03-orquestracao-rpa.md) | execução em lote, retry, relatório, CSV de saída e agendamento |

## Regras de negócio
| Arquivo | Assunto |
|---|---|
| [01.02-ingestao-e-sanitizacao.md](01.02-ingestao-e-sanitizacao.md) | leitura de txt/csv/json e sanitização da entrada |
| [01.03-anonimizacao-de-pii.md](01.03-anonimizacao-de-pii.md) | anonimização de dados pessoais |
| [02.01-classificacao.md](02.01-classificacao.md) | classificação do assunto (regex e TF-IDF) |
| [02.02-confianca-e-revisao-humana.md](02.02-confianca-e-revisao-humana.md) | limiares, urgência e revisão humana |
| [03.01-catalogo-e-allowlist.md](03.01-catalogo-e-allowlist.md) | catálogo de fontes, allowlist e verificação de links |
| [03.02-resposta-final-e-llm.md](03.02-resposta-final-e-llm.md) | resposta final, template e LLM opcional |
| [03.03-localizador-de-servicos.md](03.03-localizador-de-servicos.md) | localizador de fontes aprovadas |
| [03.04-agente-llm.md](03.04-agente-llm.md) | agente LLM em arquivos versionados |
| [03.05-categoria-da-interacao.md](03.05-categoria-da-interacao.md) | categoria de catalogação da interação |
| [04.02-interface.md](04.02-interface.md) | interface Streamlit: chat, revisão e feedback |
| [05.01-validacao-e-entrega.md](05.01-validacao-e-entrega.md) | validação, métricas e estrutura da entrega |

## Decisões de arquitetura (ADR)
| Arquivo | Decisão |
|---|---|
| [adr/001-stack-principal.md](adr/001-stack-principal.md) | stack principal |
| [adr/002-persistencia-sqlite-e-arquivos.md](adr/002-persistencia-sqlite-e-arquivos.md) | persistência em SQLite e arquivos |
| [adr/003-seguranca-sem-autenticacao.md](adr/003-seguranca-sem-autenticacao.md) | segurança de um protótipo local, sem autenticação |
| [adr/004-infra-execucao-local.md](adr/004-infra-execucao-local.md) | execução local, sem nuvem |
| [adr/005-llm-apenas-reformula-resposta.md](adr/005-llm-apenas-reformula-resposta.md) | primeira decisão sobre o papel do LLM |
| [adr/006-llm-escolhe-apenas-entre-fontes-aprovadas.md](adr/006-llm-escolhe-apenas-entre-fontes-aprovadas.md) | LLM escolhe só entre fontes aprovadas |
| [adr/007-llm-redige-a-resposta-com-rag-do-catalogo.md](adr/007-llm-redige-a-resposta-com-rag-do-catalogo.md) | LLM redige a resposta com RAG do catálogo |
