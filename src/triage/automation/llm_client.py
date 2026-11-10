"""Cliente de LLM genérico, compatível com a API de chat no formato OpenAI (`/chat/completions`)."""

import logging
from typing import Protocol

import requests

from triage.automation.link_check import SERVER_ERROR_MIN, TransientHttpError
from triage.common.retry import RetryPolicy, retry_with_backoff
from triage.config import Settings

REQUEST_TIMEOUT_SECONDS = 15.0
RETRY_ATTEMPTS = 2
RETRY_BASE_DELAY_SECONDS = 1.0
RETRY_MAX_DELAY_SECONDS = 4.0
SAMPLING_TEMPERATURE = 0.2
CLIENT_ERROR_MIN = 400
CHAT_PATH = "/chat/completions"

DEFAULT_RETRY_POLICY = RetryPolicy(
    attempts=RETRY_ATTEMPTS,
    base_delay=RETRY_BASE_DELAY_SECONDS,
    max_delay=RETRY_MAX_DELAY_SECONDS,
    transient=(requests.Timeout, requests.ConnectionError, TransientHttpError),
)

logger = logging.getLogger("triage.automation")


class LlmUnavailable(Exception):
    """Falha de rede ou HTTP persistente: o provedor não respondeu de forma utilizável."""


class LlmInvalidResponse(Exception):
    """O provedor respondeu, mas sem conteúdo aproveitável (JSON inválido, sem `choices`, texto vazio)."""


class LlmClient(Protocol):
    """Contrato mínimo do cliente: recebe um prompt e devolve o texto reformulado."""

    def rewrite(self, prompt: str) -> str: ...


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
    """Chama `{base_url}/chat/completions`; a chave só viaja no header `Authorization`."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    ) -> None:
        self._url = base_url.rstrip("/") + CHAT_PATH
        self._model = model
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._retry_policy = retry_policy

    def _post(self, prompt: str) -> object:
        """Uma tentativa: 5xx é transitório (repete); 4xx é definitivo; corpo não JSON é resposta inválida."""
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": SAMPLING_TEMPERATURE,
        }
        response = requests.post(self._url, headers=self._headers, json=body, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code >= SERVER_ERROR_MIN:
            raise TransientHttpError(response.status_code)
        if response.status_code >= CLIENT_ERROR_MIN:
            raise LlmUnavailable(f"HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as error:
            raise LlmInvalidResponse("corpo da resposta não é JSON") from error

    def rewrite(self, prompt: str) -> str:
        """Devolve o texto reformulado ou levanta `LlmUnavailable` / `LlmInvalidResponse`."""
        try:
            payload = retry_with_backoff(lambda: self._post(prompt), self._retry_policy)
        except (requests.RequestException, TransientHttpError) as error:
            raise LlmUnavailable(type(error).__name__) from error
        return _extract_content(payload)


def build_llm_client(settings: Settings) -> LlmClient | None:
    """Cliente só com o LLM habilitado e configurado por completo; senão `None` (o template responde)."""
    if not settings.llm_enabled:
        return None
    if not (settings.llm_base_url and settings.llm_model and settings.llm_api_key):
        logger.warning("LLM habilitado, mas LLM_BASE_URL, LLM_MODEL ou LLM_API_KEY está vazio; usando o template")
        return None
    return OpenAICompatibleClient(settings.llm_base_url, settings.llm_model, settings.llm_api_key)
