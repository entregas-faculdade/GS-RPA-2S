"""Cliente de LLM genérico, compatível com a API de chat no formato OpenAI (`/chat/completions`)."""

import logging
from typing import Protocol

import requests

from triage.agent import (
    AgentDefinition,
    AgentError,
    compose_system_prompt,
    lint_agent,
    load_agent,
)
from triage.automation.link_check import SERVER_ERROR_MIN, TransientHttpError
from triage.common.retry import RetryPolicy, retry_with_backoff
from triage.config import Settings

CLIENT_ERROR_MIN = 400
CHAT_PATH = "/chat/completions"
TRANSIENT_ERRORS = (requests.Timeout, requests.ConnectionError, TransientHttpError)

logger = logging.getLogger("triage.automation")


class LlmUnavailable(Exception):
    """Falha de rede ou HTTP persistente: o provedor não respondeu de forma utilizável."""


class LlmInvalidResponse(Exception):
    """O provedor respondeu, mas sem conteúdo aproveitável (JSON inválido, sem `choices`, texto vazio)."""


class LlmClient(Protocol):
    """Contrato mínimo do cliente: executa uma tarefa do agente sobre a mensagem e devolve o texto."""

    def complete(self, task: str, user_message: str) -> str: ...


def _extract_content(payload: object) -> str:
    """Tira o texto de `choices[0].message.content`; qualquer outro formato é `LlmInvalidResponse`."""
    try:
        content = payload["choices"][0]["message"]["content"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as error:
        raise LlmInvalidResponse("resposta sem choices/message/content") from error
    if not isinstance(content, str) or not content.strip():
        raise LlmInvalidResponse("conteúdo vazio ou não textual")
    return content.strip()


class OpenAICompatibleClient:
    """Chama `{base_url}/chat/completions` com o agente; a chave só viaja no header `Authorization`.

    `models` é o modelo principal seguido dos alternativos, tentados nesta ordem quando um falha.
    """

    def __init__(self, base_url: str, api_key: str, models: tuple[str, ...], agent: AgentDefinition) -> None:
        self._url = base_url.rstrip("/") + CHAT_PATH
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._models = models
        self._agent = agent
        self._retry_policy = RetryPolicy(
            attempts=agent.params.attempts,
            base_delay=agent.params.base_delay_seconds,
            max_delay=agent.params.max_delay_seconds,
            transient=TRANSIENT_ERRORS,
        )

    def _post(self, model: str, system_prompt: str, user_message: str) -> object:
        """Uma tentativa: 5xx é transitório (repete); 4xx é definitivo; corpo não JSON é resposta inválida."""
        params = self._agent.params
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            "temperature": params.temperature,
            "max_tokens": params.max_tokens,
        }
        response = requests.post(self._url, headers=self._headers, json=body, timeout=params.timeout_seconds)
        if response.status_code >= SERVER_ERROR_MIN:
            raise TransientHttpError(response.status_code)
        if response.status_code >= CLIENT_ERROR_MIN:
            raise LlmUnavailable(f"HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as error:
            raise LlmInvalidResponse("corpo da resposta não é JSON") from error

    def _complete_with(self, model: str, system_prompt: str, user_message: str) -> str:
        try:
            payload = retry_with_backoff(lambda: self._post(model, system_prompt, user_message), self._retry_policy)
        except (requests.RequestException, TransientHttpError) as error:
            raise LlmUnavailable(type(error).__name__) from error
        return _extract_content(payload)

    def complete(self, task: str, user_message: str) -> str:
        """Devolve o texto da tarefa ou levanta `LlmUnavailable` / `LlmInvalidResponse` quando todos os modelos falham."""
        system_prompt = compose_system_prompt(self._agent, task)
        last_error: LlmUnavailable | LlmInvalidResponse | None = None
        for index, model in enumerate(self._models):
            try:
                return self._complete_with(model, system_prompt, user_message)
            except (LlmUnavailable, LlmInvalidResponse) as error:
                last_error = error
                logger.warning("Modelo %s (%d/%d) falhou: %s", model, index + 1, len(self._models), error)
        raise last_error  # type: ignore[misc]  # `models` nunca é vazio: o cliente só nasce com o modelo principal


def _load_valid_agent(agent_id: str) -> AgentDefinition | None:
    """Agente validado pelo linter e carregado; qualquer defeito é registrado (sem prompt) e devolve `None`."""
    problems = lint_agent(agent_id)
    if problems:
        logger.error("Agente LLM '%s' inválido (%s); LLM desligado, o template responde", agent_id, "; ".join(problems))
        return None
    try:
        return load_agent(agent_id)
    except AgentError as error:
        logger.error("Agente LLM '%s' não carregou (%s); LLM desligado, o template responde", agent_id, error)
        return None


def build_llm_client(settings: Settings) -> LlmClient | None:
    """Cliente só com o LLM habilitado, configurado por completo e com agente válido; senão `None`."""
    if not settings.llm_enabled:
        return None
    if not (settings.llm_base_url and settings.llm_model and settings.llm_api_key):
        logger.warning("LLM habilitado, mas LLM_BASE_URL, LLM_MODEL ou LLM_API_KEY está vazio; usando o template")
        return None
    agent = _load_valid_agent(settings.llm_agent_id)
    if agent is None:
        return None
    models = (settings.llm_model, *settings.llm_fallback_models)
    return OpenAICompatibleClient(settings.llm_base_url, settings.llm_api_key, models, agent)
