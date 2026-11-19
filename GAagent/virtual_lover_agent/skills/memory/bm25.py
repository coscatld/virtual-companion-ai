import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence


HAN_RUN = re.compile(r"([\u3400-\u4dbf\u4e00-\u9fff]+)")
WORDS = re.compile(r"[^\W_]+")
HAN_STOP_CHARACTERS = frozenset("的了是在和与及有我你他她它们这那要想吗呢啊得地着把个哪什怎会被还")
ENGLISH_STOP_WORDS = frozenset(
    "a an and are can did do does for from i in is it me my of on or the to was what with you your".split()
)


def _tokens(text: str) -> list[str]:
    tokens = []
    parts = HAN_RUN.split(unicodedata.normalize("NFKC", text).casefold())
    for part in parts[::2]:
        tokens.extend(word for word in WORDS.findall(part) if word not in ENGLISH_STOP_WORDS)
    for han in parts[1::2]:
        tokens.extend(character for character in han if character not in HAN_STOP_CHARACTERS)
        tokens.extend(han[index:index + 2] for index in range(len(han) - 1))
    return tokens


def search_bm25(query: str, documents: Sequence[str], limit: int = 3) -> list[str]:
    """Rank summaries in chronological order, preferring newer summaries on tied scores."""
    terms = set(_tokens(query))
    if not terms or not documents or limit <= 0:
        return []

    counts = [Counter(_tokens(document)) for document in documents]
    lengths = [sum(count.values()) for count in counts]
    average_length = sum(lengths) / len(counts)
    if not average_length:
        return []

    inverse_frequency = {}
    for term in sorted(terms):
        document_frequency = sum(term in count for count in counts)
        if document_frequency:
            inverse_frequency[term] = math.log1p(
                (len(counts) - document_frequency + 0.5) / (document_frequency + 0.5)
            )

    k1 = 1.2
    b = 0.75
    scores = []
    for index, count in enumerate(counts):
        length_normalization = k1 * (1 - b + b * lengths[index] / average_length)
        score = 0.0
        for term, idf in inverse_frequency.items():
            frequency = count[term]
            if frequency:
                is_han_unigram = len(term) == 1 and HAN_RUN.fullmatch(term)
                weight = 0.25 if is_han_unigram else 1
                score += weight * idf * frequency * (k1 + 1) / (frequency + length_normalization)
        if score > 0:
            scores.append((score, index))

    scores.sort(reverse=True)
    return [documents[index] for _, index in scores[:limit]]
