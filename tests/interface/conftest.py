"""Fixtures da interface: modelo treinado nos dados sintéticos, catálogo real e verificador de link simulado."""

import dataclasses
from pathlib import Path

import pytest
from sklearn.pipeline import Pipeline

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import load_catalog
from triage.automation.link_check import LinkStatus
from triage.automation.resolver import CatalogLookup
from triage.classification.model import train
from triage.config import Settings, load_settings
from triage.interface.service import AppService
from triage.pipeline import Deps
from triage.storage import Repository

REPO_ROOT = Path(__file__).resolve().parents[2]
LABELED_CSV = REPO_ROOT / "data" / "labeled" / "requests_labeled.csv"


def _always_ok(_url: str) -> LinkStatus:
    return LinkStatus(True, 200, None)


def _no_sleep(_seconds: float) -> None:
    """Espera nula nos testes."""


@pytest.fixture(scope="session")
def trained_model() -> Pipeline:
    return train(LABELED_CSV)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return dataclasses.replace(load_settings(tmp_path / "sem.env"), output_dir=str(tmp_path / "out"), llm_enabled=False)


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    return Repository(tmp_path / "triage.db")


@pytest.fixture
def service(repository: Repository, settings: Settings, trained_model: Pipeline) -> AppService:
    lookup = CatalogLookup(load_catalog(extra_dir=None), load_allowed_suffixes(), _always_ok)
    deps = Deps(repository=repository, lookup=lookup, settings=settings, model=trained_model, sleep=_no_sleep)
    return AppService(deps)
