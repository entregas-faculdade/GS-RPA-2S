"""Catálogo, allowlist, verificação de links, montagem da resposta e categoria da interação."""

from triage.automation.topics import (
    NO_TOPIC,
    TopicChoice,
    TopicRequest,
    TopicsError,
    TopicVocabulary,
    choose_topic,
    load_topics,
)

__all__ = [
    "NO_TOPIC",
    "TopicChoice",
    "TopicRequest",
    "TopicVocabulary",
    "TopicsError",
    "choose_topic",
    "load_topics",
]
