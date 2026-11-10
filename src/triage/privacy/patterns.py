"""Expressões regulares dos dados pessoais cobertos (CPF, telefone BR e e-mail)."""

import re

# 11 dígitos com `.` e `-` opcionais; só o formato totalmente pontuado dispensa a validação dos dígitos.
CPF_PATTERN = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
CPF_PUNCTUATED_PATTERN = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")

# Telefone: exige alguma marca de telefone (+55, parênteses, separador ou celular completo de 11
# dígitos) para não confundir com protocolo, ano ou valor.
PHONE_PATTERN = re.compile(
    r"""
    (?<!\d)
    (?:
        \+55\s?(?:\(?\d{2}\)?\s?)?9?\d{4}[-\s]?\d{4}   # com +55, DDD opcional
      | \(\d{2}\)\s?9?\d{4}[-\s]?\d{4}               # (DD) 91234-5678
      | \d{2}[\s-]9?\d{4}-?\d{4}                    # DD 91234-5678
      | 9?\d{4}-\d{4}                               # 91234-5678 ou 1234-5678
      | [1-9]{2}9\d{8}                              # celular sem pontuação: 11912345678
    )
    (?!\d)
    """,
    re.VERBOSE,
)

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")

CPF_MARKER = "[CPF]"
PHONE_MARKER = "[TELEFONE]"
EMAIL_MARKER = "[EMAIL]"

NAME_MARKER = "[NOME]"
ADDRESS_MARKER = "[ENDERECO]"
POSTAL_CODE_MARKER = "[CEP]"
RG_MARKER = "[RG]"
DATE_MARKER = "[DATA]"
DOCUMENT_MARKER = "[DOCUMENTO]"

# Todos os marcadores que a anonimização insere; o pré-processamento os remove antes de classificar.
ALL_MARKERS = (
    CPF_MARKER,
    PHONE_MARKER,
    EMAIL_MARKER,
    NAME_MARKER,
    ADDRESS_MARKER,
    POSTAL_CODE_MARKER,
    RG_MARKER,
    DATE_MARKER,
    DOCUMENT_MARKER,
)

KIND_CPF = "cpf"
KIND_PHONE = "phone"
KIND_EMAIL = "email"
KIND_NAME = "name"
KIND_ADDRESS = "address"
KIND_POSTAL_CODE = "postal_code"
KIND_RG = "rg"
KIND_DATE = "date"
KIND_DOCUMENT = "document"

# Os marcadores acima não têm dígito nem `@`; `(?<![\w\[])` impede casar texto dentro de um marcador já inserido.
_NOT_AFTER_WORD = r"(?<![\w\[])"
_NUMBER_LABEL = r"[ \t]*(?:n[ºo°]?\.?[ \t]*)?:?[ \t]*"

# CEP: `00000-000`, ou oito dígitos colados precedidos de "CEP".
POSTAL_CODE_PATTERN = re.compile(r"(?<![\d-])\d{5}-\d{3}(?![\d-])")
POSTAL_CODE_LABELED_PATTERN = re.compile(r"(\bCEP\b" + _NUMBER_LABEL + r")\d{8}(?!\d)", re.IGNORECASE)

# RG: número após "RG" (grupo 2) e o formato pontuado `0.000.000-0`.
RG_LABELED_PATTERN = re.compile(r"(\bRG\b" + _NUMBER_LABEL + r")(\d[\d.\-]{2,}[\dXx])", re.IGNORECASE)
RG_FORMAT_PATTERN = re.compile(r"(?<![\d.])\d{1,2}\.\d{3}\.\d{3}-[\dXx](?!\w)")

# Documentos: sequência numérica (grupo 2) após o rótulo; o tamanho de 9 a 15 dígitos é conferido no código.
DOCUMENT_LABELED_PATTERN = re.compile(
    r"((?:t[ií]tulo\s+de\s+eleitor|cart[aã]o\s+sus|cnh|nis|pis|cnpj|passaporte|matr[ií]cula)\b"
    + _NUMBER_LABEL
    + r")(\d[\d .\-/]*\d)",
    re.IGNORECASE,
)
CNPJ_PUNCTUATED_PATTERN = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")

# Data completa: dd/mm/aaaa, dd-mm-aaaa, dd.mm.aaaa (mesmo separador) e aaaa-mm-dd. Data sem ano não casa.
DATE_PATTERN = re.compile(
    r"(?<![\d/.\-])(?:(?:0?[1-9]|[12]\d|3[01])([/.\-])(?:0?[1-9]|1[0-2])\1\d{4}"
    r"|(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))(?!\d)"
)

# Introdução explícita de nome. O nome em si é lido por `names.py`; o padrão termina no espaço seguinte.
NAME_INTRO_PATTERN = re.compile(
    _NOT_AFTER_WORD
    + r"(?:meu\s+nome(?:\s+completo)?\s+(?:é|e|eh)\s+|me\s+chamo\s+|chamo-me\s+"
    + r"|nome(?:\s+completo|\s+d[oa]\s+(?:pai|m[ãa]e|filho|filha|titular|requerente))?\s*:\s*)",
    re.IGNORECASE,
)
# Tratamento (Sr., Dra., senhor...): em minúsculas é palavra comum ("o senhor pode"), então `names.py` exige maiúscula.
TITLE_INTRO_PATTERN = re.compile(_NOT_AFTER_WORD + r"(?:(?:srta|sra|sr|dra|dr)\b\.?|senhora|senhor)[ \t]+", re.IGNORECASE)

