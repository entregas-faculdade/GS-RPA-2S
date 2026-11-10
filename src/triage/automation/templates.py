"""Resposta-padrão em template: determinística, em português, e também o caminho seguro do LLM."""

from triage.automation.catalog import ServiceEntry

RESPONSE_TEMPLATE = (
    "Para resolver o seu pedido, o serviço indicado é: {display_name}.\n"
    "Órgão responsável: {agency}.\n"
    "{instructions}\n"
    "Acesse o link oficial: {url}"
)


def render_template(service: ServiceEntry) -> str:
    """Monta a resposta com nome do serviço, órgão, instruções e o link oficial do catálogo."""
    return RESPONSE_TEMPLATE.format(
        display_name=service.display_name,
        agency=service.agency,
        instructions=service.instructions,
        url=service.url,
    )
