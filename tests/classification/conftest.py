"""Fixtures dos testes de classificação: CSV rotulado pequeno e modelo treinado nele (dados sintéticos)."""

from collections.abc import Callable
from pathlib import Path

import pytest
from sklearn.pipeline import Pipeline

from triage.classification.model import train

SAMPLE_TEXTS = {
    "driver_license": ["renovar a cnh vencida", "primeira habilitação para dirigir", "segunda via da carteira de motorista"],
    "property_tax": ["segunda via do iptu", "parcelar imposto do imóvel", "isenção do imposto predial"],
    "id_card": ["tirar o rg", "carteira de identidade perdida", "documento de identidade novo"],
    "cpf_registration": ["regularizar o cpf", "inscrição no cpf", "cpf suspenso na receita"],
    "voter_id": ["título de eleitor novo", "zona eleitoral", "votação e título eleitoral"],
    "social_benefits": ["cadastro no cadúnico", "bolsa família bloqueado", "benefício social"],
    "social_security": ["aposentadoria por idade", "agendar o inss", "pensão e previdência social"],
    "birth_certificate": ["certidão de nascimento", "certidão de casamento", "certidão de óbito"],
    "other": ["previsão do tempo", "restaurante perto", "passaporte novo"],
}
HEADER = "id,text,label,split,urgent"


def _write_sample_csv(path: Path, extra_rows: tuple[str, ...] = ()) -> Path:
    lines = [HEADER]
    index = 0
    for label, texts in SAMPLE_TEXTS.items():
        for text in texts:
            index += 1
            lines.append(f"S{index:03d},{text},{label},train,0")
    lines.extend(extra_rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def sample_labels() -> set[str]:
    return set(SAMPLE_TEXTS)


@pytest.fixture
def sample_header() -> str:
    return HEADER


@pytest.fixture
def write_sample_csv() -> Callable[..., Path]:
    """Grava o CSV pequeno (todas as linhas em `train`) mais as linhas extras já formatadas."""
    return _write_sample_csv


@pytest.fixture(scope="session")
def sample_model(tmp_path_factory: pytest.TempPathFactory) -> Pipeline:
    return train(_write_sample_csv(tmp_path_factory.mktemp("sample") / "sample.csv"))
