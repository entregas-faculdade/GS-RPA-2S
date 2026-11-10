"""Anonimização de nomes de pessoas, sem modelo de NER.

Dois caminhos: (a) a sequência de palavras após uma introdução explícita ("meu nome é", "me chamo",
"nome:", "Sr."...) e (b) em qualquer posição, um prenome da lista `data/first_names.json` seguido dos
sobrenomes. Na dúvida, mascara. Risco residual: nome fora de contexto e fora da lista passa.
"""

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from triage.privacy.patterns import NAME_INTRO_PATTERN, NAME_MARKER, TITLE_INTRO_PATTERN

logger = logging.getLogger(__name__)

FIRST_NAMES_PATH = Path(__file__).resolve().parents[3] / "data" / "first_names.json"
MAX_NAME_WORDS = 7
CONNECTORS = frozenset({"de", "da", "do", "dos", "das"})
# Prenome precedido por estes é topônimo ("São Paulo", "Santa Maria"), que não se mascara.
PLACE_PREFIXES = frozenset({"sao", "santa", "santo"})
PLACE_NAMES = frozenset({("joao", "pessoa")})
# Palavras (sem acento, minúsculas) que encerram um nome: o que um pedido costuma dizer depois dele.
NON_NAME_WORDS = frozenset(
    {
        "e", "ou", "que", "com", "sem", "para", "pra", "por", "em", "na", "no", "nas", "nos", "ao", "aos",
        "a", "o", "as", "os", "um", "uma", "se", "mas", "pois", "como", "onde", "quando", "porque", "ja",
        "nao", "nem", "sim", "ola", "oi", "bom", "boa", "dia", "tarde", "noite",
        "eu", "me", "meu", "minha", "meus", "minhas", "sou", "estou", "esta", "estao", "tenho", "tem",
        "preciso", "precisa", "precisamos", "quero", "quer", "queria", "gostaria", "necessito", "necessita",
        "desejo", "deseja", "solicito", "solicita", "venho", "vim", "moro", "mora", "resido", "reside",
        "nasci", "nasceu", "nascido", "nascida", "trabalho", "trabalha", "vou", "vai", "fui", "foi",
        "perdi", "perdeu", "perdido", "roubaram", "roubou", "posso", "pode", "podem", "consigo", "peco", "pede",
        "aposentado", "aposentada", "desempregado", "desempregada", "casado", "casada", "solteiro", "solteira",
        "viuvo", "viuva", "residente", "morador", "moradora", "cidadao", "titular", "portador", "portadora",
        "cadastro", "cpf", "rg", "cnh", "cep", "urgente", "favor", "obrigado", "obrigada", "ajuda", "ajudar",
        "saber", "informar", "informacao", "atualmente", "hoje", "ontem", "nome", "pai", "mae", "filho", "filha",
        "esposa", "marido", "irmao", "irma", "solicitou", "pediu", "disse", "falou", "informou", "precisou",
    }
)  # fmt: skip
_GAP_PATTERN = re.compile(r"[ \t]+")
_WORD_PATTERN = re.compile(r"(?<![\w\[])[^\W\d_]+(?:-[^\W\d_]+)*(?![\w\]])")


@dataclass(frozen=True)
class _Word:
    text: str
    start: int
    end: int
    folded: str


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def load_first_names(path: Path) -> frozenset[str]:
    """Lê a lista de prenomes (sem acento, minúsculas). Falha segura: arquivo ausente ou inválido → vazio."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list) or not all(isinstance(name, str) for name in raw):
            raise ValueError("a lista de prenomes deve ser um array de textos")
    except (OSError, ValueError):
        logger.error("Lista de prenomes indisponível em %s; só o contexto mascara nomes.", path)
        return frozenset()
    return frozenset(_fold(name) for name in raw)


@lru_cache(maxsize=1)
def _first_names() -> frozenset[str]:
    return load_first_names(FIRST_NAMES_PATH)


def _tokenize(text: str) -> list[_Word]:
    matches = _WORD_PATTERN.finditer(text)
    return [_Word(match.group(), match.start(), match.end(), _fold(match.group())) for match in matches]


def _is_glued(text: str, left: _Word, right: _Word) -> bool:
    """Diz se só espaço ou tabulação separa as duas palavras."""
    return _GAP_PATTERN.fullmatch(text[left.end : right.start]) is not None


def _is_name_word(word: _Word) -> bool:
    return word.folded not in NON_NAME_WORDS and word.folded not in CONNECTORS


def _next_member(text: str, words: list[_Word], last: int) -> int | None:
    """Índice da palavra que continua o nome após `last` (levando o conector junto), ou None."""
    index = last + 1
    if index >= len(words) or not _is_glued(text, words[last], words[index]):
        return None
    if words[index].folded not in CONNECTORS:
        return index if _is_name_word(words[index]) else None
    following = index + 1
    if following < len(words) and _is_glued(text, words[index], words[following]) and _is_name_word(words[following]):
        return following
    return None


def _run_end(text: str, words: list[_Word], first: int) -> int:
    """Índice da última palavra do nome que começa em `first`."""
    last = first
    for _ in range(MAX_NAME_WORDS - 1):
        member = _next_member(text, words, last)
        if member is None:
            break
        last = member
    return last


def _span(text: str, words: list[_Word], first: int) -> tuple[int, int]:
    return words[first].start, words[_run_end(text, words, first)].end


def _context_spans(text: str, words: list[_Word]) -> list[tuple[int, int]]:
    by_start = {word.start: index for index, word in enumerate(words)}
    spans = []
    for pattern, needs_capital in ((NAME_INTRO_PATTERN, False), (TITLE_INTRO_PATTERN, True)):
        for match in pattern.finditer(text):
            first = by_start.get(match.end())
            if first is None or not _is_name_word(words[first]):
                continue
            if needs_capital and not words[first].text[0].isupper():
                continue
            spans.append(_span(text, words, first))
    return spans


def _is_place(text: str, words: list[_Word], index: int) -> bool:
    """Diz se o prenome é parte de um topônimo ("São Paulo", "João Pessoa")."""
    if index > 0 and _is_glued(text, words[index - 1], words[index]) and words[index - 1].folded in PLACE_PREFIXES:
        return True
    if index + 1 >= len(words) or not _is_glued(text, words[index], words[index + 1]):
        return False
    return (words[index].folded, words[index + 1].folded) in PLACE_NAMES


def _list_spans(text: str, words: list[_Word], first_names: frozenset[str]) -> list[tuple[int, int]]:
    return [
        _span(text, words, index)
        for index, word in enumerate(words)
        if word.folded in first_names and not _is_place(text, words, index)
    ]


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def mask_names(text: str) -> tuple[str, int]:
    """Troca cada nome de pessoa por `[NOME]` e devolve a quantidade de trocas."""
    words = _tokenize(text)
    spans = _merge(_context_spans(text, words) + _list_spans(text, words, _first_names()))
    pieces: list[str] = []
    cursor = 0
    for start, end in spans:
        pieces.extend((text[cursor:start], NAME_MARKER))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces), len(spans)
