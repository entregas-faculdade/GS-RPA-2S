---
tipo: "processo"
titulo: "Backlog — Achados Registrados, Não Agendados"
dominio: "Governança de Specs (SDD)"
status: "🟢 Vigente"
tags: ["processo", "backlog", "achados", "sdd"]
relacionados: ["[[00-indice]]", "[[00-prompt-revisor]]", "[[00-prompt-executor]]"]
---

# 0. O que é este arquivo

O lugar onde um achado **descansa**. Nem executado, nem esquecido.

Antes deste arquivo existir, um problema encontrado no meio do caminho tinha só dois destinos: virar
trabalho **agora** (uma plan nova, um ciclo inteiro) ou se perder. Como a doutrina proíbe perder, tudo
virava trabalho — e cada execução gerava as próximas, sem caso-base. Este arquivo é o caso-base.

**Um item aqui não é uma plan.** Não tem `NN`, não tem status, não entra em fila, ninguém o executa. É uma
linha dizendo *"isto existe e alguém olhou"*. Só vira trabalho quando **o usuário** manda — e aí passa pela
triagem normal ([[00-prompt-revisor]] §4) como qualquer outra demanda.

**Quem escreve:** o **revisor**, sempre. O executor **relata** achados no resumo dele (é o formato da
[[00-prompt-executor]] §5); quem transcreve para cá é o revisor, no veredito.
**Quem promove:** só o **usuário**. Nenhum agente decide sozinho que chegou a hora de um item.
**Quem remove:** quem promoveu (o item sai daqui quando vira plan ou prompt direto) — ou o revisor, ao
registrar um achado novo (§4), quando encontra um antigo que deixou de valer. O usuário pode podar a
qualquer momento.

---

# 1. A regra que este arquivo sustenta

> **Achado descoberto durante a execução da plan-N não vira trabalho antes da plan-N fechar.**

Sem exceção. Ele desce para cá, e o ciclo em andamento termina primeiro. Isso é o que impede o aninhamento:
uma execução nunca abre outra execução por dentro.

Três coisas alimentam este arquivo:

| Origem | Quem traz | Quando |
|---|---|---|
| Achado fora do escopo | executor, no resumo | o revisor transcreve no veredito |
| Divergência entre spec fixa e código | revisor, no ritual de entrada | ao encontrar |
| Ressalva relevante que não reprova a execução | revisor, no veredito | ao aprovar |

**Nada aqui é urgente por estar aqui.** Se um achado é grave a ponto de não poder esperar, ele não é backlog
— é uma demanda que o revisor leva ao usuário na hora, em texto livre, e que vira plan ou prompt direto pela
via normal.

---

# 2. A tabela

> **Como escrever:** uma linha por achado, e **uma linha só**. Se você precisa de um parágrafo, o item não é
> achado — é uma demanda; leve ao usuário.
>
> - **#** — sequencial simples. Reaproveitável: sai um, o número volta a ficar livre. Isto **não** é `plan-FF.NN`.
> - **Achado** — o que há de errado, em uma frase, com `arquivo:linha` quando existir.
> - **Origem** — `execução`, `via direta` ou `ritual`. **Nunca `plan-FF.NN`**: a plan é removida na síntese e a
>   referência morre. Saber que o achado veio de uma execução basta; de qual plan, não ajuda depois que ela sai.
> - **Registrado em** — data absoluta (`AAAA-MM-DD`).
> - **Peso** — `alto` · `médio` · `baixo`. É uma dica ao usuário, não uma fila: nada aqui é agendado.

