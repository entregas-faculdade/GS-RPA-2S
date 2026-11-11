"""Mensagens fixas ao cidadão fora do template de serviço: sem fonte e emergência. Nunca geradas por LLM."""

import logging
from collections.abc import Iterable

from triage.automation.catalog import STATUS_APPROVED, ServiceEntry

AREA_SAFETY = "safety"
KIND_CHANNEL = "channel"
FORWARDED_TO_HUMAN = "O seu pedido também foi encaminhado a atendimento humano."
NO_INFORMATION_TEXT = (
    "Não encontrei uma fonte oficial para o seu pedido, por isso não tenho essa informação. "
    "O seu pedido foi encaminhado a atendimento humano."
)
EMERGENCY_HEADER = "Se há risco imediato à vida ou à segurança, ligue agora:"
EMERGENCY_PRIORITY_TEXT = "O seu pedido foi encaminhado a atendimento humano com prioridade."

logger = logging.getLogger("triage.automation")


def build_no_information_message() -> str:
    """Diz que o sistema não tem fonte oficial para o pedido e que ele foi a atendimento humano, sem prometer prazo."""
    return NO_INFORMATION_TEXT


def _emergency_lines(entries: Iterable[ServiceEntry]) -> list[str]:
    """Um `rótulo: número` por telefone dos canais aprovados de `safety`, sem repetir o mesmo par."""
    lines: list[str] = []
    for entry in entries:
        if entry.status != STATUS_APPROVED or entry.area != AREA_SAFETY or entry.kind != KIND_CHANNEL:
            continue
        for phone in entry.phones:
            line = f"{phone.label}: {phone.number}"
            if line not in lines:
                lines.append(line)
    return lines


def build_emergency_message(entries: Iterable[ServiceEntry]) -> str:
    """Mensagem de emergência com os telefones aprovados do catálogo; sem nenhum, só o encaminhamento prioritário."""
    lines = _emergency_lines(entries)
    if not lines:
        logger.warning("Nenhum canal de emergência aprovado no catálogo; a mensagem sai só com o encaminhamento")
        return EMERGENCY_PRIORITY_TEXT
    return "\n".join([EMERGENCY_HEADER, *lines, FORWARDED_TO_HUMAN])
