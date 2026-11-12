# Quadro de temas

Temas da disciplina *AI for RPA* usados no robô de triagem de pedidos de serviços públicos e a função de cada um
no fluxo (sanitização e anonimização → classificação → resposta ou revisão humana).

| Tema | O que é | Onde entra no fluxo | O que resolve |
|---|---|---|---|
| **Automação / RPA** | Robô que executa uma tarefa de ponta a ponta sem intervenção: leitura de pasta, agendamento, retry com espera, idempotência e relatório de execução. | Todo o pipeline (`triage.pipeline`, `run.py`): lê os arquivos, processa cada pedido isoladamente, repete o que falha por motivo transitório, cataloga cada interação (categoria e tag `needs_human`) e grava o relatório e o CSV da execução. | Tira o atendimento manual de pedidos repetitivos; uma falha em um pedido ou arquivo não derruba os demais; rodar duas vezes a mesma pasta não duplica nada. |
| **NLP** | Processamento de linguagem natural: normalização do texto e vetorização TF-IDF com um classificador (regressão logística). | Etapa 2 (`triage.classification`): limpa o texto (minúsculas, sem acento, sem stopwords) e estima a probabilidade de cada serviço. | Descobre de qual serviço o cidadão está falando mesmo com frases livres, informais ou com erro de digitação, e fornece a confiança que decide entre responder e pedir revisão. |
| **Regras / regex** | Expressões regulares e listas de termos escritas à mão. | Etapas 1 e 2: sanitização da entrada (HTML, caracteres de controle, tamanho) e atalho por palavra-chave (CNH, CPF, IPTU etc.) mais léxico de urgência. | Barra entrada maliciosa ou malformada, dá resposta rápida e inequívoca quando o assunto é explícito e manda à revisão humana pedidos de emergência. |
| **Anonimização de PII** | Substituição de dados pessoais por marcadores antes de qualquer uso do texto. | Etapa 1 (`triage.privacy`): CPF, telefone e e-mail viram `[CPF]`, `[TELEFONE]` e `[EMAIL]` antes de classificar, gravar, logar ou enviar a um LLM. | Garante que dado pessoal não chegue ao log, ao banco nem a uma API externa (LGPD); o classificador só vê texto anonimizado. |

**Por que esta combinação.** O problema é encaminhar o cidadão ao serviço público certo sem arriscar um link errado
nem expor dado pessoal. Regras resolvem o óbvio com custo zero e são auditáveis; NLP cobre a linguagem livre que
as regras não alcançam e mede a própria confiança; a anonimização vem antes de tudo para que nenhuma etapa
posterior manipule dado pessoal; e a automação amarra as etapas com resiliência (retry, isolamento de falha,
relatório) e com a revisão humana para o que o robô não resolve. Governança é o eixo transversal: allowlist de
domínios, fila de revisão e um LLM opcional, que **redige a resposta** sobre fontes aprovadas do catálogo e **escolhe a
categoria da interação** numa lista fechada, sempre sobre texto anonimizado e sob uma guarda de saída (link e telefone só
das fontes enviadas, categoria só da lista). O LLM não classifica o pedido, não decide se ele é respondido nem escolhe
URL; sem ele, o texto-modelo e as regras fazem o mesmo trabalho.

Medição e casos de falha de cada tema: [evidencias/evidence.ipynb](evidencias/evidence.ipynb).
