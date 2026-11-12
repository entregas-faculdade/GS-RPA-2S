"""Categoria de catalogação da interação: o LLM escolhe sobre um vocabulário fechado; sem ele, regras determinísticas."""

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from triage.automation.catalog import ServiceEntry
from triage.automation.llm_client import LlmClient, LlmInvalidResponse, LlmUnavailable
from triage.automation.rag import (
    DELIMITERS,
    HISTORY_CLOSE,
    HISTORY_OPEN,
    REQUEST_CLOSE,
    REQUEST_OPEN,
)
from triage.classification.decision import OTHER_LABEL
from triage.classification.rules import CATEGORY_RULES

TOPICS_PATH = Path(__file__).resolve().parents[3] / "data" / "interaction_topics.json"
CATEGORIZE_TASK = "categorize"
OTHER_TOPIC = "other"
SAFETY_TOPIC = "safety"
SOURCE_LLM = "llm"
SOURCE_CATALOG = "catalog"
SOURCE_CLASSIFIER = "classifier"
SOURCE_RULE = "rule"
SOURCE_NONE = "none"
CATEGORIES_HEADER = "CATEGORIAS"
OUTPUT_NOISE = " \t\r\n\"'`“”‘’."
REJECTION_NOT_A_TOPIC = "not_a_topic"

logger = logging.getLogger("triage.automation")


class TopicsError(Exception):
    """O vocabulário de categorias não pôde ser carregado: a mensagem diz o que corrigir."""


@dataclass(frozen=True)
class Topic:
    """Uma categoria do vocabulário: `description` só serve ao prompt do LLM."""

    id: str
    label: str
    description: str


@dataclass(frozen=True)
class TopicVocabulary:
    """Vocabulário fechado de categorias e o mapa das categorias do classificador para ele."""

    topics: tuple[Topic, ...]
    classifier_map: dict[str, str]

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(topic.id for topic in self.topics)


@dataclass(frozen=True)
class TopicChoice:
    """Categoria escolhida e quem a escolheu (`llm`, `catalog`, `classifier`, `rule` ou `none`)."""

    topic: str | None
    source: str


@dataclass(frozen=True)
class TopicRequest:
    """O que `choose_topic` precisa saber do pedido; `text` e `history` já anonimizados."""

    text: str
    classifier_category: str
    is_urgent: bool = False
    service: ServiceEntry | None = None
    history: Sequence[str] = ()


NO_TOPIC = TopicChoice(topic=None, source=SOURCE_NONE)


def _topic_from(raw: object) -> Topic:
    if not isinstance(raw, dict):
        raise TopicsError("cada categoria deve ser um objeto com id, label e description")
    values = [raw.get(name) for name in ("id", "label", "description")]
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise TopicsError(f"categoria com id, label ou description ausente ou vazio: {raw!r}")
    return Topic(*values)


def _check_topics(topics: tuple[Topic, ...], path: Path) -> None:
    ids = [topic.id for topic in topics]
    if len(set(ids)) != len(ids):
        raise TopicsError(f"{path}: ids de categoria repetidos")
    if not ids or ids[-1] != OTHER_TOPIC:
        raise TopicsError(f"{path}: a categoria '{OTHER_TOPIC}' deve existir e ser a última")


def _check_map(classifier_map: object, ids: frozenset[str], path: Path) -> dict[str, str]:
    if not isinstance(classifier_map, dict) or not classifier_map:
        raise TopicsError(f"{path}: 'classifier_map' deve ser um objeto não vazio")
    unknown = sorted(str(value) for value in classifier_map.values() if value not in ids)
    if unknown:
        raise TopicsError(f"{path}: 'classifier_map' aponta para categoria inexistente: {', '.join(unknown)}")
    return dict(classifier_map)


