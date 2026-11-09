"""Validação dos dígitos verificadores do CPF."""

CPF_LENGTH = 11


def _check_digit(digits: list[int]) -> int:
    """Dígito verificador de módulo 11 para a sequência recebida."""
    weight = len(digits) + 1
    total = sum(digit * (weight - index) for index, digit in enumerate(digits))
    remainder = (total * 10) % 11
    return 0 if remainder == 10 else remainder


def is_valid_cpf(value: str) -> bool:
    """Diz se `value` (só dígitos ou pontuado) tem os dígitos verificadores de um CPF."""
    digits = [int(char) for char in value if char.isdigit()]
    if len(digits) != CPF_LENGTH or len(set(digits)) == 1:
        return False
    return digits[9] == _check_digit(digits[:9]) and digits[10] == _check_digit(digits[:10])
