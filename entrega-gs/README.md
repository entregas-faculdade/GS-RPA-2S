# Entrega: Global Solution 2026.2 (AI for RPA)

Robô de triagem de pedidos de serviços públicos. Este guia aponta cada entregável do enunciado
([docs/enunciado-gs-2026-2-rpa-ia.pdf](../docs/enunciado-gs-2026-2-rpa-ia.pdf), seção 5).

## Integrantes

- Igor Paixão Sarak (RM 563726)
- Lucca Phelipe Masini (RM 564121)
- Bernardo Braga Perobeli (RM 562468)

## O problema

Muita gente não sabe a qual órgão recorrer para tirar a CNH, atualizar o título de eleitor ou consultar um benefício
do INSS, e acaba perdida entre sites diferentes. O robô atende o cidadão que descreve o que precisa em uma frase: lê o
pedido, anonimiza os dados pessoais, descobre o assunto e responde com o link oficial do serviço, ou encaminha o pedido
a uma fila de revisão humana quando não tem segurança para responder. O recorte é o piloto do estado e da capital de
São Paulo, mais as fontes federais.

## Entregáveis

| Entregável do enunciado | Onde está |
|---|---|
| Código | [run.py](../run.py) (robô em lote), [app.py](../app.py) (interface Streamlit), [src/](../src/) |
| README | este arquivo e o [README.md](../README.md) da raiz (instalação, configuração, resultados) |
| Quadro de temas | [quadro-de-temas.md](quadro-de-temas.md) |
| Evidências | [evidencias/evidence.ipynb](evidencias/evidence.ipynb) (notebook já executado, com as saídas salvas) |
| Parágrafo de dados, ética e ODS | [etica-dados-ods.md](etica-dados-ods.md) |

## Como executar

Requisitos: Python (verificado com 3.14) e internet. Comandos para o PowerShell, na raiz do repositório:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env        # depois preencha LLM_API_KEY no .env (opcional)
python scripts/train_model.py
python run.py --input data/samples
python -m streamlit run app.py
```

## Como configurar a chave

O `.env` guarda só a `LLM_API_KEY`, e ela é opcional. Sem chave, o robô funciona do mesmo jeito, em modo
determinístico (texto-modelo do catálogo e regras). Detalhes em [../README.md](../README.md#como-configurar-as-chaves).

## Avaliação em 5 minutos

1. Rode `python run.py --input data/samples --no-llm` (depois de `python scripts/train_model.py`).
2. Abra o notebook [evidencias/evidence.ipynb](evidencias/evidence.ipynb): as saídas já estão salvas.
3. Abra o [quadro de temas](quadro-de-temas.md).