| # | Achado | Origem | Registrado em | Peso |
|---|---|---|---|---|
| 1 | `ruff check .` falha em `.githooks/verify_commit.py:204` (E731, arquivo vindo da base) e os critérios das plans 04.03 e 05.01 usam `ruff check .`; falta um `ruff.toml` do repositório que fixe as regras e exclua `.githooks/` | execução | 2026-11-09 | médio |
| 2 | `pip install -r requirements-dev.txt` falha no Windows em ambiente virtual com caminho longo (jupyterlab, "Long Path support"); passou em caminho curto — registrar no README de entrega | execução | 2026-11-09 | baixo |
| 3 | `sanitizer.py:36-38` — `MAX_TEXT_LENGTH` é checado no texto bruto antes da normalização NFKC, que pode expandir caracteres (ex.: `ﷺ` vira 18 caracteres): o texto sanitizado pode passar de 2000, e quem consumir `Request.text` não deve presumir esse teto | execução | 2026-11-09 | baixo |
| 4 | `privacy/patterns.py` — formas raras deixam resíduo: DDD com zero (`011 91234-5678` → `011 [TELEFONE]`) e e-mail com letra acentuada na parte local (`joão@exemplo.com` → `joã[EMAIL]`); `4 dígitos-4 dígitos` como protocolo (`2024-1234`) vira `[TELEFONE]` (precisão aceita a favor da garantia) | execução | 2026-11-09 | baixo |
| 5 | `tests/storage/test_hashing.py:13` — `test_hash_ignores_unicode_composition` compara "ã" composto com "a" + acento combinante, indistinguíveis no editor; escrever as duas formas com escapes Unicode para a intenção ficar legível | execução | 2026-11-09 | baixo |
| 6 | `requirements.txt` — `joblib` é importado direto em `classification/model.py` mas não está fixado (vem de transitiva do scikit-learn), e o ambiente local roda scikit-learn 1.8.0 contra o 1.9.1 fixado; modelo `.joblib` treinado numa versão pode não carregar em outra | execução | 2026-11-09 | baixo |
| 7 | `.env.example` não lista `CONFIDENCE_MIN` e `AMBIGUITY_MARGIN`, lidos por `config.py` | execução | 2026-11-09 | baixo |
| 8 | `automation/link_check.py:38-40` — `requests` segue redirecionamentos e a URL final não é validada contra a allowlist: uma URL `gov.br` que redirecione para fora do domínio passa no `check_link` | execução | 2026-11-09 | médio |
| 9 | `data/catalog.json` — `birth_certificate` aponta para uma notícia de 2021 (o `gov.br/mdh` recusa o cliente `requests`) e `voter_id` e `property_tax` para o hub genérico `gov.br/pt-br/servicos` e `tse.jus.br` está fora da allowlist; decisão do usuário: incluir `tse.jus.br` e uma URL específica de título de eleitor, ou manter o hub | execução | 2026-11-09 | baixo |
| 12 | `pipeline/processor.py` (`_store`) — `save_request` e `enqueue_review` são duas transações: se a fila falhar de forma persistente depois de o pedido ser gravado, a segunda execução o vê como duplicado e o caminho seguro (`route_to_safe_review`) não o enfileira, então ele some da revisão | execução | 2026-11-10 | médio |
| 13 | `classification/model.py` (`DEFAULT_MODEL_PATH`) — o modelo é lido de `output/models/` relativo à pasta atual e ignora `--output`; sem `scripts/train_model.py` antes, o `run.py` encaminha tudo à revisão (`low_confidence`); documentar o passo no README de entrega | execução | 2026-11-10 | baixo |
| 14 | `python -m ruff check run.py src tests` com o ruff 0.17.4 fixado acusa 9 erros em arquivos de plans anteriores (I001 em `sanitizer.py`, `test_decision.py`, `test_model.py`, `test_sanitizer.py` e `test_repository.py`; UP033 em `allowlist.py` e `urgency.py`; UP017 em `repository.py`; SIM117 em `test_repository.py:143`), 8 corrigíveis com `--fix` | execução | 2026-11-10 | baixo |
| 15 | `pipeline/processor.py` (`process_request`) — pedido repetido volta como `skipped_duplicate` sem texto de resposta, então a interface só diz "já registrado"; oferecer um modo que devolva a resposta já decidida sem regravar | execução | 2026-11-10 | baixo |
| 16 | `interface/service.py` (`send_feedback`) — "uma avaliação por resposta" é controlada só em memória do serviço: reiniciar o app permite avaliar de novo o mesmo pedido, e o storage aceita feedbacks repetidos para o mesmo hash | execução | 2026-11-10 | baixo |
| 17 | `privacy/names.py` — prenome da lista dentro de nome de lugar vira falso positivo (`Vila Madalena` → `Vila [NOME]`); estender os prefixos de topônimo (vila, jardim, parque, bairro) | execução | 2026-11-10 | baixo |
| 18 | `docs/quadro-de-temas.md` ainda diz que a anonimização cobre só CPF, telefone e e-mail; atualizar para os nove tipos | revisão | 2026-11-10 | baixo |
| 19 | `automation/resolver.py` — `resolve_entry` não confere `status`: uma entrada `candidate` passada diretamente é entregue; checar `approved` também ali | revisão | 2026-11-10 | médio |
| 20 | `data/urgency_terms.json` — o léxico casa frases exatas: `dor muito forte no peito` e `dificuldade em respirar` não são urgentes; 6 pedidos `urgent=1` do CSV (L031, L052, L125, L131, L150, L178) nunca foram detectados por léxico | revisão | 2026-11-10 | médio |
| 21 | `data/labeled/README.md` ainda descreve 180 pedidos, 20 por categoria e a divisão 14 train / 6 test; o CSV tem 418 linhas (40 ou mais de treino por categoria) | revisão | 2026-11-10 | baixo |
| 22 | `classification/rules.py` — o marcador `[CPF]` aciona a regra de CPF mesmo quando o assunto é outro: L372 (certidão de nascimento) e L409 (nota fiscal) têm rótulo diferente da regra, e em uso a regra única vence o modelo; medir se a regra de CPF deve exigir o assunto e não só o marcador | revisão | 2026-11-10 | médio |
| 23 | `AMBIGUITY_MARGIN=0,15` é inerte com `CONFIDENCE_MIN` ≥ 0,60 (a folga mínima já é 0,20); a validação cruzada deu resultado idêntico de 0,05 a 0,25. Escrever isso em `02.02` ou rever o papel do parâmetro | revisão | 2026-11-10 | baixo |
| 24 | `notebooks/evidence.ipynb`, seção 6 (limites) ainda diz "São 8 serviços curados à mão" (o catálogo tem 51 entradas aprovadas) e as células 0 e 6 dizem que o LLM "só reformula" (agora ele redige sobre as fontes do catálogo); atualizar quando os números do piloto fecharem | revisão | 2026-11-10 | baixo |
| 25 | `automation/finder.py` — o localizador cobre 47,9% do teste e erra 3 de 18 pedidos sem fonte; entradas sobrepostas (certidão, título de eleitor, INSS) derrubam a folga e dão `None`, e ele não distingue cidade ou estado (IPVA do Rio devolve a fonte de SP); ampliar a amostra e rever `keywords` das entradas duplicadas | revisão | 2026-11-10 | médio |
| 26 | `automation/messages.py` — a mensagem de emergência lista os 6 canais de `safety` na ordem do catálogo (190, 193, 192, 199, 100, 180); para um pedido de saúde (o léxico de urgência é só de saúde) o SAMU 192 devia vir primeiro, e 100 e 180 são ruído; decidir se a lista se ordena ou se filtra por tipo de urgência | revisão | 2026-11-10 | médio |

