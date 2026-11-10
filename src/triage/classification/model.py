"""Modelo TF-IDF + regressão logística: treino, persistência e probabilidades por categoria.

O modelo treinado é um artefato local (`output/` não é versionado): regenere-o com
`python scripts/train_model.py`. Hiperparâmetros e `random_state` fixos garantem que o mesmo CSV
produza as mesmas probabilidades.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from triage.classification.preprocessing import normalize
from triage.config import DEFAULT_OUTPUT_DIR

DEFAULT_MODEL_PATH = Path(DEFAULT_OUTPUT_DIR) / "models" / "classifier.joblib"
TEXT_COLUMN = "text"
LABEL_COLUMN = "label"
SPLIT_COLUMN = "split"
TRAIN_SPLIT = "train"

RANDOM_STATE = 42
NGRAM_RANGE = (1, 2)
REGULARIZATION_C = 10.0
MAX_ITERATIONS = 1000


class ModelNotAvailableError(Exception):
    """O arquivo do modelo está ausente, corrompido ou não é um classificador."""


def _build_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(preprocessor=normalize, ngram_range=NGRAM_RANGE, sublinear_tf=True)),
            ("logreg", LogisticRegression(C=REGULARIZATION_C, max_iter=MAX_ITERATIONS, random_state=RANDOM_STATE)),
        ]
    )


def train(csv_path: Path) -> Pipeline:
    """Treina o pipeline só com as linhas `split=train` do CSV rotulado."""
    data = pd.read_csv(csv_path, encoding="utf-8")
    missing = {TEXT_COLUMN, LABEL_COLUMN, SPLIT_COLUMN} - set(data.columns)
    if missing:
        raise ValueError(f"CSV rotulado sem as colunas {sorted(missing)}: {csv_path}")
    train_rows = data[data[SPLIT_COLUMN] == TRAIN_SPLIT]
    if train_rows.empty:
        raise ValueError(f"CSV rotulado sem linhas com {SPLIT_COLUMN}={TRAIN_SPLIT}: {csv_path}")
    return _build_pipeline().fit(train_rows[TEXT_COLUMN], train_rows[LABEL_COLUMN])


def save(model: Pipeline, path: Path) -> None:
    """Grava o modelo em `path`, criando as pastas que faltarem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load(path: Path) -> Pipeline:
    """Carrega o modelo; arquivo ausente, corrompido ou de outro tipo vira `ModelNotAvailableError`."""
    try:
        model = joblib.load(path)
    except Exception as error:  # joblib/pickle levantam tipos variados para arquivo corrompido
        raise ModelNotAvailableError(f"Modelo indisponível em {path}: {error}") from error
    if not hasattr(model, "predict_proba"):
        raise ModelNotAvailableError(f"O arquivo {path} não contém um classificador com predict_proba")
    return model


def predict_proba(model: Pipeline, text: str) -> dict[str, float]:
    """Probabilidade de cada categoria que o modelo conhece (soma 1)."""
    probabilities = model.predict_proba([text])[0]
    return {label: float(value) for label, value in zip(model.classes_, probabilities, strict=True)}
