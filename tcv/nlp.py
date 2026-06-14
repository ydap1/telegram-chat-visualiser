from __future__ import annotations

import re

import nltk
from nltk.corpus import stopwords


def ensure_nltk_data() -> None:
    for resource, package in [
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('tokenizers/punkt', 'punkt'),
        ('corpora/stopwords', 'stopwords'),
    ]:
        try:
            nltk.data.find(resource)
        except LookupError:
            nltk.download(package, quiet=True)


def clean(text: str) -> str:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()


def stopword_set(langs: list[str] | None = None) -> set[str]:
    if langs is None:
        langs = ['english', 'russian']
    result: set[str] = set()
    for lang in langs:
        try:
            result.update(stopwords.words(lang))
        except OSError:
            pass
    return result


# Russian filler / slang words not covered by NLTK's stopword list
_RU_EXTRA: frozenset[str] = frozenset({
    # phonetic / slang variants of common words
    'ваще', 'типа', 'типо', 'щас', 'ща', 'дак', 'хз', 'чет', 'чё', 'чо', 'че',
    'норм', 'окей', 'лан', 'короче', 'короч', 'оч', 'мб', 'прям',
    # filler adverbs / connectors missed by NLTK
    'вроде', 'пока', 'блин', 'ага', 'угу', 'вот', 'тут', 'там',
    'наверное', 'наверно', 'конечно', 'именно', 'просто', 'вообще',
    'совсем', 'тоже', 'уже', 'ещё', 'еще', 'даже', 'уж', 'потом',
    'сейчас', 'раньше', 'раз', 'итак', 'значит', 'кстати', 'вообщем',
    'хотя', 'хотябы', 'сразу', 'очень', 'также', 'ток',
    'всё', 'все', 'всем', 'всего', 'всей', 'всех', 'всеми',
    'такие', 'таких', 'таким', 'такими',
    # demonstratives — NLTK misses most forms
    'это', 'эта', 'этот', 'этого', 'этому', 'этим', 'этой', 'этих', 'эту',
    'та', 'те', 'тех', 'тем', 'теми', 'той', 'такое',
    # pronoun cases missed by NLTK
    'тебя', 'тебе', 'тобой',
    # relative pronouns (declined)
    'который', 'которые', 'которых', 'которому', 'которого', 'которой', 'которым', 'которыми',
    # laughter / reactions
    'лол', 'лмао', 'кек', 'хах', 'хаха', 'хахах', 'хахаха', 'хахахаха',
    'ахах', 'ахахах', 'ахахаха', 'хд',
    # channel link CTA text appearing in forwarded posts (not user-generated content)
    'подписаться', 'подпишитесь', 'подписывайтесь',
    # expletives / mat used as fillers (not content words)
    'бля', 'блять', 'блт', 'ебать', 'ебат', 'пиздец', 'пздц', 'нахуй',
    'хуй', 'хуя', 'хуе', 'хуев', 'сука', 'суки',
    'похуй', 'похую', 'нихуя', 'хуйня', 'хуйни',
})


def extended_stopword_set(langs: list[str] | None = None) -> set[str]:
    """NLTK stopwords plus Russian chat fillers, slang, and expletive fillers."""
    return stopword_set(langs) | _RU_EXTRA


def tokenize_and_filter(text: str, stop: set[str]) -> list[str]:
    return [w.lower() for w in nltk.word_tokenize(text) if w.isalpha() and w.lower() not in stop]
