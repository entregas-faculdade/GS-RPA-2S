"""Anonimização de dados pessoais (CPF, telefone, e-mail) antes de log ou API."""

from triage.privacy.anonymizer import AnonymizationResult, anonymize

__all__ = ["AnonymizationResult", "anonymize"]