---

# 3. Promover um item

Só o usuário dispara. Ao promover, o **revisor**:

1. Tria o item pela [[00-prompt-revisor]] §4 — plan se deixa verdade documentada, prompt direto se não.
2. Conduz a via escolhida como qualquer outra demanda.
3. **Remove a linha daqui**, na mesma ação. Item promovido não fica de lembrança: a partir daí quem responde
   por ele é o [[00-indice]] (se virou plan) ou a própria conversa (se virou prompt direto).

Promover **não** é obrigatório e não tem prazo. Um item pode ficar aqui indefinidamente sem que isso seja
dívida — é exatamente para isso que ele existe.

---

# 4. Regras de manutenção

- **Este arquivo não cresce sem limite, e o dreno tem gatilho.** Ele registra o que **ainda** é verdade.
  **Ao registrar um achado, o revisor relê os que já estão aqui** — é a única vez em que alguém abre o
  arquivo inteiro, e por isso é onde ele se drena. Achado corrigido de passagem por outra tarefa, código que
  deixou de existir, problema que a spec fixa passou a permitir: a linha **sai** na mesma ação, e o revisor
  diz isso na resposta. Regra de limpeza sem gatilho não roda — foi assim que o índice virou cemitério.
- **Não duplique.** Antes de registrar, procure — o mesmo achado visto em duas execuções é uma linha só.
- **Sem status, sem dono, sem prazo.** Se você sentiu falta de um desses campos, o item não é backlog: é
  plan. Promova ou deixe.