# Endereço: logradouro + nome próprio + número e complementos.
# Palavras de frase (verbo, preposição, posse, tempo) nunca fazem parte do nome da rua: "a rua está sem iluminação",
# "rua da escola passam 20 ônibus". `\b` fecha a palavra para "em" não casar com "embaixo".
_CONNECTOR = r"(?i:de|da|do|das|dos)"
_CAPITALIZED = r"[A-ZÀ-Ý][^\W\d_]*(?:-[^\W\d_]+)*"
_SENTENCE_WORDS = (
    r"(?i:em|na|no|nas|nos|sem|com|que|e|a|o|as|os|ao|aos|um|uma|para|pra|por|perto|se|mas|pois|como|quando|onde"
    r"|est[áa]|est[ãa]o|h[áa]|ficou|ficam|fica|passam|passa|tem|t[êe]m|tinha|foi|era|vai|v[ãa]o|desde|durante"
    r"|lotad[ao]|alagad[ao]|esburacad[ao]|nest[ae]|ness[ae]|minha|meu|minhas|meus|sua|seu"
    r"|nossa|nosso|esta|este|essa|esse|quero|preciso|precisa|reclamar|muito|muita|mais|j[áa]|n[ãa]o|ainda"
    r"|hoje|ontem|dias?|anos?|vezes|horas?|meses|semanas?)"
)
_NOT_SENTENCE_WORD = r"(?!" + _SENTENCE_WORDS + r"\b)"
_NOT_CONNECTOR = r"(?!" + _CONNECTOR + r"\b)"
_CAPITALIZED_WORD = _NOT_SENTENCE_WORD + _CAPITALIZED
_STREET_TYPE = (
    r"(?i:(?:rua|avenida|alameda|travessa|pra[çc]a|rodovia|estrada|largo|av)\.?"
    r"|(?:r|al|tv|trav|pç|pça|pc|rod|estr|lgo)\.)"
)
# Nome capitalizado (ou conector + capitalizado): vale mesmo sem número.
_STREET_NAME = (
    r"[ \t]+(?:" + _CONNECTOR + r"[ \t]+" + _CAPITALIZED_WORD + "|" + _NOT_CONNECTOR + _CAPITALIZED_WORD + ")"
    r"(?:[ \t]+(?:" + _CONNECTOR + r"[ \t]+)?" + _CAPITALIZED_WORD + r")*"
)
_STREET_NUMBER = r"[ \t]*,?[ \t]*(?:(?i:n[ºo°]?\.?)[ \t]*)?\d{1,6}[A-Za-z]?(?!\w)"
# Número seguido de unidade ou quantidade ("3 dias", "20 ônibus") é duração ou contagem, não número de porta.
_NOT_QUANTITY = r"(?![ \t]+(?i:dias?|anos?|vezes|horas?|minutos?|meses|semanas?|metros?|km|quilos?|reais|[ôo]nibus|carros?|buracos?)\b)"
_STREET_NO_NUMBER = r"[ \t]*,?[ \t]*(?i:s/n)(?!\w)"
_COMPLEMENT = (
    r"[ \t]*[,\-]?[ \t]*(?i:apartamento|apto|ap|bloco|bl|casa|sala|conjunto|cj|lote|quadra|qd|andar|fundos)\.?"
    r"[ \t]*[nº°.]*[ \t]*(?:\d+[A-Za-z]?|[A-Z](?!\w))"
)
_STREET_TAIL = "(?:" + _STREET_NUMBER + "|" + _STREET_NO_NUMBER + "|" + _COMPLEMENT + ")"
_PLAIN_STREET_TAIL = "(?:" + _STREET_NUMBER + _NOT_QUANTITY + "|" + _STREET_NO_NUMBER + "|" + _COMPLEMENT + ")"
# Nome em qualquer caixa, de 1 a 3 palavras (inclusive numeral: "7 de setembro"): só vale com número ou
# complemento depois, senão "rua em frente à escola" e "a rua da escola" seriam mascarados.
_PLAIN_WORD = _NOT_SENTENCE_WORD + r"[^\W_]+(?:-[^\W_]+)*"
_STREET_PLAIN_NAME = r"[ \t]+" + _PLAIN_WORD + r"(?:[ \t]+" + _PLAIN_WORD + r"){0,2}"
ADDRESS_PATTERN = re.compile(
    _NOT_AFTER_WORD
    + _STREET_TYPE
    + "(?:"
    + _STREET_NAME
    + _STREET_TAIL
    + "*|"
    + _STREET_PLAIN_NAME
    + _PLAIN_STREET_TAIL
    + "+)"
)
