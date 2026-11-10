"""Fixtures do pipeline: modelo treinado nos dados rotulados sintéticos, catálogo real e rede simulada."""

import dataclasses
from collections.abc import Callable
from pathlib import Path

import pytest
from sklearn.pipeline import Pipeline

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import load_catalog
from triage.automation.link_check import LinkStatus
from triage.automation.resolver import CatalogLookup
from triage.classification.model import train
from triage.config import Settings, load_settings
from triage.pipeline import Deps
from triage.storage import Repository

REPO_ROOT = Path(__file__).resolve().parents[2]
LABELED_CSV = REPO_ROOT / "data" / "labeled" / "requests_labeled.csv"


def no_sleep(_seconds: float) -> None:
    """Espera nula nos testes de retry."""


@pytest.fixture(scope="session")
def trained_model() -> Pipeline:
    return train(LABELED_CSV)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return dataclasses.replace(load_settings(tmp_path / "sem.env"), output_dir=str(tmp_path / "out"), llm_enabled=False)


def link_checker(ok: bool = True) -> Callable[[str], LinkStatus]:
    def check(_url: str) -> LinkStatus:
        return LinkStatus(ok, 200 if ok else None, None if ok else "Timeout")

    return check


@pytest.fixture
def make_deps(tmp_path: Path, settings: Settings, trained_model: Pipeline) -> Callable[..., Deps]:
    """Monta `Deps` com banco temporário, catálogo real e verificador de link simulado (nunca usa a rede)."""

    def build(**overrides: object) -> Deps:
        checker = overrides.pop("link_ok", True)
        lookup = CatalogLookup(load_catalog(), load_allowed_suffixes(), link_checker(checker))
        values = {
            "repository": Repository(tmp_path / "triage.db"),
            "lookup": lookup,
            "settings": settings,
            "model": trained_model,
            "sleep": no_sleep,
        }
        return Deps(**{**values, **overrides})

    return build
