"""Anonimização de dados pessoais (CPF, telefone, e-mail, nome, endereço, CEP, RG, data e documentos) antes de log ou API."""

from triage.privacy.anonymizer import AnonymizationResult, anonymize

__all__ = ["AnonymizationResult", "anonymize"]
