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
