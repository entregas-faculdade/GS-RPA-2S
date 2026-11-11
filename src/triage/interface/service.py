"""Serviço da interface: orquestra o núcleo para as telas, sem regra de negócio própria."""

import csv
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from triage.classification import is_urgent
from triage.classification.decision import OTHER_LABEL
from triage.classification.rules import CATEGORY_RULES
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
from triage.storage import LabeledRequest, StorageError, request_hash
from triage.storage.schema import RATING_DOWN, RATING_UP, VALID_RATINGS

logger = logging.getLogger("triage.interface")

REQUEST_SOURCE = "interface"
KIND_ANSWERED = "answered"
KIND_HUMAN_REVIEW = "human_review"
KIND_DUPLICATE = "duplicate"
KIND_INVALID = "invalid"
KIND_ERROR = "error"
EXPORT_COLUMNS = ("id", "text", "label", "split", "urgent")
EXPORT_SPLIT = "train"
EXPORT_ID_PREFIX = "R"
EXPORT_ID_LENGTH = 12
EXPORT_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S"
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

    @staticmethod
    def label_options() -> tuple[str, ...]:
        """As categorias que o revisor pode informar: as do catálogo mais `other`."""
        return (*CATEGORY_RULES, OTHER_LABEL)

    def resolve(self, review_id: int, note: str, category: str | None = None) -> bool:
        """Marca o item como resolvido, gravando antes a categoria correta quando ela vem.

        Categoria fora das opções, item inexistente ou falha de banco devolvem `False` sem resolver.
        """
        if category is not None and not self._label_review(review_id, category):
            return False
        try:
            return self._deps.repository.resolve_review(review_id, note.strip())
        except StorageError:
            return False

    def export_labeled(self, directory: str | Path) -> Path | None:
        """Grava os pedidos rotulados (texto anonimizado) em CSV; `None` sem rótulos ou com falha."""
        try:
            labeled = self._deps.repository.labeled_requests()
            if not labeled:
                return None
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime(EXPORT_TIMESTAMP_FORMAT)
            path = target / f"labeled_{stamp}.csv"
            self._write_export(path, labeled)
        except (StorageError, OSError) as error:
            logger.error("Falha ao exportar pedidos rotulados (%s)", type(error).__name__)
            return None
        return path

    @staticmethod
    def _write_export(path: Path, labeled: list[LabeledRequest]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(EXPORT_COLUMNS)
            for item in labeled:
                row_id = EXPORT_ID_PREFIX + item.request_hash[:EXPORT_ID_LENGTH]
                urgent = int(is_urgent(item.anonymized_text))
                writer.writerow((row_id, item.anonymized_text, item.category, EXPORT_SPLIT, urgent))

    def _label_review(self, review_id: int, category: str) -> bool:
        if category not in self.label_options():
            return False
        try:
            for item in self._deps.repository.pending_reviews():
                if item.id == review_id:
                    self._deps.repository.set_label(item.request_hash, category)
                    return True
        except StorageError:
            return False
        return False

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
            return SubmitOutcome(KIND_HUMAN_REVIEW, response_text or MESSAGE_HUMAN_REVIEW)
        if status == STATUS_SKIPPED_DUPLICATE:
            return SubmitOutcome(KIND_DUPLICATE, MESSAGE_DUPLICATE)
        return SubmitOutcome(KIND_ERROR, MESSAGE_ERROR)


__all__ = ["RATING_DOWN", "RATING_UP", "AppService", "ReviewEntry", "SubmitOutcome", "build_service"]
