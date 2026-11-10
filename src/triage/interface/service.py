"""Serviço da interface: orquestra o núcleo para as telas, sem regra de negócio própria."""

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from triage.config import Settings
from triage.ingestion import Request, sanitize
from triage.ingestion.sanitizer import TextTooLargeError, validate
from triage.pipeline import Deps, build_deps, process_request
from triage.pipeline.processor import (
    STATUS_ANSWERED,
    STATUS_QUEUED_FOR_REVIEW,
    STATUS_SKIPPED_DUPLICATE,
)
from triage.privacy import anonymize
from triage.storage import StorageError, request_hash
from triage.storage.schema import RATING_DOWN, RATING_UP, VALID_RATINGS

logger = logging.getLogger("triage.interface")

REQUEST_SOURCE = "interface"
KIND_ANSWERED = "answered"
KIND_HUMAN_REVIEW = "human_review"
KIND_DUPLICATE = "duplicate"
KIND_INVALID = "invalid"
KIND_ERROR = "error"
MESSAGE_HUMAN_REVIEW = "Encaminhamos seu pedido para atendimento humano."
MESSAGE_DUPLICATE = "Este pedido já foi registrado."
MESSAGE_INVALID = "Não foi possível ler seu pedido. Descreva o que você precisa em uma frase completa."
MESSAGE_TOO_LARGE = "Seu pedido é muito longo. Resuma-o e envie de novo."
MESSAGE_ERROR = "Não foi possível registrar seu pedido agora. Tente novamente em instantes."


@dataclass(frozen=True)
class SubmitOutcome:
    """O que a tela mostra após um envio; `request_hash` só existe quando o pedido foi respondido (feedback)."""

    kind: str
    message: str
    request_hash: str | None = None


@dataclass(frozen=True)
class ReviewEntry:
    """Item da fila de revisão com os dados do pedido; o texto é sempre o anonimizado."""

    id: int
    reason: str
    created_at: str
    category: str | None
    confidence: float | None
    anonymized_text: str


def build_service(settings: Settings, db_path: str | Path) -> "AppService":
    """Monta o serviço com as dependências reais; banco inacessível levanta `StorageError`."""
    return AppService(build_deps(settings, db_path))


class AppService:
    """Operações das telas Cidadão e Revisão sobre o pipeline e o storage."""

    def __init__(self, deps: Deps) -> None:
        self._deps = deps
        self._rated: set[str] = set()

    def submit(self, text: str) -> SubmitOutcome:
        """Sanitiza e processa o pedido; nunca levanta exceção para a tela."""
        request = self._build_request(text)
        if isinstance(request, SubmitOutcome):
            return request
        try:
            result = process_request(request, self._deps)
        except Exception as error:  # noqa: BLE001 - a tela mostra mensagem amigável, nunca traceback
            logger.error("Falha ao processar pedido da interface (%s)", type(error).__name__)
            return SubmitOutcome(KIND_ERROR, MESSAGE_ERROR)
        return self._outcome_from(result.status, result.response_text, request.text)

    def pending_reviews(self) -> list[ReviewEntry]:
        """Fila pendente completada com categoria, confiança e texto anonimizado de cada pedido."""
        entries = []
        for item in self._deps.repository.pending_reviews():
            record = self._deps.repository.get_request(item.request_hash)
            entries.append(
                ReviewEntry(
                    item.id,
                    item.reason,
                    item.created_at,
                    record.category if record else None,
                    record.confidence if record else None,
                    record.anonymized_text if record else "",
                )
            )
        return entries

    def resolve(self, review_id: int, note: str) -> bool:
        """Marca o item como resolvido; `False` se ele não existe ou já foi resolvido."""
        return self._deps.repository.resolve_review(review_id, note.strip())

    def send_feedback(self, request_hash: str, rating: str) -> bool:
        """Grava a avaliação uma única vez por pedido; repetida, inválida ou com falha de banco devolve `False`."""
        if rating not in VALID_RATINGS or request_hash in self._rated:
            return False
        try:
            self._deps.repository.add_feedback(request_hash, rating)
        except StorageError:
            return False
        self._rated.add(request_hash)
        return True

    @staticmethod
    def _build_request(text: str) -> Request | SubmitOutcome:
        try:
            cleaned = sanitize(text)
        except TextTooLargeError:
            return SubmitOutcome(KIND_INVALID, MESSAGE_TOO_LARGE)
        request = Request(uuid.uuid4().hex, cleaned, REQUEST_SOURCE)
        if validate(request) is not None:
            return SubmitOutcome(KIND_INVALID, MESSAGE_INVALID)
        return request

    @staticmethod
    def _outcome_from(status: str, response_text: str | None, sanitized_text: str) -> SubmitOutcome:
        if status == STATUS_ANSWERED and response_text:
            return SubmitOutcome(KIND_ANSWERED, response_text, request_hash(anonymize(sanitized_text).text))
        if status == STATUS_QUEUED_FOR_REVIEW:
            return SubmitOutcome(KIND_HUMAN_REVIEW, MESSAGE_HUMAN_REVIEW)
        if status == STATUS_SKIPPED_DUPLICATE:
            return SubmitOutcome(KIND_DUPLICATE, MESSAGE_DUPLICATE)
        return SubmitOutcome(KIND_ERROR, MESSAGE_ERROR)


__all__ = ["RATING_DOWN", "RATING_UP", "AppService", "ReviewEntry", "SubmitOutcome", "build_service"]