def load_topics(path: Path = TOPICS_PATH, classifier_categories: Sequence[str] = ()) -> TopicVocabulary:
    """Lê e valida o JSON; arquivo ausente ou inválido é `TopicsError`, com a causa preservada.

    `classifier_categories`, se informado, exige que cada categoria do classificador tenha mapa.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise TopicsError(f"vocabulário de categorias ausente ou ilegível: {path}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("topics"), list):
        raise TopicsError(f"{path}: esperava um objeto com a lista 'topics'")
    topics = tuple(_topic_from(item) for item in raw["topics"])
    _check_topics(topics, path)
    classifier_map = _check_map(raw.get("classifier_map"), frozenset(t.id for t in topics), path)
    missing = sorted(set(classifier_categories) - set(classifier_map))
    if missing:
        raise TopicsError(f"{path}: categoria do classificador sem mapa: {', '.join(missing)}")
    return TopicVocabulary(topics=topics, classifier_map=classifier_map)


@cache
def _default_vocabulary() -> TopicVocabulary:
    return load_topics(classifier_categories=(*CATEGORY_RULES, OTHER_LABEL))


def _neutralize(text: str) -> str:
    """Tira os delimitadores da mensagem do texto, para que ele não feche um bloco de dado e simule instrução."""
    for delimiter in DELIMITERS:
        text = text.replace(delimiter, " ")
    return text


def build_topic_message(request: TopicRequest, vocabulary: TopicVocabulary) -> str:
    """Mensagem ao LLM: pedido e conversa anterior como dado, e as categorias lidas do vocabulário."""
    lines = [REQUEST_OPEN, _neutralize(request.text), REQUEST_CLOSE]
    if request.history:
        messages = (f"- {_neutralize(message)}" for message in request.history)
        lines.extend(["", HISTORY_OPEN, *messages, HISTORY_CLOSE])
    lines.extend(["", CATEGORIES_HEADER])
    lines.extend(f"- {topic.id}: {topic.label} — {topic.description}" for topic in vocabulary.topics)
    return "\n".join(lines)


def guard_topic_output(output: str, vocabulary: TopicVocabulary) -> tuple[str | None, str | None]:
    """Aceita só um id exato do vocabulário (sem espaços, aspas, ponto final ou diferença de caixa).

    Devolve `(id, None)` quando serve e `(None, motivo)` quando a saída é rejeitada.
    """
    candidate = output.strip(OUTPUT_NOISE).casefold()
    if candidate in vocabulary.ids:
        return candidate, None
    return None, REJECTION_NOT_A_TOPIC


def _ask_llm(client: LlmClient, request: TopicRequest, vocabulary: TopicVocabulary) -> str | None:
    """Id aprovado pela guarda, ou `None` em qualquer falha; o log traz só o tipo do erro ou o motivo."""
    try:
        output = client.complete(CATEGORIZE_TASK, build_topic_message(request, vocabulary))
    except (LlmUnavailable, LlmInvalidResponse) as error:
        logger.warning("LLM sem categoria (%s); usando regras determinísticas", type(error).__name__)
        return None
    topic, rejection = guard_topic_output(output, vocabulary)
    if topic is None:
        logger.warning("Categoria do LLM rejeitada (%s); usando regras determinísticas", rejection)
    return topic


def _deterministic(request: TopicRequest, vocabulary: TopicVocabulary) -> TopicChoice:
    """`area` da fonte resolvida, se houver; senão o mapa da categoria do classificador."""
    if request.service is not None and request.service.area in vocabulary.ids:
        return TopicChoice(request.service.area, SOURCE_CATALOG)
    topic = vocabulary.classifier_map.get(request.classifier_category, OTHER_TOPIC)
    return TopicChoice(topic, SOURCE_CLASSIFIER)


def choose_topic(
    request: TopicRequest, client: LlmClient | None, vocabulary: TopicVocabulary | None = None
) -> TopicChoice:
    """Categoria da interação: urgência (`rule`, sem LLM) → LLM (`llm`) → catálogo → classificador.

    Falha do LLM nunca levanta: cai no determinístico. Só o vocabulário inválido levanta `TopicsError`.
    """
    if request.is_urgent:
        return TopicChoice(SAFETY_TOPIC, SOURCE_RULE)
    vocabulary = vocabulary or _default_vocabulary()
    if client is not None:
        topic = _ask_llm(client, request, vocabulary)
        if topic is not None:
            return TopicChoice(topic, SOURCE_LLM)
    return _deterministic(request, vocabulary)
