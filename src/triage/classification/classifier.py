"""Classificação do assunto: atalho por regex quando casa uma categoria só; senão, o modelo."""

from dataclasses import dataclass

from sklearn.pipeline import Pipeline

from triage.classification.model import DEFAULT_MODEL_PATH, load, predict_proba
from triage.classification.rules import match_categories

SOURCE_RULE = "rule"
SOURCE_MODEL = "model"


@dataclass(frozen=True)
class Classification:
    """Categoria escolhida, probabilidades do modelo para todas as categorias e a origem da decisão."""

    label: str
    probabilities: dict[str, float]
    source: str


def classify(text: str, model: Pipeline | None = None) -> Classification:
    """Classifica um texto já anonimizado.

    Com exatamente uma regra casando, o rótulo vem da regra (`source="rule"`); com nenhuma ou com duas
    ou mais, vem do modelo (`source="model"`). As probabilidades são sempre as do modelo. Sem `model`,
    carrega o arquivo padrão (quem classifica em lote deve carregar uma vez e passar o modelo).
    Levanta `ModelNotAvailableError` se o modelo não puder ser carregado.
    """
    loaded = model if model is not None else load(DEFAULT_MODEL_PATH)
    probabilities = predict_proba(loaded, text)
    matched = match_categories(text)
    if len(matched) == 1:
        (label,) = matched
        return Classification(label, probabilities, SOURCE_RULE)
    label = max(probabilities, key=probabilities.__getitem__)
    return Classification(label, probabilities, SOURCE_MODEL)