- **Nunca referencie um item daqui dentro do código.** Vale a mesma regra da plan: comentário não cita
  `backlog #3` (norma completa em `padrao-escrita`, `references/comentarios.md`).
- **Item que já está numa plan não fica aqui.** Um dos dois é a verdade — e é o [[00-indice]].
| 27 | `automation/llm_client.py` — `OpenAICompatibleClient` aceita `models` vazio e `complete` levanta `TypeError` (`raise None`), calado por `type: ignore[misc]`; inalcançável pela fábrica, mas a classe é pública: validar na construção com erro próprio | revisão | 2026-11-10 | baixo |
| 28 | `automation/catalog.py` e `allowlist.py` — os caminhos de `data/catalog.json` e `data/allowed_domains.json` são relativos ao diretório corrente (o `app.py` rodado de outra pasta sobe sem catálogo e manda tudo à revisão), enquanto `config/settings.json` já é localizado a partir do módulo; localizar os dados do mesmo jeito; o mesmo vale para `data/urgency_terms.json` (fora da raiz `is_urgent` marca urgente em silêncio e o CSV exportado sai com `urgent=1`) e para a pasta fixa `output/exports` da tela de revisão | revisão | 2026-11-11 | baixo |
| 29 | `automation/catalog.py` — o log de registro inválido imprime o registro inteiro; com `content` de até 3000+ caracteres a linha de log fica enorme: logar só o `id` e o motivo | revisão 03.12 | 2026-11-11 | baixo |
| 30 | `data/agents/triage-assistant/{rules,workflow}.md` — não citam o campo `Conteúdo:` nem o bloco `CONVERSA ANTERIOR` das fontes; vale reforçar que o LLM deve usar o conteúdo e só ele quando a base tiver `content` (promover se o usuário preencher `content`) | revisão 03.12 | 2026-11-11 | médio |
| 31 | `pipeline/processor.py` `_gap_rag` — toma as `max_candidates` primeiras candidatas e só depois descarta as de link morto (`_live_entries`): com a base importada (29 links mortos) elas ocupam vagas e o LLM pode ficar com menos fontes ou nenhuma; verificar a vivacidade até completar `max_candidates` vivas | revisão 03.14 | 2026-11-11 | médio |
| 32 | `interface/` — a categoria da interação e a tag `needs_human` (plan 04.06) só aparecem no CSV e no relatório; a aba Revisão e uma visão de interações por categoria poderiam mostrá-las (promover se o usuário quiser na demonstração) | planejamento 04.06 | 2026-11-12 | baixo |
| 33 | `interface/service.py` `export_labeled` — não neutraliza célula iniciada em `=`, `+`, `-` ou `@` (injeção de fórmula ao abrir o CSV numa planilha); o CSV de interações já neutraliza com um apóstrofo, e o mesmo tratamento caberia aqui | revisão 04.06 | 2026-11-12 | baixo |
| 34 | `tests/` sem `__init__.py` — dois testes com o mesmo nome de arquivo em pastas diferentes quebram a coleta do pytest; nomear os arquivos de teste de forma única ou adotar `__init__.py` | revisão 04.06 | 2026-11-12 | baixo |
| 35 | `data/interaction_topics.json` — o vocabulário não tem "trabalho e emprego" (seguro-desemprego, MEI, FGTS): na execução do notebook o LLM respondeu fora da lista para o seguro-desemprego e a guarda caiu no classificador (`other`); vale uma categoria `work` com a `area` correspondente no catálogo | revisão 05.02 | 2026-11-12 | baixo |
| 36 | `config/settings.json` `llm.model` — o modelo principal (`deepseek/deepseek-v4-flash`) devolveu "conteúdo vazio ou não textual" várias vezes no notebook e o cliente passou aos alternativos; cada falha soma segundos ao chat (o lote de 8 pedidos levou 77 s): avaliar a ordem dos modelos ou a estabilidade do principal | revisão 05.02 | 2026-11-12 | médio |
