from __future__ import annotations

import re
import sys
from collections import Counter

from wordcloud import WordCloud

from tcv import nlp, style
from tcv.parser import Message


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-.]', '_', name)


def build_frequencies(messages: list[Message], stop: set[str]) -> Counter:
    texts = [nlp.clean(m.text) for m in messages if m.type == 'message' and m.text]
    if not texts:
        return Counter()
    words = nlp.tokenize_and_filter(' '.join(texts), stop)
    return Counter(words)


def make_cloud(frequencies: Counter, width: int, height: int, num_words: int) -> WordCloud:
    wc = WordCloud(
        width=width,
        height=height,
        background_color='black',
        colormap='cool',
        max_words=num_words,
    )
    wc.generate_from_frequencies(dict(frequencies.most_common(num_words)))
    return wc


def register(sub) -> None:
    p = sub.add_parser('wordcloud', help='generate a word cloud from chat messages')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('-n', '--num-words', type=int, default=150, dest='num_words',
                   help='number of words to display (default: 150)')
    p.add_argument('-W', '--width', type=int, default=1280,
                   help='image width in pixels (default: 1280)')
    p.add_argument('-H', '--height', type=int, default=720,
                   help='image height in pixels (default: 720)')
    p.add_argument('-o', '--output', default='wordcloud.png',
                   help='output PNG path (default: wordcloud.png)')
    p.add_argument('--by-person', action='store_true', dest='by_person',
                   help='generate a separate word cloud for each sender')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load

    nlp.ensure_nltk_data()
    style.apply()

    messages, chat_name = load(args.input_file)
    stop = nlp.stopword_set()

    if args.by_person:
        by_sender: dict[str, list[Message]] = {}
        for m in messages:
            if m.type == 'message':
                by_sender.setdefault(m.sender, []).append(m)

        generated = []
        for sender, msgs in by_sender.items():
            freq = build_frequencies(msgs, stop)
            if not freq:
                continue
            wc = make_cloud(freq, args.width, args.height, args.num_words)
            base = args.output.rsplit('.', 1)
            ext = base[1] if len(base) > 1 else 'png'
            out = f'{base[0]}_{_sanitize_filename(sender)}.{ext}'
            wc.to_file(out)
            generated.append(out)

        if not generated:
            sys.exit('error: no text messages found')
        for path in generated:
            print(f'saved {path}')
    else:
        freq = build_frequencies(messages, stop)
        if not freq:
            sys.exit('error: no words remain after filtering')
        wc = make_cloud(freq, args.width, args.height, args.num_words)
        wc.to_file(args.output)
        print(f'saved to {args.output}')
