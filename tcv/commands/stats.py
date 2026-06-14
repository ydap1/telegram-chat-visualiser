from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict

from tcv import nlp
from tcv.parser import Message


def compute(messages: list[Message]) -> list[dict]:
    nlp.ensure_nltk_data()
    stop = nlp.stopword_set()

    senders = sorted({m.sender for m in messages if m.type == 'message'})
    rows = []

    for sender in senders:
        msgs = [m for m in messages if m.type == 'message' and m.sender == sender]
        voice = [m for m in msgs if m.media_type == 'voice_message']
        media = [m for m in msgs if m.media_type and m.media_type != 'voice_message']
        replies = [m for m in msgs if m.reply_to_id is not None]

        words_all: list[str] = []
        for m in msgs:
            words_all.extend(nlp.tokenize_and_filter(nlp.clean(m.text), stop))

        word_counts = Counter(words_all)
        top_word = word_counts.most_common(1)[0][0] if word_counts else '—'

        total_words = sum(len(nlp.tokenize_and_filter(nlp.clean(m.text), {})) for m in msgs)
        avg_words = round(total_words / len(msgs), 1) if msgs else 0

        hour_counts: Counter[int] = Counter(m.date.hour for m in msgs)
        peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0

        voice_secs = sum(m.duration_seconds or 0 for m in voice)

        rows.append({
            'sender': sender,
            'messages': len(msgs),
            'words': total_words,
            'avg_words': avg_words,
            'unique_words': len(word_counts),
            'media': len(media),
            'voice': len(voice),
            'voice_min': round(voice_secs / 60, 1),
            'replies': len(replies),
            'peak_hour': f'{peak_hour:02d}:00',
            'top_word': top_word,
        })

    rows.sort(key=lambda r: r['messages'], reverse=True)
    return rows


def _print_table(rows: list[dict], chat_name: str, messages: list[Message]) -> None:
    try:
        from tabulate import tabulate
        use_tabulate = True
    except ImportError:
        use_tabulate = False

    text_msgs = [m for m in messages if m.type == 'message']
    if not text_msgs:
        sys.exit('error: no messages found')

    dates = [m.date for m in text_msgs]
    span = (max(dates) - min(dates)).days + 1

    print(f'\nChat: {chat_name}')
    print(f'Period: {min(dates).date()} → {max(dates).date()} ({span} days)')
    print(f'Total messages: {len(text_msgs):,}')
    print()

    headers = ['sender', 'msgs', 'words', 'avg', 'vocab', 'media', 'voice', 'voice min',
               'replies', 'peak', 'top word']
    table = [
        [
            r['sender'][:28],
            f"{r['messages']:,}",
            f"{r['words']:,}",
            r['avg_words'],
            f"{r['unique_words']:,}",
            r['media'],
            r['voice'],
            r['voice_min'],
            r['replies'],
            r['peak_hour'],
            r['top_word'],
        ]
        for r in rows
    ]

    if use_tabulate:
        print(tabulate(table, headers=headers, tablefmt='rounded_outline'))
    else:
        print('\t'.join(headers))
        for row in table:
            print('\t'.join(str(c) for c in row))


def register(sub) -> None:
    p = sub.add_parser('stats', help='per-person message statistics')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('--csv', dest='csv_output', metavar='FILE',
                   help='also save stats as a CSV file')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, chat_name = load(args.input_file)
    rows = compute(messages)

    if not rows:
        sys.exit('error: no messages found')

    _print_table(rows, chat_name, messages)

    if args.csv_output:
        with open(args.csv_output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f'\nCSV saved to {args.csv_output}')
