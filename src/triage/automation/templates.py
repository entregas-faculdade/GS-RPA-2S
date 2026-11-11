"""Resposta-padrão em template: determinística, em português, e também o caminho seguro do LLM."""

from triage.automation.catalog import KIND_SERVICE, ServiceEntry

RESPONSE_TEMPLATE = (
    "Para resolver o seu pedido, o serviço indicado é: {display_name}.\n"
    "Órgão responsável: {agency}.\n"
    "Abrangência: {coverage}.\n"
    "{instructions}"
)
GENERAL_CHANNEL_TEMPLATE = (
    "Não encontrei um serviço específico para o seu pedido. O canal oficial indicado é o do órgão: {display_name}. "
    "Ele pode atender ao seu pedido; se não for o que você procura, descreva o pedido de outra forma ou procure o atendimento do próprio órgão.\n"
    "Órgão responsável: {agency}.\n"
    "Abrangência: {coverage}.\n"
    "{instructions}"
)
LINKS_HEADER = "Acesse o link oficial:"
LINKS_HEADER_PLURAL = "Acesse os links oficiais:"
PHONES_HEADER = "Telefones:"


def _section(header: str, lines: list[str]) -> str:
    return "\n".join([header, *lines])


def render_template(service: ServiceEntry) -> str:
    """Monta a resposta com nome, órgão, abrangência, instruções, todos os links e os telefones, se houver.

    Portal ou canal geral abre dizendo que não há serviço específico e se apresenta como sugestão.
    """
    opening = RESPONSE_TEMPLATE if service.kind == KIND_SERVICE else GENERAL_CHANNEL_TEMPLATE
    parts = [
        opening.format(
            display_name=service.display_name,
            agency=service.agency,
            coverage=service.coverage,
            instructions=service.instructions,
        )
    ]
    if service.links:
        header = LINKS_HEADER if len(service.links) == 1 else LINKS_HEADER_PLURAL
        parts.append(_section(header, [f"{link.label}: {link.url}" for link in service.links]))
    if service.phones:
        parts.append(_section(PHONES_HEADER, [f"{phone.label}: {phone.number}" for phone in service.phones]))
    return "\n".join(parts)
