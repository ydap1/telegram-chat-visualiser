import argparse
import json
import re
import sys

import nltk
from nltk.corpus import stopwords
from wordcloud import WordCloud


def ensure_nltk_data():
    for resource, package in [
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('tokenizers/punkt', 'punkt'),
        ('corpora/stopwords', 'stopwords'),
    ]:
        try:
            nltk.data.find(resource)
        except LookupError:
            nltk.download(package, quiet=True)


def extract_text(field):
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        parts = []
        for part in field:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get('text', ''))
        return ''.join(parts)
    return ''


def clean(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()


def parse_args():
    p = argparse.ArgumentParser(description='Generate a word cloud from a Telegram chat export JSON file')
    p.add_argument('input_file', help='path to the Telegram JSON export')
    p.add_argument('-n', '--num-words', type=int, default=150, help='number of words to display (default: 150)')
    p.add_argument('-W', '--width', type=int, default=1280, help='image width in pixels (default: 1280)')
    p.add_argument('-H', '--height', type=int, default=720, help='image height in pixels (default: 720)')
    p.add_argument('-o', '--output', default='wordcloud.png', help='output PNG path (default: wordcloud.png)')
    return p.parse_args()


def main():
    ensure_nltk_data()
    args = parse_args()

    try:
        with open(args.input_file, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f'error: file not found: {args.input_file}')
    except json.JSONDecodeError as e:
        sys.exit(f'error: invalid JSON: {e}')

    texts = []
    for msg in data.get('messages', []):
        if msg.get('type') != 'message':
            continue
        cleaned = clean(extract_text(msg.get('text', '')))
        if cleaned:
            texts.append(cleaned)

    if not texts:
        sys.exit('error: no text messages found in the export file')

    combined = ' '.join(texts)
    stopwords_set = set(stopwords.words('english')) | set(stopwords.words('russian'))
    words = nltk.word_tokenize(combined)
    filtered = [w.lower() for w in words if w.isalpha() and w.lower() not in stopwords_set]

    if not filtered:
        sys.exit('error: no words remain after filtering stopwords')

    fdist = nltk.FreqDist(filtered)
    frequencies = dict(fdist.most_common(args.num_words))

    wc = WordCloud(width=args.width, height=args.height, background_color='black')
    wc.generate_from_frequencies(frequencies)
    wc.to_file(args.output)
    print(f'saved to {args.output}')


if __name__ == '__main__':
    main()
