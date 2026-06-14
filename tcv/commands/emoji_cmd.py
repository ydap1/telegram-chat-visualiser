from __future__ import annotations

import re
import sys
from collections import Counter

import matplotlib.pyplot as plt

from tcv import style
from tcv.parser import Message

# Covers the vast majority of emoji Unicode blocks
_EMOJI_RE = re.compile(
    r'[\U0001F300-\U0001F9FF'
    r'\U0001FA00-\U0001FAFF'
    r'\U00002600-\U000027BF'
    r'\U00002300-\U000023FF]',
    flags=re.UNICODE,
)


def extract(messages: list[Message]) -> Counter:
    counts: Counter[str] = Counter()
    for m in messages:
        if m.type == 'message':
            counts.update(_EMOJI_RE.findall(m.text))
    return counts


def make_figure(counts: Counter, n: int = 30) -> plt.Figure:
    style.apply()

    top = counts.most_common(n)
    if not top:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'no emoji found', ha='center', va='center', transform=ax.transAxes)
        return fig

    emojis = [e for e, _ in top]
    vals = [c for _, c in top]

    fig, ax = plt.subplots(figsize=(max(10, n * 0.4), 5))
    bars = ax.bar(range(len(emojis)), vals, color=style.PALETTE[0], alpha=0.85)

    ax.set_xticks(range(len(emojis)))
    ax.set_xticklabels(emojis, fontsize=14)
    ax.set_ylabel('count')
    ax.set_title(f'Top {n} emoji')
    ax.grid(axis='y', alpha=0.4)

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.01,
                str(val), ha='center', va='bottom', fontsize=7, color=style.MUTED)

    fig.tight_layout()
    return fig


def register(sub) -> None:
    p = sub.add_parser('emoji', help='emoji frequency analysis')
    p.add_argument('input_file', help='Telegram JSON export')
    p.add_argument('-n', '--top', type=int, default=30,
                   help='number of top emoji to show (default: 30)')
    p.add_argument('-o', '--output', default='emoji.png',
                   help='output PNG path (default: emoji.png)')
    p.set_defaults(func=run)


def run(args) -> None:
    from tcv.parser import load
    messages, _ = load(args.input_file)
    counts = extract(messages)

    if not counts:
        sys.exit('error: no emoji found in messages')

    print(f'Found {len(counts)} unique emoji, {sum(counts.values())} total')
    for emoji, count in counts.most_common(10):
        print(f'  {emoji}  {count}')

    fig = make_figure(counts, n=args.top)
    fig.savefig(args.output)
    plt.close(fig)
    print(f'saved to {args.output}')
