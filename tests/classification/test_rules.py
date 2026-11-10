"""Testes das regras regex: cada categoria com casos positivos e negativos."""

import pytest

from triage.classification.rules import CATEGORY_RULES, match_categories

POSITIVES = [
    ("driver_license", "onde tiro minha CNH?"),
    ("driver_license", "perdi a carteira nacional de habilitação"),
    ("driver_license", "quero a carteira de motorista"),
    ("driver_license", "como fazer a primeira habilitacao"),
    ("property_tax", "segunda via do IPTU"),
    ("property_tax", "parcelar o imposto predial"),
    ("id_card", "preciso do RG novo"),
    ("id_card", "perdi a carteira de identidade"),
    ("id_card", "emitir cédula de identidade"),
    ("id_card", "atualizar o documento de identidade"),
    ("cpf_registration", "meu CPF está irregular"),
    ("voter_id", "perdi o Título de Eleitor"),
    ("voter_id", "atualizar título eleitoral"),
    ("voter_id", "qual a minha zona eleitoral"),
    ("social_benefits", "atualizar o CadÚnico"),
    ("social_benefits", "meu cad unico venceu"),
    ("social_benefits", "bolsa família bloqueado"),
    ("social_security", "agendar no INSS"),
    ("social_security", "pedir aposentadoria"),
    ("social_security", "dúvida sobre previdência social"),
    ("birth_certificate", "segunda via da certidão de nascimento"),
    ("birth_certificate", "certidão de casamento atualizada"),
    ("birth_certificate", "preciso da certidão de óbito"),
]

NEGATIVES = [
    ("driver_license", "carteira de trabalho"),
    ("driver_license", "minha cnhs"),
    ("property_tax", "imposto de renda"),
    ("id_card", "tela rgb do monitor"),
    ("id_card", "carteira de vacinação"),
    ("cpf_registration", "cpfs de terceiros"),
    ("voter_id", "título de capitalização"),
    ("social_benefits", "bolsa de estudos"),
    ("social_security", "seguro do carro"),
    ("birth_certificate", "certidão negativa de débitos"),
]


@pytest.mark.parametrize(("category", "text"), POSITIVES)
def test_rule_matches_its_category(category: str, text: str) -> None:
    assert match_categories(text) == {category}


@pytest.mark.parametrize(("category", "text"), NEGATIVES)
def test_rule_does_not_match_unrelated_text(category: str, text: str) -> None:
    assert category not in match_categories(text)


def test_every_category_has_positive_and_negative_case() -> None:
    assert {category for category, _ in POSITIVES} == set(CATEGORY_RULES)
    assert {category for category, _ in NEGATIVES} == set(CATEGORY_RULES)


def test_no_match_returns_empty_set() -> None:
    assert match_categories("previsão do tempo para amanhã") == frozenset()


def test_two_categories_can_match_together() -> None:
    assert match_categories("preciso do CPF para tirar a CNH") == {"cpf_registration", "driver_license"}


def test_anonymization_marker_alone_does_not_trigger_cpf_rule() -> None:
    assert match_categories("meu documento é [CPF]") == frozenset()
