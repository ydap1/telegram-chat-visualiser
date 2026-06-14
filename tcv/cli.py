from __future__ import annotations

import argparse
import sys


def main() -> None:
    p = argparse.ArgumentParser(
        prog='tcv',
        description='Generate a Telegram chat analytics dashboard',
    )
    p.add_argument('input', help='export directory (HTML) or result.json file')
    p.add_argument('-o', '--output', default='dashboard.html',
                   help='output HTML path (default: dashboard.html)')
    p.add_argument('-n', '--num-words', type=int, default=150, dest='num_words',
                   help='words in the word cloud image (default: 150)')
    args = p.parse_args()

    from tcv.parser import load
    from tcv.dashboard import generate

    print(f'Loading {args.input} ...')
    messages, chat_name = load(args.input)

    text_count = sum(1 for m in messages if m.type == 'message')
    if not text_count:
        sys.exit('error: no messages found')
    print(f'Loaded {text_count:,} messages. Generating dashboard ...')

    html = generate(messages, chat_name, num_words=args.num_words)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Saved → {args.output}')


if __name__ == '__main__':
    main()
