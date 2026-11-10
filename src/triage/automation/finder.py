"""Localizador determinístico de fontes aprovadas a partir do texto anonimizado do pedido.

Sem LLM e sem rede: TF-IDF e cosseno sobre o catálogo. Só devolve a entrada; nunca produz link nem telefone.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer

from triage.automation.catalog import ServiceEntry, approved_only
from triage.classification.preprocessing import normalize
from triage.config import Settings

NGRAM_RANGE = (1, 2)

logger = logging.getLogger("triage.automation")


@dataclass(frozen=True)
class FinderMatch:
    """A melhor fonte para o pedido, com a pontuação (cosseno) e a folga para a melhor de outra entrada."""

    entry: ServiceEntry
    score: float
    margin: float


def _search_document(entry: ServiceEntry) -> str:
    """Texto de busca da entrada: o que o cidadão diria (palavras-chave e nome) mais o órgão."""
    return " ".join((*entry.keywords, entry.display_name, entry.agency))


def _build_index(entries: tuple[ServiceEntry, ...]) -> tuple[TfidfVectorizer, Any] | None:
    """Ajusta o TF-IDF nos documentos das entradas; sem entradas ou sem nenhum termo útil, não há índice."""
    documents = [_search_document(entry) for entry in entries]
    if not any(normalize(document) for document in documents):
        return None
    vectorizer = TfidfVectorizer(preprocessor=normalize, ngram_range=NGRAM_RANGE, sublinear_tf=True)
    return vectorizer, vectorizer.fit_transform(documents)


def _best_and_margin(scores: list[float]) -> tuple[int, float]:
    """Posição da maior pontuação (empate: a primeira) e a diferença para a maior das outras posições."""
    best = scores.index(max(scores))
    others = scores[:best] + scores[best + 1 :]
    return best, scores[best] - max(others, default=0.0)


class ServiceFinder:
    """Procura, entre as entradas aprovadas, a fonte que melhor atende o texto de um pedido.

    As entradas chegam prontas (injetadas) e entram ordenadas por `id`: a ordem em que vierem não muda o resultado.
    """

    def __init__(self, entries: Iterable[ServiceEntry], settings: Settings) -> None:
        self._entries = tuple(sorted(approved_only(list(entries)), key=lambda entry: entry.id))
        self._min_score = settings.finder_min_score
        self._margin = settings.finder_margin
        self._index = _build_index(self._entries)

    def best(self, text: str) -> FinderMatch | None:
        """A melhor entrada com a pontuação e a folga, sem aplicar limiar; `None` se o texto não tem termo conhecido."""
        if self._index is None or not text.strip():
            return None
        vectorizer, matrix = self._index
        query = vectorizer.transform([text])
        if query.nnz == 0:
            return None
        scores = matrix.dot(query.T).toarray().ravel().tolist()
        position, margin = _best_and_margin(scores)
        return FinderMatch(self._entries[position], scores[position], margin)

    def find(self, text: str) -> FinderMatch | None:
        """A fonte aprovada do pedido, ou `None` se a pontuação ou a folga ficam abaixo do limiar."""
        match = self.best(text)
        if match is None:
            return None
        if match.score < self._min_score or match.margin < self._margin:
            logger.info("Nenhuma fonte com confiança suficiente (pontuação %.2f, folga %.2f)", match.score, match.margin)
            return None
        return match
