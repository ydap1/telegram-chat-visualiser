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


def tokenize_and_filter(text: str, stop: set[str]) -> list[str]:
    return [w.lower() for w in nltk.word_tokenize(text) if w.isalpha() and w.lower() not in stop]
